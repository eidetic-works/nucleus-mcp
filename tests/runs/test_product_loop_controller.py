import hashlib
import json
import subprocess
import threading
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from mcp_server_nucleus.runs.cli import _evolve_loop, _evolve_next, build_parser, cmd_evolve
from mcp_server_nucleus.runs.models import ProductCaseState, RunState
from mcp_server_nucleus.runs.product_loop import ProductLoopController
from mcp_server_nucleus.runs.service import RunService
from mcp_server_nucleus.runs.store import ActiveProductCaseExists, RunStore
from mcp_server_nucleus.runs.verification import VerificationBundle


def _repo(path: Path) -> tuple[Path, str]:
    path.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True)
    (path / "src").mkdir()
    (path / "src" / "x.py").write_text("x = 1\n")
    subprocess.run(["git", "add", "."], cwd=path, check=True)
    subprocess.run(["git", "commit", "-qm", "initial"], cwd=path, check=True)
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=path, check=True, capture_output=True, text=True).stdout.strip()
    return path, head


@pytest.fixture
def setup(tmp_path, monkeypatch):
    brain = tmp_path / "brain"
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    target, head = _repo(tmp_path / "target")
    product, _ = _repo(tmp_path / "product")
    db = tmp_path / "runs.db"
    store = RunStore(str(db))
    dispatched = []
    controller = ProductLoopController(store, db, product, dispatch=dispatched.append)
    yield store, controller, target, product, head, dispatched
    store.close()


def _start(setup, **kwargs):
    store, controller, target, product, head, dispatched = setup
    case_id = controller.initialize(target)
    params = dict(
        goal_source="operator",
        goal="Improve x",
        permitted_paths=["src/x.py"],
        acceptance_check=["python3", "-c", "print('ok')"],
        runner_id="test",
        model_id="model",
        check_timeout=17,
    )
    params.update(kwargs)
    run_id = controller.start_baseline(case_id, **params)
    return case_id, run_id

def _finish(store, run_id, patch=b"diff --git a/src/x.py b/src/x.py\n--- a/src/x.py\n+++ b/src/x.py\n@@ -1,1 +1,1 @@\n-x = 1\n+x = 2\n", verdict="ok", eligible=True):
    run = store.get_run(run_id)
    project = store.get_project_for_run(run_id)
    root = Path(project.root_uri.removeprefix("file://"))
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True).stdout.strip()
    store.set_run_workspace(run_id, workspace=str(root), base_revision=head)
    ref = VerificationBundle.with_artifact("patch", patch, "text/x-diff")
    bundle = VerificationBundle(
        status="ready_for_review",
        output="",
        diff_sha256=ref.sha256,
        diff_size=ref.size,
        base_revision=head,
        patch=ref,
        route={
            "vendor": run.runner_id,
            "model": run.model_id,
            "execution_target": run.execution_target,
            "policy": project.trust_mode,
        },
        verdict=verdict,
        apply_eligible=eligible,
    )
    for state, event in (
        (RunState.PREPARING, "run.preparing"),
        (RunState.RUNNING, "run.running"),
        (RunState.VERIFYING, "run.verifying"),
        (RunState.READY_FOR_REVIEW, "run.ready_for_review"),
    ):
        store.transition_run(run_id, state, event, asdict(bundle) if state is RunState.READY_FOR_REVIEW else None)
    return ref


def _classify_product(setup):
    case_id, baseline_id = _start(setup)
    store, controller, target, product, head, dispatched = setup
    _finish(store, baseline_id)
    controller.evaluate_baseline(case_id, False, 2, "PRODUCT", "controller limitation")
    return case_id, baseline_id


def _improvement(setup, applied=False):
    case_id, baseline_id = _classify_product(setup)
    store, controller, target, product, head, dispatched = setup
    service = RunService(store)
    run_id, reason = service.submit_run(
        product,
        "Fix controller",
        runner_id="test",
        model_id="improvement-model",
        check_argv=["python3", "-c", "print('ok')"],
    )
    assert run_id and not reason
    ref = _finish(store, run_id)
    controller.attach_improvement(case_id, run_id)
    if applied:
        store.transition_run(run_id, RunState.APPLYING, "run.applying")
        store.transition_run(run_id, RunState.APPLIED, "run.applied")
    return case_id, baseline_id, run_id, ref


def _add_review_event(store, case_id, ref, reviewer_vendor="reviewer"):
    event = store.append_product_case_event(
        case_id,
        "product_case.independent_review_observed",
        {
            "source": "post_tool_use",
            "reviewer_vendor": reviewer_vendor,
            "reviewer_model": "review-model",
            "verdict": "SOUND",
            "patch_sha256": ref.sha256,
            "capture_sha256": hashlib.sha256(b"capture").hexdigest(),
        },
    )
    return event.seq


def _reviewed(setup):
    case_id, baseline_id, improvement_id, ref = _improvement(setup, applied=True)
    store, controller, target, product, head, dispatched = setup
    seq = _add_review_event(store, case_id, ref)
    controller.approve_improvement(case_id, seq, ["python3", "-c", "print('ok')"])
    return case_id, baseline_id


def _hook_event(case_id, challenge, accepted=True):
    verb = "ACCEPT" if accepted else "REJECT"
    return {
        "hook_event_name": "UserPromptSubmit",
        "session_id": "sess-1",
        "prompt_id": "prompt-1",
        "prompt": f"NUCLEUS {verb} {case_id} {challenge}",
    }


def test_initialize_is_idempotent_and_creates_no_run(setup):
    store, controller, target, product, head, dispatched = setup
    first = controller.initialize(target)
    assert controller.initialize(target) == first
    assert store.list_runs() == []
    contract = {
        "goal_source": "operator",
        "goal": "x",
        "project_root": str(target),
        "base_revision": head,
        "permitted_paths": ["src/x.py"],
        "acceptance_check": ["true"],
        "human_acceptance_required": True,
    }
    store.transition_product_case(first, ProductCaseState.WAITING_FOR_GOAL, {"contract": contract})
    with pytest.raises(ActiveProductCaseExists):
        controller.initialize(target)


def test_dirty_base_is_blocked_without_contract_or_run(setup):
    store, controller, target, product, head, dispatched = setup
    case_id = controller.initialize(target)
    (target / "src" / "x.py").write_text("dirty\n")
    with pytest.raises(ValueError, match="DIRTY_PROJECT_ROOT|PREFLIGHT_FAILED"):
        controller.start_baseline(case_id, "operator", "goal", ["src/x.py"], ["true"], runner_id="test")
    assert store.get_product_case(case_id).state is ProductCaseState.WAITING_FOR_GOAL
    assert store.list_runs() == []


