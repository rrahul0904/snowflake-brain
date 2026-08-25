# Verified Talent Marketplace — Feature Contract

Status: Proposed feature contract

## Product thesis

Extend the certification-preparation product into a candidate-controlled talent network for Snowflake-certified professionals.

The platform should connect three moments in one lifecycle:

1. prepare for a SnowPro certification;
2. prove the resulting credential using official verification evidence;
3. optionally become discoverable to verified recruiters looking for Snowflake talent.

This is an independent talent marketplace. It must not imply that Snowflake Inc. operates, sponsors, endorses, or verifies this marketplace.

## Core product boundary

A certificate upload is evidence, not verification.

The platform must never label a credential `verified` solely because a candidate uploaded a PDF, image, screenshot, resume, email, or self-entered credential number.

A verified credential requires confirmation against official issuer evidence or a controlled manual review of official verification evidence.

Candidates are private by default. Uploading or verifying a credential never makes a candidate public automatically.

## Candidate journey

### 1. Create candidate profile

Existing authenticated candidates can create a talent profile containing only career-relevant fields they explicitly choose to provide:

- preferred name
- professional headline
- current role
- Snowflake experience in years
- primary Snowflake role: data engineer, architect, administrator, data scientist, developer, analyst, platform engineer, consultant, other
- Snowflake skills
- adjacent technologies
- country / region / metro area
- remote / hybrid / onsite preference
- employment preference: full-time, contract, consulting
- availability date / availability state
- work-authorization statement supplied by the candidate
- optional LinkedIn / GitHub / portfolio links
- optional resume

Do not request age, date of birth, race, ethnicity, religion, disability, marital status, sexual orientation, gender identity, medical information, Social Security number, passport number, or other fields that are unnecessary for the marketplace.

### 2. Add a certification

Candidate selects a supported certification and provides one or more evidence types:

- official Snowflake certification verification URL;
- public digital badge URL issued for the credential;
- credential ID where an official verification workflow supports it;
- certificate PDF/image as supporting evidence only.

The uploaded document is stored in private object storage and is never directly exposed to recruiters or public candidate profiles.

### 3. Verification workflow

Credential status lifecycle:

- `draft` — candidate has started entry;
- `submitted` — evidence supplied;
- `verification_pending` — awaiting official/manual verification;
- `verified` — official evidence matched;
- `verification_failed` — evidence did not match;
- `expired` — credential validity ended;
- `revoked` — issuer evidence indicates credential is no longer valid;
- `needs_reverification` — prior verification is stale or credential metadata changed.

Verification records must include:

- credential type
- normalized credential name
- credential ID fingerprint when available
- issuing organization
- issue date
- expiration date when provided
- official verification URL
- verification method
- verified-at timestamp
- verifier identity (`system`, provider integration, or internal reviewer)
- evidence hash
- result / reason code

### 4. Candidate controls visibility

Visibility must be an explicit independent setting:

- `private` — visible only to candidate and authorized administrators;
- `verified_recruiters` — searchable only by approved recruiter accounts;
- `public` — public shareable candidate page.

Default: `private`.

Before enabling recruiter/public visibility, candidate must affirm:

- which profile fields will be visible;
- which verified credentials will be displayed;
- whether recruiters may send contact requests;
- whether their resume can be shared after they accept a contact request.

Candidate can disable discoverability immediately at any time.

## Verification sources

Snowflake's public certification site currently exposes a `Verify a SnowPro Certification` path. Verification adapters should be provider-based so implementation can evolve without changing the candidate data model.

Initial provider strategy:

### `snowflake_official_directory`

Preferred when the candidate supplies a valid official Snowflake verification result or verification URL.

Do not depend on undocumented scraping as a long-term production contract. If Snowflake exposes a documented API/integration, use it. Otherwise support controlled reviewer confirmation from official issuer evidence.

### `official_digital_badge`

Accept a candidate-supplied public digital credential URL where the issuer can be confirmed as Snowflake and the badge metadata can be validated through a permitted integration or controlled review.

### `manual_official_evidence`

A reviewer verifies official issuer evidence and records a reason code and source URL. A PDF/screenshot can assist the review but cannot be the sole basis for verified status.

## Certification catalog

The talent network should not hard-code only COF-C03. Credentials are catalog data.

Minimum fields:

- credential code
- credential family (`core`, `advanced`, `specialty`, etc.)
- public display name
- issuer
- active / retired state
- verification-provider configuration
- validity / expiration rules when known

The catalog can support current and future SnowPro credentials without schema changes.

## Recruiter experience

Recruiter accounts are separate from candidate accounts and require approval before candidate discovery.

Recruiter onboarding:

