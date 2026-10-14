# ADR 0001: Preserve V26, Vercel and Neon for GA

- Status: Accepted
- Date: 2026-10-13

## Context

The repository already has a production-oriented V26 vanilla JavaScript SPA, FastAPI API, Vercel deployment and managed Neon PostgreSQL persistence. The user brief explicitly freezes these choices unless a proven blocker exists.

## Decision

Keep these components for GA. Keep SQLite for local/test compatibility only. Run schema migration separately from request-serving runtime and keep production question content in governed PostgreSQL releases.

## Consequences

No framework or production datastore migration is in scope. Hosted Preview verification must prove the deployed behavior and runtime privileges before acceptance; local tests alone do not.
