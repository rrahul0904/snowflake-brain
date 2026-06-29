# Snowflake Brain Rebuild - High Level Tasks

## Objective

Rebuild Snowflake Brain into a serious certification training system for a student preparing for multiple Snowflake certifications over six months. The app must respect the structure of the downloaded paid course archive: certification track, course, section, lesson, practice test, and question order.

## Current Problem

The current prototype indexes useful raw content, but the learning experience is too mixed together:

- Lessons from different courses appear like one blended library.
- Practice tests are treated like a random question pool.
- The UI does not guide a student through a certification path.
- The assistant is not integrated into lessons and quiz review.
- Transcript quality is inconsistent and non-English captions have appeared.
- There is no six-month study plan or daily workflow.

## Target Experience

The app should work like a private Snowflake certification academy:

1. Student chooses a certification track.
2. Student chooses a course inside that track.
3. Lessons appear only for that selected course, grouped by section.
4. Practice tests appear as separate full tests, such as Practice Test 1 and Practice Test 2.
5. Practice mode gives instant feedback after Submit Answer.
6. Exam mode saves answers and grades only after Submit Test.
7. The local assistant answers using indexed course content and cites sources.
8. The dashboard tells the student what to do today.

## Major Workstreams

### 1. Content Hierarchy

Create durable hierarchy:

- Certification track
- Course
- Course section
- Lesson
- Practice test
- Question
- Transcript chunk
- Study plan item

### 2. Indexing

Rebuild ingestion so it preserves source archive structure:

- Detect certification track from course title and folder.
- Preserve original course folder.
- Preserve section order.
- Preserve lesson order.
- Preserve practice test order.
- Preserve question order.
- Filter non-English transcripts.
- Generate English study notes when no valid English transcript exists.

### 3. Backend APIs

Expose scoped APIs:

- Tracks
- Courses by track
- Sections by course
- Lessons by course
- Practice tests by course
- Questions by practice test
- Attempts and grading
- Local assistant search
- Daily study plan
- Readiness and weak-topic analytics

### 4. Lessons Experience

Replace the mixed lesson page with a course-scoped learning page:

- Track selector
- Course selector
- Section list
- Ordered lesson playlist
- Video player
- English transcript or generated study notes
- Related practice questions
- Local assistant for selected lesson

### 5. Practice Experience

Replace the generic quiz page with a real test runner:

- Track selector
- Course selector
- Practice test catalog
- Full test launch
- Mixed drill as optional secondary path
- Submit Answer in practice mode
- Submit Test in exam mode
- Score report
- Missed-question review
- Assistant beside current question

### 6. Local Assistant

Build a local RAG-style assistant based on indexed course material:

- Retrieve matching lessons, transcript chunks, documents, and question explanations.
- Generate a concise answer from retrieved snippets.
- Show source titles and links.
- Work without requiring an external OpenAI or Anthropic API key.

### 7. Six-Month Study Planner

Add a student plan for six Snowflake certifications:

- Track goals
- Target exam dates
- Weekly milestones
- Daily tasks
- Readiness score
- Weak-topic repair queue
- Practice test progress

### 8. UI Redesign

Move from a generic dashboard to a certification prep console:

- Clear certification track context.
- Course-scoped content.
- Compact test navigation.
- Clear submit and review actions.
- Integrated assistant panel.
- Dense, professional, study-focused layout.

## Acceptance Criteria

The rebuild is acceptable when:

- Choosing SnowPro Core shows only SnowPro Core courses, lessons, and tests.
- Choosing Snowflake Cost Optimization shows only that course's lessons and tests.
- Practice Test 1 loads as a complete test with all source questions.
- Practice mode has an obvious Submit Answer button and immediate result.
- Exam mode has an obvious Submit Test button and final score report.
- Lesson transcripts are English only, or replaced with English study notes.
- The assistant answers from indexed local material and shows sources.
- The dashboard tells the student what to study today.

