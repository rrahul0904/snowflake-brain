# Learning Intelligence

The learner loop uses one candidate evidence authority: diagnostic and practice attempts, task coverage, mock results, confidence, repeated mistakes, review history and exam runway. `app/adaptive_readiness.py` derives readiness state, evidence quality, blockers, weak tasks, due review and a recommended next action from that evidence. `app/learning_intelligence.py` owns review and mistake workflows. The browser does not maintain an alternate progress or readiness authority.

Readiness describes evidence and study risk; it is not a guaranteed pass probability. Sparse, stale, guessed or narrow evidence lowers confidence and must produce explicit blockers. Recommendations resolve to a mapped lesson, exam trap, quick reference, eligible practice, Due Today item or build task. When an LLM is unavailable, deterministic mapped content and study actions remain usable. Socratic coaching withholds the correct answer until grading policy permits it.

The canonical interaction sequence is exam guide, diagnostic, weak task, lesson, concept check, targeted practice, build exercise, mistake repair, due review, timed mock, replay, refreshed readiness, exact next action and official credential verification.
