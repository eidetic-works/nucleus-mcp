/**
 * Relay envelope builder + validator.
 *
 * Implements the envelope format defined in
 * `docs/spec/relay_envelope_spec.md` §2 (Required + Optional fields).
 *
 * The envelope is a JSON object carrying coordination signals between
 * independent agent runtimes. This module is transport-agnostic — it only
 * handles the canonical JSON shape. The `RelayClient` in `index.ts` wraps
 * the filesystem transport on top of this.
 */

// §2.1 Required fields. Order preserved for readability.
export const REQUIRED_FIELDS = [
  "id",
  "from",
  "to",
  "subject",
  "body",
  "priority",
  "created_at",
  "read",
  "read_at",
  "read_by",
] as const;

// §2.1 priority enum.
export const VALID_PRIORITIES = [
  "low",
  "normal",
  "high",
  "urgent",
  "critical",
] as const;

// §2.1 id policy: caller-supplied ids are preserved verbatim when they match
// this charset/length window; otherwise a fresh server-minted id is produced.
export const ID_PATTERN = /^[A-Za-z0-9._:-]{8,128}$/;

// §2.1 subject policy: ≤256 chars, no newlines.
const MAX_SUBJECT_LEN = 256;

export type Priority = (typeof VALID_PRIORITIES)[number];

/** Optional sender / routing metadata (spec §2.2). */
export interface EnvelopeOptions {
  from_role?: string | null;
  from_provider?: string | null;
  from_session_id?: string | null;
  to_session_id?: string | null;
  in_reply_to?: string | null;
  context?: Record<string, unknown>;
  task_id?: string | null;
  project?: string | null;
}

/** Canonical relay envelope (spec §2.1 + §2.2). */
export interface RelayEnvelope extends Required<EnvelopeOptions> {
  id: string;
  from: string;
  to: string;
  subject: string;
  body: string;
  priority: Priority;
  created_at: string;
  read: boolean;
  read_at: string | null;
  read_by: string | null;
  read_by_sessions: Record<string, string>;
}

/** Raised when an envelope is malformed (missing/invalid fields). */
export class EnvelopeError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "EnvelopeError";
    // Restore prototype chain for ES5 targets.
    Object.setPrototypeOf(this, EnvelopeError.prototype);
  }
}

/** ISO-8601 UTC timestamp with `Z` suffix (spec §2.1 created_at). */
export function nowIso(): string {
  // Format: YYYY-MM-DDTHH:MM:SS.sssZ (millisecond precision is sufficient
  // and matches the JS Date.toISOString() shape used everywhere in Node).
  return new Date().toISOString();
}

/**
 * Mint a server-format message id: `relay_<YYYYMMDD>_<HHMMSS>_<8hex>`.
 * Matches the spec §2.1 server-minted format.
 */
export function mintMessageId(): string {
  const d = new Date();
  const pad = (n: number, len = 2) => String(n).padStart(len, "0");
  const ts =
    `${d.getUTCFullYear()}${pad(d.getUTCMonth() + 1)}${pad(d.getUTCDate())}` +
    `_${pad(d.getUTCHours())}${pad(d.getUTCMinutes())}${pad(d.getUTCSeconds())}`;
  const hex = Array.from({ length: 4 }, () =>
    Math.floor(Math.random() * 256)
      .toString(16)
      .padStart(2, "0"),
  ).join("");
  return `relay_${ts}_${hex}`;
}

/**
 * Return a valid envelope id.
 *
 * Caller-supplied ids that match `ID_PATTERN` are preserved verbatim;
 * anything else (undefined, empty, bad charset, wrong length) gets a fresh
 * server-minted id. Matches spec §2.1.
 */
export function normalizeId(messageId?: string | null): string {
  if (messageId && ID_PATTERN.test(messageId)) {
    return messageId;
  }
  return mintMessageId();
}

/**
 * Build a relay envelope object matching spec §2.
 *
 * The caller MUST supply `sender` (the MCP server process cannot infer
 * which client is calling — spec §2.1 `from` is required). All other
 * optional fields default to spec-compliant values.
 *
 * @throws {EnvelopeError} if a required argument is empty or priority invalid.
 */
