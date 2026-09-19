# Clouding Academy donor integration

Branch: `feat/donor-clouding-academy`

Implemented as a Snowflake-native daily learning loop:
- deterministic daily certification task
- Blitz active-recall cards
- server-persisted recall evidence in the existing candidate learning-event ledger
- cross-device consecutive-day Blitz streak and same-day idempotency
- Architecture Builder reasoning prompt by COF-C03 domain
- direct handoff to task lessons, deterministic labs, targeted practice, adaptive readiness, mocks and progress

The branch reuses the existing certification blueprint, candidate identity, learning-intelligence database, and evidence systems. It does not create a second curriculum, question bank, or browser-local progress authority.

A recall mark is candidate-owned evidence. Multiple clicks on the same task/day do not inflate the streak. The streak is calculated from persisted server records rather than `localStorage`.