1. create recruiter account;
2. verify email;
3. provide company name and company website;
4. verify company email/domain where possible;
5. accept recruiter terms and acceptable-use policy;
6. pass manual/automated marketplace review;
7. receive `approved` recruiter state.

Recruiter states:

- `pending`
- `approved`
- `suspended`
- `revoked`

### Recruiter search filters

Only candidate-authorized fields are searchable.

Recommended filters:

- verified certification(s)
- certification family
- number of active verified certifications
- certification expiration window
- Snowflake role
- Snowflake experience range
- skills / technologies
- location
- remote availability
- employment type
- availability
- candidate-updated recency

Do not expose candidate preparation scores, practice answers, mock scores, mistakes, confidence, payment history, account security state, or private learning telemetry to recruiters.

### Search result card

Example:

```text
A. Candidate
Senior Snowflake Data Engineer · New York / Remote

VERIFIED CREDENTIALS
✓ SnowPro Core
✓ SnowPro Advanced: Data Engineer

Snowflake experience: 6 years
Skills: Snowpark · Streams/Tasks · dbt · AWS · Terraform
Availability: Open to opportunities

[View profile] [Request introduction]
```

Do not use the Snowflake logo as our verification mark. Use an original marketplace verification icon and copy such as `Credential verified from issuer evidence`.

## Recruiter-to-candidate contact

Recruiters should not receive candidate email/phone numbers from search results.

Contact flow:

1. recruiter clicks `Request introduction`;
2. recruiter supplies role title, company, employment type, location, compensation/rate range where legally appropriate, and message;
3. candidate receives an in-product/email notification;
4. candidate accepts or declines;
5. only after acceptance can configured contact information or resume be released.

This protects candidate privacy and prevents the marketplace from becoming a bulk lead database.

## Talent quality model

Search relevance may use objective, candidate-authorized career fields, for example:

- direct certification match;
- current verified credential count;
- certification recency;
- candidate-declared role/skill match;
- profile recency;
- availability match.

Do not automatically use preparation performance or infer employability from private study behavior.

If the platform later adds independently assessed hands-on labs, those must be displayed under a separate product-owned label such as `Platform Skill Validation`; they must never be represented as Snowflake-issued certification.

## Database model

### `talent_candidate_profiles`

- `candidate_id` PK/FK
- `public_slug` unique nullable
- `headline`
- `current_role`
- `snowflake_years_experience`
- `primary_role`
- `country_code`
- `region`
- `metro`
- `remote_preference`
- `employment_preferences_json`
- `availability_status`
- `available_from`
- `work_authorization_text`
- `linkedin_url`
- `github_url`
- `portfolio_url`
- `visibility` (`private`, `verified_recruiters`, `public`)
- `contact_requests_enabled`
- `profile_updated_at`
- `created_at`
- `updated_at`

### `talent_candidate_skills`

- `id`
- `candidate_id`
- `skill_key`
- `display_name`
- `years_experience` nullable
- `candidate_asserted` boolean
- `created_at`

### `credential_catalog`

- `id`
- `credential_key` unique
- `issuer`
- `credential_code`
- `display_name`
- `credential_family`
- `active`
- `verification_config_json`
- `created_at`
- `updated_at`

### `candidate_credentials`

- `id`
- `candidate_id`
- `credential_catalog_id`
- `status`
- `credential_id_fingerprint`
- `issue_date`
- `expiration_date`
- `official_verification_url`
- `public_badge_url`
- `evidence_object_key` nullable
- `evidence_sha256` nullable
- `verified_at` nullable
- `last_reverified_at` nullable
- `created_at`
- `updated_at`

Unique constraints should prevent one issuer credential from being claimed by multiple active candidate identities unless explicitly resolved by an administrator.

### `credential_verification_events`

Immutable audit log:

- `id`
- `candidate_credential_id`
- `status_from`
- `status_to`
- `verification_method`
- `provider`
- `source_url`
- `reason_code`
- `reviewer_user_id` nullable
- `provider_response_hash` nullable
- `created_at`

Never store provider secrets/raw access tokens here.

### `talent_visibility_consents`

Immutable consent history:

- `id`
- `candidate_id`
- `visibility`
- `terms_version`
- `fields_json`
- `consented_at`
- `revoked_at` nullable

### `recruiter_accounts`

- `id`
- `email`
- `email_verified_at`
- `company_name`
- `company_domain`
- `company_website`
- `status`
- `approved_at`
- `approved_by`
- `terms_version`
- `created_at`
- `updated_at`

### `recruiter_contact_requests`

- `id`
- `recruiter_id`
- `candidate_id`
- `role_title`
- `company_name`
- `employment_type`
- `location_text`
- `compensation_text` nullable
- `message`
- `status` (`pending`, `accepted`, `declined`, `withdrawn`, `expired`)
- `created_at`
- `responded_at` nullable

