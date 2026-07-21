# @nucleus/relay-sdk

Minimal TypeScript SDK for the Nucleus relay envelope protocol.

Implements the envelope format defined in
`docs/spec/relay_envelope_spec.md` §2 and the three core operations
(post / read / ack) from spec §3.

## Install

```sh
npm install @nucleus/relay-sdk
```

Separate from `nucleus-mcp`. Zero runtime deps (Node standard library only).

## Usage

```ts
import { RelayClient } from "@nucleus/relay-sdk";

const client = new RelayClient({ sender: "my_agent" });

// Build + write an envelope to <brain>/relay/<recipient>/
await client.post({
  to: "claude_code_main",
  subject: "[DONE] task",
  body: "shipped the SDK",
  priority: "normal",
});

// List messages in a bucket
const msgs = await client.read({ bucket: "claude_code_main" });

// Mark a message read (coarse-grained ack)
await client.ack(msgs[0].id);
```

## API

### `RelayClient`

- `new RelayClient({ sender, brainPath?, fromRole?, fromProvider?, fromSessionId? })`
- `post({ to, subject, body, priority?, ... })` — build + atomically write an envelope
- `read({ bucket? })` — list messages in a bucket (or all buckets when omitted)
- `ack(messageId)` — mark a message read; idempotent

### Envelope helpers

- `buildEnvelope({ sender, to, subject, body, priority?, ... })`
- `validateEnvelope(envelope)` → `{ ok, errors }`
- `mintMessageId()`, `normalizeId(id?)`, `nowIso()`
- `REQUIRED_FIELDS`, `VALID_PRIORITIES`, `ID_PATTERN`
- `EnvelopeError`

## Transport

Default transport is the filesystem mailbox (spec §3.1): envelopes are
written atomically (stage to `.tmp` then `rename`) to
`<brain>/relay/<recipient>/<ts>_<id>.json`. The brain root resolves from
`NUCLEUS_BRAIN_PATH` env or `./.brain` by default.

## License

MIT