export function buildEnvelope(args: {
  sender: string;
  to: string;
  subject: string;
  body: string;
  priority?: Priority;
  message_id?: string | null;
} & EnvelopeOptions): RelayEnvelope {
  const {
    sender,
    to,
    subject,
    body,
    priority = "normal",
    message_id = null,
    from_role = null,
    from_provider = null,
    from_session_id = null,
    to_session_id = null,
    in_reply_to = null,
    context = {},
    task_id = null,
    project = null,
  } = args;

  if (!sender || !sender.trim()) {
    throw new EnvelopeError("envelope: 'from' (sender) is required");
  }
  if (!to || !to.trim()) {
    throw new EnvelopeError("envelope: 'to' is required");
  }
  if (subject === null || subject === undefined) {
    throw new EnvelopeError("envelope: 'subject' is required");
  }
  const subj = String(subject);
  if (/[\r\n]/.test(subj)) {
    throw new EnvelopeError("envelope: 'subject' must not contain newlines");
  }
  if (subj.length > MAX_SUBJECT_LEN) {
    throw new EnvelopeError(
      `envelope: 'subject' exceeds ${MAX_SUBJECT_LEN} chars`,
    );
  }
  if (body === null || body === undefined) {
    throw new EnvelopeError("envelope: 'body' is required");
  }
  if (!VALID_PRIORITIES.includes(priority as Priority)) {
    throw new EnvelopeError(
      `envelope: priority '${priority}' not in [${VALID_PRIORITIES.join(", ")}]`,
    );
  }

  return {
    id: normalizeId(message_id),
    from: String(sender),
    to: String(to),
    subject: subj,
    body: String(body),
    priority: priority as Priority,
    created_at: nowIso(),
    read: false,
    read_at: null,
    read_by: null,
    from_role: from_role ?? null,
    from_provider: from_provider ?? null,
    from_session_id: from_session_id ?? null,
    to_session_id: to_session_id ?? null,
    in_reply_to: in_reply_to ?? null,
    context: context ?? {},
    task_id: task_id ?? null,
    project: project ?? null,
    read_by_sessions: {},
  };
}

export interface ValidationResult {
  ok: boolean;
  errors: string[];
}

/**
 * Validate a dict against the relay envelope spec §2.
 *
 * Returns `{ ok, errors }`. `ok` is true iff the envelope has every
 * required field with a non-null value of the right shape, the priority
 * is in the allowed enum, and the subject has no newlines and is ≤256
 * chars. `errors` is the list of human-readable violations (empty when
 * `ok` is true).
 *
 * This is the validator referenced by the SDK acceptance test
 * "Envelope validator rejects missing required fields".
 */
export function validateEnvelope(envelope: unknown): ValidationResult {
  const errors: string[] = [];
  if (typeof envelope !== "object" || envelope === null || Array.isArray(envelope)) {
    return { ok: false, errors: ["envelope: must be a JSON object"] };
  }
  const env = envelope as Record<string, unknown>;

  for (const field of REQUIRED_FIELDS) {
    if (!(field in env)) {
      errors.push(`envelope: missing required field '${field}'`);
      continue;
    }
    // read_at / read_by may legitimately be null — only require presence.
    if (field === "read_at" || field === "read_by") {
      continue;
    }
    const val = env[field];
    if (val === null || val === undefined) {
      errors.push(`envelope: required field '${field}' is empty`);
      continue;
    }
    if (typeof val === "string" && !val.trim()) {
      errors.push(`envelope: required field '${field}' is empty`);
    }
  }

  // Priority enum.
  const prio = env["priority"];
  if (
    prio !== null &&
    prio !== undefined &&
    (typeof prio !== "string" || !VALID_PRIORITIES.includes(prio as Priority))
  ) {
    errors.push(
      `envelope: priority '${prio}' not in [${VALID_PRIORITIES.join(", ")}]`,
    );
  }

  // Subject shape.
  const subj = env["subject"];
  if (typeof subj === "string") {
    if (/[\r\n]/.test(subj)) {
      errors.push("envelope: 'subject' must not contain newlines");
    }
    if (subj.length > MAX_SUBJECT_LEN) {
      errors.push(`envelope: 'subject' exceeds ${MAX_SUBJECT_LEN} chars`);
    }
  }

  // read must be boolean.
  if ("read" in env && typeof env["read"] !== "boolean") {
    errors.push("envelope: 'read' must be a boolean");
  }

  // created_at must be a string.
  const ca = env["created_at"];
  if (ca !== null && ca !== undefined && typeof ca !== "string") {
    errors.push("envelope: 'created_at' must be an ISO-8601 string");
  }

  return { ok: errors.length === 0, errors };
}
