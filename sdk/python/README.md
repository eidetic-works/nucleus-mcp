# nucleus-relay-sdk

Minimal Python SDK for the Nucleus relay envelope protocol.

Implements the envelope format defined in
[`docs/spec/relay_envelope_spec.md`](../../docs/spec/relay_envelope_spec.md) §2
and the three core operations (post / read / ack) from §3.

## Install

```bash
pip install nucleus-relay-sdk
```

Separate from `nucleus-mcp` — this package has zero runtime dependencies and
only depends on the Python standard library.

## Usage

```python
from nucleus_relay_sdk import RelayClient

client = RelayClient(sender="my_agent")
client.post(to="claude_code_main", subject="[DONE] task", body="shipped")
msgs = client.read(bucket="claude_code_main")
client.ack(msgs[0]["id"])
```

## API

### `RelayClient(sender, *, brain_path=None, from_role=None, from_provider=None, from_session_id=None)`

- `post(to, subject, body, priority="normal")` — build + atomically write an envelope
- `read(bucket=None)` — list messages in a bucket (or all buckets when `None`)
- `ack(message_id)` — mark a message read; idempotent

### Envelope helpers

- `build_envelope(...)` — build a spec-compliant envelope dict
- `validate_envelope(env)` — returns `(ok, errors)` tuple
- `mint_message_id()` — `relay_<YYYYMMDD>_<HHMMSS>_<8hex>`
- `EnvelopeError` — raised on malformed envelopes

## Transport

Default transport is the filesystem mailbox: envelopes are written atomically
(stage to `.tmp`, then `os.replace`) to `<brain>/relay/<recipient>/<ts>_<id>.json`.
The brain root resolves from `NUCLEUS_BRAIN_PATH` env var or `./.brain` by default.