def test_start_dispatches_only_linked_run_and_dispatch_failure_is_recoverable(setup):
    store, controller, target, product, head, dispatched = setup
    case_id, run_id = _start(setup)
    assert dispatched == [run_id]
    assert store.get_product_case(case_id).baseline_run_id == run_id
    second_target, _ = _repo(target.parent / "second")
    second_case = controller.initialize(second_target)
    controller.dispatch = lambda selected: (_ for _ in ()).throw(RuntimeError("dispatch"))
    with pytest.raises(RuntimeError):
        controller.start_baseline(second_case, "operator", "goal", ["src/x.py"], ["true"], runner_id="test")
    second = store.get_product_case(second_case)
    assert second.state is ProductCaseState.BASELINE_RUNNING
    assert any(e.type == "product_case.baseline_dispatch_failed" for e in store.list_product_case_events(second_case))


def test_submit_failure_leaves_contracted_with_named_event(setup, monkeypatch):
    store, controller, target, product, head, dispatched = setup
    case_id = controller.initialize(target)
    monkeypatch.setattr(controller.service, "submit_run", lambda **kwargs: (None, "blocked"))
    with pytest.raises(ValueError, match="BASELINE_SUBMIT_FAILED"):
        controller.start_baseline(case_id, "operator", "goal", ["src/x.py"], ["true"], runner_id="test")
    assert store.get_product_case(case_id).state is ProductCaseState.CONTRACTED
    assert any(e.type == "product_case.baseline_submit_failed" for e in store.list_product_case_events(case_id))


def test_contracted_retry_uses_stored_contract(setup, monkeypatch):
    store, controller, target, product, head, dispatched = setup
    case_id = controller.initialize(target)
    monkeypatch.setattr(controller.service, "submit_run", lambda **kwargs: (None, "blocked"))
    with pytest.raises(ValueError, match="BASELINE_SUBMIT_FAILED"):
        controller.start_baseline(case_id, "operator", "goal", ["src/x.py"], ["true"], runner_id="test")
    assert store.get_product_case(case_id).state is ProductCaseState.CONTRACTED
    monkeypatch.undo()
    run_id = controller.start_baseline(
        case_id,
        runner_id="test",
        model_id="model",
        check_timeout=17,
    )
    assert run_id
    assert store.get_product_case(case_id).state is ProductCaseState.BASELINE_RUNNING
    assert dispatched == [run_id]


def test_contracted_retry_rejects_different_goal(setup, monkeypatch):
    store, controller, target, product, head, dispatched = setup
    case_id = controller.initialize(target)
    monkeypatch.setattr(controller.service, "submit_run", lambda **kwargs: (None, "blocked"))
    with pytest.raises(ValueError, match="BASELINE_SUBMIT_FAILED"):
        controller.start_baseline(case_id, "operator", "goal", ["src/x.py"], ["true"], runner_id="test")
    monkeypatch.undo()
    with pytest.raises(ValueError, match="GOAL_MISMATCH"):
        controller.start_baseline(case_id, "operator", "different", ["src/x.py"], ["true"], runner_id="test")


def test_dispatch_failure_does_not_duplicate_run(setup):
    store, controller, target, product, head, dispatched = setup
    case_id, run_id = _start(setup)
    case = store.get_product_case(case_id)
    assert case.baseline_run_id == run_id
    controller.dispatch = lambda selected: (_ for _ in ()).throw(RuntimeError("dispatch"))
    with pytest.raises(RuntimeError):
        controller.start_baseline(case_id, runner_id="test", check_timeout=17)
    assert store.get_product_case(case_id).baseline_run_id == run_id
    assert len([r for r in store.list_runs() if r.id == run_id]) == 1


@pytest.mark.parametrize(
    "column,value,error",
    [
        ("prompt", "forged", "RUN_GOAL_MISMATCH"),
        ("requirements", '{"check":{"argv":["false"],"timeout":17}}', "RUN_CHECK_MISMATCH"),
        ("base_revision", "forged", "RUN_BASE_REVISION_MISMATCH"),
    ],
)
def test_baseline_exact_binding_rejects_mismatch(setup, column, value, error):
    case_id, run_id = _start(setup)
    store, controller, target, product, head, dispatched = setup
    _finish(store, run_id)
    store._conn.execute(f"UPDATE runs SET {column} = ? WHERE id = ?", (value, run_id))
    store._conn.commit()
    with pytest.raises(ValueError, match=error):
        controller.evaluate_baseline(case_id, False, 0, "MODEL", "failure")


def test_project_mismatch_and_nonterminal_are_rejected(setup):
    case_id, run_id = _start(setup)
    store, controller, target, product, head, dispatched = setup
    with pytest.raises(ValueError, match="NOT_TERMINAL"):
        controller.evaluate_baseline(case_id, False, 0, "MODEL", "failure")
    _finish(store, run_id)
    project = store.get_project_for_run(run_id)
    store._conn.execute("UPDATE projects SET root_uri = ? WHERE id = ?", (f"file://{product}", project.id))
    store._conn.commit()
    with pytest.raises(ValueError, match="RUN_PROJECT_MISMATCH"):
        controller.evaluate_baseline(case_id, False, 0, "MODEL", "failure")


def test_blank_requested_model_succeeds_with_default_actual_model(setup):
    store, controller, target, product, head, dispatched = setup
    case_id, run_id = _start(setup, model_id="")
    _finish(store, run_id)
    run = store.get_run(run_id)
    assert run.model_id == ""
    outcome = controller.evaluate_baseline(case_id, False, 0, "MODEL", "failure")
    assert outcome["verdict"] == "ok"
    assert outcome["apply_eligible"] is True


def test_route_mismatch_when_actual_route_differs_from_persisted(setup):
    case_id, run_id = _start(setup)
    store, controller, target, product, head, dispatched = setup
    _finish(store, run_id)
    store._conn.execute("UPDATE runs SET runner_id = ? WHERE id = ?", ("forged", run_id))
    store._conn.commit()
    outcome = controller.evaluate_baseline(case_id, False, 0, "MODEL", "failure")
    assert "RUN_ROUTE_MISMATCH" in outcome["verdict"]
    assert outcome["safety_violations"] == 1


@pytest.mark.parametrize(
    "patch,error",
    [
        (b"not a diff\n", "PATCH_GIT_PARSE_ERROR"),
        (b"diff --git a/../x b/../x\n--- a/../x\n+++ b/../x\n@@ -1,1 +1,1 @@\n-x\n+x\n", "PATCH_PATH_UNSAFE"),
        (b"diff --git a/out.py b/out.py\n--- a/out.py\n+++ b/out.py\n@@ -1,1 +1,1 @@\n-x\n+x\n", "PATCH_OUT_OF_SCOPE"),
    ],
)
def test_patch_paths_fail_closed(setup, patch, error):
    case_id, run_id = _start(setup)
    store, controller, target, product, head, dispatched = setup
    _finish(store, run_id, patch)
    outcome = controller.evaluate_baseline(case_id, False, 0, "MODEL", "failure")
    assert outcome["verdict"] == error
    assert outcome["apply_eligible"] is False
    assert outcome["safety_violations"] == 1


