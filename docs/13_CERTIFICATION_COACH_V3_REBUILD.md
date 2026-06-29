# Snowflake Brain - v3 Certification Coach Rebuild

Last updated: 2026-06-29

## Why v3 exists

The earlier builds behaved like a local content browser. That is not the product goal.

The real goal is:

> User provides video lessons and practice papers; Snowflake Brain becomes a certification coach that helps the user pass.

## Product reframing

Old model:

- Dashboard
- Lessons
- Search
- Flashcards
- Labs
- Analytics

New model:

- Goal setup
- Today
- Learn
- Practice
- Review
- Readiness

## Core behavior

### 1. Goal setup first

If no active goal exists, Today should not show an empty dashboard. It should show onboarding:

- choose certification
- target exam date
- study hours per week
- daily question target
- create plan
- then start diagnostic

### 2. Diagnostic first

The first meaningful action after goal setup is a 30-question diagnostic. The app should not pretend to know readiness before the user answers questions.

### 3. Today is the coach mission

Today should answer:

- What exam am I preparing for?
- What is the next action?
- What is blocking readiness?
- What should I repair?
- What content does the system have for this certification?

### 4. Learn replaces raw Lessons

Learn uses the existing lesson player, but the framing is different:

- lessons are part of the exam loop
- complete lesson
- then practice questions from the course/topic
- content quality must remain visible

### 5. Practice becomes the center

Practice now presents certification-prep modes:

- Diagnostic test
- Weak-topic drill
- Readiness exam
- Downloaded mock/source tests

### 6. Review becomes mistake repair

Review should not be analytics. It should be the repair queue for weak topics, missed/repeated mistakes, flashcards, and lesson gaps.

### 7. Readiness is strict

Readiness should not be motivational. It should say whether the user is ready to book the exam and why not.

## Files changed

- `frontend/router.js`
- `frontend/app.js`
- `frontend/components/nav.js`
- `frontend/components/topbar.js`
- `frontend/views/dashboard.js`
- `frontend/views/video.js`
- `frontend/views/quiz.js`
- `frontend/views/analytics.js`
- `frontend/views/readiness.js`
- `frontend/styles.css`

## Verification

Run:

```bash
python3 -m compileall app
node --check frontend/router.js
node --check frontend/app.js
node --check frontend/components/nav.js
node --check frontend/components/topbar.js
node --check frontend/views/dashboard.js
node --check frontend/views/video.js
node --check frontend/views/quiz.js
node --check frontend/views/analytics.js
node --check frontend/views/readiness.js
```

## Manual route checks

Open:

```text
#/today
#/learn
#/practice
#/review
#/readiness
#/lessons
#/video
#/quiz
#/analytics
```

Expected:

- no active goal: Today shows certification setup
- active goal: Today shows mission, diagnostic/next task, readiness blockers
- Learn shows exam-loop lesson player
- Practice shows diagnostic, weak drill, readiness exam, and source tests
- Review shows repair actions
- Readiness explains blockers before exam booking
