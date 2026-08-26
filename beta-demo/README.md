# Fresh Snowflake Certification Demo v1

This directory is a clean rebuild of the public demo experience. It intentionally does **not** restore the deleted legacy beta implementation.

## Implemented slice

- Application shell with top navigation + left study navigation
- Responsive mobile drawer
- Light/dark theme
- Home hero centered on SnowPro readiness, exam pacing, and next learning actions — no globe or decorative world visualization
- Home readiness dashboard
- COF-C03 domain weights and 19-objective study hierarchy
- Domain/task learning pages
- Practice hub with Quick, Adaptive, Advanced, and Redo Mistakes modes
- Interactive sample practice session
- Automatic mistake collection and mastery state
- Readiness dashboard with target exam date
- Quick/full mock exam entry experience
- Interactive timed mock preview with question map, previous/next navigation, flags, countdown timer, submit confirmation, scoring, domain breakdown, and remediation links
- Cheat sheet and decision-tree references
- Community insight filtering
- Resource hub
- Account/demo-state page
- Local persistence via `localStorage`

## Demo vs production

The static demo uses a small independently authored sample set to demonstrate interactions. Production formats remain 30 questions / 45 minutes for the quick mock and 100 questions / 120 minutes for the full mock, with the private production question bank owned by the full application.

## Content/IP boundary

The demo captures product and interaction patterns only. It does not copy competitor branding, proprietary questions, or article text. Sample Snowflake questions in this demo are independently authored for prototyping.

## Visual boundary

The public demo intentionally avoids decorative globe/world-map hero treatments. The hero should communicate certification value through readiness, blueprint coverage, target-date pacing, mistakes, practice accuracy, and next-best actions.

## Run locally

```bash
python3 -m http.server 8088 --directory beta-demo
```

Then open `http://localhost:8088/#home`.