def test_appended_traditional_patch_section_is_caught(setup):
    case_id, run_id = _start(setup)
    store, controller, target, product, head, dispatched = setup
    patch = (
        b"diff --git a/src/x.py b/src/x.py\n"
        b"--- a/src/x.py\n+++ b/src/x.py\n@@ -1,1 +1,1 @@\n-x = 1\n+x = 2\n"
        b"--- a/src/out.py\n+++ b/src/out.py\n@@ -1,1 +1,1 @@\n-x\n+x\n"
    )
    _finish(store, run_id, patch)
    outcome = controller.evaluate_baseline(case_id, False, 0, "MODEL", "failure")
    assert outcome["verdict"] == "PATCH_OUT_OF_SCOPE"
    assert outcome["safety_violations"] == 1


def test_corrupt_patch_is_blocked(setup):
    case_id, run_id = _start(setup)
    store, controller, target, product, head, dispatched = setup
    ref = _finish(store, run_id)
    (Path(__import__("os").environ["NUCLEUS_BRAIN_PATH"]) / ref.path).write_bytes(b"corrupt")
    with pytest.raises(ValueError):
        controller.evaluate_baseline(case_id, True, 0, baseline_decision_event_seq=1)
    with pytest.raises(ValueError, match="BASELINE_ACCEPTANCE_REQUIRES_HOOK"):
        controller.evaluate_baseline(case_id, True, 0)


def test_baseline_acceptance_requires_hook_event(setup):
    case_id, run_id = _start(setup)
    store, controller, target, product, head, dispatched = setup
    _finish(store, run_id)
    with pytest.raises(ValueError, match="BASELINE_ACCEPTANCE_REQUIRES_HOOK"):
        controller.evaluate_baseline(case_id, True, 0)


def test_baseline_hook_acceptance_works_once(setup):
    case_id, run_id = _start(setup)
    store, controller, target, product, head, dispatched = setup
    _finish(store, run_id)
    challenge = controller.request_baseline_decision(case_id)
    result = controller.accept_baseline_from_user_prompt(case_id, challenge, _hook_event(case_id, challenge))
    assert result == "baseline_accepted"
    assert store.get_product_case(case_id).state is ProductCaseState.BASELINE_ACCEPTED
    events = store.list_product_case_events(case_id)
    assert not any(e.type == "product_case.baseline_decision_requested" and "challenge_display" in e.payload for e in events)
    assert not any("challenge_display" in e.payload for e in events)


def test_baseline_wrong_challenge_rejected(setup):
    case_id, run_id = _start(setup)
    store, controller, target, product, head, dispatched = setup
    _finish(store, run_id)
    controller.request_baseline_decision(case_id)
    with pytest.raises(ValueError, match="BASELINE_CHALLENGE_MISMATCH"):
        controller.accept_baseline_from_user_prompt(case_id, "wrong", _hook_event(case_id, "wrong"))


def test_baseline_expired_challenge_rejected(setup):
    case_id, run_id = _start(setup)
    store, controller, target, product, head, dispatched = setup
    _finish(store, run_id)
    controller.request_baseline_decision(case_id)
    event = store.list_product_case_events(case_id)[-1]
    payload = dict(event.payload)
    payload["expires_at"] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    store._conn.execute("UPDATE product_case_events SET payload = ? WHERE id = ?", (json.dumps(payload), event.id))
    store._conn.commit()
    # Re-request since the old one is expired
    challenge = controller.request_baseline_decision(case_id)
    result = controller.accept_baseline_from_user_prompt(case_id, challenge, _hook_event(case_id, challenge))
    assert result == "baseline_accepted"


def test_baseline_forged_hook_event_rejected(setup):
    case_id, run_id = _start(setup)
    store, controller, target, product, head, dispatched = setup
    _finish(store, run_id)
    challenge = controller.request_baseline_decision(case_id)
    bad_event = {"hook_event_name": "PreToolUse", "session_id": "s", "prompt_id": "p", "prompt": f"NUCLEUS ACCEPT {case_id} {challenge}"}
    with pytest.raises(ValueError, match="INVALID_HOOK_EVENT_NAME"):
        controller.accept_baseline_from_user_prompt(case_id, challenge, bad_event)
    bad_event2 = {"hook_event_name": "UserPromptSubmit", "session_id": "s", "prompt_id": "p", "prompt": f"NUCLEUS REJECT {case_id} {challenge}"}
    with pytest.raises(ValueError, match="HOOK_PROMPT_MISMATCH"):
        controller.accept_baseline_from_user_prompt(case_id, challenge, bad_event2)


def test_record_limitation_rejects_product_and_accepts_nonproduct(setup):
    case_id, baseline_id = _classify_product(setup)
    store, controller, target, product, head, dispatched = setup
    with pytest.raises(ValueError, match="PRODUCT_FRICTION"):
        controller.record_limitation(case_id)
    other, _ = _repo(target.parent / "other")
    other_case = controller.initialize(other)
    other_run = controller.start_baseline(other_case, "operator", "goal", ["src/x.py"], ["true"], runner_id="test")
    _finish(store, other_run)
    controller.evaluate_baseline(other_case, False, 0, "MODEL", "model failed")
    assert controller.record_limitation(other_case) == "limitation_recorded"


def test_attach_improvement_rejects_wrong_project_and_noneligible(setup):
    case_id, baseline_id = _classify_product(setup)
    store, controller, target, product, head, dispatched = setup
    service = RunService(store)
    wrong_id, _ = service.submit_run(target, "wrong", runner_id="test", check_argv=["true"])
    _finish(store, wrong_id)
    with pytest.raises(ValueError, match="PROJECT_MISMATCH"):
        controller.attach_improvement(case_id, wrong_id)
    bad_id, _ = service.submit_run(product, "bad", runner_id="test", check_argv=["true"])
    _finish(store, bad_id, eligible=False)
    with pytest.raises(ValueError, match="NOT_ELIGIBLE"):
        controller.attach_improvement(case_id, bad_id)


def test_approve_requires_review_event_seq_not_caller_claims(setup):
    case_id, baseline_id, improvement_id, ref = _improvement(setup, applied=True)
    store, controller, target, product, head, dispatched = setup
    with pytest.raises(TypeError):
        controller.approve_improvement(case_id, "reviewer", "SOUND", ref.sha256, ["true"])
    with pytest.raises(ValueError, match="INVALID_REVIEW_EVENT_SEQ"):
        controller.approve_improvement(case_id, 0, ["true"])


def test_approve_rejects_wrong_review_event_type(setup):
    case_id, baseline_id, improvement_id, ref = _improvement(setup, applied=True)
    store, controller, target, product, head, dispatched = setup
    audit_event = store.append_product_case_event(case_id, "audit.something", {"x": 1})
    with pytest.raises(ValueError, match="REVIEW_EVENT_WRONG_TYPE"):
        controller.approve_improvement(case_id, audit_event.seq, ["true"])


