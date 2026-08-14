# Monetization policy

## No advertising networks

Snowflake Certification Guide does not support display advertising.

The product must not add:

- banner ads
- interstitial ads
- pop-up or pop-under ads
- video ads
- native-ad network placements
- Google AdSense / Google Ads display SDKs
- DoubleClick or other ad-serving networks
- Prebid/header bidding
- Taboola/Outbrain-style recommendation ads
- Meta/Facebook ad pixels used for ad targeting
- third-party behavioral advertising SDKs
- paid placement that changes editorial ranking

CI scans the active frontend for common ad-network/SDK identifiers.

## Affiliate resources

The only supported third-party monetized links are editorial resource recommendations displayed inside the authenticated Resources page.

Amazon Associates links are disabled by default. Enable them only after a valid Associates account/tag is configured:

```bash
AFFILIATE_RESOURCES_ENABLED=true
AMAZON_ASSOCIATE_TAG=your-tag-20
```

The application builds Amazon product-detail links server-side. It does not embed an Amazon storefront, iframe, ad widget, tracking pixel, advertising script, customer review, star rating, or price feed.

The Resources page displays the required Amazon Associates disclosure and an additional plain-language commission disclosure next to the recommended books. Each monetized outbound link is also labelled `Paid link` and uses `rel="sponsored noopener noreferrer"`.

Affiliate status does not affect Free/Premium entitlement, question selection, readiness scores, recommendation ranking, or curriculum content.

## Editorial rule

A book/resource is included because it is useful to the candidate, not because a merchant paid for placement. If a resource is outdated, misleading, or no longer useful, it must be removed even if it earns commission.
