# Component Architecture

## API components

`app/main.py` composes the FastAPI service, middleware, read-only schema verification, readiness endpoints and routers. Routers are transport adapters; domain modules own policy and persistence behavior.

| Concern | Existing authority | Key paths |
| --- | --- | --- |
| Candidate identity and sessions | `app/auth.py`, account lifecycle | `app/routers/auth.py`, `app/routers/account.py` |
| Certification and skill map | `app/skill_brain.py`, authored configuration | `app/routers/skills.py`, `config/` |
| Question content and releases | `app/question_bank.py`, `app/question_versions.py`, `app/question_bank_releases.py` | question bank runtime and editorial routers |
| Practice and mocks | existing practice/mock domain modules | `app/routers/certification_practice.py`, mock routers |
| Learning evidence and readiness | `app/learning_intelligence.py`, `app/adaptive_readiness.py` | intelligence and adaptive routers |
| Membership | `app/billing/` and trusted webhook transitions | `app/routers/billing.py` |
| Editorial | `app/question_editorial.py` and review governance | question source intake and QA scripts |
| Operations | `app/observability.py`, `app/security.py` | health, ready and protected metrics routes |

## State authorities

There is one internal candidate identity; one certification blueprint/skill graph; one governed question release authority; one candidate evidence store reused by practice, mocks, review and readiness; one server-side entitlement authority; and one release identity exposed by `/api/release`. Browser views compose these authorities and do not establish access, grades or readiness.

Donor features are integrated as views and workflows over these authorities. They do not create alternate curriculum, question, candidate-progress or readiness stores.

## Frontend

`frontend/index-v26.html`, `frontend/app-complete.js` and `frontend/router-complete.js` form the V26 SPA shell. Feature views in `frontend/views/` call the API and render candidate/public surfaces. Shared navigation, API, session and design-system modules remain the common shell. Direct hash routes are presentation routes, never authorization boundaries.
