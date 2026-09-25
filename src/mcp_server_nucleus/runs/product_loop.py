from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import subprocess
import threading
import types
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Callable
from urllib.parse import unquote, urlparse

from .dispatcher import RunDispatcher
from .models import ProductCaseState, RunState
from .service import RunService
from .store import ActiveProductCaseExists, RunStore
from .verification import VerificationBundle
from .verifiers import CommandVerifier


_TERMINAL_RUN_STATES = frozenset(
    {
        RunState.READY_FOR_REVIEW,
        RunState.APPLIED,
        RunState.COMPLETED,
        RunState.FAILED,
        RunState.CANCELLED,
        RunState.DISMISSED,
        RunState.PREVIEWED,
    }
)
_ELIGIBLE_RUN_STATES = frozenset({RunState.READY_FOR_REVIEW, RunState.APPLIED})
_FAILURE_OWNERS = frozenset({"PRODUCT", "MODEL", "ENVIRONMENT", "CONTRACT", "TASK", "HUMAN"})
_OUTPUT_LIMIT = 8192
_GIT_TIMEOUT = 10
_CHALLENGE_TTL_MINUTES = 10

_SAFETY_REASONS = frozenset(
    {
        "PATCH_MISSING",
        "PATCH_INTEGRITY_FAILED",
        "PATCH_PATH_UNSAFE",
        "PATCH_OUT_OF_SCOPE",
        "PATCH_GIT_PARSE_ERROR",
        "PATCH_GIT_TIMEOUT",
        "PATCH_GIT_LAUNCH_ERROR",
        "PATCH_RENAME_OR_COPY",
        "PATCH_MODE_CHANGE",
        "BUNDLE_BASE_REVISION_MISMATCH",
        "BUNDLE_BASE_REVISION_MISSING",
        "RUN_ROUTE_MISMATCH",
        "RUN_ROUTE_MISSING",
        "RUN_BASE_REVISION_MISMATCH",
    }
)


def _canonical(path: str | Path) -> str:
    return str(Path(path).expanduser().resolve(strict=False))


def _project_root(root_uri: str) -> str:
    parsed = urlparse(root_uri)
    if parsed.scheme != "file":
        raise ValueError("RUN_PROJECT_NOT_LOCAL")
    return _canonical(unquote(parsed.path))


def _strict_nonnegative_int(value: Any, name: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"INVALID_{name.upper()}")
    return value


def _strict_bool(value: Any, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"INVALID_{name.upper()}")
    return value


def _strict_positive_int(value: Any, name: str) -> int:
    if type(value) is not int or value <= 0:
        raise ValueError(f"INVALID_{name.upper()}")
    return value


def _requirements(run: Any) -> dict[str, Any]:
    try:
        value = json.loads(run.requirements)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("RUN_REQUIREMENTS_INVALID") from exc
    if not isinstance(value, dict) or not isinstance(value.get("check"), dict):
        raise ValueError("RUN_REQUIREMENTS_INVALID")
    return value["check"]


def _json_value(value: Any) -> Any:
    if hasattr(value, "value"):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    return value