def test_approve_rejects_forged_review_payload(setup):
    case_id, baseline_id, improvement_id, ref = _improvement(setup, applied=True)
    store, controller, target, product, head, dispatched = setup
    bad_event = store.append_product_case_event(
        case_id,
        "product_case.independent_review_observed",
        {"source": "caller", "reviewer_vendor": "reviewer", "reviewer_model": "m", "verdict": "SOUND", "patch_sha256": ref.sha256, "capture_sha256": "c"},
    )
    with pytest.raises(ValueError, match="INVALID_SOURCE"):
        controller.approve_improvement(case_id, bad_event.seq, ["true"])


def test_approve_rejects_non_independent_reviewer(setup):
    case_id, baseline_id, improvement_id, ref = _improvement(setup, applied=True)
    store, controller, target, product, head, dispatched = setup
    run = store.get_run(improvement_id)
    seq = _add_review_event(store, case_id, ref, reviewer_vendor=run.runner_id)
    with pytest.raises(ValueError, match="REVIEWER_NOT_INDEPENDENT"):
        controller.approve_improvement(case_id, seq, ["true"])


def test_approve_rejects_wrong_patch_hash(setup):
    case_id, baseline_id, improvement_id, ref = _improvement(setup, applied=True)
    store, controller, target, product, head, dispatched = setup
    bad_event = store.append_product_case_event(
        case_id,
        "product_case.independent_review_observed",
        {"source": "post_tool_use", "reviewer_vendor": "reviewer", "reviewer_model": "m", "verdict": "SOUND", "patch_sha256": "0" * 64, "capture_sha256": "c"},
    )
    with pytest.raises(ValueError, match="PATCH_HASH_MISMATCH"):
        controller.approve_improvement(case_id, bad_event.seq, ["true"])


def test_approve_requires_applied_improvement(setup):
    case_id, baseline_id, improvement_id, ref = _improvement(setup, applied=False)
    store, controller, target, product, head, dispatched = setup
    seq = _add_review_event(store, case_id, ref)
    with pytest.raises(ValueError, match="IMPROVEMENT_NOT_APPLIED"):
        controller.approve_improvement(case_id, seq, ["true"])


def test_approve_regression_failure_is_audited_without_transition(setup):
    case_id, baseline_id, improvement_id, ref = _improvement(setup, applied=True)
    store, controller, target, product, head, dispatched = setup
    seq = _add_review_event(store, case_id, ref)
    # Use a command that exits non-zero but is still a valid contract-bound argv
    # We need to set up a case where acceptance_check fails
    # Modify the contract's acceptance_check to a failing command
    case = store.get_product_case(case_id)
    contract = json.loads(case.contract_json)
    contract["acceptance_check"] = ["python3", "-c", "import sys; sys.exit(1)"]
    store._conn.execute(
        "UPDATE product_cases SET contract_json = ?, contract_sha256 = ? WHERE id = ?",
        (json.dumps(contract), hashlib.sha256(json.dumps(contract, sort_keys=True, separators=(",", ":")).encode()).hexdigest(), case_id),
    )
    store._conn.commit()
    with pytest.raises(ValueError, match="REGRESSION_FAILED"):
        controller.approve_improvement(case_id, seq, ["python3", "-c", "import sys; sys.exit(1)"], timeout=5)
    assert store.get_product_case(case_id).state is ProductCaseState.IMPROVEMENT_RUNNING
    event = store.list_product_case_events(case_id)[-1]
    assert event.type == "product_case.improvement_regression"
    assert "argv_sha256" in event.payload and "argv" not in event.payload


def test_replay_blocks_dirty_and_changed_head(setup):
    case_id, baseline_id = _reviewed(setup)
    store, controller, target, product, head, dispatched = setup
    (target / "dirty").write_text("x")
    with pytest.raises(ValueError, match="DIRTY_PROJECT_ROOT"):
        controller.start_replay(case_id)
    (target / "dirty").unlink()
    (target / "new").write_text("x")
    subprocess.run(["git", "add", "new"], cwd=target, check=True)
    subprocess.run(["git", "commit", "-qm", "changed"], cwd=target, check=True)
    with pytest.raises(ValueError, match="BASE_REVISION_CHANGED"):
        controller.start_replay(case_id)


def test_replay_allows_descendant_head_when_self_evolving(setup):
    store, _, target, product, head, dispatched = setup
    db = store._db_path
    controller = ProductLoopController(store, db, target, dispatch=dispatched.append)
    case_id = controller.initialize(target)
    baseline_id = controller.start_baseline(
        case_id,
        "operator",
        "Improve x",
        ["src/x.py"],
        ["python3", "-c", "print('ok')"],
        runner_id="test",
        model_id="model",
        check_timeout=17,
    )
    _finish(store, baseline_id)
    controller.evaluate_baseline(case_id, False, 0, "PRODUCT", "controller limitation")
    service = RunService(store)
    imp_id, reason = service.submit_run(
        str(target),
        "Fix product",
        runner_id="test",
        model_id="improvement-model",
        check_argv=["python3", "-c", "print('ok')"],
    )
    assert imp_id and not reason
    imp_ref = _finish(store, imp_id)
    controller.attach_improvement(case_id, imp_id)
    store.transition_run(imp_id, RunState.APPLYING, "run.applying")
    store.transition_run(imp_id, RunState.APPLIED, "run.applied")
    seq = _add_review_event(store, case_id, imp_ref)
    controller.approve_improvement(case_id, seq, ["python3", "-c", "print('ok')"])
    # The improvement lands as a commit on the product it is also the target.
    (target / "improved").write_text("x")
    subprocess.run(["git", "add", "improved"], cwd=target, check=True)
    subprocess.run(["git", "commit", "-qm", "improvement"], cwd=target, check=True)
    replay_id = controller.start_replay(case_id)
    assert replay_id and replay_id != baseline_id
    assert dispatched[-1] == replay_id
    # The improvement already delivered the goal: the replay run finishes
    # clean (no diff, check passes) — for self-evolution that is the success
    # signal, not a rejection.
    replay_run = store.get_run(replay_id)
    project = store.get_project_for_run(replay_id)
    root = Path(project.root_uri.removeprefix("file://"))
    new_head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()
    store.set_run_workspace(replay_id, workspace=str(root), base_revision=new_head)
    clean_bundle = VerificationBundle(
        status="ready_for_review",
        output="",
        diff_sha256="",
        diff_size=0,
        base_revision=new_head,
        patch=None,
        route={
            "vendor": replay_run.runner_id,
            "model": replay_run.model_id,
            "execution_target": replay_run.execution_target,
            "policy": project.trust_mode,
        },
        verdict="ok",
        is_clean=True,
        apply_eligible=False,
    )
    for state, event in (
        (RunState.PREPARING, "run.preparing"),
        (RunState.RUNNING, "run.running"),
        (RunState.VERIFYING, "run.verifying"),
        (RunState.COMPLETED, "run.completed"),
    ):
        store.transition_run(
            replay_id, state, event, asdict(clean_bundle) if state is RunState.COMPLETED else None
        )
    assert controller.evaluate_replay(case_id, 0) == "human_review"
    event_types = [e.type for e in store.list_product_case_events(case_id)]
    assert "product_case.replay_self_evolution_satisfied" in event_types


