# Verified Snowflake Talent Marketplace — Feature Contract

## Product outcome

Extend the certification-preparation product into a candidate-controlled verified talent network:

```text
Prepare -> Certify -> Verify credential -> Build professional profile
        -> opt in to recruiter discovery -> candidate-controlled introduction
```

The marketplace is independent. Snowflake and SnowPro are used descriptively; the product must not imply that Snowflake Inc. operates, sponsors, endorses, certifies, or approves this marketplace.

## Implementation status

### Implemented in this branch: candidate credential verification foundation

- authenticated `#/credentials` Licenses & Certifications experience
- public Credly SnowPro badge URL intake
- HTTPS/host/path validation and outbound-host restriction
- normalized Snowflake issuer / SnowPro credential checks
- conservative candidate-name-to-Credly-recipient matching
- credential states: `pending`, `verified`, `expired`, `needs_review`, `rejected`
- same Credly badge cannot be claimed by two candidate accounts
- immutable verification-event history
- no raw Credly HTML stored; only normalized evidence and hashes
- re-verification flow
- candidate credential removal
- private-by-default talent profile
- recruiter/public discoverability locked until at least one active verified credential exists
- visibility automatically disabled if the last active verified credential is no longer active
- credential and talent-profile data included in candidate account export
- PostgreSQL migration plus SQLite compatibility bootstrap
- dedicated SQLite and PostgreSQL credential smoke tests

### Not implemented yet

- certificate PDF/image upload and private object storage
- manual administrator review console for `needs_review`
- recruiter accounts / company verification
- recruiter talent-library search
- recruiter saved lists
- candidate contact/introduction requests
- resume/contact-information release workflow
- Snowflake certification-directory verification provider
- recruiter subscriptions/monetization
- ATS integration

The recruiter-side work must not be described as live until those boundaries are implemented and tested.

## Verification model

### Principle

**An uploaded certificate is evidence, not authority.**

A candidate receives a verified credential only when the platform can validate issuer-backed evidence. The first implemented provider is a public Credly badge URL.

### LinkedIn-style candidate fields

The candidate-facing model mirrors the useful fields people expect in a Licenses & Certifications profile:

- credential name
- issuing organization
- issue date
- expiration date when applicable
- credential/badge ID
- credential URL
- verification state

Unlike a plain social profile, our `Verified` status is server-generated and cannot be set by the candidate.

### Credly verification flow

1. Candidate signs into their existing candidate account.
2. Candidate opens `#/credentials`.
3. Candidate pastes the public Credly URL from the badge Share experience.
4. Server accepts only HTTPS URLs on `credly.com` / `www.credly.com` with the supported badge UUID path.
5. Server retrieves only Credly-hosted verification evidence and refuses cross-host redirects.
6. Server normalizes the evidence into:
   - badge ID
   - credential name
   - issuer
   - recipient name
   - issued date
   - expiration date/status
   - canonical credential URL
7. Decision rules:
   - issuer is not Snowflake -> `rejected`
   - credential is not recognized as SnowPro -> `rejected`
   - recipient missing -> `needs_review`
   - recipient does not conservatively match candidate display name -> `needs_review`
   - issuer/title/name match but provider says expired -> `expired`
   - issuer/title/name match and active -> `verified`
8. A verification event is appended for every verification/reverification.
9. Candidate may enable recruiter discovery only while at least one credential is `verified`.

### Why the name rule is deliberately strict

Automatic identity binding should prefer false negatives over false positives. Punctuation, case, accents, and token order can normalize, but extra/missing name tokens do not auto-pass. A future manual-review path can handle maiden names, middle-name differences, legal-name changes, and other legitimate cases.

## Credential upload — next slice

When PDF/image upload is added:

- upload is private by default
- object is stored outside public/static assets
- malware/type/size checks run before acceptance
- document is never exposed to recruiters
- OCR/extracted text can assist review but cannot itself mark a credential verified
- verified facts must still trace to issuer-backed evidence or an authorized manual review
- document retention and deletion follow the candidate's privacy controls

## Candidate talent profile

Current fields:

- professional headline
- location
- availability
- `recruiter_discoverable`
- `public_profile`

Defaults:

- recruiter discoverable: **off**
- public profile: **off**

Rules:

- `public_profile=true` implies recruiter discoverability.
- either visibility mode requires at least one active verified credential.
- losing the final active verified credential turns both modes off.
- raw certificate evidence and learning telemetry remain private.

Future candidate fields may include:

- role family / target roles
- years of Snowflake experience
- employment type preference
- remote/hybrid/on-site preference
- professional skills
- LinkedIn/GitHub links
- resume
- work-authorization statement supplied by the candidate
- notice period / availability date

Sensitive or legally risky employment attributes must not be inferred from learning behavior or credential evidence.

## Strict separation from learning telemetry

