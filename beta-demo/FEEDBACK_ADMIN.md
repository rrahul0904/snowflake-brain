# Beta Feedback Administration

The public beta persists feedback into the managed PostgreSQL database through `POST /api/feedback`.

## Required Vercel environment variables

- `DATABASE_URL` — managed PostgreSQL connection string. Do not commit it.
- `FEEDBACK_ADMIN_TOKEN` — long random bearer token used only by the private dashboard/API read path.
- `FEEDBACK_IP_HASH_SECRET` — optional separate secret used to HMAC coarse client IP signals. If omitted the admin token is used. Raw IP addresses are not stored.

## Public submission

The beta feedback form submits rating, area, message, optional email, context, route, theme, viewport and client timestamp. The server adds submission timestamp and user-agent, and stores only an HMAC hash of an IP signal when a hashing secret is configured.

## Retention

Feedback is stored in `public.beta_feedback_submissions` with no TTL and no automatic deletion job. The public application exposes no update/delete endpoints. Database administrators retain the ability to remove a row when required for privacy, legal or support reasons.

## Private dashboard

Open `/feedback-admin.html` and enter `FEEDBACK_ADMIN_TOKEN` in the browser. The token is held only in page memory for the session and is sent as a bearer token to `GET /api/feedback`.

Dashboard capabilities:

- total responses
- average rating
- five-star count
- responses with email
- full-text search across message/email/context/route
- area filter
- rating filter
- theme filter
- route filter
- pagination
- CSV export

There is intentionally no delete/edit UI and no real-time notification system.

## Security

`feedback-admin.html` is not a security boundary by itself; the API bearer token is. Keep the admin token secret, rotate it if exposed, and never place it in the public HTML or repository.
