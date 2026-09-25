import hashlib
import json
import sqlite3

import pytest

from mcp_server_nucleus.runs.models import ProductCaseState, outcome_score
from mcp_server_nucleus.runs.store import (
    ActiveProductCaseExists,
    InvalidProductCaseContract,
    InvalidProductCaseOutcome,
    InvalidProductCaseTransition,
    InvalidProductCaseUpdate,
    ProductCaseHashMismatch,
    ProductCasePreconditionError,
    RunStore,
    StaleProductCaseState,
)


@pytest.fixture
def store(tmp_path):
    with RunStore(str(tmp_path / "runs.db")) as value:
        yield value


@pytest.fixture
def project_root(tmp_path):
    return str(tmp_path / "repo")


def _contract(project_root, **updates):
    value = {
        "goal_source": "operator",
        "goal": "Improve the product loop",
        "project_root": project_root,
        "base_revision": "abc123",
        "permitted_paths": ["src/models.py", "src/store.py"],
        "acceptance_check": ["pytest", "-q"],
        "human_acceptance_required": True,
    }
    value.update(updates)
    return value


def _outcome(contract_sha256, **updates):
    value = {
        "contract_sha256": contract_sha256,
        "verdict": "ok",
        "apply_eligible": True,
        "accepted": True,
        "human_interventions": 0,
        "safety_violations": 0,
    }
    value.update(updates)
    return value


def _runs(store, count=3):
    project = store.create_project("file:///repo", "strict")
    conversation = store.create_conversation(project.id, "product loop")
    return [
        store.create_run(
            conversation.id,
            runner_id=f"runner-{index}",
            model_id=f"model-{index}",
            execution_target="local",
            mode="inspect",
            idempotency_key=f"key-{index}",
        )
        for index in range(count)
    ]


def _baseline_running(store, project_root):
    run = _runs(store, 1)[0]
    case = store.create_product_case(_contract(project_root), project_root)
    return store.transition_product_case(
        case.id,
        ProductCaseState.CONTRACTED,
        {"baseline_run_id": run.id},
    )


def _friction(store, project_root, owner="PRODUCT"):
    case = _baseline_running(store, project_root)
    outcome = _outcome(
        case.contract_sha256,
        accepted=False,
        verdict="fail",
        apply_eligible=False,
        human_interventions=2,
        safety_violations=1,
    )
    return store.transition_product_case(
        case.id,
        ProductCaseState.BASELINE_RUNNING,
        {"baseline_outcome": outcome, "failure_owner": owner, "friction": "observed friction"},
    )


def _row_bytes(store, case_id):
    row = store._conn.execute("SELECT * FROM product_cases WHERE id = ?", (case_id,)).fetchone()
    return tuple(row)


def test_schema_v9_and_canonical_contract_sha256(store, project_root):
    case = store.create_product_case(_contract(f"  {project_root}  "), f"  {project_root}  ")
    assert store._conn.execute("SELECT version FROM schema_version").fetchone()[0] == 9
    assert case.project_root == project_root
    assert case.contract_sha256 == hashlib.sha256(case.contract_json.encode()).hexdigest()
    assert json.loads(case.contract_json)["project_root"] == project_root


def test_baseline_accepted_frees_active_slot(store, project_root):
    case = _baseline_running(store, project_root)
    case = store.transition_product_case(
        case.id,
        ProductCaseState.BASELINE_RUNNING,
        {"baseline_outcome": _outcome(case.contract_sha256)},
    )
    assert case.state is ProductCaseState.BASELINE_ACCEPTED
    assert store.get_active_product_case(project_root) is None
    assert store.create_product_case(project_root=project_root).id != case.id


@pytest.mark.parametrize("owner", ["MODEL", "ENVIRONMENT", "CONTRACT", "TASK", "HUMAN"])
def test_limitation_recorded_frees_active_slot(store, project_root, owner):
    case = _friction(store, project_root, owner)
    case = store.transition_product_case(case.id, ProductCaseState.FRICTION_CLASSIFIED, {})
    assert case.state is ProductCaseState.LIMITATION_RECORDED
    assert store.get_active_product_case(project_root) is None
    assert store.create_product_case(project_root=project_root).id != case.id


def test_product_cannot_limitation_record_without_mutation(store, project_root):
    case = _friction(store, project_root)
    before = _row_bytes(store, case.id), len(store.list_product_case_events(case.id))
    with pytest.raises(ProductCasePreconditionError):
        store.transition_product_case(case.id, ProductCaseState.FRICTION_CLASSIFIED, {})
    assert (_row_bytes(store, case.id), len(store.list_product_case_events(case.id))) == before


