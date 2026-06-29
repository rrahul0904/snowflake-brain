# Snowflake Brain Rebuild - Design Document

## Product Vision

Snowflake Brain should be a private certification training workspace built from the user's downloaded paid course archive. It should help a student prepare for six Snowflake certifications in six months by turning videos, transcripts, practice tests, and explanations into a structured study system.

The app should not feel like a file browser or a random quiz pool. It should feel like a focused certification academy.

## Primary User

A student who:

- Owns multiple Snowflake courses and practice exams.
- Wants to pass several Snowflake certifications.
- Needs a daily plan, not just raw content.
- Wants to learn from videos and then test recall.
- Wants explanations grounded in their own course material.

## Core User Goals

1. Pick the certification I am studying.
2. See only relevant courses and tests.
3. Follow lessons in the correct order.
4. Practice with full downloaded tests.
5. Know immediately what I got wrong.
6. Ask an assistant based on my own course archive.
7. Track readiness until I am exam-ready.

## Information Architecture

### Top-Level Areas

- Dashboard
- Study Plan
- Lessons
- Practice Tests
- Review
- Assistant
- Labs
- Analytics

### Main Context

Every major page should know the current context:

- Selected certification track
- Selected course
- Selected practice test or lesson

Global search can cross the whole archive, but normal study flows should not.

## Certification Tracks

Initial tracks:

- SnowPro Core
- SnowPro Associate Platform
- SnowPro Advanced Architect
- SnowPro Advanced Data Engineer
- SnowPro Snowpark
- Snowflake Cortex and GenAI
- Snowflake Cost Optimization
- Apache Iceberg
- General Snowflake

Track mapping is inferred from course title and folder name. The mapping must be editable later.

## Page Design

### Dashboard

Purpose:

Show the student's current mission.

Main sections:

- Current certification goal
- Today plan
- Readiness score
- Weak topics
- Continue lesson
- Continue practice test
- Assistant prompt

The dashboard should answer: What should I do today?

### Lessons Page

Purpose:

Watch and study course videos in order.

Layout:

- Left: track selector, course selector, sections, lesson playlist
- Center: video, lesson title, metadata
- Right: assistant, related questions, notes

Rules:

- No mixed lesson list by default.
- Selecting a course shows only that course.
- Lessons are grouped by source section.
- Transcript text must be English.
- If no valid English transcript exists, show generated English study notes.

### Practice Page

Purpose:

Take full practice tests or focused drills.

Layout:

- Left: track, course, practice test catalog
- Center: question runner
- Right: score, question map, assistant

Modes:

- Practice mode: Submit Answer shows correct, incorrect, explanation, assistant sources.
- Exam mode: Save answers, then Submit Test grades everything.

Rules:

- Practice Test 1 and Practice Test 2 must remain separate.
- A test should load all source questions unless the student chooses a custom drill.
- Mixed random drill is secondary, not default.

### Assistant

Purpose:

Answer questions using local indexed material.

Inputs:

- Free-form student question
- Current lesson
- Current quiz question
- Selected answer and correct answer after submission

Outputs:

- Short explanation
- Key facts
- Exam tip
- Source list

First version should use SQLite full-text search and source-grounded summarization. A later version can add embeddings or a local LLM.

### Study Plan

Purpose:

Guide six-month preparation.

Inputs:

- Certifications selected
- Exam dates
- Weekly availability

Outputs:

- Weekly plan
- Daily tasks
- Practice test schedule
- Review days
- Weak-topic repair queue

## UX Principles

- Course scope must be obvious.
- Submit actions must be explicit.
- Practice tests must be recognizable by name and count.
- The app should use compact professional layouts.
- Avoid giant cards for dense study workflows.
- Do not show instructional filler text inside the app unless it directly helps the task.
- The assistant should be visible where confusion happens: lesson and quiz pages.

## Non-Goals For First Rebuild

- Real model fine-tuning.
- Cloud-hosted multi-user accounts.
- Payment or subscription.
- Full local LLM runtime.
- Perfect automatic certification mapping.

## Risks

### Course Mapping Errors

Some downloaded course titles may map to the wrong track.

Mitigation:

- Use clear inferred mapping.
- Add admin override later.

### Transcript Quality

Some downloaded captions are non-English or auto-translated.

Mitigation:

- Reject non-English scripts and signal words.
- Generate English study notes as fallback.

### Large Question Banks

Full tests can have 100+ questions.

Mitigation:

- Paginate or virtualize question maps.
- Keep session state client-side for first version.

### RAG Quality

Search-only RAG may be less fluent than a full LLM.

Mitigation:

- Start with source-grounded answers.
- Add embeddings/local model later.