### `recruiter_search_audit`

Low-sensitivity abuse/audit record:

- recruiter
- timestamp
- normalized filter categories
- result count
- request ID

Do not persist sensitive raw search text unnecessarily.

## API contract

Candidate APIs:

```text
GET    /api/talent/me
PUT    /api/talent/me
PUT    /api/talent/me/visibility
GET    /api/talent/me/credentials
POST   /api/talent/me/credentials
GET    /api/talent/me/credentials/{credential_id}
POST   /api/talent/me/credentials/{credential_id}/submit
DELETE /api/talent/me/credentials/{credential_id}
GET    /api/talent/me/contact-requests
POST   /api/talent/me/contact-requests/{request_id}/accept
POST   /api/talent/me/contact-requests/{request_id}/decline
```

Credential upload uses a separate signed private upload flow rather than accepting arbitrary public object URLs.

Recruiter APIs:

```text
POST   /api/recruiter/register
GET    /api/recruiter/me
GET    /api/recruiter/talent/search
GET    /api/recruiter/talent/{public_candidate_id}
POST   /api/recruiter/talent/{public_candidate_id}/contact
GET    /api/recruiter/contact-requests
```

Admin APIs:

```text
GET    /api/admin/credential-verification/queue
POST   /api/admin/credential-verification/{id}/verify
POST   /api/admin/credential-verification/{id}/reject
GET    /api/admin/recruiters/pending
POST   /api/admin/recruiters/{id}/approve
POST   /api/admin/recruiters/{id}/suspend
```

All administrator actions require existing admin authorization infrastructure or a dedicated protected admin boundary; never reuse a public candidate cookie as administrator authorization.

## Frontend routes

Candidate:

```text
#/account/credentials
#/talent/profile
#/talent/privacy
#/talent/inbox
```

Recruiter:

```text
#/recruiter
#/recruiter/register
#/recruiter/search
#/recruiter/candidate/:id
#/recruiter/inbox
```

Public, only for candidates who explicitly enable it:

```text
#/talent/:public_slug
```

## Candidate profile UI

Account page gains a new card:

```text
VERIFIED CREDENTIALS

SnowPro Core                          ✓ Verified
Issued: Mar 2026 · Expires: Mar 2028
Issuer evidence checked: Aug 24, 2026

[View verification] [Manage visibility]

+ Add certification
```

Verification badge states must be visually distinct:

- Verified
- Verification pending
- Expired
- Unable to verify

Never show an unverified upload with the same visual treatment as a verified credential.

## Recruiter talent library UI

Top-level recruiter screen:

```text
Verified Talent
Find Snowflake professionals by verified credentials and experience.

[Certification ▾] [Role ▾] [Experience ▾] [Location ▾]
[Remote ▾] [Availability ▾]                         Search

127 candidates
```

Candidate cards emphasize verified facts rather than scores or artificial ranking numbers.

Useful recruiter collections:

- Multiple active certifications
- Advanced Data Engineering
- Advanced Architecture
- Available now
- Remote consultants
- Recently verified

## Credential document security

Certificate documents are sensitive supporting documents even if the certification itself is public.

Requirements:

- private object storage only;
- encryption at rest and in transit;
- generated opaque object keys;
- content-type allowlist;
- file-size limit;
- malware scanning before reviewer access;
- no public bucket/object ACL;
- short-lived signed read URLs for authorized review only;
- access logging;
- evidence hash for duplicate/fraud detection;
- delete the original upload after verification according to retention policy unless a documented business reason requires longer retention.

Recommended default: retain the normalized verification record; delete raw uploaded evidence 30 days after a final verification decision unless dispute/legal retention applies.

## Privacy / candidate rights

Marketplace participation must be optional and separate from certification-prep account terms.

Candidate controls:

- opt in / opt out;
- preview exactly what recruiters see;
- hide individual certifications;
- disable recruiter messages;
- revoke public profile URL;
- export talent-profile data;
- delete talent profile independently of study history where technically possible;
- request correction of a verification result.

A candidate who turns visibility off must disappear from recruiter search immediately, not after a batch refresh.

## Recruiter abuse controls

- verified recruiter accounts only;
- rate limits on search/profile views/contact requests;
- no bulk export of the candidate directory;
- no candidate email scraping;
- no public sequential candidate IDs;
- audit recruiter access;
- report/block recruiter capability;
- recruiter suspension control;
- candidate contact-frequency limits;
- terms prohibit credential resale, list enrichment, discriminatory use, and unauthorized redistribution.

## Trademark / independence controls

Use Snowflake and SnowPro only descriptively to identify the third-party certification ecosystem.

Required marketplace copy:

