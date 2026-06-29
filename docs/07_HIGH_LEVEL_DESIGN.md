# Snowflake Brain - High Level Design

Last updated: 2026-06-29

## 1. Product Goal

Snowflake Brain is a private local certification-prep workspace built from a user's downloaded Snowflake training archive.

The product goal is not to be a generic quiz app or file browser. The product goal is to help a student prepare for multiple Snowflake certifications through a structured daily learning loop:

1. Pick a certification goal.
2. Follow today's assigned work.
3. Study lessons in course order.
4. Take full practice exams without merging unrelated tests.
5. Review mistakes.
6. Ask a local course-context tutor.
7. Track readiness by certification and topic.

## 2. Target User

Primary user:

- A student who owns multiple Snowflake courses and practice exams.
- Wants to complete 3 or more Snowflake certifications over a fixed period.
- Needs an organized study system, not raw folders.
- Wants local/private use of downloaded material.
- Wants clear feedback on weak areas and exam readiness.

Primary 100-day scenario:

- User selects 3 target certifications.
- User provides target end date or exam dates.
- App generates a daily study plan.
- User studies lessons, takes practice tests, and reviews weak areas.
- App updates readiness from real activity events.

## 3. Core Product Principles

### 3.1 Scope Before Polish

The app must first get the study workflow correct:

- Today
- Lessons
- Practice
- Review

Search, flashcards, labs, AI tutor, and analytics are useful, but they should support the core loop instead of becoming disconnected first-class pages too early.

### 3.2 Preserve Source Boundaries

The app must not casually merge source content.

Rules:

- A course shows only its own lessons.
- A practice test shows only its own questions.
- A certification track shows only its mapped courses and tests.
- Global mixed search/drill is allowed only when explicitly selected.

### 3.3 Make Content Trust Visible

The app must show what kind of content it is using.

Examples:

- Real transcript.
- Generated English study notes.
- Missing transcript.
- Empty practice test shell.
- Full mock exam.
- Section quiz.
- Assignment.
- Duplicate question group.
- Manually remapped course.

### 3.4 Local-First Assistant

The assistant must work in local mode by default.

External LLMs may be optional later, but the default product promise is:

- Local archive.
- Local search.
- Local source citations.
- No required external API key.

### 3.5 Real Events Drive Progress

The app should not trust a generic Done button as proof of learning.

Progress should come from real events:

- `lesson_completed`
- `quiz_question_answered`
- `practice_test_finished`
- `flashcard_reviewed`
- `lab_submitted`
- `weak_topic_repaired`

## 4. Product Information Architecture

The visible product should be reduced to four primary workflows.

### 4.1 Today

Purpose:

The daily command center.

It answers:

- What should I study today?
- Which certification am I working on?
- What tasks are overdue?
- What is my readiness?
- What weak topics need repair?

Primary components:

- Active certification goals.
- Today's tasks.
- Overdue tasks.
- Readiness score.
- Continue lesson.
- Continue practice test.
- Weak-topic repair queue.

### 4.2 Lessons

Purpose:

Course-scoped learning experience.

Primary components:

- Track selector.
- Course selector.
- Section outline.
- Ordered lesson playlist.
- Video player.
- Transcript / generated notes panel.
- Content quality badge.
- Related questions.
- Lesson-context assistant.
- Mark lesson complete.

Rules:

- No mixed lesson list by default.
- Selecting SnowPro Core must not show Cost Optimization lessons.
- Selecting Cost Optimization must not show SnowPro Core lessons.
- Generated notes must not be presented as real transcripts.

### 4.3 Practice

Purpose:

Serious exam-prep runner.

Primary components:

- Track selector.
- Course selector.
- Practice catalog.
- Full mock exams.
- Course practice tests.
- Topic drills.
- Missed questions.
- Bookmarked questions.
- Practice mode.
- Exam mode.
- Score report.
- Missed-question review.

Rules:

- Practice Test 1, 2, 3, etc. must remain separate.
- A source test with 98 questions must load 98 questions.
- Practice mode shows feedback after each submitted answer.
- Exam mode shows feedback only after final submit.

### 4.4 Review

Purpose:

Weakness repair and readiness tracking.

Primary components:

- Missed questions.
- Duplicate question warnings.
- Flashcards due.
- Topic readiness.
- Certification readiness.
- Practice test history.
- Content quality audit.

## 5. Secondary Workflows

These can exist as routes or panels, but should not dominate the product until the core loop is stable.

### Search

Use for global lookup across local archive.

### Flashcards

Use as a review tool generated from misses and manual saves.

### Labs

Use for SQL command practice, mapped to topics/certifications.

### AI Tutor

Use inside Lessons and Practice first. A standalone AI page can exist later.

### Analytics

Use as Review once it becomes actionable.

## 6. Main User Journeys

### Journey 1: Create 100-Day Roadmap

1. User opens Today.
2. User selects 3 certifications.
3. User selects target end date.
4. App generates sequential study windows.
5. App creates daily tasks from lessons, question drills, mock exams, labs, and review.

### Journey 2: Study A Lesson

1. User opens Lessons.
2. User selects track.
3. User selects course.
4. User selects section and lesson.
5. User watches video.
6. User reads transcript or generated notes.
7. User asks assistant a lesson question.
8. User marks lesson complete.
9. App records `lesson_completed`.
10. App updates study plan and readiness.

### Journey 3: Practice Mode

1. User opens Practice.
2. User selects track and course.
3. User selects a full test, quiz, or drill.
4. User starts Practice Mode.
5. User answers one question.
6. User clicks Submit Answer.
7. App shows correct/incorrect, explanation, source, and exam trap.
8. Misses can become flashcards.
9. App records `quiz_question_answered`.

### Journey 4: Exam Mode

1. User opens Practice.
2. User selects full mock exam.
3. User starts Exam Mode.
4. User answers all questions.
5. User submits test.
6. App grades the full session.
7. App shows score report and missed-question review.
8. App records `practice_test_finished`.
9. Readiness updates.

### Journey 5: Review Weak Topics

1. User opens Review.
2. App shows weak topics by accuracy and coverage.
3. User reviews missed questions.
4. User reviews due flashcards.
5. User retakes topic drill.
6. App records `weak_topic_repaired`.

## 7. UI Direction

The app should use one design system.

Recommended style:

- Compact professional dashboard.
- Dark/local-academy theme is acceptable if consistent.
- Dense but readable layouts.
- Panels only where they frame real tools.
- No decorative hero sections inside workflow pages.
- No separate visual identities per page.

## 8. Non-Goals For The Next Build Phase

Do not prioritize:

- More standalone pages.
- Cosmetic-only redesign.
- Real model fine-tuning.
- Multi-user accounts.
- Payments/subscriptions.
- Cloud deployment.
- Full offline LLM runtime.

## 9. Success Criteria

The product becomes credible when:

- The student can follow today's tasks without guessing.
- Lessons are course-scoped and ordered.
- Practice tests are separate and complete.
- Exam sessions persist.
- AI tutor cites local sources.
- Readiness is based on real activity.
- The app exposes content quality honestly.

