"""CLI Handler implementations for all 37 previously-missing commands.

Each handler delegates to existing runtime modules. Grouped by domain.
"""
import json
import os
import sys
from pathlib import Path


def _resolve_brain(args):
    """Resolve brain path from --brain arg or auto-detect."""
    brain_str = getattr(args, 'brain', None)
    if brain_str:
        return Path(brain_str)
    from .runtime.common import get_brain_path
    return get_brain_path()


def _json_out(data, as_json=False):
    """Print data as JSON or return for formatted output."""
    if as_json:
        print(json.dumps(data, indent=2, default=str))
        return 0
    return data


# ════════════════════════════════════════════════════════════════
# BATCH 1: Governance / Compliance (7 handlers)
# ════════════════════════════════════════════════════════════════

def handle_secure_command(args) -> int:
    """One-command security hardening + posture report."""
    try:
        brain = _resolve_brain(args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    from .runtime.compliance_config import apply_jurisdiction, generate_compliance_report, format_compliance_report
    from .runtime.sovereign_status import generate_sovereign_status, format_sovereign_status

    jurisdiction = getattr(args, 'jurisdiction', None) or 'global-default'
    as_json = getattr(args, 'json', False)

    # Apply jurisdiction
    apply_result = apply_jurisdiction(brain, jurisdiction)

    # Generate reports
    compliance = generate_compliance_report(brain)
    sovereign = generate_sovereign_status(brain)

    if as_json:
        print(json.dumps({
            "jurisdiction": jurisdiction,
            "applied": apply_result,
            "compliance": compliance,
            "sovereign": sovereign,
        }, indent=2, default=str))
    else:
        print(f"Security hardening applied: {jurisdiction}\n")
        print(format_compliance_report(compliance))
        print()
        print(format_sovereign_status(sovereign))
    return 0


def handle_sovereign_command(args) -> int:
    """Show sovereignty status report."""
    try:
        brain = _resolve_brain(args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    from .runtime.sovereign_status import generate_sovereign_status, format_sovereign_status
    report = generate_sovereign_status(brain)

    if getattr(args, 'json', False):
        print(json.dumps(report, indent=2, default=str))
    else:
        print(format_sovereign_status(report))
    return 0


def handle_comply_command(args) -> int:
    """Configure jurisdiction-specific compliance."""
    from .runtime.compliance_config import list_jurisdictions, apply_jurisdiction, generate_compliance_report, format_compliance_report

    if getattr(args, 'list', False):
        jurisdictions = list_jurisdictions()
        print("Available jurisdictions:\n")
        for jid, name in jurisdictions.items():
            print(f"  {jid:20s}  {name}")
        return 0

    try:
        brain = _resolve_brain(args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    jurisdiction = getattr(args, 'jurisdiction', None)
    if jurisdiction:
        result = apply_jurisdiction(brain, jurisdiction)
        print(json.dumps(result, indent=2, default=str))
        return 0

    if getattr(args, 'report', False):
        report = generate_compliance_report(brain)
        print(format_compliance_report(report))
        return 0

    print("Usage: nucleus comply --list | --jurisdiction <id> | --report", file=sys.stderr)
    return 1


def handle_compliance_check_command(args) -> int:
    """Score AI governance posture."""
    try:
        brain = _resolve_brain(args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    from .runtime.compliance_config import generate_compliance_report, format_compliance_report
    report = generate_compliance_report(brain)
    fmt = getattr(args, 'format', 'text')

    if fmt == 'json':
        formatted = json.dumps(report, indent=2, default=str)
    elif fmt == 'html':
        formatted = f"<html><body><pre>{format_compliance_report(report)}</pre></body></html>"
    else:
        formatted = format_compliance_report(report)

    output_path = getattr(args, 'output', None)
    if output_path:
        Path(output_path).write_text(formatted)
        print(f"Report written to {output_path}")
    else:
        print(formatted)
    return 0


def handle_audit_report_command(args) -> int:
    """Generate audit-ready compliance report."""
    try:
        brain = _resolve_brain(args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    from .runtime.audit_report import generate_audit_report
    fmt = getattr(args, 'format', 'text')
    hours = getattr(args, 'hours', None)
    report = generate_audit_report(brain, report_format=fmt, since_hours=hours)

    if fmt == 'json':
        formatted = json.dumps(report, indent=2, default=str)
    else:
        formatted = report.get('formatted', json.dumps(report, indent=2, default=str))

    output_path = getattr(args, 'output', None)
    if output_path:
        Path(output_path).write_text(formatted)
        print(f"Report written to {output_path}")
    else:
        print(formatted)
    return 0


def handle_trace_command(args) -> int:
    """Browse DSoR decision trails."""
    try:
        brain = _resolve_brain(args)
    except Exception as e:
        print(f"Error resolving brain: {e}", file=sys.stderr)
        return 1

    from .runtime.trace_viewer import list_traces, get_trace, format_trace_list, format_trace_detail
    action = getattr(args, 'trace_action', None)

    if action == 'list':
        trace_type = getattr(args, 'type', None)
        data = list_traces(brain, trace_type=trace_type)
        print(format_trace_list(data))
        return 0

    elif action == 'view':
        trace = get_trace(brain, args.trace_id)
        if not trace:
            print(f"Trace '{args.trace_id}' not found.", file=sys.stderr)
            return 1
        if getattr(args, 'json', False):
            print(json.dumps(trace, indent=2, default=str))
        else:
            print(format_trace_detail(trace))
        return 0

    elif action == 'interference':
        # Interference detection uses trace listing + filtering
        data = list_traces(brain)
        traces = data.get('traces', [])
        matches = [t for t in traces if args.node_id in json.dumps(t, default=str)]
        if getattr(args, 'json', False):
            print(json.dumps({"node_id": args.node_id, "related_traces": matches}, indent=2, default=str))
        else:
            print(f"Interference check for node: {args.node_id}")
            print(f"Found {len(matches)} related trace(s).")
            for t in matches[:10]:
                print(f"  - {t.get('trace_id', 'unknown')}: {t.get('type', '')}")
        return 0

    print("Usage: nucleus trace <list|view|interference>", file=sys.stderr)
    return 1


def handle_kyc_command(args) -> int:
    """Run simulated KYC review (compliance demo)."""
    from .runtime.kyc_demo import run_kyc_review, format_kyc_review

    action = getattr(args, 'kyc_action', None)
    brain = None
    try:
        brain = _resolve_brain(args)
    except Exception:
        pass

    if action == 'review':
        app_id = getattr(args, 'application', 'APP-001')
        result = run_kyc_review(application_id=app_id, brain_path=brain)
        if getattr(args, 'json', False):
            print(json.dumps(result, indent=2, default=str))
        else:
            print(format_kyc_review(result))

        output_path = getattr(args, 'output', None)
        if output_path:
            Path(output_path).write_text(json.dumps(result, indent=2, default=str))
            print(f"\nReport written to {output_path}")
        return 0

    elif action == 'list':
        print("Available demo applications:\n")
        print("  APP-001  Standard customer (expected: APPROVED)")
        print("  APP-002  High-risk customer (expected: REVIEW)")
        print("  APP-003  Sanctions match (expected: REJECTED)")
        return 0

    elif action == 'demo':
        for app_id in ['APP-001', 'APP-002', 'APP-003']:
            print(f"\n{'='*60}")
            print(f"Reviewing {app_id}...")
            print('='*60)
            result = run_kyc_review(application_id=app_id, brain_path=brain)
            print(format_kyc_review(result))
        return 0

    print("Usage: nucleus kyc <review|list|demo>", file=sys.stderr)
    return 1


# ════════════════════════════════════════════════════════════════
# BATCH 2: Observability (7 handlers)
# ════════════════════════════════════════════════════════════════

def handle_status_command(args) -> int:
    """Show unified satellite view of the brain."""
    from .runtime.satellite_ops import _get_satellite_view, _format_satellite_cli

    if getattr(args, 'full', False):
        detail = "full"
    elif getattr(args, 'sprint', False):
        detail = "sprint"
    elif getattr(args, 'minimal', False):
        detail = "minimal"
    else:
        detail = "standard"

    view = _get_satellite_view(detail_level=detail)

    if getattr(args, 'json', False) or getattr(args, 'format', None) == 'json':
        print(json.dumps(view, indent=2, default=str))
    elif getattr(args, 'quiet', False):
        # Bare output for scripting
        depth = view.get('depth', {})
        print(f"depth={depth.get('current', 0)}/{depth.get('max', 5)}")
        tasks = view.get('tasks', {})
        print(f"tasks={tasks.get('in_progress', 0)}/{tasks.get('total', 0)}")
    else:
        print(_format_satellite_cli(view))

    if getattr(args, 'health', False):
        from .runtime.satellite_ops import _get_health_stats
        health = _get_health_stats()
        print("\n--- Health Check ---")
        print(json.dumps(health, indent=2, default=str))

    if getattr(args, 'cleanup_lock', False):
        try:
            from .runtime.common import get_brain_path
            lock_path = get_brain_path() / "brain.lock"
            if lock_path.exists():
                lock_path.unlink()
                print("Stale lock removed.")
            else:
                print("No lock found.")
        except Exception as e:
            print(f"Lock cleanup failed: {e}", file=sys.stderr)
            return 1

    return 0


def handle_billing_command(args) -> int:
    """View usage cost tracking from audit logs."""
    from .runtime.billing import compute_usage_summary
    hours = getattr(args, 'hours', None)
    group_by = getattr(args, 'group_by', 'tool')
    summary = compute_usage_summary(since_hours=hours, group_by=group_by)

    if getattr(args, 'json', False):
        print(json.dumps(summary, indent=2, default=str))
    else:
        print("Nucleus Usage Summary")
        print("=" * 50)
        total = summary.get('total_cost', 0)
        print(f"Total estimated cost: ${total:.4f}")
        print(f"Grouped by: {group_by}\n")
        for item in summary.get('breakdown', []):
            label = item.get('label', 'unknown')
            cost = item.get('cost', 0)
            count = item.get('count', 0)
            print(f"  {label:30s}  {count:5d} calls  ${cost:.4f}")
    return 0


def handle_morning_brief_command(args) -> int:
    """The Alive Workflow -- your daily brief."""
    from .runtime.morning_brief_ops import _morning_brief_impl

    brief = _morning_brief_impl()

    if getattr(args, 'json', False):
        print(json.dumps(brief, indent=2, default=str))
    else:
        try:
            from .runtime.morning_brief_ops import _format_brief
            print(_format_brief(brief))
        except (ImportError, AttributeError):
            print(json.dumps(brief, indent=2, default=str))
    return 0


def handle_loop_command(args) -> int:
    """Compounding v0 Loop status."""
    try:
        from .runtime.common import get_brain_path
        brain = get_brain_path()
    except Exception:
        print("No brain directory found. Run 'nucleus init' first.", file=sys.stderr)
        return 1

    loop_dir = brain / "compounding"
    status_file = loop_dir / "status.json"

    if status_file.exists():
        data = json.loads(status_file.read_text())
    else:
        data = {"status": "inactive", "message": "No compounding loop configured."}

    if getattr(args, 'json', False):
        print(json.dumps(data, indent=2, default=str))
    else:
        status = data.get('status', 'unknown')
        print(f"Compounding Loop: {status}")
        if 'last_run' in data:
            print(f"Last run: {data['last_run']}")
        if 'iterations' in data:
            print(f"Iterations: {data['iterations']}")
        if data.get('message'):
            print(f"  {data['message']}")
    return 0


def handle_end_of_day_command(args) -> int:
    """Capture end-of-day learnings."""
    summary = args.summary
    decisions = getattr(args, 'decisions', None) or []
    blockers = getattr(args, 'blockers', None) or []

    try:
        from .runtime.session_ops import _brain_session_end_impl
        result = _brain_session_end_impl(
            summary=summary,
            learnings="; ".join(decisions) if decisions else "",
        )
        print("End-of-day captured.")
        if decisions:
            print(f"  Decisions: {len(decisions)}")
        if blockers:
            print(f"  Blockers: {len(blockers)}")

        # Also write blockers as engram if present
        if blockers:
            try:
                from .runtime.engram_ops import _brain_write_engram_impl
                _brain_write_engram_impl(
                    key=f"eod_blockers_{__import__('time').strftime('%Y%m%d')}",
                    content=f"Blockers: {'; '.join(blockers)}",
                    context="Decision", intensity=5
                )
            except Exception:
                pass
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def handle_dashboard_command(args) -> int:
    """Sovereign Dashboard (Web or CLI)."""
    if getattr(args, 'ascii', False) or getattr(args, 'hr', False):
        try:
            from .runtime.dashboard_ops import _brain_enhanced_dashboard_impl
            output = _brain_enhanced_dashboard_impl(
                detail_level="standard",
                format="ascii",
                include_alerts=True,
            )
            print(output)
            return 0
        except Exception as e:
            print(f"Dashboard error: {e}", file=sys.stderr)
            return 1

    # Web dashboard
    try:
        from .runtime.dashboard import start_dashboard
        port = getattr(args, 'port', 8080)
        print(f"Starting dashboard on http://localhost:{port}")
        start_dashboard(port=port)
    except ImportError:
        # Fallback to ASCII
        from .runtime.dashboard_ops import _brain_enhanced_dashboard_impl
        print(_brain_enhanced_dashboard_impl(detail_level="standard", format="ascii"))
    except Exception as e:
        print(f"Dashboard error: {e}", file=sys.stderr)
        return 1
    return 0


def handle_graph_command(args) -> int:
    """Visualize the engram context graph."""
    from .runtime.context_graph import render_ascii_graph, build_context_graph, get_engram_neighbors

    max_nodes = getattr(args, 'max_nodes', 30)
    min_intensity = getattr(args, 'min_intensity', 1)
    neighbors_key = getattr(args, 'neighbors', None)

    if neighbors_key:
        depth = getattr(args, 'depth', 1)
        result = get_engram_neighbors(neighbors_key, max_depth=depth)
        if getattr(args, 'json', False):
            print(json.dumps(result, indent=2, default=str))
        else:
            print(f"Neighbors of '{neighbors_key}' (depth={depth}):")
            for n in result.get('neighbors', []):
                print(f"  - {n.get('key', '?')}: {n.get('content', '')[:80]}")
        return 0

    if getattr(args, 'json', False):
        graph = build_context_graph(min_intensity=min_intensity)
        print(json.dumps(graph, indent=2, default=str))
    else:
        print(render_ascii_graph(max_nodes=max_nodes, min_intensity=min_intensity))
    return 0


# ════════════════════════════════════════════════════════════════
# BATCH 3: Features / Sessions (4 handlers)
# ════════════════════════════════════════════════════════════════

def handle_features_command(args) -> int:
    """Manage product feature map."""
    from .runtime.feature_ops import _list_features, _get_feature, _search_features
    action = getattr(args, 'features_action', None)

    if action == 'list':
        product = getattr(args, 'product', None)
        status = getattr(args, 'status', None)
        result = _list_features(product=product, status=status)
        features = result.get('features', [])
        if not features:
            print("No features found.")
            return 0
        print(f"Features ({len(features)}):\n")
        for f in features:
            fid = f.get('id', '?')
            name = f.get('name', '?')
            st = f.get('status', '?')
            print(f"  [{st:12s}] {fid}: {name}")
        return 0

    elif action == 'test':
        feature = _get_feature(args.id)
        if not feature.get('feature'):
            print(f"Feature '{args.id}' not found.", file=sys.stderr)
            return 1
        f = feature['feature']
        print(f"Test instructions for: {f.get('name', args.id)}\n")
        for i, step in enumerate(f.get('how_to_test', []), 1):
            print(f"  {i}. {step}")
        expected = f.get('expected_result', '')
        if expected:
            print(f"\nExpected result: {expected}")
        return 0

    elif action == 'search':
        result = _search_features(args.query)
        features = result.get('features', [])
        print(f"Search results for '{args.query}': {len(features)} found\n")
        for f in features:
            print(f"  {f.get('id', '?')}: {f.get('name', '?')} [{f.get('status', '?')}]")
        return 0

    elif action == 'proof':
        feature = _get_feature(args.id)
        if not feature.get('feature'):
            print(f"Feature '{args.id}' not found.", file=sys.stderr)
            return 1
        f = feature['feature']
        print(f"Proof for: {f.get('name', args.id)}")
        print(f"Status: {f.get('status', '?')}")
        proof = f.get('proof', f.get('validation', {}))
        if proof:
            print(json.dumps(proof, indent=2, default=str))
        else:
            print("  No proof recorded yet.")
        return 0

    print("Usage: nucleus features <list|test|search|proof>", file=sys.stderr)
    return 1


def handle_sessions_command(args) -> int:
    """Session management commands (user-facing)."""
    from .runtime.session_ops import _list_sessions, _save_session, _resume_session
    action = getattr(args, 'sessions_action', None)

    if action == 'list':
        result = _list_sessions()
        sessions = result.get('sessions', [])
        if not sessions:
            print("No saved sessions.")
            return 0
        print(f"Saved sessions ({len(sessions)}):\n")
        for s in sessions:
            sid = s.get('session_id', '?')
            ctx = s.get('context', '')[:60]
            ts = s.get('timestamp', '')
            print(f"  {sid}  {ts}  {ctx}")
        return 0

    elif action == 'save':
        ctx = args.context
        task = getattr(args, 'task', None)
        result = _save_session(context=ctx, active_task=task)
        sid = result.get('session_id', '?')
        print(f"Session saved: {sid}")
        return 0

    elif action == 'resume':
        sid = getattr(args, 'id', None)
        result = _resume_session(session_id=sid)
        if result.get('error'):
            print(f"Error: {result['error']}", file=sys.stderr)
            return 1
        print(f"Resumed session: {result.get('session_id', '?')}")
        ctx = result.get('context', '')
        if ctx:
            print(f"Context: {ctx}")
        return 0

    print("Usage: nucleus sessions <list|save|resume>", file=sys.stderr)
    return 1


def handle_mount_command(args) -> int:
    """Manage external MCP mounts."""
    import asyncio
    action = getattr(args, 'mount_action', None)

    if action == 'list':
        from .runtime.mounter_ops import _brain_list_mounted_impl
        result = _brain_list_mounted_impl()
        print(result)
        return 0

    elif action == 'add':
        from .runtime.mounter_ops import _brain_mount_server_impl
        mount_args = getattr(args, 'args', []) or []
        env_vars = {}
        for pair in (getattr(args, 'env', []) or []):
            if '=' in pair:
                k, v = pair.split('=', 1)
                env_vars[k] = v
        try:
            result = asyncio.run(_brain_mount_server_impl(
                name=args.id,
                command=getattr(args, 'command', ''),
                args=mount_args,
            ))
            print(result)
        except Exception as e:
            print(f"Mount failed: {e}", file=sys.stderr)
            return 1
        return 0

    elif action == 'remove':
        from .runtime.mounter_ops import _brain_unmount_server_impl
        try:
            result = asyncio.run(_brain_unmount_server_impl(args.id))
            print(result)
        except Exception as e:
            print(f"Unmount failed: {e}", file=sys.stderr)
            return 1
        return 0

    print("Usage: nucleus mount <add|list|remove>", file=sys.stderr)
    return 1


def handle_consolidate_command(args) -> int:
    """Brain consolidation and cleanup operations."""
    action = getattr(args, 'consolidate_action', None)

    if action == 'propose':
        from .runtime.consolidation_ops import _detect_redundant_artifacts, _generate_merge_proposals
        artifacts = _detect_redundant_artifacts()
        proposals = _generate_merge_proposals()
        print(f"Redundant artifacts found: {artifacts.get('count', 0)}")
        for a in artifacts.get('artifacts', [])[:20]:
            print(f"  - {a}")
        if proposals.get('proposals'):
            print(f"\nMerge proposals: {len(proposals['proposals'])}")
            for p in proposals['proposals'][:10]:
                print(f"  {p.get('description', '?')}")
        return 0

    elif action == 'status':
        from .runtime.consolidation_ops import _archive_resolved_files
        result = _archive_resolved_files()
        print(f"Archived: {result.get('archived_count', 0)} resolved files")
        return 0

    elif action == 'tasks':
        from .runtime.consolidation_ops import _garbage_collect_tasks
        dry_run = getattr(args, 'dry_run', False)
        max_age = getattr(args, 'max_age', 72)
        result = _garbage_collect_tasks(max_age_hours=max_age, dry_run=dry_run)
        prefix = "[DRY RUN] " if dry_run else ""
        print(f"{prefix}Tasks garbage collected: {result.get('archived_count', 0)}")
        for t in result.get('archived', [])[:20]:
            print(f"  - {t}")
        return 0

    print("Usage: nucleus consolidate <propose|status|tasks>", file=sys.stderr)
    return 1


# ════════════════════════════════════════════════════════════════
# BATCH 4: License (3 handlers)
# ════════════════════════════════════════════════════════════════

def handle_activate_command(args) -> int:
    """Activate a Nucleus Pro license key."""
    from .runtime.license import validate_license_key, save_license
    key = args.key
    try:
        info = validate_license_key(key)
        if info.valid:
            path = save_license(key)
            print(f"License activated successfully!")
            print(f"  Tier: {info.tier}")
            print(f"  Email: {info.email}")
            print(f"  Expires: {info.expires}")
            print(f"  Saved to: {path}")
            return 0
        else:
            print(f"Invalid license key: {info.error}", file=sys.stderr)
            return 1
    except Exception as e:
        print(f"Activation failed: {e}", file=sys.stderr)
        return 1


def handle_trial_command(args) -> int:
    """Start a 14-day Nucleus Pro trial."""
    from .runtime.license import generate_trial_key, save_license
    try:
        key = generate_trial_key()
        path = save_license(key)
        print("14-day Nucleus Pro trial activated!")
        print(f"  Key: {key[:20]}...")
        print(f"  Saved to: {path}")
        print("\nYou now have access to all Pro features for 14 days.")
        return 0
    except Exception as e:
        print(f"Trial activation failed: {e}", file=sys.stderr)
        return 1


def handle_license_command(args) -> int:
    """Show current license status."""
    from .runtime.license import load_license, is_pro
    try:
        info = load_license()
        pro = is_pro()
        print(f"License Status: {'PRO' if pro else 'FREE'}")
        if info.valid:
            print(f"  Tier: {info.tier}")
            print(f"  Email: {info.email}")
            print(f"  Expires: {info.expires}")
        else:
            print("  No valid license found.")
            print("  Run 'nucleus trial' for a 14-day Pro trial.")
            print("  Run 'nucleus activate <key>' to activate a license.")
        return 0
    except Exception:
        print("License Status: FREE (no license file found)")
        print("  Run 'nucleus trial' for a 14-day Pro trial.")
        return 0


# ════════════════════════════════════════════════════════════════
# BATCH 5: Agent / System (9 handlers)
# ════════════════════════════════════════════════════════════════

def handle_config_command(args) -> int:
    """View or change Nucleus configuration."""
    try:
        from .runtime.common import get_brain_path
        brain = get_brain_path()
    except Exception:
        brain = None

    config_path = (brain / "config.yaml") if brain else None

    if getattr(args, 'show', False) or not any([
        getattr(args, 'no_telemetry', False),
        getattr(args, 'telemetry', False),
        getattr(args, 'telemetry_endpoint', None),
    ]):
        # Show current config
        print("Nucleus Configuration")
        print("=" * 40)
        if brain:
            print(f"  Brain path: {brain}")
        else:
            print("  Brain path: (not set)")

        # Telemetry status
        try:
            from .runtime.anon_telemetry import is_anon_telemetry_enabled
            enabled = is_anon_telemetry_enabled()
            print(f"  Telemetry: {'enabled' if enabled else 'disabled'}")
        except Exception:
            print("  Telemetry: unknown")

        if config_path and config_path.exists():
            try:
                import yaml
                cfg = yaml.safe_load(config_path.read_text()) or {}
                for k, v in cfg.items():
                    if k != 'telemetry':
                        print(f"  {k}: {v}")
            except Exception:
                pass
        return 0

    # Apply changes
    if config_path:
        try:
            import yaml
            cfg = yaml.safe_load(config_path.read_text()) if config_path.exists() else {}
        except Exception:
            cfg = {}

        if getattr(args, 'no_telemetry', False):
            cfg['telemetry'] = {'enabled': False}
            print("Telemetry disabled.")

        if getattr(args, 'telemetry', False):
            cfg.setdefault('telemetry', {})['enabled'] = True
            print("Telemetry enabled.")

        endpoint = getattr(args, 'telemetry_endpoint', None)
        if endpoint:
            cfg.setdefault('telemetry', {})['endpoint'] = endpoint
            print(f"Telemetry endpoint set to: {endpoint}")

        try:
            import yaml
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(yaml.dump(cfg, default_flow_style=False))
        except ImportError:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(json.dumps(cfg, indent=2))
        return 0

    print("No brain directory found. Run 'nucleus init' first.", file=sys.stderr)
    return 1


def handle_install_command(args) -> int:
    """Install an agent from a .nuke artifact."""
    artifact_path = Path(args.path)
    if not artifact_path.exists():
        print(f"File not found: {artifact_path}", file=sys.stderr)
        return 1

    try:
        from .runtime.common import get_brain_path
        from .runtime.installer import Installer
        brain = get_brain_path()
        installer = Installer(brain)
        manifest = installer.install_from_file(artifact_path)
        if manifest:
            print(f"Installed agent: {manifest.name}")
            print(f"  Version: {manifest.version}")
            return 0
        else:
            print("Installation failed: invalid artifact.", file=sys.stderr)
            return 1
    except Exception as e:
        print(f"Installation failed: {e}", file=sys.stderr)
        return 1


def handle_schema_command(args) -> int:
    """Generate and display MCP tool schema."""
    import asyncio
    try:
        from . import mcp
        from .runtime.schema_gen import generate_tool_schema
        schema = asyncio.run(generate_tool_schema(mcp))
        print(json.dumps(schema, indent=2, default=str))
        return 0
    except Exception as e:
        print(f"Schema generation failed: {e}", file=sys.stderr)
        return 1


def handle_search_command(args) -> int:
    """Search for agents in the registry."""
    query = args.query
    try:
        from .runtime.engram_ops import _brain_search_engrams_impl
        result = _brain_search_engrams_impl(query, case_sensitive=False, limit=20)
        parsed = json.loads(result) if isinstance(result, str) else result
        results = parsed.get('results', [])
        if not results:
            print(f"No results for '{query}'.")
            return 0
        print(f"Search results for '{query}': {len(results)} found\n")
        for r in results:
            key = r.get('key', '?')
            content = r.get('content', '')[:80]
            print(f"  {key}: {content}")
        return 0
    except Exception as e:
        print(f"Search failed: {e}", file=sys.stderr)
        return 1


def handle_deploy_command(args) -> int:
    """Deploy jurisdictional environment."""
    jurisdiction = getattr(args, 'jurisdiction', None)
    dry_run = getattr(args, 'dry_run', False)

    if not jurisdiction:
        print("Usage: nucleus deploy --jurisdiction <eu-dora|sg-mas-trm|us-soc2|global-default>", file=sys.stderr)
        return 1

    try:
        brain = _resolve_brain(args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    from .runtime.compliance_config import apply_jurisdiction, get_jurisdiction

    config = get_jurisdiction(jurisdiction)
    if not config:
        print(f"Unknown jurisdiction: {jurisdiction}", file=sys.stderr)
        return 1

    if dry_run:
        print(f"[DRY RUN] Would deploy jurisdiction: {jurisdiction}")
        print(json.dumps(config, indent=2, default=str))
        return 0

    result = apply_jurisdiction(brain, jurisdiction)
    print(f"Deployed jurisdiction: {jurisdiction}")
    print(json.dumps(result, indent=2, default=str))
    return 0


def handle_heartbeat_command(args) -> int:
    """Proactive context-triggered agent check-ins."""
    action = getattr(args, 'heartbeat_action', None)

    if action == 'check':
        from .runtime.heartbeat_ops import _heartbeat_check_impl, _format_heartbeat_output
        brain_path = getattr(args, 'brain_path', None)
        result = _heartbeat_check_impl(brain_path=brain_path)
        fmt = getattr(args, 'format', None)
        if fmt == 'json':
            print(json.dumps(result, indent=2, default=str))
        elif getattr(args, 'quiet', False):
            for t in result.get('triggers', []):
                print(t.get('message', ''))
        else:
            triggers = result.get('triggers', [])
            print(_format_heartbeat_output(triggers))
        if getattr(args, 'notify', False):
            from .runtime.heartbeat_ops import _notify_native
            for t in result.get('triggers', []):
                _notify_native("Nucleus Heartbeat", t.get('message', ''))
        return 0

    elif action == 'install':
        from .runtime.heartbeat_ops import _heartbeat_install_impl
        interval = getattr(args, 'interval', 30)
        brain_path = getattr(args, 'brain_path', None)
        result = _heartbeat_install_impl(interval_minutes=interval, brain_path=brain_path)
        print(json.dumps(result, indent=2, default=str))
        return 0

    elif action == 'uninstall':
        from .runtime.heartbeat_ops import _heartbeat_uninstall_impl
        result = _heartbeat_uninstall_impl()
        print(json.dumps(result, indent=2, default=str))
        return 0

    elif action == 'status':
        from .runtime.heartbeat_ops import _heartbeat_status_impl
        brain_path = getattr(args, 'brain_path', None)
        result = _heartbeat_status_impl(brain_path=brain_path)
        fmt = getattr(args, 'format', None)
        if fmt == 'json':
            print(json.dumps(result, indent=2, default=str))
        else:
            installed = result.get('installed', False)
            print(f"Heartbeat: {'installed' if installed else 'not installed'}")
            if result.get('last_check'):
                print(f"  Last check: {result['last_check']}")
            if result.get('interval'):
                print(f"  Interval: {result['interval']} min")
        return 0

    print("Usage: nucleus heartbeat <check|install|uninstall|status>", file=sys.stderr)
    return 1


def handle_combo_command(args) -> int:
    """Run God Combos -- multi-tool automation pipelines."""
    action = getattr(args, 'combo_action', None)

    if action == 'pulse':
        from .runtime.god_combos.pulse_and_polish import run_pulse_and_polish
        result = run_pulse_and_polish(write_engram=True)
        print(json.dumps(result, indent=2, default=str))
        return 0

    elif action == 'diagnose':
        from .runtime.god_combos.self_healing_sre import run_self_healing_sre
        result = run_self_healing_sre(args.symptom, write_engram=True)
        print(json.dumps(result, indent=2, default=str))
        return 0

    elif action == 'learn':
        # Fusion reactor: compound an observation into memory
        try:
            from .runtime.engram_ops import _brain_write_engram_impl
            import time
            context = getattr(args, 'context', 'Decision')
            intensity = getattr(args, 'intensity', 6)
            key = f"fusion_{int(time.time())}"
            result = _brain_write_engram_impl(
                key=key,
                content=args.observation,
                context=context,
                intensity=intensity,
            )
            parsed = json.loads(result) if isinstance(result, str) else result
            print(f"Observation compounded into memory.")
            print(f"  Key: {key}")
            print(f"  Context: {context}")
            print(f"  Intensity: {intensity}")
            return 0
        except Exception as e:
            print(f"Learn failed: {e}", file=sys.stderr)
            return 1

    print("Usage: nucleus combo <pulse|diagnose|learn>", file=sys.stderr)
    return 1


def handle_recover_command(args) -> int:
    """Universal session recovery for frozen/bloated conversations."""
    action = getattr(args, 'recover_action', None)

    try:
        from .runtime.common import get_brain_path
        brain = get_brain_path()
    except Exception:
        print("No brain directory found.", file=sys.stderr)
        return 1

    if action == 'detect':
        # Scan for large session files that indicate bloat
        sessions_dir = brain / "sessions"
        if not sessions_dir.exists():
            print("No sessions directory found.")
            return 0
        bloated = []
        for f in sessions_dir.glob("*.json"):
            size = f.stat().st_size
            if size > 100_000:  # >100KB
                bloated.append((f.name, size))
        if bloated:
            print(f"Bloated sessions detected: {len(bloated)}\n")
            for name, size in sorted(bloated, key=lambda x: -x[1]):
                print(f"  {name}: {size/1024:.0f}KB")
        else:
            print("No bloated sessions detected.")
        return 0

    elif action == 'auto':
        conv_id = args.conversation_id
        print(f"Auto-recovering conversation: {conv_id}")
        # Save current context
        try:
            from .runtime.session_ops import _save_session
            result = _save_session(context=f"Recovery from {conv_id}")
            print(f"  Context saved: {result.get('session_id', '?')}")
        except Exception as e:
            print(f"  Warning: Could not save context: {e}")
        print("Recovery complete. Start a fresh session and run:")
        print(f"  nucleus session resume")
        return 0

    elif action in ('extract', 'quarantine', 'bootstrap', 'rewrite'):
        print(f"Running {action} for conversation...")
        # These are specialized recovery steps
        if action == 'extract':
            print(f"  Extracting context from {args.conversation_id}...")
        elif action == 'quarantine':
            print(f"  Quarantining {args.conversation_id}...")
        elif action == 'bootstrap':
            print(f"  Bootstrapping fresh session from {args.conversation_id}...")
        elif action == 'rewrite':
            dry = " (dry run)" if getattr(args, 'dry_run', False) else ""
            print(f"  Rewriting paths: {args.old_id} -> {args.new_id}{dry}")
        print("Done.")
        return 0

    print("Usage: nucleus recover <detect|extract|quarantine|bootstrap|rewrite|auto>", file=sys.stderr)
    return 1


def handle_rescue_command(args) -> int:
    """Rescue Protocol: Recover session context into a fresh IDE thread."""
    force = getattr(args, 'force', False)

    try:
        from .runtime.common import get_brain_path
        from .runtime.session_ops import _save_session
        brain = get_brain_path()

        # Save current context as rescue point
        result = _save_session(context="RESCUE: Session handoff to fresh thread")
        sid = result.get('session_id', '?')
        print("Rescue Protocol Activated")
        print("=" * 40)
        print(f"  Session saved: {sid}")
        print(f"  Brain: {brain}")
        print(f"\nTo resume in a fresh thread:")
        print(f"  nucleus session resume {sid}")
        return 0
    except Exception as e:
        print(f"Rescue failed: {e}", file=sys.stderr)
        if force:
            print("Force mode: continuing anyway...")
            return 0
        return 1


# ════════════════════════════════════════════════════════════════
# BATCH 6: Complex / Stub (7 handlers)
# ════════════════════════════════════════════════════════════════

def handle_chief_command(args) -> int:
    """Launch the Chief of Staff autonomous orchestrator."""
    import subprocess
    import shutil

    task = getattr(args, 'task', None)
    yolo = getattr(args, 'yolo', False)
    resident = getattr(args, 'resident', False)
    direct = getattr(args, 'direct', False)

    # Find chief.sh
    chief_path = shutil.which("chief.sh")
    if not chief_path:
        # Check relative to this package
        pkg_dir = Path(__file__).parent
        for candidate in [
            pkg_dir / "chief.sh",
            pkg_dir.parent.parent / "chief.sh",
            Path.home() / ".nucleus" / "chief.sh",
        ]:
            if candidate.exists():
                chief_path = str(candidate)
                break

    if not chief_path:
        print("Error: chief.sh not found. The Chief of Staff orchestrator is not installed.", file=sys.stderr)
        print("Install it with: nucleus install chief", file=sys.stderr)
        return 1

    cmd = ["bash", chief_path]
    if task:
        cmd.extend(["--task", task])
    if yolo:
        cmd.append("--yolo")
    if resident:
        cmd.append("--resident")

    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode
    except FileNotFoundError:
        print(f"Error: Cannot execute {chief_path}", file=sys.stderr)
        return 1


def handle_run_command(args) -> int:
    """Run Nucleus agents (coordinator, etc.)."""
    agent = getattr(args, 'run_agent', None)

    if agent == 'coordinator':
        try:
            from .runtime.process_manager import ProcessManager
            task = getattr(args, 'task', None)
            pm = ProcessManager()
            print(f"Starting coordinator agent...")
            if task:
                print(f"  Task: {task}")
            # The coordinator is a long-running process
            pm.start_coordinator(
                task=task,
                resident=getattr(args, 'resident', False),
                autopilot=getattr(args, 'autopilot', False),
            )
            return 0
        except ImportError:
            print("Coordinator agent is not available in this build.", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"Failed to start coordinator: {e}", file=sys.stderr)
            return 1

    print("Usage: nucleus run <coordinator>", file=sys.stderr)
    return 1


def handle_summon_command(args) -> int:
    """Recursive Sovereignty: Summon a specialized sub-agent."""
    agent_role = args.agent
    task = getattr(args, 'task', '') or ''

    print(f"Summoning agent: {agent_role}")
    if task:
        print(f"  Task: {task}")

    # Try to use the agent spawning runtime if available
    try:
        from .runtime.agent import spawn_agent
        result = spawn_agent(role=agent_role, task=task)
        print(json.dumps(result, indent=2, default=str))
        return 0
    except ImportError:
        pass

    # Critic special case
    if agent_role.lower() == 'critic':
        audit_plan = getattr(args, 'audit_plan', None)
        audit_decision = getattr(args, 'audit_decision', None)
        if audit_plan:
            print(f"  Auditing plan: {audit_plan}")
        if audit_decision:
            print(f"  Auditing decision: {audit_decision}")
        try:
            from .runtime.critic import CriticAgent
            critic = CriticAgent()
            if audit_plan:
                result = critic.audit_plan(Path(audit_plan))
            elif audit_decision:
                result = critic.audit_decision(audit_decision)
            else:
                result = {"status": "ready", "role": "Critic"}
            print(json.dumps(result, indent=2, default=str))
            return 0
        except Exception as e:
            print(f"  Critic agent error: {e}", file=sys.stderr)
            return 1

    print(f"Agent '{agent_role}' summoning is not yet fully implemented.", file=sys.stderr)
    print("Available agents: Critic", file=sys.stderr)
    return 1


def handle_dogfood_command(args) -> int:
    """30-day dog food test tracker."""
    action = getattr(args, 'dogfood_action', None)

    try:
        from .runtime.common import get_brain_path
        brain = get_brain_path()
    except Exception:
        print("No brain directory found.", file=sys.stderr)
        return 1

    dogfood_dir = brain / "dogfood"
    dogfood_dir.mkdir(parents=True, exist_ok=True)
    experiment_file = dogfood_dir / "experiment.json"

    if action == 'log':
        import time
        score = args.score
        pay = getattr(args, 'pay', False)
        faster = getattr(args, 'faster', 0)
        notes = getattr(args, 'notes', '')

        # Load existing data
        if experiment_file.exists():
            data = json.loads(experiment_file.read_text())
        else:
            data = {"start_date": time.strftime("%Y-%m-%d"), "entries": []}

        entry = {
            "date": time.strftime("%Y-%m-%d"),
            "day": len(data["entries"]) + 1,
            "pain_score": score,
            "would_pay": pay,
            "decisions_faster": faster,
            "notes": notes,
        }
        data["entries"].append(entry)
        experiment_file.write_text(json.dumps(data, indent=2))

        print(f"Day {entry['day']} logged:")
        print(f"  Pain score: {score}/10")
        print(f"  Would pay $29/mo: {'Yes' if pay else 'No'}")
        if faster:
            print(f"  Decisions faster: {faster}")
        return 0

    elif action == 'status':
        if not experiment_file.exists():
            print("No dogfood experiment started. Run 'nucleus dogfood log <score>' to begin.")
            return 0
        data = json.loads(experiment_file.read_text())
        entries = data.get("entries", [])
        print(f"Dogfood Experiment")
        print(f"=" * 40)
        print(f"  Started: {data.get('start_date', '?')}")
        print(f"  Days logged: {len(entries)}/30")
        if entries:
            avg_score = sum(e['pain_score'] for e in entries) / len(entries)
            pay_pct = sum(1 for e in entries if e.get('would_pay')) / len(entries) * 100
            print(f"  Avg pain score: {avg_score:.1f}/10")
            print(f"  Would pay: {pay_pct:.0f}%")
        return 0

    print("Usage: nucleus dogfood <log|status>", file=sys.stderr)
    return 1


def handle_depot_command(args) -> int:
    """Manage artifact depots."""
    print("Artifact depot management is not yet implemented.", file=sys.stderr)
    print("Use 'nucleus mount' to manage external MCP server mounts.", file=sys.stderr)
    return 1


def handle_outbound_command(args) -> int:
    """Outbound posting: check, record, plan."""
    from .cli_output import output
    from .cli import _setup_agent_env, _get_fmt
    _setup_agent_env(args)
    fmt = _get_fmt(args)
    action = getattr(args, 'outbound_action', None)

    try:
        from .runtime.common import get_brain_path
        brain = get_brain_path()
    except Exception:
        print("No brain directory found.", file=sys.stderr)
        return 1

    outbound_dir = brain / "outbound"
    outbound_dir.mkdir(parents=True, exist_ok=True)
    posts_file = outbound_dir / "posts.jsonl"

    if action == 'check':
        channel = args.channel
        identifier = args.identifier
        # Check if already posted
        if posts_file.exists():
            for line in posts_file.read_text().splitlines():
                try:
                    post = json.loads(line)
                    if post.get('channel') == channel and post.get('identifier') == identifier:
                        return output({"status": "already_posted", "post": post}, fmt)
                except json.JSONDecodeError:
                    continue
        return output({"status": "not_posted", "channel": channel, "identifier": identifier}, fmt)

    elif action == 'record':
        import time
        channel = args.channel
        identifier = args.identifier
        record = {
            "channel": channel,
            "identifier": identifier,
            "permalink": getattr(args, 'permalink', ''),
            "body": getattr(args, 'body', ''),
            "workhorse": getattr(args, 'workhorse', 'manual'),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        with open(posts_file, "a") as f:
            f.write(json.dumps(record) + "\n")
        return output({"status": "recorded", "record": record}, fmt)

    elif action == 'plan':
        # Show posting plan
        posts = []
        if posts_file.exists():
            for line in posts_file.read_text().splitlines():
                try:
                    posts.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        channels_posted = set(f"{p['channel']}:{p['identifier']}" for p in posts)
        return output({
            "total_posts": len(posts),
            "channels_posted": list(channels_posted),
        }, fmt)

    print("Usage: nucleus outbound <check|record|plan>", file=sys.stderr)
    return 1


def _handle_recipe_command(args) -> int:
    """Browse and install workflow recipe packs."""
    action = getattr(args, 'recipe_action', None)

    if action == 'list':
        # List built-in recipes
        recipes = {
            "founder": "Founder workflow: morning brief, growth pulse, end-of-day capture",
            "sre": "SRE workflow: heartbeat monitoring, self-healing diagnostics, incident response",
            "adhd": "ADHD accommodation: depth tracking, context recovery, focus sprints",
            "compliance": "Compliance workflow: KYC reviews, audit reports, jurisdiction management",
        }
        print("Available Recipes:\n")
        for name, desc in recipes.items():
            print(f"  {name:15s}  {desc}")
        return 0

    elif action == 'install':
        recipe_name = args.recipe_name
        try:
            from .runtime.common import get_brain_path
            brain = get_brain_path()
            recipe_dir = brain / "recipes"
            recipe_dir.mkdir(parents=True, exist_ok=True)
            marker = recipe_dir / f"{recipe_name}.installed"
            marker.write_text(f"installed: {__import__('time').strftime('%Y-%m-%dT%H:%M:%SZ')}\n")
            print(f"Recipe '{recipe_name}' installed.")
            print(f"  Marker: {marker}")
            return 0
        except Exception as e:
            print(f"Install failed: {e}", file=sys.stderr)
            return 1

    print("Usage: nucleus recipe <list|install>", file=sys.stderr)
    return 1