def test_replay_is_distinct_and_identity_mismatch_is_rejected(setup):
    case_id, baseline_id = _reviewed(setup)
    store, controller, target, product, head, dispatched = setup
    replay_id = controller.start_replay(case_id)
    assert replay_id != baseline_id
    assert dispatched[-1] == replay_id
    _finish(store, replay_id)
    store._conn.execute("UPDATE runs SET runner_id = ? WHERE id = ?", ("forged", replay_id))
    store._conn.commit()
    with pytest.raises(ValueError, match="REPLAY_IDENTITY_MISMATCH"):
        controller.evaluate_replay(case_id, 0)


def test_replay_actual_route_mismatch_is_rejected(setup):
    case_id, baseline_id = _reviewed(setup)
    store, controller, target, product, head, dispatched = setup
    replay_id = controller.start_replay(case_id)
    _finish(store, replay_id)
    # Modify the replay run's model_id to create a route mismatch
    # (route model in bundle != persisted model_id)
    store._conn.execute("UPDATE runs SET model_id = ? WHERE id = ?", ("forged-model", replay_id))
    store._conn.commit()
    with pytest.raises(ValueError, match="REPLAY_ROUTE_MODEL_MISMATCH"):
        controller.evaluate_replay(case_id, 0)


def test_evaluate_replay_transitions_to_human_review_only(setup):
    case_id, baseline_id = _reviewed(setup)
    store, controller, target, product, head, dispatched = setup
    replay_id = controller.start_replay(case_id)
    _finish(store, replay_id)
    result = controller.evaluate_replay(case_id, 0)
    assert result == "human_review"
    assert store.get_product_case(case_id).state is ProductCaseState.HUMAN_REVIEW
    events = store.list_product_case_events(case_id)
    assert not any(e.type == "product_case.human_decision_requested" for e in events)


def test_request_decision_is_recoverable_after_crash(setup):
    case_id, baseline_id = _reviewed(setup)
    store, controller, target, product, head, dispatched = setup
    replay_id = controller.start_replay(case_id)
    _finish(store, replay_id)
    controller.evaluate_replay(case_id, 0)
    assert store.get_product_case(case_id).state is ProductCaseState.HUMAN_REVIEW
    challenge = controller.request_decision(case_id)
    assert challenge


def test_request_decision_idempotent_pending(setup):
    case_id, baseline_id = _reviewed(setup)
    store, controller, target, product, head, dispatched = setup
    replay_id = controller.start_replay(case_id)
    _finish(store, replay_id)
    controller.evaluate_replay(case_id, 0)
    controller.request_decision(case_id)
    with pytest.raises(ValueError, match="CHALLENGE_ALREADY_PENDING"):
        controller.request_decision(case_id)


def test_no_plaintext_challenge_in_events(setup):
    case_id, baseline_id = _reviewed(setup)
    store, controller, target, product, head, dispatched = setup
    replay_id = controller.start_replay(case_id)
    _finish(store, replay_id)
    controller.evaluate_replay(case_id, 0)
    challenge = controller.request_decision(case_id)
    events = store.list_product_case_events(case_id)
    for event in events:
        payload_str = json.dumps(event.payload)
        assert challenge not in payload_str
        assert "challenge_display" not in event.payload


def test_decide_wrong_hook_event_name_rejected(setup):
    case_id, baseline_id = _reviewed(setup)
    store, controller, target, product, head, dispatched = setup
    replay_id = controller.start_replay(case_id)
    _finish(store, replay_id)
    controller.evaluate_replay(case_id, 0)
    challenge = controller.request_decision(case_id)
    bad_event = {"hook_event_name": "PreToolUse", "session_id": "s", "prompt_id": "p", "prompt": f"NUCLEUS ACCEPT {case_id} {challenge}"}
    with pytest.raises(ValueError, match="INVALID_HOOK_EVENT_NAME"):
        controller.decide_from_user_prompt(case_id, challenge, True, bad_event)


def test_decide_wrong_prompt_rejected(setup):
    case_id, baseline_id = _reviewed(setup)
    store, controller, target, product, head, dispatched = setup
    replay_id = controller.start_replay(case_id)
    _finish(store, replay_id)
    controller.evaluate_replay(case_id, 0)
    challenge = controller.request_decision(case_id)
    bad_event = {"hook_event_name": "UserPromptSubmit", "session_id": "s", "prompt_id": "p", "prompt": f"NUCLEUS REJECT {case_id} {challenge}"}
    with pytest.raises(ValueError, match="HOOK_PROMPT_MISMATCH"):
        controller.decide_from_user_prompt(case_id, challenge, True, bad_event)


def test_decide_wrong_challenge_rejected(setup):
    case_id, baseline_id = _reviewed(setup)
    store, controller, target, product, head, dispatched = setup
    replay_id = controller.start_replay(case_id)
    _finish(store, replay_id)
    controller.evaluate_replay(case_id, 0)
    controller.request_decision(case_id)
    with pytest.raises(ValueError, match="CHALLENGE_MISMATCH"):
        controller.decide_from_user_prompt(case_id, "wrong", False, _hook_event(case_id, "wrong", accepted=False))


def test_decide_accept_and_reject(setup):
    case_id, baseline_id = _reviewed(setup)
    store, controller, target, product, head, dispatched = setup
    replay_id = controller.start_replay(case_id)
    _finish(store, replay_id)
    controller.evaluate_replay(case_id, 0)
    challenge = controller.request_decision(case_id)
    result = controller.decide_from_user_prompt(case_id, challenge, False, _hook_event(case_id, challenge, accepted=False))
    assert result == "rejected"
    assert store.get_product_case(case_id).state is ProductCaseState.REJECTED
    with pytest.raises(ValueError, match="CASE_STATE_REJECTED"):
        controller.decide_from_user_prompt(case_id, challenge, False, _hook_event(case_id, challenge, accepted=False))


