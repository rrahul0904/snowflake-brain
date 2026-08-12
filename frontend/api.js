export async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    let message = response.statusText;
    try {
      const body = await response.json();
      message = body.detail || message;
    } catch {
      message = await response.text();
    }
    throw new Error(message || "Request failed");
  }
  return response.json();
}

export const getSummary = () => api("/api/summary");
export const getCourses = () => api("/api/courses");
export const getTracks = () => api("/api/tracks");
export const getTrackCourses = (id) => api(`/api/tracks/${encodeURIComponent(id)}/courses`);
export const getCourse = (id) => api(`/api/courses/${encodeURIComponent(id)}`);
export const getCourseSections = (id) => api(`/api/courses/${encodeURIComponent(id)}/sections`);
export const getCoursePracticeTests = (id) => api(`/api/courses/${encodeURIComponent(id)}/practice-tests`);
export const getIndexStatus = () => api("/api/index/status");
export const rebuildIndex = () => api("/api/index/rebuild", { method: "POST", body: "{}" });
export const getProgressSummary = () => api("/api/progress/summary");
export const getTopicProgress = () => api("/api/progress/by-topic");
export const getHeatmap = () => api("/api/progress/heatmap");
export const getStudyGoals = (params = {}) => api(`/api/study/goals?${new URLSearchParams(params)}`);
export const createStudyGoal = (payload) => api("/api/study/goals", { method: "POST", body: JSON.stringify(payload) });
export const createStudyRoadmap = (payload) => api("/api/study/roadmap", { method: "POST", body: JSON.stringify(payload) });
export const updateStudyGoal = (id, payload) =>
  api(`/api/study/goals/${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify(payload) });
export const generateStudyPlan = (id, payload = {}) =>
  api(`/api/study/goals/${encodeURIComponent(id)}/generate-plan`, { method: "POST", body: JSON.stringify(payload) });
export const getStudyPlan = (id, params = {}) =>
  api(`/api/study/goals/${encodeURIComponent(id)}/plan?${new URLSearchParams(params)}`);
export const updateStudyPlanItem = (id, payload) =>
  api(`/api/study/plan-items/${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify(payload) });
export const getTodayPlan = (params = {}) => api(`/api/study/today?${new URLSearchParams(params)}`);
export const getStudyReadiness = (params = {}) => api(`/api/study/readiness?${new URLSearchParams(params)}`);
export const getContentAudit = () => api("/api/study/content-audit");
export const getQuestions = (params) => api(`/api/questions?${new URLSearchParams(params)}`);
export const getQuestion = (id) => api(`/api/questions/${encodeURIComponent(id)}`);
export const getPracticeTests = (params = {}) => api(`/api/practice-tests?${new URLSearchParams(params)}`);
export const getPracticeTestQuestions = (id, params = {}) => api(`/api/practice-tests/${encodeURIComponent(id)}/questions?${new URLSearchParams(params)}`);
export const startQuiz = (payload) => api("/api/quiz/start", { method: "POST", body: JSON.stringify(payload) });
export const gradeQuiz = (payload) => api("/api/quiz/grade", { method: "POST", body: JSON.stringify(payload) });
export const recordAttempt = (id, payload) =>
  api(`/api/questions/${encodeURIComponent(id)}/attempt`, { method: "POST", body: JSON.stringify(payload) });
export const toggleBookmark = (id) => api(`/api/questions/${encodeURIComponent(id)}/bookmark`, { method: "POST", body: "{}" });
export const getBookmark = (id) => api(`/api/questions/${encodeURIComponent(id)}/bookmark`);
export const addQuestionNote = (id, body) =>
  api(`/api/questions/${encodeURIComponent(id)}/notes`, { method: "POST", body: JSON.stringify({ body }) });
export const addFlashcard = (payload) => api("/api/flashcards", { method: "POST", body: JSON.stringify(payload) });
export const getDueFlashcards = () => api("/api/flashcards");
export const getAllFlashcards = () => api("/api/flashcards/all");
export const reviewFlashcard = (id, grade) =>
  api(`/api/flashcards/${id}/review`, { method: "POST", body: JSON.stringify({ grade }) });
export const deleteFlashcard = (id) => api(`/api/flashcards/${id}`, { method: "DELETE" });
export const generateFlashcards = (payload) =>
  api("/api/flashcards/generate", { method: "POST", body: JSON.stringify(payload) });