Recruiters must never receive or filter candidates by:

- practice score
- mock score
- questions missed
- confidence ratings
- readiness score
- study frequency
- mistake notebook
- subscription tier

Employment discovery is based on candidate-authorized professional profile information and verified credential facts only.

## Recruiter boundary — future implementation

Recruiter accounts must be separate from candidate accounts and include:

1. verified email
2. company/domain data
3. recruiter terms
4. marketplace approval state
5. audit trail

Recruiter states:

```text
pending -> approved -> suspended -> revoked
```

A recruiter search result should show only candidate-authorized professional data and active verified credentials.

### Search dimensions

- certification
- certification count
- credential status
- role
- professional skills
- location
- remote preference
- experience band
- availability

### Contact model

Do not expose email/phone by default.

```text
Recruiter finds candidate
 -> submits structured introduction request
 -> candidate receives request
 -> candidate accepts or declines
 -> contact/resume is released only according to candidate settings
```

No unrestricted CSV export of the candidate library.

## Proposed tables

### Implemented

`candidate_talent_profiles`

`candidate_credentials`

`credential_verification_events`

### Future

`credential_documents`

`credential_manual_reviews`

`recruiter_accounts`

`recruiter_company_domains`

`recruiter_audit_events`

`candidate_profile_skills`

`candidate_contact_preferences`

`recruiter_candidate_requests`

`recruiter_saved_candidates`

## API surface

### Implemented candidate APIs

```text
GET    /api/credentials
POST   /api/credentials/credly/verify
POST   /api/credentials/{credential_uid}/reverify
DELETE /api/credentials/{credential_uid}
GET    /api/talent/profile
PATCH  /api/talent/profile
```

All require an authenticated candidate session.

### Future recruiter/admin APIs

Recruiter and administrator routes are intentionally omitted until their identity, authorization, abuse-control, and privacy boundaries exist.

## Fraud and security controls

Implemented:

- allowlisted Credly HTTPS hosts only
- UUID badge path validation
- cross-host redirect rejection
- bounded response size
- request timeout
- immutable evidence hash
- duplicate badge claim protection
- conservative candidate-name match
- candidate cannot directly set verification status
- candidate cannot turn on discoverability without an active verified credential

Future controls:

- verification retry rate limiting
- provider health/circuit breaker
- manual review with reviewer identity and reason
- periodic background reverification
- recruiter anti-scraping limits
- recruiter audit events
- candidate report/block workflow
- abuse monitoring

## Privacy and retention

- Profile discovery is opt-in.
- Certificate documents, when added, remain private.
- Verification facts are candidate-owned account data and are included in account export.
- Credential/profile rows use candidate foreign keys with deletion cascades.
- Recruiters see no study telemetry.
- Public profile is a separate explicit toggle from recruiter-only discovery.

Before a broad marketplace launch, privacy notice and terms must explicitly describe recruiter discovery, credential verification, contact requests, public profiles, retention, and deletion.

## Marketplace monetization — future

Candidate credential verification should remain free or broadly accessible; charging candidates merely to prove their legitimate SnowPro credential would undermine network growth.

Potential recruiter plans:

| Plan | Capability |
|---|---|
| Recruiter Free | limited verified-talent search |
| Recruiter Pro | advanced filters + introduction requests |
| Recruiter Team | seats + shared saved candidates |
| Enterprise | governance, integrations, analytics |

Do not monetize by selling raw candidate lists.

## Definition of Done

### Candidate verification foundation

- [x] authenticated credentials route
- [x] Credly public URL accepted and canonicalized
- [x] non-Credly / malformed URL rejected
- [x] Snowflake issuer required
- [x] SnowPro credential family required
- [x] recipient ownership match required for auto-verification
- [x] name mismatch routes to manual-review state
- [x] expiration disables active verification
- [x] duplicate badge claim blocked
- [x] immutable verification events stored
- [x] raw provider HTML not stored
- [x] reverify and remove actions
- [x] discoverability private by default
- [x] active verified credential required for discovery
- [x] final active credential loss disables visibility
- [x] candidate account export includes credential/profile facts
- [x] SQLite smoke
- [x] PostgreSQL smoke

### Remaining marketplace release gates

- [ ] private certificate-document upload/storage
- [ ] manual review console
- [ ] recruiter identity/company verification
- [ ] recruiter-only search authorization
- [ ] recruiter search UI/API
- [ ] introduction-request workflow
- [ ] candidate-controlled resume/contact release
- [ ] recruiter rate limiting / anti-scraping
- [ ] privacy/terms update for employment marketplace
- [ ] scheduled credential reverification
- [ ] browser E2E covering candidate credential UX
- [ ] production deployment verification

Until all required recruiter-side and privacy gates are complete, this feature must be described as the **candidate verified-credential foundation**, not a live recruiter marketplace.
