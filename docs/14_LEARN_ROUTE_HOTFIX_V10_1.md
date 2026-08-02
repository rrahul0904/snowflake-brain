# v10.1 Learn Route Hotfix

This hotfix addresses a route mismatch where `#/learn` could show the Exam Studio view due to stale cached frontend assets or an incorrect local router copy.

Changes:
- Bumped frontend asset version to `20260630-refoundationv10_1`.
- Asserted `#/learn` loads `frontend/views/video.js` and `#/practice` loads `frontend/views/quiz.js`.
- Added per-view `VIEW_ID` exports and router mismatch detection.
- Expanded static and browser route smoke tests so `#/learn` must render the real course player text, not Exam Studio.

The Learn page remains the primary video lesson workspace.
