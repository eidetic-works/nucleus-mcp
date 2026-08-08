"""MCP tool facade for W8 Team-tier audit log.

Exposes ``nucleus_audit`` — a facade tool with four actions:

Actions:
  log_event   - Append an audit event. params: {event_type, actor, resource,
                outcome, metadata?, team_id?, ts?}
  query       - Query audit records for ONE team. Rejects team_id='*'.
                params: {team_id, since?, until?, actor?, event_type?, limit?, offset?}
  admin_query - Cross-tenant query (team_id='*' allowed). Requires admin token
                in env NUCLEUS_AUDIT_ADMIN_TOKEN. params: {admin_token, team_id?,
                since?, until?, actor?, event_type?, limit?, offset?}
  verify      - Verify chain integrity for a team. params: {team_id}

This module follows the Super-Tools facade pattern used by other tool modules.
Only Team-tier subscribers should have nucleus_audit in their allowed-tools list.

Multi-tenant ACL (closes cc-peer C1 on PR #595): the ``query`` action is the
single-tenant entry point and explicitly rejects ``team_id='*'``. Cross-tenant
reads go through ``admin_query``, which requires a constant-time match against
``NUCLEUS_AUDIT_ADMIN_TOKEN``. If the env var is unset or empty, ``admin_query``
is hard-disabled. Every successful ``admin_query`` is itself appended to a
synthetic ``__admin__`` team chain for dogfood audit-of-audit.
"""

import hmac
import json
import logging
import os

from ._dispatch import async_dispatch, resolve_make_response

logger = logging.getLogger("nucleus.tool.audit_log")


def register(mcp, helpers):
    """Register the nucleus_audit facade tool."""
    make_response = resolve_make_response(helpers)

    from ..runtime.audit_log import log_event, query_audit, verify_chain, AuditRecord

    def _record_to_dict(r: AuditRecord) -> dict:
        return {
            "id": r.id,
            "team_id": r.team_id,
            "event_type": r.event_type,
            "actor": r.actor,
            "resource": r.resource,
            "outcome": r.outcome,
            "metadata": r.metadata,
            "ts": r.ts,
            "prev_hash": r.prev_hash,
            "hash": r.hash,
        }

    def _admin_token_ok(supplied: str) -> bool:
        expected = os.environ.get("NUCLEUS_AUDIT_ADMIN_TOKEN", "")
        if not expected or not supplied:
            return False
        return hmac.compare_digest(supplied, expected)

    def _h_log_event(**params):
        event_type = params.get("event_type", "")
        actor = params.get("actor", "")
        resource = params.get("resource", "")
        outcome = params.get("outcome", "")
        if not all([event_type, actor, resource, outcome]):
            return make_response(
                False,
                error="log_event requires: event_type, actor, resource, outcome",
            )
        record = log_event(
            event_type=event_type,
            actor=actor,
            resource=resource,
            outcome=outcome,
            metadata=params.get("metadata"),
            team_id=params.get("team_id", "default"),
            ts=params.get("ts"),
        )
        return make_response(True, data=_record_to_dict(record))

    def _h_query(**params):
        team_id = params.get("team_id", "default")
        if team_id == "*":
            return make_response(
                False,
                error="query rejects team_id='*'. Use admin_query with NUCLEUS_AUDIT_ADMIN_TOKEN.",
            )
        records = query_audit(
            team_id=team_id,
            since=params.get("since"),
            until=params.get("until"),
            actor=params.get("actor"),
            event_type=params.get("event_type"),
            limit=params.get("limit", 100),
            offset=params.get("offset", 0),
        )
        return make_response(
            True,
            data={"count": len(records), "records": [_record_to_dict(r) for r in records]},
        )

    def _h_admin_query(**params):
        supplied_token = params.get("admin_token", "")
        if not _admin_token_ok(supplied_token):
            logger.warning("nucleus_audit admin_query rejected (bad/missing token)")
            return make_response(False, error="admin_query: invalid or missing admin_token")
        team_id = params.get("team_id", "*")
        records = query_audit(
            team_id=team_id,
            since=params.get("since"),
            until=params.get("until"),
            actor=params.get("actor"),
            event_type=params.get("event_type"),
            limit=params.get("limit", 100),
            offset=params.get("offset", 0),
        )
        dogfood_log_ok = True
        try:
            log_event(
                event_type="admin_query",
                actor="admin",
                resource=f"audit_log:team_id={team_id}",
                outcome="success",
                metadata={
                    "filters": {
                        k: params.get(k)
                        for k in ("since", "until", "actor", "event_type")
                        if params.get(k)
                    },
                    "result_count": len(records),
                },
                team_id="__admin__",
            )
        except Exception:
            dogfood_log_ok = False
            logger.exception("admin_query dogfood log failed (non-fatal)")
        return make_response(
            True,
            data={
                "count": len(records),
                "records": [_record_to_dict(r) for r in records],
                "dogfood_log_ok": dogfood_log_ok,
            },
        )

    def _h_verify(**params):
        team_id = params.get("team_id", "default")
        ok, broken_at = verify_chain(team_id=team_id)
        return make_response(
            ok,
            data={"chain_ok": ok, "broken_at_id": broken_at},
        )

    ROUTER = {
        "log_event": _h_log_event,
        "query": _h_query,
        "admin_query": _h_admin_query,
        "verify": _h_verify,
    }

    # These handlers absorb **params, so _dispatch cannot read their contract
    # from the signature (see _dispatch._allowed_param_names). Declare it
    # explicitly. Keys transcribed from the handler bodies — every params.get()
    # is covered and nothing extra is granted. Without this, admin_query — the
    # cross-tenant path gated on NUCLEUS_AUDIT_ADMIN_TOKEN — accepts and
    # silently discards arbitrary keys.
    _h_log_event._nucleus_params = (
        "event_type", "actor", "resource", "outcome", "metadata", "team_id", "ts",
    )
    _h_query._nucleus_params = (
        "team_id", "since", "until", "actor", "event_type", "limit", "offset",
    )
    _h_admin_query._nucleus_params = (
        "admin_token", "team_id", "since", "until", "actor", "event_type",
        "limit", "offset",
    )
    _h_verify._nucleus_params = ("team_id",)
    _LOG_LABELS = {
        "log_event": "nucleus_audit log_event failed",
        "query": "nucleus_audit query failed",
        "admin_query": "nucleus_audit admin_query failed",
        "verify": "nucleus_audit verify failed",
    }

    @mcp.tool(title="Audit Log", annotations={"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False})
    async def nucleus_audit(action: str, params: dict = {}) -> str:
        """W8 Team-tier tamper-evident audit log (SHA-256 hash chain).

Actions:
  log_event   - Append an audit event to the chain.
                params: {event_type, actor, resource, outcome, metadata?, team_id?, ts?}
  query       - Single-tenant query. Rejects team_id='*'.
                params: {team_id, since?, until?, actor?, event_type?, limit?, offset?}
  admin_query - Cross-tenant query (team_id='*' allowed). Requires
                NUCLEUS_AUDIT_ADMIN_TOKEN env match. Logs every successful
                call to the synthetic '__admin__' chain.
                params: {admin_token, team_id?, since?, until?, actor?, event_type?, limit?, offset?}
  verify      - Verify SHA-256 chain integrity for a team.
                params: {team_id}
"""
        return await async_dispatch(
            action,
            params,
            ROUTER,
            "nucleus_audit",
        )

    return [("nucleus_audit", nucleus_audit)]