class ProductLoopController:
    def __init__(
        self,
        store: RunStore,
        db_path: str | Path,
        product_root: str | Path,
        dispatch: Callable[[str], Any] | None = None,
        dispatch_timeout: float | None = None,
    ) -> None:
        self.store = store
        self.db_path = Path(db_path)
        self.product_root = _canonical(product_root)
        self.service = RunService(store)
        raw_dispatch = dispatch or (lambda run_id: RunDispatcher(self.db_path).run_once(run_id=run_id))
        if dispatch_timeout is not None and dispatch_timeout > 0:
            def _timed_dispatch(run_id: str) -> Any:
                result: list[Any] = []
                errors: list[Exception] = []
                def _worker():
                    try:
                        result.append(raw_dispatch(run_id))
                    except Exception as e:
                        errors.append(e)

                thread = threading.Thread(
                    target=_worker,
                    daemon=True,
                )
                thread.daemon = True
                thread.start()
                thread.join(timeout=dispatch_timeout)
                if thread.is_alive():
                    raise TimeoutError(f"DISPATCH_TIMEOUT after {dispatch_timeout}s for run {run_id}")
                if errors:
                    raise errors[0]
                return result[0] if result else None
            self.dispatch = _timed_dispatch
        else:
            self.dispatch = raw_dispatch
        self._decision_lock = threading.RLock()

    def _case(self, case_id: str, state: ProductCaseState | None = None):
        case = self.store.get_product_case(case_id)
        if state is not None and case.state is not state:
            raise ValueError(f"CASE_STATE_{case.state.value.upper()}")
        return case

    def _contract(self, case: Any) -> dict[str, Any]:
        try:
            contract = json.loads(case.contract_json)
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError("CONTRACT_INVALID") from exc
        if not isinstance(contract, dict):
            raise ValueError("CONTRACT_INVALID")
        return contract

    def _audit(self, case_id: str, event_type: str, payload: dict[str, Any]) -> None:
        self.store.append_product_case_event(case_id, event_type, payload)

    def _git_snapshot(self, project_root: str) -> str:
        root = Path(project_root)
        try:
            head = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ValueError("GIT_HEAD_UNAVAILABLE") from exc
        if head.returncode != 0 or not head.stdout.strip():
            raise ValueError("GIT_HEAD_UNAVAILABLE")
        try:
            status = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ValueError("GIT_STATUS_UNAVAILABLE") from exc
        if status.returncode != 0:
            raise ValueError("GIT_STATUS_UNAVAILABLE")
        if status.stdout.strip():
            raise ValueError("DIRTY_PROJECT_ROOT")
        return head.stdout.strip()

    def _git_is_ancestor(self, ancestor: str, descendant: str, root: str) -> bool:
        try:
            probe = subprocess.run(
                ["git", "merge-base", "--is-ancestor", ancestor, descendant],
                cwd=root,
                capture_output=True,
                timeout=_GIT_TIMEOUT,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return False
        return probe.returncode == 0

    def _git_parse_patch_paths(
        self,
        patch: bytes,
        project_root: str,
        permitted_paths: list[str] | None,
    ) -> list[str]:
        try:
            numstat = subprocess.run(
                ["git", "apply", "--numstat", "-z", "--"],
                input=patch,
                cwd=project_root,
                capture_output=True,
                timeout=_GIT_TIMEOUT,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise ValueError("PATCH_GIT_TIMEOUT") from exc
        except (OSError, FileNotFoundError) as exc:
            raise ValueError("PATCH_GIT_LAUNCH_ERROR") from exc
        if numstat.returncode != 0:
            raise ValueError("PATCH_GIT_PARSE_ERROR")
        try:
            summary = subprocess.run(
                ["git", "apply", "--summary", "--"],
                input=patch,
                cwd=project_root,
                capture_output=True,
                timeout=_GIT_TIMEOUT,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise ValueError("PATCH_GIT_TIMEOUT") from exc
        except (OSError, FileNotFoundError) as exc:
            raise ValueError("PATCH_GIT_LAUNCH_ERROR") from exc
        if summary.returncode != 0:
            raise ValueError("PATCH_GIT_PARSE_ERROR")
        for line in summary.stdout.decode("utf-8", errors="replace").splitlines():
            stripped = line.strip()
            if stripped.startswith("rename ") or stripped.startswith("copy "):
                raise ValueError("PATCH_RENAME_OR_COPY")
            if stripped.startswith("mode change"):
                raise ValueError("PATCH_MODE_CHANGE")
        parts = numstat.stdout.split(b"\x00")
        changed: list[str] = []
        for part in parts:
            if not part:
                continue
            if b"\t" in part:
                fields = part.split(b"\t", 2)
                if len(fields) < 3:
                    raise ValueError("PATCH_GIT_PARSE_ERROR")
                path_bytes = fields[2]
            else:
                path_bytes = part
            path_str = path_bytes.decode("utf-8", errors="replace")
            if "\x00" in path_str or "\\" in path_str:
                raise ValueError("PATCH_PATH_UNSAFE")
            path = PurePosixPath(path_str)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError("PATCH_PATH_UNSAFE")
            normalized = str(path)
            if normalized in {"", "."}:
                raise ValueError("PATCH_PATH_UNSAFE")
            changed.append(normalized)
        if not changed:
            raise ValueError("PATCH_GIT_PARSE_ERROR")
        if permitted_paths is not None:
            root = Path(project_root)
            for changed_path in changed:
                allowed = False
                for permitted in permitted_paths:
                    target = root / permitted
                    if changed_path == permitted or (target.is_dir() and changed_path.startswith(f"{permitted}/")):
                        allowed = True
                        break
                if not allowed:
                    raise ValueError("PATCH_OUT_OF_SCOPE")
        return changed

    def _validate_run_contract(
        self,
        case: Any,
        run_id: str,
        baseline: Any | None = None,
    ) -> tuple[Any, Any, dict[str, Any]]:
        contract = self._contract(case)
        run = self.store.get_run(run_id)
        project = self.store.get_project_for_run(run_id)
        if _project_root(project.root_uri) != contract["project_root"]:
            raise ValueError("RUN_PROJECT_MISMATCH")
        if run.prompt != contract["goal"]:
            raise ValueError("RUN_GOAL_MISMATCH")
        check = _requirements(run)
        if check.get("argv") != contract["acceptance_check"]:
            raise ValueError("RUN_CHECK_MISMATCH")
        if run.base_revision != contract["base_revision"]:
            # Replay runs of a self-evolving case launch on the improved HEAD,
            # a descendant of the contract base — that is the expected shape.
            if not (
                baseline is not None
                and _canonical(self.product_root) == _canonical(contract["project_root"])
                and self._git_is_ancestor(
                    contract["base_revision"], run.base_revision, contract["project_root"]
                )
            ):
                raise ValueError("RUN_BASE_REVISION_MISMATCH")
        if baseline is not None:
            baseline_project = self.store.get_project_for_run(baseline.id)
            if run.id == baseline.id:
                raise ValueError("REPLAY_RUN_NOT_DISTINCT")
            identity = ("runner_id", "execution_target", "mode")
            if any(getattr(run, key) != getattr(baseline, key) for key in identity):
                raise ValueError("REPLAY_IDENTITY_MISMATCH")
            if project.trust_mode != baseline_project.trust_mode:
                raise ValueError("REPLAY_TRUST_MISMATCH")
            if check.get("timeout") != _requirements(baseline).get("timeout"):
                raise ValueError("REPLAY_CHECK_TIMEOUT_MISMATCH")
            baseline_bundle = self.service.get_run_bundle(baseline.id)
            replay_bundle = self.service.get_run_bundle(run.id)
            baseline_route = baseline_bundle.route if isinstance(baseline_bundle.route, dict) else {}
            replay_route = replay_bundle.route if isinstance(replay_bundle.route, dict) else {}
            # A baseline that died before verification leaves no bundle route;
            # persisted-field identity above already proves sameness, so only
            # compare captured routes when both exist.
            if baseline_route and replay_route and baseline_route != replay_route:
                raise ValueError("REPLAY_ACTUAL_ROUTE_MISMATCH")
            if run.model_id and run.model_id != replay_route.get("model"):
                raise ValueError("REPLAY_ROUTE_MODEL_MISMATCH")
        return run, project, check

    def _bundle_evidence(
        self,
        run: Any,
        project: Any,
        contract: dict[str, Any] | None,
        permitted_paths: list[str] | None,
    ) -> tuple[Any, bytes | None, list[str], str | None]:
        bundle = self.service.get_run_bundle(run.id)
        reasons: list[str] = []
        patch: bytes | None = None
        patch_sha: str | None = None
        if bundle.patch is None or bundle.patch.size <= 0:
            reasons.append("PATCH_MISSING")
        else:
            try:
                patch = VerificationBundle.read_artifact(bundle.patch)
            except ValueError:
                reasons.append("PATCH_INTEGRITY_FAILED")
            if patch is not None and not patch:
                reasons.append("PATCH_MISSING")
            elif patch:
                patch_sha = hashlib.sha256(patch).hexdigest()
                try:
                    self._git_parse_patch_paths(
                        patch,
                        contract["project_root"] if contract is not None else _project_root(project.root_uri),
                        permitted_paths,
                    )
                except ValueError as exc:
                    reasons.append(str(exc))
        route = bundle.route if isinstance(bundle.route, dict) else {}
        if not route:
            reasons.append("RUN_ROUTE_MISSING")
        else:
            if route.get("vendor") != run.runner_id:
                reasons.append("RUN_ROUTE_MISMATCH")
            if route.get("execution_target") != run.execution_target:
                reasons.append("RUN_ROUTE_MISMATCH")
            if route.get("policy") != project.trust_mode:
                reasons.append("RUN_ROUTE_MISMATCH")
            if run.model_id and route.get("model") != run.model_id:
                reasons.append("RUN_ROUTE_MISMATCH")
        if contract is not None:
            if bundle.base_revision is None:
                reasons.append("BUNDLE_BASE_REVISION_MISSING")
            elif bundle.base_revision != contract["base_revision"]:
                reasons.append("BUNDLE_BASE_REVISION_MISMATCH")
        return bundle, patch, reasons, patch_sha

    def _outcome(self, case: Any, run: Any, project: Any, accepted: bool, human_interventions: int) -> dict[str, Any]:
        contract = self._contract(case)
        bundle, patch, reasons, _ = self._bundle_evidence(run, project, contract, contract["permitted_paths"])
        safety_reasons = [r for r in reasons if r in _SAFETY_REASONS]
        eligible = (
            patch is not None
            and not reasons
            and bundle.verdict == "ok"
            and bundle.apply_eligible is True
            and run.state in _ELIGIBLE_RUN_STATES
        )
        if eligible:
            verdict = "ok"
        elif reasons:
            verdict = reasons[0]
        elif run.state not in _ELIGIBLE_RUN_STATES:
            verdict = "RUN_NOT_REVIEWABLE"
        elif bundle.verdict != "ok":
            verdict = f"BUNDLE_{str(bundle.verdict).upper()}"
        elif bundle.apply_eligible is not True:
            verdict = "BUNDLE_NOT_APPLY_ELIGIBLE"
        else:
            verdict = "OUTCOME_NOT_ELIGIBLE"
        return {
            "contract_sha256": case.contract_sha256,
            "verdict": verdict,
            "apply_eligible": eligible,
            "accepted": accepted,
            "human_interventions": human_interventions,
            "safety_violations": len(safety_reasons),
        }

    def _run_regression(self, case_id: str, regression_argv: list[str], timeout: int) -> dict[str, Any]:
        argv_hash = hashlib.sha256(
            json.dumps(regression_argv, separators=(",", ":"), ensure_ascii=False).encode()
        ).hexdigest()
        cancel_event = threading.Event()
        ctx = types.SimpleNamespace(
            workspace=types.SimpleNamespace(target_path=str(self.product_root)),
            cancel_event=cancel_event,
        )
        verifier = CommandVerifier(
            "regression",
            regression_argv,
            timeout=timeout,
            cancel_event=cancel_event,
        )
        result = verifier.verify(ctx)
        output = (result.output or b"")[:_OUTPUT_LIMIT]
        payload: dict[str, Any] = {
            "argv_sha256": argv_hash,
            "status": result.status,
            "rc": result.exit_code,
            "output": output.decode("utf-8", errors="replace"),
        }
        self._audit(case_id, "product_case.improvement_regression", payload)
        if result.status != "ok":
            raise ValueError(f"REGRESSION_{result.status.upper()}")
        return payload

    def _validate_hook_event(self, hook_event: Any, case_id: str, challenge: str, accepted: bool) -> dict[str, Any]:
        if not isinstance(hook_event, dict):
            raise ValueError("INVALID_HOOK_EVENT")
        if hook_event.get("hook_event_name") != "UserPromptSubmit":
            raise ValueError("INVALID_HOOK_EVENT_NAME")
        session_id = hook_event.get("session_id")
        prompt_id = hook_event.get("prompt_id")
        prompt = hook_event.get("prompt")
        if not isinstance(session_id, str) or not session_id.strip():
            raise ValueError("INVALID_HOOK_SESSION")
        if not isinstance(prompt_id, str) or not prompt_id.strip():
            raise ValueError("INVALID_HOOK_PROMPT_ID")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("INVALID_HOOK_PROMPT")
        verb = "ACCEPT" if accepted else "REJECT"
        expected = f"NUCLEUS {verb} {case_id} {challenge}"
        if prompt != expected:
            raise ValueError("HOOK_PROMPT_MISMATCH")
        return {"session_id": session_id.strip(), "prompt_id": prompt_id.strip()}

    def _find_unconsumed_challenge(
        self,
        events: list[Any],
        requested_type: str,
        consumed_type: str,
    ) -> Any:
        consumed_hashes = {
            (event.payload if isinstance(event, dict) else event).get("challenge_sha256")
            for event in events
            if (event.get("type") if isinstance(event, dict) else event.type) == consumed_type
        }
        for event in reversed(events):
            event_type = event.get("type") if isinstance(event, dict) else event.type
            event_payload = event.get("payload", {}) if isinstance(event, dict) else event.payload
            if (
                event_type == requested_type
                and event_payload.get("challenge_sha256") not in consumed_hashes
            ):
                return event
        return None

    def initialize(self, project_root: str | Path) -> str:
        root = _canonical(project_root)
        active = self.store.get_active_product_case(root)
        if active is not None:
            if active.state is ProductCaseState.WAITING_FOR_GOAL:
                return active.id
            raise ActiveProductCaseExists(f"ACTIVE_CASE_{active.state.value.upper()}")
        return self.store.create_product_case(project_root=root).id

    def start_baseline(
        self,
        case_id: str,
        goal_source: str = "",
        goal: str = "",
        permitted_paths: list[str] | None = None,
        acceptance_check: list[str] | None = None,
        runner_id: str = "",
        model_id: str = "",
        execution_target: str = "in-process",
        trust_mode: str = "default",
        mode: str = "write",
        check_timeout: int = 300,
    ) -> str:
        if not runner_id:
            runner_id = os.environ.get("NUCLEUS_DEFAULT_RUNNER", "agy")
        case = self.store.get_product_case(case_id)
        if case.state is ProductCaseState.WAITING_FOR_GOAL:
            check_timeout = _strict_positive_int(check_timeout, "check_timeout")
            ok, reason = self.service.preflight(case.project_root, runner_id, acceptance_check)
            if not ok:
                raise ValueError(f"PREFLIGHT_FAILED:{reason}")
            base_revision = self._git_snapshot(case.project_root)
            contract = {
                "goal_source": goal_source,
                "goal": goal,
                "project_root": case.project_root,
                "base_revision": base_revision,
                "permitted_paths": permitted_paths or [],
                "acceptance_check": acceptance_check or [],
                "human_acceptance_required": True,
            }
            case = self.store.transition_product_case(
                case.id, ProductCaseState.WAITING_FOR_GOAL, {"contract": contract}
            )
        elif case.state is ProductCaseState.CONTRACTED:
            contract = self._contract(case)
            if goal_source and goal_source != contract["goal_source"]:
                raise ValueError("CONTRACTED_RETRY_GOAL_SOURCE_MISMATCH")
            if goal and goal != contract["goal"]:
                raise ValueError("CONTRACTED_RETRY_GOAL_MISMATCH")
            if permitted_paths and permitted_paths != contract["permitted_paths"]:
                raise ValueError("CONTRACTED_RETRY_FILES_MISMATCH")
            if acceptance_check and acceptance_check != contract["acceptance_check"]:
                raise ValueError("CONTRACTED_RETRY_CHECK_MISMATCH")
            check_timeout = _strict_positive_int(check_timeout, "check_timeout")
            ok, reason = self.service.preflight(case.project_root, runner_id, acceptance_check)
            if not ok:
                raise ValueError(f"PREFLIGHT_FAILED:{reason}")
        elif case.state is ProductCaseState.BASELINE_RUNNING:
            if not case.baseline_run_id:
                raise ValueError("BASELINE_RUNNING_WITHOUT_RUN")
            contract = self._contract(case)
            check_timeout = _strict_positive_int(check_timeout, "check_timeout")
        else:
            raise ValueError(f"CASE_STATE_{case.state.value.upper()}")
        contract = self._contract(case)
        if case.baseline_run_id:
            try:
                existing = self.store.get_run(case.baseline_run_id)
            except Exception:
                existing = None
            if existing is not None and existing.state is RunState.QUEUED:
                try:
                    self.dispatch(case.baseline_run_id)
                except Exception as exc:
                    self._audit(
                        case.id,
                        "product_case.baseline_dispatch_failed",
                        {"run_id": case.baseline_run_id, "error": type(exc).__name__},
                    )
                    raise
                return case.baseline_run_id
            raise ValueError("BASELINE_RUN_ALREADY_LINKED")
        try:
            run_id, reason = self.service.submit_run(
                project_root=case.project_root,
                prompt=contract["goal"],
                runner_id=runner_id,
                model_id=model_id,
                execution_target=execution_target,
                mode=mode,
                trust_mode=trust_mode,
                check_argv=contract["acceptance_check"],
                check_timeout=check_timeout,
            )
        except Exception as exc:
            self._audit(case.id, "product_case.baseline_submit_failed", {"error": type(exc).__name__})
            raise
        if run_id is None:
            self._audit(case.id, "product_case.baseline_submit_failed", {"reason": reason or "unknown"})
            raise ValueError(f"BASELINE_SUBMIT_FAILED:{reason or 'unknown'}")
        self.store.transition_product_case(case.id, ProductCaseState.CONTRACTED, {"baseline_run_id": run_id})
        try:
            self.dispatch(run_id)
        except Exception as exc:
            self._audit(
                case.id,
                "product_case.baseline_dispatch_failed",
                {"run_id": run_id, "error": type(exc).__name__},
            )
            raise
        return run_id

    def evaluate_baseline(
        self,
        case_id: str,
        accepted: bool,
        human_interventions: int,
        failure_owner: str | None = None,
        friction: str | None = None,
        baseline_decision_event_seq: int | None = None,
    ) -> dict[str, Any]:
        accepted = _strict_bool(accepted, "accepted")
        human_interventions = _strict_nonnegative_int(human_interventions, "human_interventions")
        case = self._case(case_id, ProductCaseState.BASELINE_RUNNING)
        run = self.store.get_run(case.baseline_run_id)
        if run.state not in _TERMINAL_RUN_STATES:
            raise ValueError("BASELINE_RUN_NOT_TERMINAL")
        run, project, _ = self._validate_run_contract(case, run.id)
        outcome = self._outcome(case, run, project, accepted, human_interventions)
        if accepted:
            if baseline_decision_event_seq is None:
                raise ValueError("BASELINE_ACCEPTANCE_REQUIRES_HOOK")
            events = self.store.list_product_case_events(case.id)
            review_event = None
            for event in events:
                if event.seq == baseline_decision_event_seq:
                    review_event = event
                    break
            if review_event is None:
                raise ValueError("BASELINE_DECISION_EVENT_NOT_FOUND")
            if review_event.type != "product_case.baseline_decision_observed":
                raise ValueError("BASELINE_DECISION_EVENT_WRONG_TYPE")
            payload = review_event.payload
            required_keys = {"source", "session_id", "prompt_id", "challenge_sha256", "accepted"}
            if set(payload.keys()) != required_keys:
                raise ValueError("BASELINE_DECISION_EVENT_INVALID_PAYLOAD")
            if payload["source"] != "user_prompt":
                raise ValueError("BASELINE_DECISION_EVENT_INVALID_SOURCE")
            if payload["accepted"] is not True:
                raise ValueError("BASELINE_DECISION_EVENT_NOT_ACCEPTED")
            for key in ("session_id", "prompt_id", "challenge_sha256"):
                value = payload[key]
                if not isinstance(value, str) or not value.strip() or "\x00" in value:
                    raise ValueError("BASELINE_DECISION_EVENT_INVALID_PAYLOAD")
            requested = self._find_unconsumed_challenge(
                events,
                "product_case.baseline_decision_requested",
                "product_case.baseline_decision_consumed",
            )
            if requested is None:
                raise ValueError("BASELINE_CHALLENGE_ALREADY_CONSUMED")
            if not hmac.compare_digest(payload["challenge_sha256"], requested.payload.get("challenge_sha256", "")):
                raise ValueError("BASELINE_CHALLENGE_MISMATCH")
            try:
                expires_at = datetime.fromisoformat(requested.payload["expires_at"])
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError("BASELINE_CHALLENGE_INVALID") from exc
            if expires_at <= datetime.now(timezone.utc):
                raise ValueError("BASELINE_CHALLENGE_EXPIRED")
            if not outcome["apply_eligible"] or outcome["safety_violations"] or outcome["verdict"] != "ok":
                raise ValueError("BASELINE_NOT_ELIGIBLE")
            self.store.transition_product_case(
                case.id,
                ProductCaseState.BASELINE_RUNNING,
                {"baseline_outcome": outcome},
            )
            self._audit(
                case.id,
                "product_case.baseline_decision_consumed",
                {
                    "challenge_sha256": payload["challenge_sha256"],
                    "session_id": payload["session_id"],
                    "prompt_id": payload["prompt_id"],
                    "accepted": True,
                },
            )
        else:
            if failure_owner not in _FAILURE_OWNERS:
                raise ValueError("INVALID_FAILURE_OWNER")
            if not isinstance(friction, str) or not friction.strip() or "\x00" in friction:
                raise ValueError("INVALID_FRICTION")
            updates = {
                "baseline_outcome": outcome,
                "failure_owner": failure_owner,
                "friction": friction,
            }
            self.store.transition_product_case(case.id, ProductCaseState.BASELINE_RUNNING, updates)
        return outcome

    def request_baseline_decision(self, case_id: str) -> str:
        case = self._case(case_id, ProductCaseState.BASELINE_RUNNING)
        run = self.store.get_run(case.baseline_run_id)
        if run.state not in _TERMINAL_RUN_STATES:
            raise ValueError("BASELINE_RUN_NOT_TERMINAL")
        run, project, _ = self._validate_run_contract(case, run.id)
        outcome = self._outcome(case, run, project, True, 0)
        if not outcome["apply_eligible"] or outcome["safety_violations"] or outcome["verdict"] != "ok":
            raise ValueError("BASELINE_NOT_ELIGIBLE_FOR_DECISION")
        events = self.store.list_product_case_events(case.id)
        existing = self._find_unconsumed_challenge(
            events,
            "product_case.baseline_decision_requested",
            "product_case.baseline_decision_consumed",
        )
        if existing is not None:
            try:
                expires_at = datetime.fromisoformat(existing.payload["expires_at"])
                if expires_at > datetime.now(timezone.utc):
                    raise ValueError("BASELINE_CHALLENGE_ALREADY_PENDING")
            except KeyError:
                pass
            except TypeError:
                pass
            except ValueError as exc:
                if str(exc) == "BASELINE_CHALLENGE_ALREADY_PENDING":
                    raise
                pass
        challenge = secrets.token_urlsafe(24)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=_CHALLENGE_TTL_MINUTES)
        self._audit(
            case.id,
            "product_case.baseline_decision_requested",
            {
                "challenge_sha256": hashlib.sha256(challenge.encode()).hexdigest(),
                "expires_at": expires_at.isoformat(),
                "requested_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        return challenge

    def accept_baseline_from_user_prompt(
        self,
        case_id: str,
        challenge: str,
        hook_event: dict[str, Any],
    ) -> str:
        if not isinstance(challenge, str) or not challenge:
            raise ValueError("INVALID_CHALLENGE")
        case = self._case(case_id, ProductCaseState.BASELINE_RUNNING)
        hook_info = self._validate_hook_event(hook_event, case_id, challenge, True)
        events = self.store.list_product_case_events(case.id)
        requested = self._find_unconsumed_challenge(
            events,
            "product_case.baseline_decision_requested",
            "product_case.baseline_decision_consumed",
        )
        if requested is None:
            raise ValueError("BASELINE_CHALLENGE_ALREADY_CONSUMED")
        try:
            expires_at = datetime.fromisoformat(requested.payload["expires_at"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("BASELINE_CHALLENGE_INVALID") from exc
        if expires_at <= datetime.now(timezone.utc):
            raise ValueError("BASELINE_CHALLENGE_EXPIRED")
        supplied = hashlib.sha256(challenge.encode()).hexdigest()
        expected = requested.payload.get("challenge_sha256", "")
        if not hmac.compare_digest(supplied, expected):
            raise ValueError("BASELINE_CHALLENGE_MISMATCH")
        self._audit(
            case.id,
            "product_case.baseline_decision_observed",
            {
                "source": "user_prompt",
                "session_id": hook_info["session_id"],
                "prompt_id": hook_info["prompt_id"],
                "challenge_sha256": expected,
                "accepted": True,
            },
        )
        observed_event = self.store.list_product_case_events(case.id)[-1]
        outcome = self.evaluate_baseline(
            case_id,
            True,
            0,
            baseline_decision_event_seq=observed_event.seq,
        )
        return "baseline_accepted"

    def record_limitation(self, case_id: str) -> str:
        case = self._case(case_id, ProductCaseState.FRICTION_CLASSIFIED)
        if case.failure_owner == "PRODUCT":
            raise ValueError("PRODUCT_FRICTION_REQUIRES_IMPROVEMENT")
        return self.store.transition_product_case(case.id, ProductCaseState.FRICTION_CLASSIFIED, {}).state.value

    def attach_improvement(self, case_id: str, run_id: str) -> str:
        case = self._case(case_id, ProductCaseState.FRICTION_CLASSIFIED)
        if case.failure_owner != "PRODUCT":
            raise ValueError("NON_PRODUCT_FRICTION")
        if run_id == case.baseline_run_id:
            raise ValueError("IMPROVEMENT_RUN_NOT_DISTINCT")
        run = self.store.get_run(run_id)
        project = self.store.get_project_for_run(run_id)
        if _project_root(project.root_uri) != self.product_root:
            raise ValueError("IMPROVEMENT_PROJECT_MISMATCH")
        if run.state not in _ELIGIBLE_RUN_STATES:
            raise ValueError("IMPROVEMENT_RUN_NOT_REVIEWABLE")
        bundle, patch, reasons, _ = self._bundle_evidence(run, project, None, None)
        if patch is None or reasons or bundle.verdict != "ok" or bundle.apply_eligible is not True:
            raise ValueError(reasons[0] if reasons else "IMPROVEMENT_NOT_ELIGIBLE")
        self.store.transition_product_case(
            case.id, ProductCaseState.FRICTION_CLASSIFIED, {"improvement_run_id": run_id}
        )
        return run_id

    def approve_improvement(
        self,
        case_id: str,
        review_event_seq: int,
        regression_argv: list[str],
        timeout: int = 300,
    ) -> dict[str, Any]:
        case = self._case(case_id, ProductCaseState.IMPROVEMENT_RUNNING)
        timeout = _strict_positive_int(timeout, "timeout")
        if not isinstance(review_event_seq, int) or review_event_seq <= 0:
            raise ValueError("INVALID_REVIEW_EVENT_SEQ")
        events = self.store.list_product_case_events(case.id)
        improvement_attach_seq = 0
        review_event = None
        for event in events:
            if event.type == "product_case.improvement_running":
                improvement_attach_seq = max(improvement_attach_seq, event.seq)
            if event.seq == review_event_seq:
                review_event = event
        if review_event is None:
            raise ValueError("REVIEW_EVENT_NOT_FOUND")
        if review_event.type != "product_case.independent_review_observed":
            raise ValueError("REVIEW_EVENT_WRONG_TYPE")
        if improvement_attach_seq and review_event_seq <= improvement_attach_seq:
            raise ValueError("REVIEW_EVENT_BEFORE_IMPROVEMENT")
        payload = review_event.payload
        required_keys = {"source", "reviewer_vendor", "reviewer_model", "verdict", "patch_sha256", "capture_sha256"}
        if set(payload.keys()) != required_keys:
            raise ValueError("REVIEW_EVENT_INVALID_PAYLOAD")
        for key in required_keys:
            value = payload[key]
            if not isinstance(value, str) or not value.strip() or "\x00" in value:
                raise ValueError("REVIEW_EVENT_INVALID_PAYLOAD")
        if payload["source"] != "post_tool_use":
            raise ValueError("REVIEW_EVENT_INVALID_SOURCE")
        if payload["verdict"] != "SOUND":
            raise ValueError("REVIEW_EVENT_NOT_SOUND")
        run = self.store.get_run(case.improvement_run_id)
        if run.state is not RunState.APPLIED:
            raise ValueError("IMPROVEMENT_NOT_APPLIED")
        contract = self._contract(case)
        project = self.store.get_project_for_run(run.id)
        bundle, patch, reasons, patch_sha = self._bundle_evidence(run, project, None, None)
        if patch is None or reasons or bundle.verdict != "ok" or bundle.apply_eligible is not True:
            raise ValueError(reasons[0] if reasons else "IMPROVEMENT_NOT_ELIGIBLE")
        if not hmac.compare_digest(payload["patch_sha256"], patch_sha or ""):
            raise ValueError("REVIEW_PATCH_HASH_MISMATCH")
        if payload["reviewer_vendor"].strip().casefold() == run.runner_id.strip().casefold():
            raise ValueError("REVIEWER_NOT_INDEPENDENT")
        if not isinstance(regression_argv, list) or not regression_argv:
            raise ValueError("INVALID_REGRESSION_ARGV")
        if any(not isinstance(v, str) or not v for v in regression_argv):
            raise ValueError("INVALID_REGRESSION_ARGV")
        if regression_argv != contract["acceptance_check"]:
            raise ValueError("REGRESSION_ARGV_NOT_BOUND_TO_CONTRACT")
        self._run_regression(case_id, regression_argv, timeout)
        self.store.transition_product_case(
            case.id,
            ProductCaseState.IMPROVEMENT_RUNNING,
            {"independent_review": "SOUND", "regression_passed": True},
        )
        return {"status": "reviewed"}

    def start_replay(self, case_id: str) -> str:
        case = self._case(case_id, ProductCaseState.IMPROVEMENT_REVIEWED)
        contract = self._contract(case)
        head = self._git_snapshot(contract["project_root"])
        if head != contract["base_revision"]:
            # Self-evolution: when the product under improvement is also the
            # target repo, an applied improvement legitimately advances HEAD.
            # Replay is still meaningful if the contract base is an ancestor of
            # HEAD — the goal is then re-verified on the improved product.
            self_evolving = _canonical(self.product_root) == _canonical(
                contract["project_root"]
            )
            if not (
                self_evolving
                and self._git_is_ancestor(
                    contract["base_revision"], head, contract["project_root"]
                )
            ):
                raise ValueError("REPLAY_BASE_REVISION_CHANGED")
        baseline = self.store.get_run(case.baseline_run_id)
        baseline_project = self.store.get_project_for_run(baseline.id)
        check = _requirements(baseline)
        baseline_bundle = self.service.get_run_bundle(baseline.id)
        baseline_route = baseline_bundle.route if isinstance(baseline_bundle.route, dict) else {}
        try:
            run_id, reason = self.service.submit_run(
                project_root=contract["project_root"],
                prompt=contract["goal"],
                runner_id=baseline.runner_id,
                model_id=baseline.model_id,
                execution_target=baseline.execution_target,
                mode=baseline.mode,
                trust_mode=baseline_project.trust_mode,
                check_argv=contract["acceptance_check"],
                check_timeout=check.get("timeout", 300),
            )
        except Exception as exc:
            self._audit(case.id, "product_case.replay_submit_failed", {"error": type(exc).__name__})
            raise
        if run_id is None:
            self._audit(case.id, "product_case.replay_submit_failed", {"reason": reason or "unknown"})
            raise ValueError(f"REPLAY_SUBMIT_FAILED:{reason or 'unknown'}")
        if run_id == baseline.id:
            self._audit(case.id, "product_case.replay_submit_failed", {"reason": "not_distinct"})
            raise ValueError("REPLAY_RUN_NOT_DISTINCT")
        self.store.transition_product_case(
            case.id, ProductCaseState.IMPROVEMENT_REVIEWED, {"replay_run_id": run_id}
        )
        try:
            self.dispatch(run_id)
        except Exception as exc:
            self._audit(
                case.id,
                "product_case.replay_dispatch_failed",
                {"run_id": run_id, "error": type(exc).__name__},
            )
            raise
        return run_id

    def evaluate_replay(self, case_id: str, human_interventions: int) -> str:
        human_interventions = _strict_nonnegative_int(human_interventions, "human_interventions")
        case = self._case(case_id, ProductCaseState.REPLAY_RUNNING)
        replay = self.store.get_run(case.replay_run_id)
        if replay.state not in _TERMINAL_RUN_STATES:
            raise ValueError("REPLAY_RUN_NOT_TERMINAL")
        baseline = self.store.get_run(case.baseline_run_id)
        self._validate_run_contract(case, baseline.id)
        replay, project, _ = self._validate_run_contract(case, replay.id, baseline)
        outcome = self._outcome(case, replay, project, True, human_interventions)
        satisfied_clean = False
        if not outcome["apply_eligible"] or outcome["safety_violations"] or outcome["verdict"] != "ok":
            # Self-evolution: the applied improvement already delivered the
            # goal on the product, so a clean replay whose check passes is the
            # terminal success signal — nothing remains to patch.
            contract = self._contract(case)
            bundle = self.service.get_run_bundle(replay.id)
            _, _, replay_reasons, _ = self._bundle_evidence(
                replay, project, contract, contract["permitted_paths"]
            )
            satisfied_clean = (
                _canonical(self.product_root) == _canonical(contract["project_root"])
                and replay.state in _TERMINAL_RUN_STATES
                and bundle.is_clean
                and bundle.verdict == "ok"
                and set(replay_reasons)
                <= {"PATCH_MISSING", "BUNDLE_BASE_REVISION_MISMATCH"}
            )
            if not satisfied_clean:
                raise ValueError("REPLAY_NOT_ELIGIBLE")
            outcome["verdict"] = "ok"
            self._audit(
                case.id,
                "product_case.replay_self_evolution_satisfied",
                {"replay_run_id": replay.id, "is_clean": True},
            )
        updates = {"replay_outcome": outcome}
        if satisfied_clean:
            updates["self_evolution_satisfied"] = True
        self.store.transition_product_case(
            case.id, ProductCaseState.REPLAY_RUNNING, updates
        )
        return "human_review"

    def request_decision(self, case_id: str) -> str:
        with self._decision_lock:
            case = self._case(case_id, ProductCaseState.HUMAN_REVIEW)
            events = self.store.list_product_case_events(case.id)
            existing = self._find_unconsumed_challenge(
                events,
                "product_case.human_decision_requested",
                "product_case.human_decision_consumed",
            )
            if existing is not None:
                try:
                    expires_at = datetime.fromisoformat(existing.payload["expires_at"])
                    if expires_at > datetime.now(timezone.utc):
                        raise ValueError("CHALLENGE_ALREADY_PENDING")
                except KeyError:
                    pass
                except TypeError:
                    pass
                except ValueError as exc:
                    if str(exc) == "CHALLENGE_ALREADY_PENDING":
                        raise
                    pass
            challenge = secrets.token_urlsafe(24)
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=_CHALLENGE_TTL_MINUTES)
            self._audit(
                case.id,
                "product_case.human_decision_requested",
                {
                    "challenge_sha256": hashlib.sha256(challenge.encode()).hexdigest(),
                    "expires_at": expires_at.isoformat(),
                    "requested_at": datetime.now(timezone.utc).isoformat(),
                },
            )
            return challenge

    def decide_from_user_prompt(
        self,
        case_id: str,
        challenge: str,
        accepted: bool,
        hook_event: dict[str, Any],
    ) -> str:
        accepted = _strict_bool(accepted, "accepted")
        if not isinstance(challenge, str) or not challenge:
            raise ValueError("INVALID_CHALLENGE")
        hook_info = self._validate_hook_event(hook_event, case_id, challenge, accepted)
        with self._decision_lock:
            case = self._case(case_id, ProductCaseState.HUMAN_REVIEW)
            events = self.store.list_product_case_events(case.id)
            requested = self._find_unconsumed_challenge(
                events,
                "product_case.human_decision_requested",
                "product_case.human_decision_consumed",
            )
            if requested is None:
                raise ValueError("CHALLENGE_ALREADY_CONSUMED")
            try:
                expires_at = datetime.fromisoformat(requested.payload["expires_at"])
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError("CHALLENGE_INVALID") from exc
            if expires_at <= datetime.now(timezone.utc):
                raise ValueError("CHALLENGE_EXPIRED")
            supplied = hashlib.sha256(challenge.encode()).hexdigest()
            expected = requested.payload.get("challenge_sha256", "")
            if not hmac.compare_digest(supplied, expected):
                raise ValueError("CHALLENGE_MISMATCH")
            result = self.store.transition_product_case(
                case.id,
                ProductCaseState.HUMAN_REVIEW,
                {"human_accepted": accepted},
            )
            self._audit(
                case.id,
                "product_case.human_decision_consumed",
                {
                    "challenge_sha256": expected,
                    "accepted": accepted,
                    "session_id": hook_info["session_id"],
                    "prompt_id": hook_info["prompt_id"],
                },
            )
            return result.state.value

    def status(self, case_id: str | None = None, project_root: str | Path | None = None) -> dict[str, Any]:
        if case_id is not None:
            case = self.store.get_product_case(case_id)
        elif project_root is not None:
            case = self.store.get_active_product_case(_canonical(project_root))
            if case is None:
                raise ValueError("PRODUCT_CASE_NOT_FOUND")
        else:
            case = self.store.get_active_product_case()
            if case is None:
                raise ValueError("PRODUCT_CASE_NOT_FOUND")
        case_data = {key: _json_value(value) for key, value in asdict(case).items()}
        contract = json.loads(case.contract_json) if case.contract_json else None
        events = [
            {
                "seq": event.seq,
                "type": event.type,
                "payload": event.payload,
                "created_at": event.created_at.isoformat(),
            }
            for event in self.store.list_product_case_events(case.id)
        ]
        linked_runs: dict[str, Any] = {}
        for name in ("baseline", "improvement", "replay"):
            run_id = getattr(case, f"{name}_run_id")
            if run_id:
                try:
                    linked_runs[name] = {"run_id": run_id, "state": self.store.get_run(run_id).state.value}
                except Exception:
                    linked_runs[name] = {"run_id": run_id, "state": "unknown"}
        next_action = self._next_action(case, linked_runs, events)
        return {
            "case": case_data,
            "contract": contract,
            "events": events,
            "linked_runs": linked_runs,
            "next_action": next_action,
        }

    def _next_action(
        self,
        case: Any,
        linked_runs: dict[str, Any],
        events: list[Any],
    ) -> str:
        state = case.state
        if state is ProductCaseState.WAITING_FOR_GOAL:
            return "wait for a real operator goal"
        if state is ProductCaseState.CONTRACTED:
            if case.baseline_run_id:
                return "dispatch the existing linked baseline run"
            return "recover baseline submission"
        if state is ProductCaseState.BASELINE_RUNNING:
            run_info = linked_runs.get("baseline", {})
            run_state = run_info.get("state", "unknown")
            if run_state == "queued":
                return "dispatch the existing linked baseline run"
            if run_state in ("ready_for_review", "applied", "completed", "failed", "cancelled", "dismissed", "previewed"):
                return "evaluate baseline after the linked run is terminal"
            return "wait for the linked baseline run to finish"
        if state is ProductCaseState.BASELINE_ACCEPTED:
            return "none"
        if state is ProductCaseState.FRICTION_CLASSIFIED:
            return "attach an improvement run or record the non-product limitation"
        if state is ProductCaseState.LIMITATION_RECORDED:
            return "none"
        if state is ProductCaseState.IMPROVEMENT_RUNNING:
            return "apply and independently approve the improvement"
        if state is ProductCaseState.IMPROVEMENT_REVIEWED:
            return "start replay"
        if state is ProductCaseState.REPLAY_RUNNING:
            run_info = linked_runs.get("replay", {})
            run_state = run_info.get("state", "unknown")
            if run_state == "queued":
                return "dispatch the existing linked replay run"
            if run_state in ("ready_for_review", "applied", "completed", "failed", "cancelled", "dismissed", "previewed"):
                return "evaluate replay after the linked run is terminal"
            return "wait for the linked replay run to finish"
        if state is ProductCaseState.HUMAN_REVIEW:
            unconsumed = self._find_unconsumed_challenge(
                events,
                "product_case.human_decision_requested",
                "product_case.human_decision_consumed",
            )
            if unconsumed is None:
                return "request a human decision"
            return "wait for a real user-prompt decision"
        if state is ProductCaseState.RETAINED:
            return "none"
        if state is ProductCaseState.REJECTED:
            return "none"
        return "unknown"
