"""Coverage tests for mcp_server_nucleus/selfhealer.py — the intent-level
self-healing engine (4-dimension context capture, classification, deterministic
fixes, LLM diagnosis, and the SelfHealer orchestrator)."""
import json
import types
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from mcp_server_nucleus import selfhealer


# ── fixtures ────────────────────────────────────────────────────────

@pytest.fixture
def brain(tmp_path):
    bp = tmp_path / ".brain"
    (bp / "ledger").mkdir(parents=True)
    (bp / "engrams").mkdir(parents=True)
    (bp / "sessions").mkdir(parents=True)
    (bp / "tasks").mkdir(parents=True)
    return bp


@pytest.fixture
def healer(brain):
    return selfhealer.SelfHealer(brain_path=brain)


# ── _get_error_output ───────────────────────────────────────────────

class TestGetErrorOutput:
    def test_captures_type_message_traceback(self):
        try:
            raise ValueError("boom")
        except ValueError as e:
            out = selfhealer._get_error_output(e)
        assert out["type"] == "ValueError"
        assert out["message"] == "boom"
        assert "ValueError" in out["traceback"]


# ── _get_code_file ──────────────────────────────────────────────────

class TestGetCodeFile:
    def test_no_traceback_returns_unavailable(self):
        assert selfhealer._get_code_file(None) == {"available": False}

    def test_with_traceback_reads_source(self, tmp_path):
        src = tmp_path / "mod.py"
        src.write_text("\n".join(f"line {i}" for i in range(40)) + "\nraise X\n")

        # Raise a real exception so we get a genuine traceback pointing at this file
        try:
            exec(compile("raise RuntimeError('hit')\n", str(src), "exec"))
        except RuntimeError:
            out = selfhealer._get_code_file()
        assert out["available"] is True
        assert out["filename"] == str(src)
        assert isinstance(out["source_lines"], list)

    def test_walks_to_innermost_frame(self, tmp_path):
        src = tmp_path / "inner.py"
        src.write_text("a\nb\nc\nd\ne\n")

        def outer():
            exec(compile("raise RuntimeError('hit')\n", str(src), "exec"))

        try:
            outer()
        except RuntimeError:
            out = selfhealer._get_code_file()
        assert out["available"] is True
        # innermost frame points at src
        assert out["filename"] == str(src)

    def test_unreadable_file_still_available(self, tmp_path):
        # Point a real traceback at a file that doesn't exist on disk
        try:
            exec(compile("raise RuntimeError('hit')\n", "/nonexistent/path/x.py", "exec"))
        except RuntimeError:
            out = selfhealer._get_code_file()
        assert out["available"] is True
        assert out["source_lines"] == []


# ── _get_intent_context ─────────────────────────────────────────────

class TestGetIntentContext:
    def test_empty_brain(self, brain):
        intent = selfhealer._get_intent_context(brain)
        assert intent["engrams"] == []
        assert intent["active_task"] is None
        assert intent["active_session"] is None

    def test_reads_engrams_and_tasks(self, brain):
        (brain / "engrams" / "ledger.jsonl").write_text(
            json.dumps({"key": "k1", "value": "v1", "intensity": 5, "timestamp": "2026-01-01"}) + "\n"
            + json.dumps({"key": "k2", "value": "v2", "intensity": 9, "timestamp": "2026-01-02"}) + "\n"
            + "not json\n"
        )
        (brain / "tasks" / "ledger.jsonl").write_text(
            json.dumps({"id": "t1", "status": "IN_PROGRESS"}) + "\n"
            + json.dumps({"id": "t2", "status": "DONE"}) + "\n"
            + "bad\n"
        )
        (brain / "sessions" / "active.json").write_text(json.dumps({"sid": "s1"}))
        intent = selfhealer._get_intent_context(brain)
        assert len(intent["engrams"]) == 2
        assert intent["engrams"][0]["key"] == "k2"  # higher intensity first
        assert intent["active_task"]["id"] == "t1"
        assert intent["active_session"]["sid"] == "s1"

    def test_corrupt_active_session(self, brain):
        (brain / "sessions" / "active.json").write_text("{bad json")
        intent = selfhealer._get_intent_context(brain)
        assert intent["active_session"] is None


# ── _get_recent_history ─────────────────────────────────────────────