export const getLabs = (params = {}) => api(`/api/labs?${new URLSearchParams(params)}`);
export const getLab = (id) => api(`/api/labs/${encodeURIComponent(id)}`);
export const getLabsConfig = () => api("/api/labs/config");
export const submitLab = (id, sql) => api(`/api/labs/${encodeURIComponent(id)}/submit`, { method: "POST", body: JSON.stringify({ sql }) });

export const getExperienceCommandCenter = (params = {}) => api(`/api/experience/command-center?${new URLSearchParams(params)}`);
export const getExperienceShell = (params = {}) => api(`/api/experience/shell?${new URLSearchParams(params)}`);
export const createExamSession = (payload) => api("/api/exam-sessions", { method: "POST", body: JSON.stringify(payload) });
export const getExamSession = (sessionId) => api(`/api/exam-sessions/${encodeURIComponent(sessionId)}`);
export const saveExamSessionAnswer = (sessionId, payload) => api(`/api/exam-sessions/${encodeURIComponent(sessionId)}/answers`, { method: "POST", body: JSON.stringify(payload) });
export const finishExamSession = (sessionId) => api(`/api/exam-sessions/${encodeURIComponent(sessionId)}/finish`, { method: "POST", body: "{}" });

export const getSkillMap = () => api("/api/skills/map");
export const getSkillSummary = (params = {}) => api(`/api/skills/summary?${new URLSearchParams(params)}`);

export const getCertificationPortfolio = () => api("/api/intelligence/portfolio");
export const getCommandBrief = (params = {}) => api(`/api/intelligence/command-brief?${new URLSearchParams(params)}`);
export const getIntelligenceReadiness = (params = {}) => api(`/api/intelligence/readiness?${new URLSearchParams(params)}`);
export const getSkillMastery = (params = {}) => api(`/api/intelligence/skill-mastery?${new URLSearchParams(params)}`);
export const getMistakeQueue = (params = {}) => api(`/api/intelligence/mistake-queue?${new URLSearchParams(params)}`);
export const getDiagnosticPlan = (params = {}) => api(`/api/intelligence/diagnostic?${new URLSearchParams(params)}`);
export const getEvidenceAudit = (params = {}) => api(`/api/intelligence/evidence-audit?${new URLSearchParams(params)}`);
export const reindexSkillMap = (trackId = "") => api(`/api/intelligence/reindex-skill-map?${new URLSearchParams({ track_id: trackId })}`, { method: "POST", body: "{}" });

export const getSkillResources = (skillId, params = {}) => api(`/api/skills/${encodeURIComponent(skillId)}/resources?${new URLSearchParams(params)}`);
export const searchBrain = (q, limit = 20) => api(`/api/search?${new URLSearchParams({ q, limit })}`);
export const askBrain = (payload) => api("/api/brain/ask", { method: "POST", body: JSON.stringify(payload) });
export const getLessons = (params = {}) => api(`/api/lessons?${new URLSearchParams(params)}`);
export const getLesson = (id) => api(`/api/lessons/${encodeURIComponent(id)}`);
export const getTranscript = (id) => api(`/api/lessons/${encodeURIComponent(id)}/transcript`);
export const recordLessonProgress = (payload) =>
  api("/api/progress/lesson", { method: "POST", body: JSON.stringify(payload) });

export const getDataAiCurriculum = () => api("/api/data-ai/curriculum");
export const completeDataAiLesson = (id) =>
  api(`/api/data-ai/lessons/${encodeURIComponent(id)}/complete`, { method: "POST", body: "{}" });
export const submitDataAiCheck = (id, selectedIndex) =>
  api(`/api/data-ai/checks/${encodeURIComponent(id)}/submit`, {
    method: "POST",
    body: JSON.stringify({ selected_index: selectedIndex }),
  });
export const submitDataAiLab = (id, code) =>
  api(`/api/data-ai/labs/${encodeURIComponent(id)}/submit`, {
    method: "POST",
    body: JSON.stringify({ code }),
  });

export async function streamAi(question, onDelta, onDone) {
  const response = await fetch("/api/ai/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, context_limit: 10 }),
  });
  if (!response.ok || !response.body) throw new Error("AI request failed");
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split("\n\n");
    buffer = events.pop() || "";
    for (const event of events) {
      const line = event.split("\n").find((item) => item.startsWith("data:"));
      if (!line) continue;
      const payload = JSON.parse(line.replace(/^data:\s*/, ""));
      if (payload.delta) onDelta(payload.delta);
      if (payload.done) onDone(payload.sources || []);
    }
  }
}

export function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

export function formatNumber(value) {
  if (typeof value === "string") return value;
  return new Intl.NumberFormat().format(value || 0);
}