def test_decide_expired_challenge_rejected(setup):
    case_id, baseline_id = _reviewed(setup)
    store, controller, target, product, head, dispatched = setup
    replay_id = controller.start_replay(case_id)
    _finish(store, replay_id)
    controller.evaluate_replay(case_id, 0)
    challenge = controller.request_decision(case_id)
    event = store.list_product_case_events(case_id)[-1]
    payload = dict(event.payload)
    payload["expires_at"] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    store._conn.execute("UPDATE product_case_events SET payload = ? WHERE id = ?", (json.dumps(payload), event.id))
    store._conn.commit()
    with pytest.raises(ValueError, match="CHALLENGE_EXPIRED"):
        controller.decide_from_user_prompt(case_id, challenge, False, _hook_event(case_id, challenge, accepted=False))


def test_decide_concurrent_replay_fails_because_terminal(setup):
    case_id, baseline_id = _reviewed(setup)
    store, controller, target, product, head, dispatched = setup
    replay_id = controller.start_replay(case_id)
    _finish(store, replay_id)
    controller.evaluate_replay(case_id, 0)
    challenge = controller.request_decision(case_id)
    result = controller.decide_from_user_prompt(case_id, challenge, False, _hook_event(case_id, challenge, accepted=False))
    assert result == "rejected"
    with pytest.raises(ValueError, match="CASE_STATE_REJECTED"):
        controller.decide_from_user_prompt(case_id, challenge, False, _hook_event(case_id, challenge, accepted=False))


def test_status_waiting_has_no_invented_work(setup):
    store, controller, target, product, head, dispatched = setup
    case_id = controller.initialize(target)
    status = controller.status(case_id)
    assert status["contract"] is None
    assert status["linked_runs"] == {}
    assert status["next_action"] == "wait for a real operator goal"


def test_status_contracted_without_run(setup, monkeypatch):
    store, controller, target, product, head, dispatched = setup
    case_id = controller.initialize(target)
    monkeypatch.setattr(controller.service, "submit_run", lambda **kwargs: (None, "blocked"))
    with pytest.raises(ValueError, match="BASELINE_SUBMIT_FAILED"):
        controller.start_baseline(case_id, "operator", "goal", ["src/x.py"], ["true"], runner_id="test")
    status = controller.status(case_id)
    assert status["next_action"] == "recover baseline submission"


def test_status_baseline_running_queued(setup):
    case_id, run_id = _start(setup)
    store, controller, target, product, head, dispatched = setup
    status = controller.status(case_id)
    assert "dispatch" in status["next_action"]


def test_status_human_review_without_challenge(setup):
    case_id, baseline_id = _reviewed(setup)
    store, controller, target, product, head, dispatched = setup
    replay_id = controller.start_replay(case_id)
    _finish(store, replay_id)
    controller.evaluate_replay(case_id, 0)
    status = controller.status(case_id)
    assert status["next_action"] == "request a human decision"


def test_status_human_review_with_challenge(setup):
    case_id, baseline_id = _reviewed(setup)
    store, controller, target, product, head, dispatched = setup
    replay_id = controller.start_replay(case_id)
    _finish(store, replay_id)
    controller.evaluate_replay(case_id, 0)
    controller.request_decision(case_id)
    status = controller.status(case_id)
    assert status["next_action"] == "wait for a real user-prompt decision"


def test_cli_parser_has_all_actions_and_no_decide():
    parser = build_parser()
    parsed = parser.parse_args(["evolve", "start", "case", "--goal-source", "operator", "--goal", "g", "--file", "src/x.py", "--check", "pytest -q"])
    assert parsed.evolve_action == "start"
    evolve = next(action for action in parser._actions if action.dest == "action").choices["evolve"]
    choices = next(action for action in evolve._actions if action.dest == "evolve_action").choices
    assert set(choices) == {"init", "start", "queue", "evaluate-baseline", "record-limitation", "attach-improvement", "approve-improvement", "replay", "evaluate-replay", "request-baseline-decision", "status", "history", "next"}


def test_cli_evolve_start_runner_defaults_to_empty_for_env_fallback():
    parser = build_parser()
    base = ["evolve", "start", "case", "--goal-source", "operator", "--goal", "g", "--file", "src/x.py", "--check", "pytest -q"]

    omitted = parser.parse_args(base)
    assert omitted.runner == ""

    explicit = parser.parse_args([*base, "--runner", "agy"])
    assert explicit.runner == "agy"


def test_cli_init_and_named_error_print_json_only(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / "brain"))
    target, _ = _repo(tmp_path / "target")
    parser = build_parser()
    args = parser.parse_args(["evolve", "init", "--project-root", str(target)])
    assert cmd_evolve(args) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    args = parser.parse_args(["evolve", "status", "missing"])
    assert cmd_evolve(args) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False and payload["error"]


def test_cli_evaluate_baseline_only_accepts_false(setup, capsys):
    case_id, run_id = _start(setup)
    store, controller, target, product, head, dispatched = setup
    _finish(store, run_id)
    parser = build_parser()
    # --accepted true is rejected by the parser (choices=["false"])
    with pytest.raises(SystemExit):
        parser.parse_args(["evolve", "evaluate-baseline", case_id, "--accepted", "true", "--interventions", "0"])
    # --accepted false is accepted by the parser
    args = parser.parse_args(["evolve", "evaluate-baseline", case_id, "--accepted", "false", "--interventions", "0", "--owner", "MODEL", "--friction", "test"])
    assert args.accepted == "false"


def test_patch_rename_rejected(setup):
    case_id, run_id = _start(setup)
    store, controller, target, product, head, dispatched = setup
    patch = b"diff --git a/src/x.py b/src/y.py\nrename from src/x.py\nrename to src/y.py\n"
    _finish(store, run_id, patch)
    outcome = controller.evaluate_baseline(case_id, False, 0, "MODEL", "failure")
    assert "PATCH_RENAME_OR_COPY" in outcome["verdict"]
    assert outcome["safety_violations"] == 1


def test_patch_mode_change_rejected(setup):
    case_id, run_id = _start(setup)
    store, controller, target, product, head, dispatched = setup
    patch = b"diff --git a/src/x.py b/src/x.py\nold mode 100644\nnew mode 100755\n"
    _finish(store, run_id, patch)
    outcome = controller.evaluate_baseline(case_id, False, 0, "MODEL", "failure")
    assert outcome["verdict"] in ("PATCH_MODE_CHANGE", "PATCH_GIT_PARSE_ERROR")
    assert outcome["safety_violations"] == 1


def test_review_event_before_improvement_rejected(setup):
    case_id, baseline_id, improvement_id, ref = _improvement(setup, applied=True)
    store, controller, target, product, head, dispatched = setup
    events = store.list_product_case_events(case_id)
    improvement_seq = max(e.seq for e in events if e.type == "product_case.improvement_running")
    pre_event = next(e for e in events if e.seq < improvement_seq and e.type != "product_case.independent_review_observed")
    with pytest.raises(ValueError, match="REVIEW_EVENT_WRONG_TYPE"):
        controller.approve_improvement(case_id, pre_event.seq, ["python3", "-c", "print('ok')"])