> Independent talent marketplace. Not affiliated with or endorsed by Snowflake Inc. Snowflake and SnowPro are trademarks of Snowflake Inc. Credential verification reflects evidence available from the credential issuer and does not constitute employment endorsement by Snowflake or this platform.

Do not:

- call the marketplace an official Snowflake talent network;
- use Snowflake logos as our product identity or verification seal;
- suggest that passing our prep course guarantees certification or employment;
- claim that this platform issues SnowPro certifications.

## Verification reliability model

Expose verification provenance without exposing internal reviewer details:

```json
{
  "status": "verified",
  "issuer": "Snowflake Inc.",
  "verified_from": "official issuer evidence",
  "verified_at": "2026-08-24T20:00:00Z",
  "expiration_date": "2028-03-15"
}
```

Do not label a candidate `Snowflake Verified`. Prefer `Credential verified` or `Verified SnowPro credential` because the platform, not Snowflake, is presenting the profile.

## Reverification

Run scheduled reverification for discoverable credentials when issuer data permits.

Triggers:

- expiration date approaching;
- verification older than configured threshold;
- candidate changes credential metadata;
- candidate requests reverification;
- issuer/provider signals invalidity;
- internal fraud review.

If a credential expires, the candidate profile remains intact but the credential must stop counting as an active verified credential.

## Fraud controls

Flag for review:

- same credential fingerprint claimed by multiple candidates;
- candidate name materially mismatches issuer evidence;
- credential URL points to non-approved domain;
- altered document metadata;
- evidence hash reused across identities;
- impossible issue/expiration dates;
- revoked/expired issuer status;
- repeated failed verification attempts.

Automated fraud rules can block publication pending review but should not permanently accuse a candidate of fraud without human review.

## Separation from learning telemetry

The candidate's study behavior is private educational data.

The following must not be exposed to recruiters by default:

- question accuracy;
- mock-exam scores;
- readiness score;
- mistake notebook;
- confidence answers;
- study frequency;
- membership/payment tier;
- failed practice attempts.

This separation should be enforced at the API/data-query layer, not merely hidden in the UI.

## Monetization

Candidate side:

- free verified credential profile;
- free recruiter discoverability opt-in;
- no pay-to-rank candidate search results.

Recruiter side can become a B2B product:

- free limited recruiter account;
- paid professional search/filter tier;
- team recruiter seats;
- saved searches;
- candidate-introduction quota;
- talent-pipeline folders;
- company ATS integration later.

Do not sell raw candidate lists.

## Success metrics

Candidate funnel:

- certified candidates adding evidence
- verification success rate
- time to verification
- percentage opting into recruiter discovery
- active profiles with at least one verified credential
- profile completeness

Recruiter funnel:

- approved recruiters
- searches per active recruiter
- candidate profile views
- introduction requests
- candidate acceptance rate
- interview-intent / hiring-intent outcomes where voluntarily reported

Trust metrics:

- verification dispute rate
- duplicate credential flags
- recruiter abuse reports
- opt-out latency
- stale/expired credential rate

## Launch phases

### Phase 1 — Verified candidate credential vault

- candidate profile
- add credential
- official evidence URL/badge URL
- private document upload
- manual verification queue
- verified/pending/expired states
- private-by-default visibility

### Phase 2 — Recruiter talent library

- recruiter onboarding/approval
- recruiter search
- verified credential filters
- candidate-controlled discoverability
- introduction requests
- recruiter audit/rate limits

### Phase 3 — Verification automation

- supported issuer/provider integrations
- scheduled reverification
- expiry notifications
- duplicate/fraud rules

### Phase 4 — Talent intelligence

- saved searches
- recruiter teams
- candidate collections
- optional independently validated hands-on skill evidence
- ATS integrations

## Definition of done for the first production release

A release is not complete until all of the following are demonstrated end to end:

1. authenticated candidate creates a talent profile;
2. candidate submits certification evidence;
3. unverified upload cannot appear as verified;
4. authorized reviewer verifies official evidence;
5. credential receives immutable verification event;
6. candidate remains absent from recruiter search while visibility is private;
7. candidate explicitly enables verified-recruiter discovery;
8. approved recruiter can find candidate through the verified certification filter;
9. unapproved recruiter cannot access the talent library;
10. recruiter cannot see candidate email/phone before candidate acceptance;
11. contact request reaches candidate;
12. candidate can accept/decline;
13. candidate can instantly turn discovery off;
14. expired credential no longer counts as active verified;
15. raw credential documents are never publicly addressable;
16. account/talent export and deletion paths include this feature's data;
17. audit logs cover verification, recruiter access, and contact events;
18. public pages include non-affiliation/trademark disclosure;
19. automated tests cover authorization and consent boundaries;
20. PostgreSQL production smoke and browser tests pass.
