#!/usr/bin/env python3
"""
AST-guided CLI sanitizer for public release.

Replaces the broken sed-line-deletion approach with Python-aware removal.
Called by sync_public_repo.sh after git archive extraction.

Usage:
    python3 scripts/sanitize_cli.py <path-to-cli.py>
"""
import re
import ast
import sys

def sanitize(filepath):
    with open(filepath) as f:
        content = f.read()

    # ═══ PHASE 1: Text replacements (syntax-safe) ═══
    # Provider help string (multi-line — must be replaced before generic subs)
    content = content.replace(
        "help='Which brother: gemini (default), anthropic, groq, claude-code (Max sub), '\n"
        "                                  'or local (Third Brother \u2014 Ollama/vLLM). '\n"
        "                                  'Anthropic requires NUCLEUS_ANTHROPIC_API_KEY. '\n"
        "                                  'Groq requires NUCLEUS_GROQ_API_KEY (free at console.groq.com). '\n"
        "                                  'Local requires Ollama or NUCLEUS_LOCAL_ENDPOINT.')",
        "help='Which provider: gemini (default), anthropic, groq. '\n"
        "                                  'Anthropic requires NUCLEUS_ANTHROPIC_API_KEY. '\n"
        "                                  'Groq requires NUCLEUS_GROQ_API_KEY (free at console.groq.com).')"
    )

    content = content.replace(', "--dangerously-skip-permissions"', '')
    content = content.replace("'gemini', 'anthropic', 'groq', 'claude-code', 'local'", "'gemini', 'anthropic', 'groq'")
    content = content.replace(', or claude-code (Max sub)', '')
    content = content.replace('(free via Max subscription)', '')
    content = content.replace("or local (Third Brother \u2014 Ollama/vLLM). ", "")
    content = content.replace("or local (Third Brother \u2014 Ollama/vLLM).", "")
    content = content.replace("the Third Brother", "the local model")
    content = content.replace("Third Brother \u2014 ", "")
    content = content.replace("Third Brother", "local model")

    # claude-code provider references in code
    content = re.sub(r',\s*"claude-code"\s*,\s*"claude_code"\s*,\s*"max"', '', content)
    content = re.sub(r'"claude-code"\s*,\s*"claude_code"\s*,\s*"max"\s*,?\s*', '', content)
    content = re.sub(r',\s*"claude-code"', '', content)
    content = re.sub(r'\(\s*,', '(', content)
    content = re.sub(r',\s*\)', ')', content)
    content = content.replace("claude-code", "anthropic")
    content = content.replace("claude_code", "anthropic")

    # Verify text replacements didn't break syntax
    try:
        compile(content, filepath, 'exec')
    except SyntaxError as e:
        print(f"FATAL: Text replacement broke syntax at line {e.lineno}: {e.msg}", file=sys.stderr)
        sys.exit(1)

    lines = content.splitlines(True)

    # ═══ PHASE 2: AST-guided function removal ═══
    tree = ast.parse(content)

    ALWAYS_REMOVE = {
        'handle_archive_command', '_archive_turn', '_archive_dir_setup',
        'handle_mine_command', 'handle_eval_command', 'handle_synth_command',
        '_dpo_capture', '_cot_capture', '_shadow_capture',
    }
    BODY_PATTERNS = ['_DPOArchive', '_CoTArchive', 'EVAL_BLOCK', 'SYNTH_BLOCK', 'training.flywheel']

    delete_lines = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            name = node.name
            start = node.lineno - 1
            end = node.end_lineno
            func_size = end - start
            func_source = ''.join(lines[start:end])

            remove = name in ALWAYS_REMOVE
            if not remove and func_size <= 200:
                for pat in BODY_PATTERNS:
                    if pat in func_source:
                        remove = True
                        break

            if remove:
                actual_start = start
                k = actual_start - 1
                while k >= 0:
                    s = lines[k].strip()
                    if s == '':
                        k -= 1
                        continue
                    if s.startswith('#'):
                        actual_start = k
                        k -= 1
                    else:
                        break
                for i in range(actual_start, end):
                    delete_lines.add(i)

    # ═══ PHASE 3: Surgical line/block removal ═══
    # All sensitive patterns from phases 1-15 of the training stack
    surgical = [
        '_retry_rejected', '_retry_prompt', '_DPOArchive', 'record_preference',
        'is_correction', 'count_preferences', 'export_dpo', 'get_preference_stats',
        '_reasoning_steps', '_reasoning_prompt', '_CoTArchive', 'record_reasoning_chain',
        'COT_CAPTURE', 'count_reasoning', 'get_reasoning', 'export_reasoning',
        'mine_preferences', 'mine_reasoning', 'MINING',
        'EVAL_BLOCK_START', 'EVAL_BLOCK_END', 'SYNTH_BLOCK_START', 'SYNTH_BLOCK_END',
        'SHADOW_CAPTURE', '_ShadowArchive', '_shadow_archive',
        '_archive_turn', '_archive_dir', '_archive_file',
        'archive_pipeline', 'training.flywheel', 'self_play',
        'synthesize_preferences', 'archive_synth', 'DPO',
        'archive_eval', 'eval_results', 'eval_suite', 'generate_eval_suite',
        'export_eval_suite', 'run_eval', 'shadow-stats', 'graduation',
        # Phase 8: SPIN
        'SPIN_BLOCK_START', 'SPIN_BLOCK_END', 'archive_spin', 'iterative_self_play',
        'spin_round', 'spin_count',
        # Phase 9: Active learning
        'ACTIVE_LEARN_BLOCK_START', 'ACTIVE_LEARN_BLOCK_END', 'archive_active',
        'active-learn', 'active_learn', 'identify_weaknesses', 'synthesize_for_weaknesses',
        'ACTIVE LEARNING', 'build_judge_fn', 'LLM-as-Judge', 'judge_model_fn',
        # Phase 10: Conductor + Pipeline
        'CONDUCTOR_BLOCK_START', 'CONDUCTOR_BLOCK_END', 'archive_conductor',
        'TRAINING CONDUCTOR', 'training_status',
        'PIPELINE_BLOCK_START', 'PIPELINE_BLOCK_END',
        'TRAINING PIPELINE', 'run_full_pipeline', 'pipe_provider', 'pipe_judge', 'pipe_dry_run',
        # Phase 11: Constitutional AI + Quality
        'CONSTITUTIONAL_BLOCK_START', 'CONSTITUTIONAL_BLOCK_END', 'archive_constitutional',
        'constitutional_revise', 'constitutional_hash', 'CONSTITUTIONAL', 'CONSTITUTION',
        'QUALITY_BLOCK_START', 'QUALITY_BLOCK_END', 'archive_quality',
        'score_training_data', 'export_filtered', 'DATA QUALITY', 'min_quality',
        # Phase 12: Registry + Shadow + Graduation
        'REGISTRY_BLOCK_START', 'REGISTRY_BLOCK_END', 'SHADOW_BLOCK_START', 'SHADOW_BLOCK_END',
        'GRADUATION_BLOCK_START', 'GRADUATION_BLOCK_END',
        'archive_register', 'archive_promote', 'register_model', 'get_registry',
        'update_model_status', 'get_active_model', 'shadow_compare', 'get_shadow_stats',
        'graduation_check', 'MODEL REGISTRY', 'SHADOW MODE', 'GRADUATION',
        'shadow_stats', 'shadow_won', '_active_model', '_shadow_task',
        '_shadow_llm', '_shadow_fn', 'promote_canary', 'promote_primary',
        # Phase 15: Model Vault
        'VAULT_BLOCK_START', 'VAULT_BLOCK_END', 'archive_vault', 'archive_rollback',
        'vault_store', 'vault_list', 'vault_restore', 'rollback_model',
        'MODEL VAULT', 'nucleus-vault', 'vault-restore',
    ]
    comment_only = [
        'EVAL BENCHMARK', 'SELF-PLAY', 'Chain-of-Thought', 'reasoning chain',
        'shadow mode', 'cot-status', 'cot-export', 'cot_count', 'cot_flag',
        'eval_path', r'eval\.jsonl', 'eval pairs', 'eval chains',
        'archive eval', 'preference pair', 'Manufacturing DPO', 'archive synthesize',
        'archive spin', 'archive constitutional', 'archive quality',
        'archive registry', 'archive graduation',
    ]

    def matches(line, pats):
        for p in pats:
            if p in line:
                return True
        return False

    def get_indent(line):
        if not line.strip():
            return -1
        return len(line) - len(line.lstrip())

    def count_brackets(line):
        return (line.count('(') + line.count('[') + line.count('{')
              - line.count(')') - line.count(']') - line.count('}'))

    def find_compound_end(lines, idx):
        """Find end of a compound block (try/except/finally, if/elif/else)."""
        indent = get_indent(lines[idx])
        if indent < 0:
            return idx + 1
        j = idx + 1
        while j < len(lines):
            if lines[j].strip() == '':
                j += 1
                continue
            ji = get_indent(lines[j])
            if ji > indent:
                j += 1
            elif ji == indent:
                s = lines[j].strip()
                if s.startswith(('except', 'finally', 'elif ', 'else:')):
                    j += 1
                    while j < len(lines):
                        if lines[j].strip() == '':
                            j += 1
                            continue
                        if get_indent(lines[j]) > indent:
                            j += 1
                        else:
                            break
                else:
                    break
            else:
                break
        return j

    # Block delimiters
    block_tags = ['EVAL_BLOCK_START', 'SYNTH_BLOCK_START', 'SPIN_BLOCK_START',
                  'ACTIVE_LEARN_BLOCK_START', 'CONDUCTOR_BLOCK_START', 'PIPELINE_BLOCK_START',
                  'CONSTITUTIONAL_BLOCK_START', 'QUALITY_BLOCK_START',
                  'REGISTRY_BLOCK_START', 'SHADOW_BLOCK_START', 'GRADUATION_BLOCK_START',
                  'VAULT_BLOCK_START']
    i = 0
    while i < len(lines):
        matched = False
        for tag in block_tags:
            end_tag = tag.replace('START', 'END')
            if tag in lines[i]:
                matched = True
                while i < len(lines):
                    delete_lines.add(i)
                    if end_tag in lines[i]:
                        break
                    i += 1
                break
        if not matched:
            i += 1
        else:
            i += 1

    # Surgical + comment deletions with bracket awareness
    for i, line in enumerate(lines):
        if i in delete_lines:
            continue
        if matches(line, surgical) or matches(line, comment_only):
            delete_lines.add(i)
            net = count_brackets(line)
            j = i + 1
            while net > 0 and j < len(lines):
                delete_lines.add(j)
                net += count_brackets(lines[j])
                j += 1
            # If deleted line is a block header, delete its entire body
            stripped_code = line.strip().split('#')[0].rstrip()
            if stripped_code.endswith(':'):
                end = find_compound_end(lines, i)
                for k in range(i, end):
                    delete_lines.add(k)

    # Argparse for sensitive commands
    for i, line in enumerate(lines):
        if i in delete_lines:
            continue
        if re.search(r"add_parser\s*\(\s*['\"](?:archive|mine|eval|synth)", line):
            indent = get_indent(line)
            delete_lines.add(i)
            net = count_brackets(line)
            j = i + 1
            while j < len(lines):
                if lines[j].strip() == '' and net <= 0:
                    break
                ji = get_indent(lines[j])
                if net > 0 or (lines[j].strip() and ji > indent):
                    delete_lines.add(j)
                    net += count_brackets(lines[j])
                    j += 1
                else:
                    break

    # Dispatch lines
    for i, line in enumerate(lines):
        if i in delete_lines:
            continue
        if re.search(r"==\s*['\"](?:archive|mine|eval|synth)['\"]", line):
            indent = get_indent(line)
            delete_lines.add(i)
            j = i + 1
            while j < len(lines):
                if lines[j].strip() == '':
                    j += 1
                    continue
                if get_indent(lines[j]) > indent:
                    delete_lines.add(j)
                    j += 1
                else:
                    break

    # ═══ PHASE 4: Cascade empty blocks ═══
    BLOCK_KW = ('if ', 'elif ', 'else:', 'for ', 'while ', 'with ', 'try:', 'except', 'finally:', 'def ', 'async ', 'class ')

    def find_block_header(lines, i):
        """Detect block header at line i, handling multi-line headers.
        Returns (header_start, body_start, indent) or None."""
        if i in delete_lines:
            return None
        stripped = lines[i].strip()
        if not stripped or stripped.startswith('#'):
            return None
        indent = get_indent(lines[i])
        if indent < 0:
            return None
        # Single-line header: ends with ':'
        code = stripped.split('#')[0].rstrip()
        if code.endswith(':'):
            return (i, i + 1, indent)
        # Multi-line header: starts with block keyword and has unclosed brackets
        if not any(stripped.startswith(kw) for kw in BLOCK_KW):
            return None
        # Scan continuation lines until we find one ending with ':'
        j = i + 1
        while j < len(lines) and j < i + 10:  # max 10 continuation lines
            cont = lines[j].strip().split('#')[0].rstrip()
            if cont.endswith(':'):
                return (i, j + 1, indent)
            if cont and get_indent(lines[j]) <= indent and not cont.startswith(('and ', 'or ')):
                break  # Not a continuation
            j += 1
        return None

    changed = True
    while changed:
        changed = False
        for i in range(len(lines)):
            hdr = find_block_header(lines, i)
            if hdr is None:
                continue
            hdr_start, body_start, indent = hdr
            j = body_start
            has_body = False
            all_del = True
            while j < len(lines):
                if lines[j].strip() == '':
                    j += 1
                    continue
                ji = get_indent(lines[j])
                if ji > indent:
                    has_body = True
                    if j not in delete_lines:
                        all_del = False
                        break
                    j += 1
                else:
                    break
            if has_body and all_del:
                end = find_compound_end(lines, hdr_start)
                for k in range(hdr_start, end):
                    if k not in delete_lines:
                        delete_lines.add(k)
                        changed = True

    # Delete preceding comments
    for i in sorted(list(delete_lines)):
        k = i - 1
        while k >= 0:
            s = lines[k].strip()
            if s == '':
                k -= 1
                continue
            if s.startswith('#') and k not in delete_lines:
                delete_lines.add(k)
                k -= 1
            else:
                break

    kept = [lines[i] for i in range(len(lines)) if i not in delete_lines]

    # ═══ PHASE 5: Fix orphaned syntax ═══
    # Fix orphaned try blocks
    for _ in range(10):
        fixes = []
        for i, line in enumerate(kept):
            if line.strip() == 'try:':
                indent = get_indent(line)
                found = False
                last = i
                j = i + 1
                while j < len(kept):
                    s = kept[j].strip()
                    if s == '':
                        j += 1
                        continue
                    ji = get_indent(kept[j])
                    if s.startswith(('except', 'finally')) and ji == indent:
                        found = True
                        break
                    if ji <= indent:
                        break
                    last = j
                    j += 1
                if not found:
                    ind = ' ' * indent
                    fixes.append((last + 1, f'{ind}except Exception:\n{ind}    pass\n'))
        if not fixes:
            break
        for idx, text in reversed(fixes):
            kept.insert(idx, text)

    # Remove empty try/except blocks
    result = []
    i = 0
    while i < len(kept):
        if kept[i].strip() == 'try:':
            j = i + 1
            while j < len(kept) and kept[j].strip() == '':
                j += 1
            if j < len(kept) and kept[j].strip().startswith('except'):
                k = j + 1
                while k < len(kept) and kept[k].strip() in ('pass', ''):
                    k += 1
                i = k
                continue
        result.append(kept[i])
        i += 1
    kept = result

    # Fix orphaned elif (convert first elif to if when preceding if was deleted)
    for i, line in enumerate(kept):
        stripped = line.strip()
        if stripped.startswith('elif '):
            # Check if there's a matching if at the same indent above
            indent = get_indent(line)
            found_if = False
            for k in range(i - 1, max(0, i - 20), -1):
                s = kept[k].strip()
                if s == '':
                    continue
                ki = get_indent(kept[k])
                if ki == indent and (s.startswith('if ') or s.startswith('elif ')):
                    found_if = True
                    break
                if ki <= indent and s != '':
                    break
            if not found_if:
                kept[i] = line.replace('elif ', 'if ', 1)

    # Write result
    with open(filepath, 'w') as f:
        f.writelines(kept)

    # Verify
    import py_compile
    try:
        py_compile.compile(filepath, doraise=True)
    except py_compile.PyCompileError as e:
        print(f"ERROR: Sanitized file has syntax error: {e}", file=sys.stderr)
        sys.exit(1)

    # Check for remaining sensitive content
    final = ''.join(kept)
    check_patterns = ['Third Brother', 'dangerously-skip', 'archive_pipeline', '_DPOArchive',
                       'EVAL_BLOCK', 'SYNTH_BLOCK', 'SPIN_BLOCK', 'VAULT_BLOCK']
    leaks = [p for p in check_patterns if p in final]
    if leaks:
        print(f"WARNING: Sensitive patterns still present: {leaks}", file=sys.stderr)

    print(f"  Sanitized: {filepath} ({len(delete_lines)} lines removed, {len(kept)} remaining)")


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <path-to-cli.py>", file=sys.stderr)
        sys.exit(1)
    sanitize(sys.argv[1])