class TestGetRecentHistory:
    def test_git_unavailable(self):
        with patch("subprocess.run", side_effect=Exception("no git")):
            hist = selfhealer._get_recent_history()
        assert hist["git_available"] is False

    def test_git_success(self):
        runs = [
            MagicMock(returncode=0, stdout="file.py|5\n"),
            MagicMock(returncode=0, stdout="abc123 msg\n"),
            MagicMock(returncode=0, stdout=" M file.py\n"),
        ]
        with patch("subprocess.run", side_effect=runs):
            hist = selfhealer._get_recent_history()
        assert hist["git_available"] is True
        assert hist["recent_diff_stat"] == "file.py|5"
        assert hist["recent_commits"] == ["abc123 msg"]
        assert hist["dirty"] is True

    def test_partial_git_failure(self):
        runs = [
            MagicMock(returncode=1, stdout="", stderr="err"),
            MagicMock(returncode=0, stdout="abc123 msg\n"),
            MagicMock(returncode=0, stdout=""),
        ]
        with patch("subprocess.run", side_effect=runs):
            hist = selfhealer._get_recent_history()
        assert hist["git_available"] is False
        assert "recent_commits" in hist
        assert hist["dirty"] is False


# ── get_full_context ────────────────────────────────────────────────

class TestGetFullContext:
    def test_structure(self, brain):
        ctx = selfhealer.get_full_context(ValueError("x"), brain, "cmd", {"a": 1})
        assert ctx["command"] == "cmd"
        assert ctx["args"] == {"a": 1}
        assert ctx["error_output"]["type"] == "ValueError"
        assert "system" in ctx
        assert ctx["system"]["brain_path"] == str(brain)
        assert ctx["id"].startswith("err-")


# ── classify_error ──────────────────────────────────────────────────

class TestClassifyError:
    def _info(self, etype, msg):
        return {"error_output": {"type": etype, "message": msg}}

    def test_permission(self):
        c = selfhealer.classify_error(self._info("PermissionError", "permission denied"))
        assert c["type"] == "permission_error"
        assert c["recoverable"] is True

    def test_file_not_found(self):
        c = selfhealer.classify_error(self._info("FileNotFoundError", "no such file"))
        assert c["type"] == "file_not_found"

    def test_brain_not_found(self):
        c = selfhealer.classify_error(self._info("ValueError", "brain not found"))
        assert c["type"] == "brain_not_found"

    def test_brain_not_set(self):
        c = selfhealer.classify_error(self._info("RuntimeError", "brain not set"))
        assert c["type"] == "brain_not_found"

    def test_data_corruption(self):
        c = selfhealer.classify_error(self._info("JSONDecodeError", "json decode expecting value"))
        assert c["type"] == "data_corruption"
        assert c["recoverable"] is False

    def test_network_error(self):
        for t in ("ConnectionError", "TimeoutError", "ConnectionRefusedError"):
            c = selfhealer.classify_error(self._info(t, "x"))
            assert c["type"] == "network_error"

    def test_import_error(self):
        c = selfhealer.classify_error(self._info("ModuleNotFoundError", "x"))
        assert c["type"] == "import_error"

    def test_code_bug(self):
        for t in ("KeyError", "TypeError", "AttributeError"):
            c = selfhealer.classify_error(self._info(t, "x"))
            assert c["type"] == "code_bug"

    def test_runtime_fallback(self):
        c = selfhealer.classify_error(self._info("RuntimeError", "something odd"))
        assert c["type"] == "runtime_error"


# ── attempt_deterministic_fix ───────────────────────────────────────

