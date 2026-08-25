# Snowflake Certification Platform — Release Assurance Matrix

This document defines the minimum evidence required before the platform can be described as release-ready. A green build is necessary but does not replace production deployment verification, private-content import verification, SME review, or an independent authenticated penetration test.

## Status language

- **PASS** — the named automated gate completed successfully on the exact release commit.
- **GAP** — implementation exists, but required assurance evidence is incomplete.
- **BLOCKER** — do not claim production GO until resolved.
- **GO** — all required automated gates plus deployment-specific checks are complete.

## Capability-to-test mapping

| Capability | Primary automated evidence | What it proves |
|---|---|---|
| COF-C03 curriculum / blueprint | `scripts/smoke_core_guide.py`, Certification Guide Smoke | 5 domains, 19 task statements, canonical guide contract |
| Public / authenticated content boundary | `scripts/test_authenticated_content_boundary.py`, `scripts/test_security_adversarial.py` | protected learning runtime is not anonymously exposed |
| Candidate registration / login / logout | `scripts/test_auth_membership.py`, `scripts/test_auth_verification_ux.py`, adversarial security suite | account lifecycle, session creation/revocation, verification UX |
| Session and browser security | `tests/test_security_units.py`, `scripts/test_security_adversarial.py`, `app/security.py` | cookie flags, cross-site mutation blocking, rate-limit safety net, hardening headers |
| Membership / entitlement | `scripts/test_auth_membership.py`, `scripts/test_billing_tier_transitions.py` | tier-aware access and membership transitions |
| Google identity | `scripts/test_google_browser_state.py`, `scripts/test_google_identity_continuity.py` | OAuth state binding and account continuity |
| Billing authority / Stripe boundary | `scripts/test_google_billing_security.py`, `scripts/test_billing_unknown_price_fail_closed.py` | billing does not trust client-supplied tier/price authority |
| Exam Pack lifecycle | `scripts/test_exam_pack_expiry_reconciliation.py` | expiry and reconciliation semantics |
| Practice / diagnostic / tier pools | `scripts/test_question_bank_tiers.py` | tier selection, diagnostic/practice/mock behavior using controlled fixtures |
| Question version immutability | `scripts/test_question_version_immutability.py` | historical sittings retain the question version used |
| Question release activation / rollback | `scripts/test_question_bank_releases.py` | controlled bank release lifecycle |
| 1,200-question private-bank metadata | `scripts/test_question_bank_manifest_contract.py` | version/hash/count/domain/task/pool/difficulty manifest consistency |
| Private-bank confidentiality | production launch gate + authenticated content boundary | bank files and answer material are not public frontend assets |
| Mock exam | `scripts/test_mock_exam.py`, `scripts/test_tier_reset_full_exams.py` | timed quick/full sitting behavior, reset/rotation, answer hiding |
| Exam entitlement concurrency | `scripts/test_exam_entitlement_concurrency.py` | limited exam allocations remain atomic under concurrency |
| Adaptive readiness | `scripts/test_adaptive_readiness_intelligence.py`, Adaptive Readiness Smoke | evidence-based readiness/recommendation behavior |
| Candidate learning intelligence | `scripts/test_candidate_learning_intelligence.py` | attempts feed downstream learning state correctly |
| Credential / Credly verification | `tests/test_security_units.py`, `scripts/smoke_verified_credentials.py`, browser matrix | Credly URL restrictions, issuer/title/name/expiry state, UI persistence |
| Account export / lifecycle | Account Lifecycle Smoke, `scripts/test_account_lifecycle.py` | candidate-owned data participates in export/lifecycle controls |
| PostgreSQL production semantics | PostgreSQL Production Smoke, Production Launch Gate | migrations, native PostgreSQL behavior, regression suite, logical backup/restore |
| SQLite development parity | Production Launch Gate SQLite convergence job | development/test backend remains behaviorally compatible |
| Browser / responsive UI | `scripts/test_production_browser_matrix.py`, V26 Visual Parity | Chromium desktop, Firefox desktop, mobile, accessibility baseline |
| Accessibility baseline | production browser matrix | landmarks, accessible names, no basic structural regressions |
| Operational readiness | `scripts/test_production_observability.py`, readiness/health checks | health/readiness, metrics boundary, basic operational signals |
| Content freshness | content freshness workflows | source-sensitive Snowflake content has a repeatable freshness process |
| Copyright / no-dump policy | Content IP Compliance workflow | public policy and prohibited-source guardrails remain present |
| Static application security | Bandit report + blocking policy | high-confidence high-severity Python SAST findings block release |
| Dependency vulnerabilities | `pip-audit --strict` | known Python dependency vulnerabilities block release |
| Dynamic public-surface security | OWASP ZAP baseline DAST | common unauthenticated web findings on an isolated running build |
| Adversarial authenticated security | `scripts/test_security_adversarial.py` | selected access-control, CSRF, traversal, injection-shaped, session and rate-limit attacks |

## Required release gates

A release candidate must have all of the following green on the exact commit:

1. Certification Guide Smoke.
2. PostgreSQL Production Smoke.
3. Production Launch Gate, including Chromium, Firefox and mobile rehearsal.
4. Verified Credentials Smoke when credential functionality is included.
5. Account Lifecycle Smoke.
6. Adaptive Readiness Smoke.
7. V26 Visual Parity.
8. Security Assurance: unit/adversarial, SAST/dependency, and ZAP DAST.
9. Question-bank manifest integrity contract.

## Checks automation cannot substitute for

The following remain separate launch evidence:

- **Private-bank runtime import verification.** The exact reviewed private artifact must be hash-checked, imported into the intended production data store, and exercised through candidate flows. A manifest alone is not runtime proof.
- **Production URL verification.** The deployed release must be fetched and exercised from the real public hostname; a successful deployment submission is not enough.
- **Independent authenticated penetration test.** Automated ZAP/Bandit/adversarial tests improve assurance, but they are not a human pentest. This becomes a required gate before scaling recruiter PII, payments, or enterprise recruiter access.
- **Independent Snowflake SME/editorial review.** Automated structure/source checks do not prove every question is unambiguous, current, or instructionally excellent.
- **Recruiter marketplace privacy/security review.** Search visibility, contact release, resume access, company verification, abuse controls, retention and deletion must be reviewed before recruiter launch.

## Question-bank truth model

The platform must report question-bank status in three separate layers:

1. **Authored artifact count** — number of questions in the reviewed private artifact.
2. **Imported runtime count** — number of active questions actually present in the release database/content store.
3. **Candidate-visible entitlement** — the subset a candidate may receive based on plan, pool, exam type and release policy.

Never use the authored count as proof of runtime import, and never expose private bank internals or answer material to the browser before submission.
