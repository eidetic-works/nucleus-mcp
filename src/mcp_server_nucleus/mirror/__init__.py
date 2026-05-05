"""Peer session-mirror substrate.

``daemon`` tails a peer agent's transcript (Cowork by default; any adapter
that yields the same JSONL shape via ``NUCLEUS_TRANSCRIPT_ROOT``) and mirrors
its last assistant turn into ``<brain>/session_mirror/cowork_last.md``.

``hook`` surfaces unread relays + the mirror as ``additionalContext`` for
SessionStart / UserPromptSubmit.
"""
