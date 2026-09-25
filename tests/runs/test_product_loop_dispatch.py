import pytest

from mcp_server_nucleus.runs.product_loop import ProductLoopController
from mcp_server_nucleus.runs.store import RunStore


def test_timed_dispatch_raises_captured_exception(tmp_path):
    db_path = tmp_path / "runs.db"
    product_root = tmp_path / "product"
    product_root.mkdir()
    store = RunStore(db_path)

    class CustomDispatchError(Exception):
        pass

    def failing_dispatch(run_id: str):
        raise CustomDispatchError("dispatch error occurred")

    controller = ProductLoopController(
        store=store,
        db_path=db_path,
        product_root=product_root,
        dispatch=failing_dispatch,
        dispatch_timeout=1.0,
    )

    with pytest.raises(CustomDispatchError, match="dispatch error occurred"):
        controller.dispatch("dummy-run-id")
