/**
 * @nucleus/relay-sdk — minimal TypeScript SDK for the relay envelope protocol.
 *
 * Implements the envelope format defined in `docs/spec/relay_envelope_spec.md`
 * §2 and the three core operations (post / read / ack) from spec §3.
 *
 * Install (separate from `nucleus-mcp`)::
 *
 *     npm install @nucleus/relay-sdk
 *
 * Usage::
 *
 *     import { RelayClient } from "@nucleus/relay-sdk";
 *
 *     const client = new RelayClient({ sender: "my_agent" });
 *     await client.post({ to: "claude_code_main", subject: "[DONE] task", body: "shipped" });
 *     const msgs = await client.read({ bucket: "claude_code_main" });
 *     await client.ack(msgs[0].id);
 *
 * The default transport is the filesystem mailbox (spec §3.1): envelopes are
 * written atomically to `<brain>/relay/<recipient>/<ts>_<id>.json`. The
 * client is transport-agnostic at the API surface — a future HTTP transport
 * can be slotted in behind the same three methods.
 */

import * as fs from "node:fs";
import * as path from "node:path";
import { promisify } from "node:util";

import {
  buildEnvelope,
  EnvelopeError,
  EnvelopeOptions,
  Priority,
  RelayEnvelope,
  validateEnvelope,
} from "./envelope";

export {
  buildEnvelope,
  validateEnvelope,
  EnvelopeError,
  EnvelopeError as RelayEnvelopeError,
  mintMessageId,
  normalizeId,
  nowIso,
  REQUIRED_FIELDS,
  VALID_PRIORITIES,
  ID_PATTERN,
} from "./envelope";
export type {
  EnvelopeOptions,
  Priority,
  RelayEnvelope,
  ValidationResult,
} from "./envelope";

const readFile = promisify(fs.readFile);
const writeFile = promisify(fs.writeFile);
const readdir = promisify(fs.readdir);
const stat = promisify(fs.stat);
const mkdir = (p: string, opts?: fs.MakeDirectoryOptions) =>
  fs.promises.mkdir(p, { recursive: true, ...opts });

/** Resolve the brain path from env or fall back to repo-local `.brain`. */
function defaultBrainPath(): string {
  const env = process.env.NUCLEUS_BRAIN_PATH;
  if (env && env.trim()) {
    return path.resolve(env);
  }
  return path.resolve(process.cwd(), ".brain");
}

/** Sanitize a recipient name for filesystem use (no path traversal). */
function sanitizeRecipient(recipient: string): string {
  return recipient.replace(/[^A-Za-z0-9._-]/g, "_");
}

/** Convert an ISO-8601 timestamp to a filename-safe prefix. */
function timestampToPrefix(iso: string): string {
  // iso looks like 2026-07-18T15:12:13.970Z → 20260718T151213970Z
  return iso
    .replace(/[-:]/g, "")
    .replace(/\.\d+$/, (m) => m.replace(".", ""))
    .replace(/\.\d+Z$/, (m) => m.replace(".", "").replace("Z", "Z"));
}

export interface RelayClientOptions {
  /** Sender identity string (spec `from`). Required. */
  sender: string;
  /** Optional override for the brain root. Defaults to `NUCLEUS_BRAIN_PATH` env or `./.brain`. */
  brainPath?: string;
  /** Optional sender metadata stamped onto every envelope built by this client. */
  fromRole?: string | null;
  fromProvider?: string | null;
  fromSessionId?: string | null;
}

export interface PostArgs extends EnvelopeOptions {
  to: string;
  subject: string;
  body: string;
  priority?: Priority;
  message_id?: string | null;
}

export interface PostResult {
  id: string;
  status: "sent";
  sent: true;
  to: string;
  path: string;
  envelope: RelayEnvelope;
}

export interface AckResult {
  acked: boolean;
  message_id?: string;
  error?: string;
  noop?: boolean;
  envelope?: RelayEnvelope;
}

/**
 * Minimal client for the relay envelope protocol.
 *
 * Three methods (spec task g4_relay_sdk_typescript):
 *   - `post(args)` — build + write an envelope
 *   - `read({ bucket })` — list messages in a bucket
 *   - `ack(messageId)` — mark a message read
 */
export class RelayClient {
  readonly sender: string;
  readonly brainPath: string;
  readonly fromRole?: string | null;
  readonly fromProvider?: string | null;
  readonly fromSessionId?: string | null;

  constructor(opts: RelayClientOptions) {
    if (!opts || !opts.sender || !String(opts.sender).trim()) {
      throw new Error("RelayClient: sender is required");
    }
    this.sender = String(opts.sender);
    this.brainPath = opts.brainPath
      ? path.resolve(opts.brainPath)
      : defaultBrainPath();
    this.fromRole = opts.fromRole ?? null;
    this.fromProvider = opts.fromProvider ?? null;
    this.fromSessionId = opts.fromSessionId ?? null;
  }