@pytest.mark.parametrize("owner", ["MODEL", "ENVIRONMENT", "CONTRACT", "TASK", "HUMAN"])
def test_non_product_cannot_start_improvement(store, project_root, owner):
    case = _friction(store, project_root, owner)
    run = store.list_runs()[0]
    with pytest.raises(ProductCasePreconditionError):
        store.transition_product_case(
            case.id,
            ProductCaseState.FRICTION_CLASSIFIED,
            {"improvement_run_id": run.id},
        )


def test_product_improvement_requires_existing_run(store, project_root):
    case = _friction(store, project_root)
    with pytest.raises(ProductCasePreconditionError):
        store.transition_product_case(
            case.id,
            ProductCaseState.FRICTION_CLASSIFIED,
            {"improvement_run_id": "missing"},
        )


@pytest.mark.parametrize("field", ["goal_source", "goal", "base_revision"])
def test_contract_whitespace_only_strings_rejected(store, project_root, field):
    with pytest.raises(InvalidProductCaseContract):
        store.create_product_case(_contract(project_root, **{field: " \t "}), project_root)


def test_whitespace_only_project_root_rejected(store):
    with pytest.raises(ValueError):
        store.create_product_case(project_root=" \t ")


def test_whitespace_only_acceptance_argument_rejected(store, project_root):
    with pytest.raises(InvalidProductCaseContract):
        store.create_product_case(_contract(project_root, acceptance_check=["pytest", "  "]), project_root)


def test_whitespace_only_run_id_rejected_without_mutation(store, project_root):
    case = store.create_product_case(_contract(project_root), project_root)
    before = _row_bytes(store, case.id), len(store.list_product_case_events(case.id))
    with pytest.raises(InvalidProductCaseUpdate):
        store.transition_product_case(case.id, ProductCaseState.CONTRACTED, {"baseline_run_id": "  "})
    assert (_row_bytes(store, case.id), len(store.list_product_case_events(case.id))) == before


def test_whitespace_only_friction_rejected(store, project_root):
    case = _baseline_running(store, project_root)
    outcome = _outcome(case.contract_sha256, accepted=False, verdict="fail", apply_eligible=False)
    with pytest.raises(InvalidProductCaseUpdate):
        store.transition_product_case(
            case.id,
            ProductCaseState.BASELINE_RUNNING,
            {"baseline_outcome": outcome, "failure_owner": "PRODUCT", "friction": "  "},
        )


@pytest.mark.parametrize("field", ["contract_sha256", "verdict"])
def test_whitespace_only_outcome_strings_rejected(store, project_root, field):
    case = _baseline_running(store, project_root)
    outcome = _outcome(case.contract_sha256)
    outcome[field] = "  "
    with pytest.raises(InvalidProductCaseOutcome):
        store.transition_product_case(
            case.id,
            ProductCaseState.BASELINE_RUNNING,
            {"baseline_outcome": outcome},
        )


@pytest.mark.parametrize(
    "paths",
    [
        ["src/a", "src/./a"],
        [" src/a"],
        ["src/a "],
        ["."],
        [""],
        ["/src/a"],
        ["../src/a"],
        ["src\\a"],
        ["C:src/a"],
        ["src/\x00a"],
    ],
)
def test_invalid_and_normalized_alias_paths_rejected(store, project_root, paths):
    with pytest.raises(InvalidProductCaseContract):
        store.create_product_case(_contract(project_root, permitted_paths=paths), project_root)


def test_permitted_paths_are_normalized(store, project_root):
    case = store.create_product_case(_contract(project_root, permitted_paths=["src/./a"]), project_root)
    assert json.loads(case.contract_json)["permitted_paths"] == ["src/a"]


@pytest.mark.parametrize("payload", [None, [], "{}", 1])
def test_non_dict_audit_payload_rejected(store, project_root, payload):
    case = store.create_product_case(project_root=project_root)
    with pytest.raises(InvalidProductCaseUpdate):
        store.append_product_case_event(case.id, "audit", payload)


def test_audit_payload_is_canonical_and_event_type_nonblank(store, project_root):
    case = store.create_product_case(project_root=project_root)
    event = store.append_product_case_event(case.id, "audit", {"z": "é", "a": 1})
    payload = store._conn.execute("SELECT payload FROM product_case_events WHERE id = ?", (event.id,)).fetchone()[0]
    assert payload == '{"a":1,"z":"é"}'
    with pytest.raises(InvalidProductCaseUpdate):
        store.append_product_case_event(case.id, "  ", {})