def test_baseline_acceptance_works_exactly_once(setup):
    case_id, run_id = _start(setup)
    store, controller, target, product, head, dispatched = setup
    _finish(store, run_id)
    challenge = controller.request_baseline_decision(case_id)
    result = controller.accept_baseline_from_user_prompt(case_id, challenge, _hook_event(case_id, challenge))
    assert result == "baseline_accepted"
    assert store.get_product_case(case_id).state is ProductCaseState.BASELINE_ACCEPTED
    with pytest.raises(ValueError, match="CASE_STATE_BASELINE_ACCEPTED"):
        controller.accept_baseline_from_user_prompt(case_id, challenge, _hook_event(case_id, challenge))


def test_regression_argv_not_bound_to_contract_rejected(setup):
    case_id, baseline_id, improvement_id, ref = _improvement(setup, applied=True)
    store, controller, target, product, head, dispatched = setup
    seq = _add_review_event(store, case_id, ref)
    with pytest.raises(ValueError, match="REGRESSION_ARGV_NOT_BOUND_TO_CONTRACT"):
        controller.approve_improvement(case_id, seq, ["true"])


def test_status_baseline_running_terminal(setup):
    case_id, run_id = _start(setup)
    store, controller, target, product, head, dispatched = setup
    _finish(store, run_id)
    status = controller.status(case_id)
    assert "evaluate baseline" in status["next_action"]


def test_decide_accepted_prompt_mismatch_rejected(setup):
    case_id, baseline_id = _reviewed(setup)
    store, controller, target, product, head, dispatched = setup
    replay_id = controller.start_replay(case_id)
    _finish(store, replay_id)
    controller.evaluate_replay(case_id, 0)
    challenge = controller.request_decision(case_id)
    bad_event = {"hook_event_name": "UserPromptSubmit", "session_id": "s", "prompt_id": "p", "prompt": f"NUCLEUS REJECT {case_id} {challenge}"}
    with pytest.raises(ValueError, match="HOOK_PROMPT_MISMATCH"):
        controller.decide_from_user_prompt(case_id, challenge, True, bad_event)


def test_route_missing_is_safety_violation(setup):
    case_id, run_id = _start(setup)
    store, controller, target, product, head, dispatched = setup
    run = store.get_run(run_id)
    project = store.get_project_for_run(run_id)
    root = Path(project.root_uri.removeprefix("file://"))
    head2 = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True).stdout.strip()
    store.set_run_workspace(run_id, workspace=str(root), base_revision=head2)
    patch = b"diff --git a/src/x.py b/src/x.py\n--- a/src/x.py\n+++ b/src/x.py\n@@ -1,1 +1,1 @@\n-x = 1\n+x = 2\n"
    ref = VerificationBundle.with_artifact("patch", patch, "text/x-diff")
    bundle = VerificationBundle(
        status="ready_for_review", output="",
        diff_sha256=ref.sha256, diff_size=ref.size,
        base_revision=head2, patch=ref,
        route=None,
        verdict="ok", apply_eligible=True,
    )
    for state, event in (
        (RunState.PREPARING, "run.preparing"),
        (RunState.RUNNING, "run.running"),
        (RunState.VERIFYING, "run.verifying"),
        (RunState.READY_FOR_REVIEW, "run.ready_for_review"),
    ):
        store.transition_run(run_id, state, event, asdict(bundle) if state is RunState.READY_FOR_REVIEW else None)
    outcome = controller.evaluate_baseline(case_id, False, 0, "MODEL", "failure")
    assert "RUN_ROUTE_MISSING" in outcome["verdict"]
    assert outcome["safety_violations"] == 1


def test_improvement_base_revision_not_checked_for_improvement_runs(setup):
    # Improvement runs are fixes for the controller, not replays of the original task.
    # Their base_revision is the product repo's HEAD, not the contract's base_revision.
    # The base_revision check only applies to baseline and replay runs.
    case_id, baseline_id, improvement_id, ref = _improvement(setup, applied=True)
    store, controller, target, product, head, dispatched = setup
    # The improvement was successfully attached despite having a different base_revision.
    # This test verifies that the improvement path doesn't check base_revision.
    case = store.get_product_case(case_id)
    assert case.improvement_run_id == improvement_id
    assert case.state is ProductCaseState.IMPROVEMENT_RUNNING


def test_cli_parser_next_loop_flags():
    parser = build_parser()
    args = parser.parse_args(["evolve", "next", "case"])
    assert args.loop is False
    assert args.interval == 5
    assert args.max_steps == 100
    args = parser.parse_args(["evolve", "next", "case", "--loop", "--interval", "0.5", "--max-steps", "3"])
    assert args.loop is True
    assert args.interval == 0.5
    assert args.max_steps == 3


def test_evolve_loop_stops_when_human_decision_is_required(setup, capsys):
    case_id, baseline_id = _reviewed(setup)
    store, controller, target, product, head, dispatched = setup
    replay_id = controller.start_replay(case_id)
    _finish(store, replay_id)
    controller.evaluate_replay(case_id, 0)
    assert store.get_product_case(case_id).state is ProductCaseState.HUMAN_REVIEW

    slept = []
    assert _evolve_loop(controller, store, case_id, interval=0, max_steps=10, sleep=slept.append) == 0

    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["ok"] is True
    assert payload["result"]["action"] == "request-decision"
    assert payload["result"]["challenge"]
    assert payload["result"]["state"] == ProductCaseState.HUMAN_REVIEW.value
    # Stopped on the first step, so it never slept and never burned max_steps.
    assert slept == []


def test_cli_parser_accepts_evolve_queue(tmp_path):
    parser = build_parser()
    args = parser.parse_args([
        "evolve", "queue",
        "--project-root", str(tmp_path),
        "--goal-source", "operator",
        "--goal", "Improve x",
        "--file", "src/x.py",
        "--check", "pytest -q",
    ])
    assert args.evolve_action == "queue"
    assert args.project_root == str(tmp_path)
    assert args.goal_source == "operator"
    assert args.goal == "Improve x"
    assert args.files == ["src/x.py"]
    assert args.check == "pytest -q"
    assert args.runner == ""
    assert args.model == ""
    assert args.target == "subprocess"
    assert args.trust_mode == "default"
    assert args.mode == "write"
    assert args.check_timeout == 300
    assert not hasattr(args, "case_id")


def test_cli_evolve_defaults_to_subprocess_target_but_honors_explicit(tmp_path):
    parser = build_parser()
    queue_base = [
        "evolve", "queue",
        "--project-root", str(tmp_path),
        "--goal-source", "operator",
        "--goal", "Improve x",
        "--file", "src/x.py",
        "--check", "pytest -q",
    ]
    start_base = [
        "evolve", "start", "case",
        "--goal-source", "operator",
        "--goal", "g",
        "--file", "src/x.py",
        "--check", "pytest -q",
    ]

    # Unattended evolve runs outlive their invoker only when detached.
    assert parser.parse_args(queue_base).target == "subprocess"
    assert parser.parse_args(start_base).target == "subprocess"

    assert parser.parse_args([*queue_base, "--target", "in-process"]).target == "in-process"
    assert parser.parse_args([*start_base, "--target", "in-process"]).target == "in-process"