  /**
   * Build a valid envelope and atomically write it to the recipient inbox.
   *
   * Returns a result object with `id`, `status="sent"`, `sent=true`, and
   * `path` (the on-disk envelope path). Throws `EnvelopeError` if the
   * envelope fails validation.
   */
  async post(args: PostArgs): Promise<PostResult> {
    const envelope = buildEnvelope({
      sender: this.sender,
      to: args.to,
      subject: args.subject,
      body: args.body,
      priority: args.priority ?? "normal",
      message_id: args.message_id ?? null,
      from_role: this.fromRole ?? args.from_role ?? null,
      from_provider: this.fromProvider ?? args.from_provider ?? null,
      from_session_id: this.fromSessionId ?? args.from_session_id ?? null,
      to_session_id: args.to_session_id ?? null,
      in_reply_to: args.in_reply_to ?? null,
      context: args.context ?? {},
      task_id: args.task_id ?? null,
      project: args.project ?? null,
    });

    const { ok, errors } = validateEnvelope(envelope);
    if (!ok) {
      throw new EnvelopeError(errors.join("; "));
    }

    const filePath = await this.writeEnvelope(envelope);
    return {
      id: envelope.id,
      status: "sent",
      sent: true,
      to: args.to,
      path: filePath,
      envelope,
    };
  }

  /**
   * List messages in a bucket (recipient inbox).
   *
   * @param bucket Recipient inbox name (e.g. `"claude_code_main"`). When
   *   omitted, lists every envelope across all buckets under
   *   `<brain>/relay/`.
   * @returns Array of envelopes, newest-first by filename (which encodes
   *   the timestamp per spec §3.1).
   */
  async read(opts?: { bucket?: string | null }): Promise<RelayEnvelope[]> {
    if (opts && opts.bucket) {
      const inboxDir = path.join(this.brainPath, "relay", opts.bucket);
      return this.readDir(inboxDir);
    }
    const relayRoot = path.join(this.brainPath, "relay");
    let entries: string[];
    try {
      entries = await readdir(relayRoot);
    } catch {
      return [];
    }
    const out: RelayEnvelope[] = [];
    for (const sub of entries.sort()) {
      const subPath = path.join(relayRoot, sub);
      let isDir = false;
      try {
        isDir = (await stat(subPath)).isDirectory();
      } catch {
        continue;
      }
      if (isDir) {
        out.push(...(await this.readDir(subPath)));
      }
    }
    out.sort((a, b) => (a.id < b.id ? 1 : -1));
    return out;
  }

  /**
   * Mark a message as read (coarse-grained ack, spec §2.1 `read`).
   *
   * Updates `read=true`, `read_at` (ISO-8601 UTC), `read_by` (this
   * client's sender). Idempotent — acking an already-read message is a
   * no-op that still returns `acked=true`.
   *
   * Returns `{ acked: true, message_id, envelope }` on success, or
   * `{ acked: false, error }` if the message was not found.
   */
  async ack(messageId: string): Promise<AckResult> {
    if (!messageId || !String(messageId).trim()) {
      return { acked: false, error: "RelayClient.ack: messageId is required" };
    }
    const messages = await this.read();
    const found = messages.find((m) => m.id === messageId);
    if (!found) {
      return { acked: false, error: `message ${messageId} not found` };
    }
    const filePath = (found as RelayEnvelope & { _path?: string })._path;
    if (!filePath) {
      return { acked: false, error: `message ${messageId} missing _path` };
    }

    // Idempotent: if already read by us, no-op.
    if (found.read && found.read_by === this.sender) {
      return { acked: true, message_id: messageId, envelope: found, noop: true };
    }

    const updated: RelayEnvelope = {
      ...found,
      read: true,
      read_at: found.read_at ?? new Date().toISOString(),
      read_by: found.read_by ?? this.sender,
      read_by_sessions: {
        ...found.read_by_sessions,
        [this.sender]: found.read_at ?? new Date().toISOString(),
      },
    };

    // Strip internal keys before persisting.
    const persist: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(updated)) {
      if (!k.startsWith("_")) {
        persist[k] = v;
      }
    }
    await atomicWriteJson(filePath, persist);
    return { acked: true, message_id: messageId, envelope: updated };
  }

  // ----------------------------------------------------------- internals

  private async readDir(inboxDir: string): Promise<RelayEnvelope[]> {
    let entries: string[];
    try {
      entries = await readdir(inboxDir);
    } catch {
      return [];
    }
    const out: RelayEnvelope[] = [];
    for (const name of entries.sort().reverse()) {
      if (!name.endsWith(".json")) continue;
      const filePath = path.join(inboxDir, name);
      try {
        const raw = await readFile(filePath, "utf-8");
        const env = JSON.parse(raw) as RelayEnvelope;
        // Attach internal path for ack() to use.
        (env as RelayEnvelope & { _path?: string })._path = filePath;
        out.push(env);
      } catch {
        continue;
      }
    }
    return out;
  }

  /** Atomically write an envelope to the recipient inbox (spec §3.1). */
  private async writeEnvelope(envelope: RelayEnvelope): Promise<string> {
    const recipient = sanitizeRecipient(envelope.to);
    const inboxDir = path.join(this.brainPath, "relay", recipient);
    await mkdir(inboxDir, { recursive: true });

    const tsPrefix = timestampToPrefix(envelope.created_at).replace("Z", "");
    const fname = `${tsPrefix}_${envelope.id}.json`;
    const target = path.join(inboxDir, fname);
    await atomicWriteJson(target, envelope as unknown as Record<string, unknown>);
    return target;
  }
}

/** Atomically write JSON: stage to `.tmp` then `fs.rename` (spec §3.1). */
async function atomicWriteJson(
  target: string,
  payload: Record<string, unknown>,
): Promise<void> {
  await mkdir(path.dirname(target), { recursive: true });
  const tmp = `${target}.${process.pid}.${Date.now()}.tmp`;
  await writeFile(tmp, JSON.stringify(payload, null, 2), "utf-8");
  await fs.promises.rename(tmp, target);
}