class TestDeterministicFix:
    def _info(self, brain, msg="x", etype="Error"):
        return {
            "system": {"brain_path": str(brain), "working_dir": str(brain.parent)},
            "error_output": {"message": msg, "type": etype},
        }

    def test_permission_fix(self, brain):
        info = self._info(brain)
        cls = {"type": "permission_error"}
        r = selfhealer.attempt_deterministic_fix(info, cls)
        assert r["attempted"] is True
        assert r["fixed"] is True

    def test_permission_fix_fails(self, brain):
        info = self._info(brain)
        cls = {"type": "permission_error"}
        with patch("os.chmod", side_effect=PermissionError("nope")):
            r = selfhealer.attempt_deterministic_fix(info, cls)
        assert r["attempted"] is True
        assert r["fixed"] is False
        assert r["suggestions"]

    def test_brain_not_found_found(self, tmp_path, brain):
        cwd = brain.parent
        (cwd / ".brain").mkdir(exist_ok=True)
        info = {"system": {"brain_path": str(tmp_path / "missing"), "working_dir": str(cwd)}}
        cls = {"type": "brain_not_found"}
        r = selfhealer.attempt_deterministic_fix(info, cls)
        assert r["fixed"] is True
        assert "Found brain" in r["action"]

    def test_brain_not_found_not_found(self, tmp_path, brain, monkeypatch):
        # Use a clean cwd with no .brain and patch home to a non-existent dir
        clean = tmp_path / "clean"
        clean.mkdir()
        monkeypatch.chdir(clean)
        monkeypatch.setattr(Path, "home", lambda: tmp_path / "nonexistent_home")
        info = {"system": {"brain_path": str(tmp_path / "missing"), "working_dir": str(clean)}}
        cls = {"type": "brain_not_found"}
        r = selfhealer.attempt_deterministic_fix(info, cls)
        assert r["fixed"] is False
        assert r["suggestions"]

    def test_file_not_found_brain_dir(self, brain):
        info = self._info(brain, msg=f"missing {brain}")
        cls = {"type": "file_not_found"}
        r = selfhealer.attempt_deterministic_fix(info, cls)
        assert r["fixed"] is True
        assert "Created" in r["action"]

    def test_file_not_found_other(self, brain):
        info = self._info(brain, msg="missing /etc/hosts")
        cls = {"type": "file_not_found"}
        r = selfhealer.attempt_deterministic_fix(info, cls)
        assert r["fixed"] is False
        assert r["suggestions"]

    def test_file_not_found_create_fails(self, brain):
        info = self._info(brain, msg=f"missing {brain}")
        cls = {"type": "file_not_found"}
        with patch("pathlib.Path.mkdir", side_effect=OSError("nope")):
            r = selfhealer.attempt_deterministic_fix(info, cls)
        assert r["fixed"] is False
        assert "creation failed" in r["action"]

    def test_network_error(self, brain):
        info = self._info(brain)
        cls = {"type": "network_error"}
        r = selfhealer.attempt_deterministic_fix(info, cls)
        assert r["attempted"] is True
        assert r["suggestions"]

    def test_unhandled_type(self, brain):
        info = self._info(brain)
        cls = {"type": "code_bug"}
        r = selfhealer.attempt_deterministic_fix(info, cls)
        assert r["attempted"] is False


# ── _build_llm_prompt ───────────────────────────────────────────────

class TestBuildPrompt:
    def test_full_prompt(self):
        info = {
            "error_output": {"type": "ValueError", "message": "boom", "traceback": "tb\n"},
            "code_file": {"available": True, "filename": "f.py", "lineno": 3,
                          "function": "fn", "source_lines": [{"line": 3, "code": "x", "is_error": True}]},
            "intent": {"active_task": {"description": "do thing", "status": "IN_PROGRESS"},
                       "engrams": [{"context": "Decision", "key": "k", "value": "v" * 200}]},
            "recent_history": {"recent_commits": ["abc msg"], "uncommitted": " M f.py"},
        }
        cls = {"type": "runtime_error", "severity": "medium"}
        prompt = selfhealer._build_llm_prompt(info, cls)
        assert "ValueError" in prompt
        assert "f.py:3" in prompt
        assert "ACTIVE TASK" in prompt
        assert "RECENT ENGRAMS" in prompt
        assert "RECENT COMMITS" in prompt
        assert "UNCOMMITTED CHANGES" in prompt
        assert "CLASSIFICATION" in prompt

    def test_prompt_minimal(self):
        info = {"error_output": {"type": "E", "message": "m", "traceback": "NoneType: None\n"}}
        cls = {"type": "x", "severity": "low"}
        prompt = selfhealer._build_llm_prompt(info, cls)
        assert "ERROR" in prompt
        assert "Traceback" not in prompt


# ── llm_diagnose ────────────────────────────────────────────────────

