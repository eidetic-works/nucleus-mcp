"""CLI Output Formatter — The Universal Interface (v1.4.1 Agent-Native).

Formats runtime results for terminal consumption:
- JSON (for jq / piping)
- Table (for humans)
- TSV (for awk/cut)
- Quiet (bare values for pipes / xargs)
- Auto-detect: JSON when piped, table when interactive TTY

Unix conventions:
- stdout = data (including structured JSON errors when --format json)
- stderr = errors/status messages
- exit 0 = success, 1 = runtime error, 2 = usage error, 3 = not found
"""

import json
import re
import sys
from typing import Any, Dict, List, Optional, Union

# Semantic exit codes (agent-friendly control flow)
EXIT_OK = 0
EXIT_ERROR = 1
EXIT_USAGE = 2
EXIT_NOT_FOUND = 3


def is_tty() -> bool:
    """Check if stdout is connected to a terminal."""
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def detect_format(explicit: Optional[str] = None, quiet: bool = False) -> str:
    """Determine output format. --quiet takes precedence, then explicit flag, then auto-detect."""
    if quiet:
        return "quiet"
    if explicit:
        return explicit.lower()
    return "table" if is_tty() else "json"


def format_json(data: Any) -> str:
    """Format data as JSON (one object or JSONL for lists)."""
    if isinstance(data, list):
        if not data:
            return "[]"
        return "\n".join(json.dumps(item, default=str) for item in data)
    return json.dumps(data, indent=2, default=str)


def format_table(rows: List[Dict[str, Any]], columns: Optional[List[str]] = None) -> str:
    """Format list of dicts as aligned table with headers."""
    if not rows:
        return "(empty)"

    if columns is None:
        columns = list(rows[0].keys())

    # Compute column widths
    widths = {col: len(col) for col in columns}
    str_rows = []
    for row in rows:
        str_row = {}
        for col in columns:
            val = row.get(col, "")
            if val is None:
                val = ""
            s = str(val)
            if len(s) > 80:
                s = s[:77] + "..."
            str_row[col] = s
            widths[col] = max(widths[col], len(s))
        str_rows.append(str_row)

    # Header
    header = "  ".join(col.upper().ljust(widths[col]) for col in columns)
    separator = "  ".join("─" * widths[col] for col in columns)
    lines = [header, separator]

    for sr in str_rows:
        line = "  ".join(sr.get(col, "").ljust(widths[col]) for col in columns)
        lines.append(line)

    return "\n".join(lines)


def format_tsv(rows: List[Dict[str, Any]], columns: Optional[List[str]] = None) -> str:
    """Format list of dicts as TSV (tab-separated values)."""
    if not rows:
        return ""
    if columns is None:
        columns = list(rows[0].keys())
    lines = ["\t".join(columns)]
    for row in rows:
        vals = [str(row.get(col, "")) for col in columns]
        lines.append("\t".join(vals))
    return "\n".join(lines)


def format_quiet(rows: List[Dict[str, Any]], key_field: Optional[str] = None) -> str:
    """Format as bare values, one per line (for pipes/xargs).

    Extracts the primary key field from each row. If key_field is not
    specified, uses the first column.
    """
    if not rows:
        return ""
    if key_field is None:
        key_field = list(rows[0].keys())[0]
    return "\n".join(str(row.get(key_field, "")) for row in rows)


def classify_error(msg: str) -> tuple:
    """Classify an error message into type and exit code.

    Returns:
        (error_type: str, exit_code: int)
    """
    lower = msg.lower() if msg else ""
    if re.search(r"not found|no .* found|no .* match|does not exist|unknown .* id", lower):
        return ("not_found", EXIT_NOT_FOUND)
    if re.search(r"usage:|missing .* argument|required|invalid .* argument|bad .* arg", lower):
        return ("usage_error", EXIT_USAGE)
    return ("runtime_error", EXIT_ERROR)


def format_scalar(data: Any, fmt: str) -> str:
    """Format a single scalar result (dict or string)."""
    if fmt == "json":
        return format_json(data)
    if isinstance(data, dict):
        lines = []
        for k, v in data.items():
            lines.append(f"  {k}: {v}")
        return "\n".join(lines)
    return str(data)


def output(data: Any, fmt: str, columns: Optional[List[str]] = None,
           error: Optional[str] = None, exit_code: int = 0,
           quiet_key: Optional[str] = None) -> int:
    """Write formatted output to stdout, errors to stderr. Returns exit code.

    Args:
        data: The payload (list of dicts for table, dict for scalar, any for json)
        fmt: 'json', 'table', 'tsv', or 'quiet'
        columns: Column order for table/tsv (optional, inferred from data)
        error: Error message to print to stderr
        exit_code: Process exit code (0=success, 1=error, 2=usage, 3=not found)
        quiet_key: Primary key field for --quiet mode (optional, inferred)

    Returns:
        exit code (for sys.exit)
    """
    if error:
        error_type, auto_exit = classify_error(error)
        final_exit = exit_code if exit_code != 0 else auto_exit
        print(f"error: {error}", file=sys.stderr)
        if fmt == "json":
            envelope = {"ok": False, "error": error_type,
                        "message": error, "exit_code": final_exit}
            print(json.dumps(envelope, indent=2))
        return final_exit

    if fmt == "quiet":
        if isinstance(data, list):
            print(format_quiet(data, quiet_key))
        elif isinstance(data, dict):
            val = next(iter(data.values()), "")
            print(str(val))
        else:
            print(str(data))
    elif fmt == "json":
        print(format_json(data))
    elif fmt == "tsv":
        if isinstance(data, list):
            print(format_tsv(data, columns))
        else:
            print(format_json(data))
    else:  # table
        if isinstance(data, list):
            print(format_table(data, columns))
        else:
            print(format_scalar(data, fmt))

    sys.stdout.flush()
    sys.stderr.flush()
    return exit_code


def parse_runtime_response(response: Any) -> tuple:
    """Parse a Nucleus runtime response (JSON string or dict).

    Returns:
        (success: bool, data: Any, error: Optional[str])
    """
    if isinstance(response, str):
        try:
            parsed = json.loads(response)
        except json.JSONDecodeError:
            return (True, response, None)
    elif isinstance(response, dict):
        parsed = response
    else:
        return (True, response, None)

    if "success" in parsed:
        if parsed["success"]:
            return (True, parsed.get("data"), None)
        else:
            return (False, None, parsed.get("error", "Unknown error"))

    if "error" in parsed and len(parsed) <= 3:
        return (False, None, parsed["error"])

    return (True, parsed, None)
