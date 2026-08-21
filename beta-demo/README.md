# Snowflake Certification Platform — Public Beta

Original public-beta experience for SnowPro Core COF-C03 preparation.

## Included
- Original Snowflake-native visual system using blue/cyan/violet instead of the Claude guide palette
- Responsive desktop, tablet, iPhone, and Android layouts
- Study Guide, Practice, Mock Exam, Adaptive, Progress, Insights, and Membership routes
- 20 original demo practice questions with explanations
- Light/dark mode
- Five membership packages
- In-product feedback collection
- Interactive dotted world globe based on the project's existing globe behavior
- Snowflake non-affiliation/trademark disclaimer
- Public Copyright & IP Notice at `/legal.html`

## Feedback persistence
Public-beta feedback is submitted to the Vercel serverless `/api/feedback` endpoint and persisted to the configured PostgreSQL/Neon database. The browser retains a local retry/fallback path if network submission fails. Admin access is protected separately as described in `FEEDBACK_ADMIN.md`.

## Content and IP integrity
The public beta is governed by `docs/CONTENT_IP_COPYRIGHT_POLICY.md`.

The policy prohibits live/recalled certification questions, exam dumps/braindumps, and unlicensed third-party commercial question-bank/course wording. Production learning material must have lawful provenance, independently authored expression, and editorial review. Snowflake/SnowPro references are descriptive only; the product must not imply Snowflake sponsorship or endorsement.

For U.S. copyright/trademark registration planning, see `docs/IP_REGISTRATION_RUNBOOK.md`.

## Design provenance
The attached Claude Certification Guide recording was used only as a reference for high-level interaction patterns such as a clear hero, study-path choice, FAQ, and content discovery. Copy, palette, typography, information architecture, cards, spacing, navigation, globe treatment, and learning flows are original to this Snowflake-focused product.
