# Fresh Snowflake Certification Demo v1

This directory is a clean rebuild of the public demo experience. It intentionally does **not** restore the deleted legacy beta implementation.

## First implemented slice

- Application shell with top navigation + left study navigation
- Responsive mobile drawer
- Light/dark theme
- Home readiness dashboard
- COF-C03 domain weights and 19-objective study hierarchy
- Domain/task learning pages
- Practice hub with Quick, Adaptive, Advanced, and Redo Mistakes modes
- Interactive sample practice session
- Automatic mistake collection and mastery state
- Readiness dashboard with target exam date
- Quick/full mock exam entry shells
- Cheat sheet and decision-tree references
- Community insight filtering
- Resource hub
- Account/demo-state page
- Local persistence via `localStorage`

## Content/IP boundary

The demo captures product and interaction patterns only. It does not copy competitor branding, proprietary questions, or article text. Sample Snowflake questions in this demo are independently authored for prototyping.

## Run locally

```bash
python3 -m http.server 8088 --directory beta-demo
```

Then open `http://localhost:8088/#home`.
