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

export const getSkillMap = () => api("/api/skills/map");
export const getCertificationCatalog = () => api("/api/skills/catalog");
export const getContentCoverage = () => api("/api/skills/content-coverage");
export const getSkillSummary = (params = {}) => api(`/api/skills/summary?${new URLSearchParams(params)}`);
export const getTaskProgress = (params = {}) => api(`/api/skills/task-progress?${new URLSearchParams(params)}`);
export const setTaskProgress = (payload) => api("/api/skills/task-progress", { method: "POST", body: JSON.stringify(payload) });
export const getStudyLesson = (skillId, params = {}) => api(`/api/skills/${encodeURIComponent(skillId)}/lesson?${new URLSearchParams(params)}`);
export const getSkillResources = (skillId, params = {}) => api(`/api/skills/${encodeURIComponent(skillId)}/resources?${new URLSearchParams(params)}`);

export const getExperienceShell = (params = {}) => api(`/api/experience/shell?${new URLSearchParams(params)}`);
export const getExperienceCommandCenter = (params = {}) => api(`/api/experience/command-center?${new URLSearchParams(params)}`);
export const getIntelligenceReadiness = (params = {}) => api(`/api/intelligence/readiness?${new URLSearchParams(params)}`);
export const getSkillMastery = (params = {}) => api(`/api/intelligence/skill-mastery?${new URLSearchParams(params)}`);
export const getDiagnosticPlan = (params = {}) => api(`/api/intelligence/diagnostic?${new URLSearchParams(params)}`);
export const getEvidenceAudit = (params = {}) => api(`/api/intelligence/evidence-audit?${new URLSearchParams(params)}`);
export const reindexSkillMap = (trackId = "") => api(`/api/intelligence/reindex-skill-map?${new URLSearchParams({ track_id: trackId })}`, { method: "POST", body: "{}" });

export const getPracticeTests = (params = {}) => api(`/api/practice-tests?${new URLSearchParams(params)}`);
export const getPracticeTestQuestions = (id, params = {}) => api(`/api/practice-tests/${encodeURIComponent(id)}/questions?${new URLSearchParams(params)}`);
export const getQuestion = (id) => api(`/api/questions/${encodeURIComponent(id)}`);
export const startQuiz = (payload) => api("/api/certification-quiz/start", { method: "POST", body: JSON.stringify(payload) });
export const gradeQuiz = (payload) => api("/api/quiz/grade", { method: "POST", body: JSON.stringify(payload) });
export const recordAttempt = (id, payload) => api(`/api/questions/${encodeURIComponent(id)}/attempt`, { method: "POST", body: JSON.stringify(payload) });
export const recordMockSession = (payload) => api("/api/certification-mock/record", { method: "POST", body: JSON.stringify(payload) });
export const toggleBookmark = (id) => api(`/api/questions/${encodeURIComponent(id)}/bookmark`, { method: "POST", body: "{}" });
export const getBookmark = (id) => api(`/api/questions/${encodeURIComponent(id)}/bookmark`);
export const addQuestionNote = (id, body) => api(`/api/questions/${encodeURIComponent(id)}/notes`, { method: "POST", body: JSON.stringify({ body }) });

export const getLabs = (params = {}) => api(`/api/labs?${new URLSearchParams(params)}`);
export const getLab = (id) => api(`/api/labs/${encodeURIComponent(id)}`);
export const getLabsConfig = () => api("/api/labs/config");
export const submitLab = (id, sql) => api(`/api/labs/${encodeURIComponent(id)}/submit`, { method: "POST", body: JSON.stringify({ sql }) });

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