def test_unrelated_integrity_error_is_not_active_case_error(store, project_root, monkeypatch):
    first = store.create_product_case(project_root=project_root)
    event_id = store.list_product_case_events(first.id)[0].id
    store._conn.execute("UPDATE product_cases SET state = ? WHERE id = ?", (ProductCaseState.REJECTED.value, first.id))
    store._conn.commit()
    monkeypatch.setattr(store, "_uuid", lambda: event_id)
    with pytest.raises(sqlite3.IntegrityError) as caught:
        store.create_product_case(project_root=project_root)
    assert not isinstance(caught.value, ActiveProductCaseExists)


def test_unrelated_fk_integrity_error_is_not_active_case_error(store, project_root):
    store._conn.execute("CREATE TABLE fk_parent (id TEXT PRIMARY KEY)")
    store._conn.execute("CREATE TABLE fk_guard (parent_id TEXT REFERENCES fk_parent(id))")
    store._conn.execute(
        "CREATE TRIGGER product_case_fk_guard BEFORE INSERT ON product_cases "
        "BEGIN INSERT INTO fk_guard(parent_id) VALUES ('missing'); END"
    )
    store._conn.commit()
    with pytest.raises(sqlite3.IntegrityError) as caught:
        store.create_product_case(project_root=project_root)
    assert caught.value.sqlite_errorname == "SQLITE_CONSTRAINT_FOREIGNKEY"
    assert not isinstance(caught.value, ActiveProductCaseExists)


def test_expected_state_wrong_type_rejected_without_mutation(store, project_root):
    case = store.create_product_case(_contract(project_root), project_root)
    before = _row_bytes(store, case.id), len(store.list_product_case_events(case.id))
    with pytest.raises(InvalidProductCaseTransition):
        store.transition_product_case(case.id, ProductCaseState.CONTRACTED.value, {"baseline_run_id": "x"})
    assert (_row_bytes(store, case.id), len(store.list_product_case_events(case.id))) == before


def test_stale_state_rejected_without_mutation(store, project_root):
    case = store.create_product_case(_contract(project_root), project_root)
    before = _row_bytes(store, case.id), len(store.list_product_case_events(case.id))
    with pytest.raises(StaleProductCaseState):
        store.transition_product_case(case.id, ProductCaseState.BASELINE_RUNNING, {})
    assert (_row_bytes(store, case.id), len(store.list_product_case_events(case.id))) == before


def test_outcome_exact_shape_hash_and_finite_json(store, project_root):
    case = _baseline_running(store, project_root)
    with pytest.raises(InvalidProductCaseOutcome):
        store.transition_product_case(
            case.id,
            ProductCaseState.BASELINE_RUNNING,
            {"baseline_outcome": _outcome(case.contract_sha256, extra=True)},
        )
    with pytest.raises(ProductCaseHashMismatch):
        store.transition_product_case(
            case.id,
            ProductCaseState.BASELINE_RUNNING,
            {"baseline_outcome": _outcome("wrong")},
        )
    with pytest.raises(InvalidProductCaseOutcome):
        store.transition_product_case(
            case.id,
            ProductCaseState.BASELINE_RUNNING,
            {"baseline_outcome": '{"accepted":NaN}'},
        )


def test_contract_non_json_value_rejected(store, project_root):
    with pytest.raises(InvalidProductCaseContract):
        store.create_product_case(_contract(project_root, goal=object()), project_root)


def test_atomic_contiguous_events(store, project_root):
    case = store.create_product_case(_contract(project_root), project_root)
    store.append_product_case_event(case.id, "audit.one", {})
    with pytest.raises(InvalidProductCaseUpdate):
        store.append_product_case_event(case.id, "audit.bad", {"value": float("nan")})
    store.append_product_case_event(case.id, "audit.two", {})
    assert [event.seq for event in store.list_product_case_events(case.id)] == [1, 2, 3]


def test_active_uniqueness(store, project_root):
    store.create_product_case(project_root=project_root)
    with pytest.raises(ActiveProductCaseExists):
        store.create_product_case(project_root=project_root)


def test_run_links_restrict_delete(store, project_root):
    case = _baseline_running(store, project_root)
    with pytest.raises(sqlite3.IntegrityError):
        store._conn.execute("DELETE FROM runs WHERE id = ?", (case.baseline_run_id,))
    store._conn.rollback()


def test_outcome_score_orders_safer_lower_touch_outcome():
    baseline = _outcome("hash", accepted=False, verdict="fail", apply_eligible=False, human_interventions=3, safety_violations=1)
    replay = _outcome("hash", human_interventions=1)
    assert outcome_score(replay) > outcome_score(baseline)
