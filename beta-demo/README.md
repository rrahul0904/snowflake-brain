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

## Feedback persistence
For the short public feedback beta, the Vercel serverless feedback endpoint emits structured `BETA_FEEDBACK_V3` events to runtime logs and the browser stores a local fallback if submission fails. Before a broader commercial launch, switch the beta to the application's existing persistent `/api/feedback` path backed by managed PostgreSQL.

## Design provenance
The attached Claude Certification Guide recording was used only as a reference for high-level interaction patterns such as a clear hero, study-path choice, FAQ, and content discovery. Copy, palette, typography, information architecture, cards, spacing, navigation, globe treatment, and learning flows are original to this Snowflake product.