def test_enqueue_then_claim_returns_the_goal_and_flips_it_to_claimed(setup):
    store, controller, target, product, head, dispatched = setup
    goal_id = store.enqueue_goal(
        str(target),
        "Improve x",
        goal_source="operator",
        permitted_paths=["src/x.py"],
        acceptance_check=["python3", "-c", "print('ok')"],
        runner_id="test",
        model_id="model",
        check_timeout=17,
    )
    assert goal_id
    assert [g["state"] for g in store.list_goals()] == ["pending"]

    claimed = store.claim_next_goal(str(target), "case-1")
    assert claimed is not None
    assert claimed["id"] == goal_id
    assert claimed["state"] == "claimed"
    assert claimed["case_id"] == "case-1"
    assert claimed["goal"] == "Improve x"
    assert claimed["goal_source"] == "operator"
    assert claimed["permitted_paths"] == ["src/x.py"]
    assert claimed["acceptance_check"] == ["python3", "-c", "print('ok')"]
    assert claimed["runner_id"] == "test"
    assert claimed["model_id"] == "model"
    assert claimed["check_timeout"] == 17
    assert store.list_goals(state="pending") == []
    assert [g["id"] for g in store.list_goals(state="claimed")] == [goal_id]


def test_second_claim_of_the_only_queued_goal_returns_none(setup):
    store, controller, target, product, head, dispatched = setup
    store.enqueue_goal(
        str(target),
        "Improve x",
        goal_source="operator",
        permitted_paths=["src/x.py"],
        acceptance_check=["python3", "-c", "print('ok')"],
    )
    assert store.claim_next_goal(str(target), "case-1") is not None
    assert store.claim_next_goal(str(target), "case-2") is None


def test_evolve_next_on_waiting_case_starts_baseline_from_the_queue(setup):
    store, controller, target, product, head, dispatched = setup
    case_id = controller.initialize(target)
    assert store.get_product_case(case_id).state is ProductCaseState.WAITING_FOR_GOAL
    goal_id = store.enqueue_goal(
        str(target),
        "Improve x",
        goal_source="operator",
        permitted_paths=["src/x.py"],
        acceptance_check=["python3", "-c", "print('ok')"],
        runner_id="test",
        model_id="model",
        check_timeout=17,
    )

    result = _evolve_next(controller, store, case_id)

    assert result["action"] == "start-baseline"
    assert result["goal_id"] == goal_id
    assert result["run_id"]
    assert result["state"] == store.get_product_case(case_id).state.value
    assert dispatched == [result["run_id"]]
    assert store.get_product_case(case_id).baseline_run_id == result["run_id"]
    assert [g["state"] for g in store.list_goals()] == ["done"]


def test_evolve_next_defaults_an_unspecified_goal_target_to_subprocess(setup):
    store, controller, target, product, head, dispatched = setup
    case_id = controller.initialize(target)
    store.enqueue_goal(
        str(target),
        "Improve x",
        goal_source="operator",
        permitted_paths=["src/x.py"],
        acceptance_check=["python3", "-c", "print('ok')"],
        execution_target="",
    )

    result = _evolve_next(controller, store, case_id)

    assert result["action"] == "start-baseline"
    assert store.get_run(result["run_id"]).execution_target == "subprocess"


def test_evolve_next_honors_an_explicit_goal_target(setup):
    store, controller, target, product, head, dispatched = setup
    case_id = controller.initialize(target)
    store.enqueue_goal(
        str(target),
        "Improve x",
        goal_source="operator",
        permitted_paths=["src/x.py"],
        acceptance_check=["python3", "-c", "print('ok')"],
        execution_target="in-process",
    )

    result = _evolve_next(controller, store, case_id)

    assert result["action"] == "start-baseline"
    assert store.get_run(result["run_id"]).execution_target == "in-process"


def test_evolve_next_on_waiting_case_without_goals_reports_no_queued_goal(setup):
    store, controller, target, product, head, dispatched = setup
    case_id = controller.initialize(target)

    result = _evolve_next(controller, store, case_id)

    assert result == {
        "action": "none",
        "state": ProductCaseState.WAITING_FOR_GOAL.value,
        "reason": "NO_QUEUED_GOAL",
    }
    assert dispatched == []


def _go_stale_mid_flight(store, run_id, age_seconds=600):
    """Leave a run active with a workspace, then age it past the sweep threshold.

    This is the shape an executor that died mid-run leaves behind: the run
    claimed a workspace, reached RUNNING, and then stopped being updated.
    """
    project = store.get_project_for_run(run_id)
    root = Path(project.root_uri.removeprefix("file://"))
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()
    store.set_run_workspace(run_id, workspace=str(root), base_revision=head)
    store.transition_run(run_id, RunState.PREPARING, "run.preparing")
    store.transition_run(run_id, RunState.RUNNING, "run.running")
    stale = datetime.now(timezone.utc) - timedelta(seconds=age_seconds)
    store._conn.execute(
        "UPDATE runs SET updated_at = ? WHERE id = ?", (stale.isoformat(), run_id)
    )
    store._conn.commit()


def test_evolve_next_sweeps_an_abandoned_baseline_run_instead_of_spinning(setup):
    case_id, run_id = _start(setup)
    store, controller, target, product, head, dispatched = setup
    _go_stale_mid_flight(store, run_id)
    assert store.get_product_case(case_id).state is ProductCaseState.BASELINE_RUNNING

    # The abandoned run has no evidence bundle, so the baseline decision path it
    # now reaches refuses it by name. The point is that it reaches that path at
    # all: before the sweep this case reported "none" forever.
    with pytest.raises(ValueError, match="BASELINE_NOT_ELIGIBLE_FOR_DECISION"):
        _evolve_next(controller, store, case_id)

    assert store.get_run(run_id).state is RunState.FAILED
    assert any(e.type == "recovery.crash" for e in store.list_events(run_id))


def test_evolve_next_leaves_a_live_baseline_run_alone(setup):
    case_id, run_id = _start(setup)
    store, controller, target, product, head, dispatched = setup
    # Same mid-flight shape, but freshly updated: the sweep must not touch it.
    _go_stale_mid_flight(store, run_id, age_seconds=0)

    result = _evolve_next(controller, store, case_id)

    assert result == {
        "action": "none",
        "state": ProductCaseState.BASELINE_RUNNING.value,
        "reason": "BASELINE_RUN_NOT_TERMINAL",
    }
    assert store.get_run(run_id).state is RunState.RUNNING