class TestLLMDiagnose:
    def test_import_error(self):
        info = {"error_output": {"type": "E", "message": "m", "traceback": ""},
                "code_file": {"available": False}, "intent": {}, "recent_history": {}}
        cls = {"type": "x", "severity": "low"}
        with patch.dict("sys.modules", {"mcp_server_nucleus.runtime.llm_client": None}):
            with patch("builtins.__import__", side_effect=ImportError("no module")):
                r = selfhealer.llm_diagnose(info, cls)
        assert r["llm_used"] is False
        assert "not available" in r["diagnosis"]

    def test_json_response(self):
        info = {"error_output": {"type": "E", "message": "m", "traceback": ""},
                "code_file": {"available": False}, "intent": {}, "recent_history": {}}
        cls = {"type": "x", "severity": "low"}
        llm = MagicMock()
        llm.generate.return_value = '{"diagnosis": "d", "fix": "f", "confidence": 0.9, "needs_human": false}'
        with patch("mcp_server_nucleus.runtime.llm_client.DualEngineLLM", return_value=llm):
            r = selfhealer.llm_diagnose(info, cls)
        assert r["llm_used"] is True
        assert r["diagnosis"] == "d"
        assert r["fix"] == "f"
        assert r["confidence"] == 0.9

    def test_non_json_response(self):
        info = {"error_output": {"type": "E", "message": "m", "traceback": ""},
                "code_file": {"available": False}, "intent": {}, "recent_history": {}}
        cls = {"type": "x", "severity": "low"}
        llm = MagicMock()
        llm.generate.return_value = "just some text"
        with patch("mcp_server_nucleus.runtime.llm_client.DualEngineLLM", return_value=llm):
            r = selfhealer.llm_diagnose(info, cls)
        assert r["llm_used"] is True
        assert r["diagnosis"] == "just some text"

    def test_llm_exception(self):
        info = {"error_output": {"type": "E", "message": "m", "traceback": ""},
                "code_file": {"available": False}, "intent": {}, "recent_history": {}}
        cls = {"type": "x", "severity": "low"}
        llm = MagicMock()
        llm.generate.side_effect = RuntimeError("boom")
        with patch("mcp_server_nucleus.runtime.llm_client.DualEngineLLM", return_value=llm):
            r = selfhealer.llm_diagnose(info, cls)
        assert r["llm_used"] is False
        assert "failed" in r["diagnosis"]


# ── SelfHealer ──────────────────────────────────────────────────────

