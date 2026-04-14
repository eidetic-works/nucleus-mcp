# Architecture Decision Records

This directory contains ADRs for significant design decisions in Nucleus MCP.

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [ADR-001](001-http-transport.md) | HTTP Transport Layer and Tenant-Aware Sovereignty Architecture | Implemented | 2026-04-14 |

## What is an ADR?

An Architecture Decision Record captures:
- **Context** — the problem and constraints at the time of the decision
- **Decision** — what was chosen and why
- **Consequences** — what the decision enables, what it trades away

ADRs are written for contributors and agents building on Nucleus. They encode the reasoning behind design choices so future work compounds on a solid foundation rather than relitigating settled questions.

## Adding a new ADR

Copy the structure from an existing ADR. Number sequentially (ADR-002, ADR-003...). Add a row to this index. Decisions worth recording: transport changes, storage format choices, auth model changes, tenant isolation approaches, API surface changes.