class TestSelfHealer:
    def test_init_default_brain(self, monkeypatch, tmp_path):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / ".brain"))
        h = selfhealer.SelfHealer()
        assert h.brain_path == tmp_path / ".brain"

    def test_init_get_brain_path_fails(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
        monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
        with patch("mcp_server_nucleus.selfhealer.get_brain_path", side_effect=ValueError("no brain")):
            h = selfhealer.SelfHealer()
        assert h.brain_path == (tmp_path / ".brain")

    def test_handle_error_fixed_deterministic(self, healer, brain):
        with patch("mcp_server_nucleus.selfhealer.get_full_context") as gfc, \
             patch("mcp_server_nucleus.selfhealer.classify_error", return_value={"type": "permission_error", "severity": "high"}), \
             patch("mcp_server_nucleus.selfhealer.attempt_deterministic_fix",
                   return_value={"attempted": True, "fixed": True, "action": "ok", "suggestions": []}):
            gfc.return_value = {"id": "err-1", "timestamp": "t", "error_output": {"type": "E", "message": "m"},
                                "code_file": {}, "intent": {}, "recent_history": {}, "system": {"brain_path": str(brain)}}
            r = healer.handle_error(ValueError("x"), use_llm=False)
        assert r["ok"] is False
        assert r["self_heal"]["fixed"] is True
        assert r["self_heal"]["needs_human"] is False

    def test_handle_error_needs_llm(self, healer, brain):
        with patch("mcp_server_nucleus.selfhealer.get_full_context") as gfc, \
             patch("mcp_server_nucleus.selfhealer.classify_error", return_value={"type": "code_bug", "severity": "high"}), \
             patch("mcp_server_nucleus.selfhealer.attempt_deterministic_fix",
                   return_value={"attempted": False, "fixed": False, "action": None, "suggestions": []}), \
             patch("mcp_server_nucleus.selfhealer.llm_diagnose",
                   return_value={"diagnosis": "d", "fix": "f", "confidence": 0.5, "needs_human": True, "llm_used": True}):
            gfc.return_value = {"id": "err-2", "timestamp": "t", "error_output": {"type": "E", "message": "m"},
                                "code_file": {}, "intent": {}, "recent_history": {}, "system": {"brain_path": str(brain)}}
            r = healer.handle_error(ValueError("x"), use_llm=True)
        assert r["self_heal"]["llm_diagnosis"]["diagnosis"] == "d"
        assert r["self_heal"]["needs_human"] is True
        assert "f" in r["self_heal"]["suggestions"]

    def test_handle_error_llm_no_fix(self, healer, brain):
        with patch("mcp_server_nucleus.selfhealer.get_full_context") as gfc, \
             patch("mcp_server_nucleus.selfhealer.classify_error", return_value={"type": "code_bug", "severity": "high"}), \
             patch("mcp_server_nucleus.selfhealer.attempt_deterministic_fix",
                   return_value={"attempted": False, "fixed": False, "action": None, "suggestions": []}), \
             patch("mcp_server_nucleus.selfhealer.llm_diagnose",
                   return_value={"diagnosis": "d", "fix": "", "confidence": 0.0, "needs_human": True, "llm_used": True}):
            gfc.return_value = {"id": "err-3", "timestamp": "t", "error_output": {"type": "E", "message": "m"},
                                "code_file": {}, "intent": {}, "recent_history": {}, "system": {"brain_path": str(brain)}}
            r = healer.handle_error(ValueError("x"))
        assert r["self_heal"]["suggestions"] == []

    def test_log_incident_writes_file(self, healer, brain):
        info = {"id": "err-x", "timestamp": "t", "command": "cmd",
                "error_output": {"type": "E", "message": "m"}, "code_file": {"filename": "f", "lineno": 1}}
        cls = {"type": "x", "severity": "low"}
        det = {"attempted": False, "fixed": False, "action": None}
        llm = {"llm_used": False, "diagnosis": "", "confidence": 0, "needs_human": True}
        healer._log_incident(info, cls, det, llm)
        log = (brain / "ledger" / "selfheal_log.jsonl").read_text()
        entry = json.loads(log.strip())
        assert entry["id"] == "err-x"
        assert entry["command"] == "cmd"

    def test_log_incident_silent_on_failure(self, brain):
        h = selfhealer.SelfHealer(brain_path=brain)
        # Force the log path to be unwritable by pointing at a file path under a non-dir
        h.error_log_path = Path("/proc/cannot/write/here.jsonl")
        info = {"id": "e", "timestamp": "t", "command": "", "error_output": {"type": "E", "message": "m"}}
        # Should not raise
        h._log_incident(info, {"type": "x", "severity": "low"}, {"attempted": False, "fixed": False}, {})


# ── public API ──────────────────────────────────────────────────────

class TestPublicAPI:
    def test_get_self_healer_singleton(self, brain, monkeypatch):
        import mcp_server_nucleus.selfhealer as sh
        sh._self_healer = None
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        h1 = sh.get_self_healer()
        h2 = sh.get_self_healer()
        assert h1 is h2
        sh._self_healer = None

    def test_handle_cli_error(self, brain, monkeypatch):
        import mcp_server_nucleus.selfhealer as sh
        sh._self_healer = None
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        with patch.object(sh.SelfHealer, "handle_error", return_value={"ok": False}) as m:
            r = sh.handle_cli_error(ValueError("x"), "cmd", use_llm=False)
        assert r == {"ok": False}
        m.assert_called_once()
        sh._self_healer = None

    def test_diagnose_and_fix_with_context(self, brain, monkeypatch):
        import mcp_server_nucleus.selfhealer as sh
        sh._self_healer = None
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        with patch.object(sh.SelfHealer, "handle_error", return_value={"ok": False}) as m:
            r = sh.diagnose_and_fix(ValueError("x"), context={"command": "cmd"}, use_llm=False)
        assert r == {"ok": False}
        args, kwargs = m.call_args
        # handle_error(exc, command, args, use_llm=...) — command is positional arg[1]
        assert args[1] == "cmd"
        sh._self_healer = None

    def test_diagnose_and_fix_with_source_context(self, brain, monkeypatch):
        import mcp_server_nucleus.selfhealer as sh
        sh._self_healer = None
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        with patch.object(sh.SelfHealer, "handle_error", return_value={"ok": False}) as m:
            sh.diagnose_and_fix(ValueError("x"), context={"source": "src"}, use_llm=False)
        args, kwargs = m.call_args
        assert args[1] == "src"
        sh._self_healer = None

    def test_diagnose_and_fix_no_context(self, brain, monkeypatch):
        import mcp_server_nucleus.selfhealer as sh
        sh._self_healer = None
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        with patch.object(sh.SelfHealer, "handle_error", return_value={"ok": False}) as m:
            sh.diagnose_and_fix(ValueError("x"), use_llm=False)
        args, kwargs = m.call_args
        assert args[1] == ""
        sh._self_healer = None
