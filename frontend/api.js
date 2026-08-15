export async function api(path, options = {}) {
  const response = await fetch(path, {
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    let message = response.statusText;
    try {
      const body = await response.json();
      message = body.detail?.message || (Array.isArray(body.detail) ? body.detail.map((item) => item.msg).join(" ") : body.detail) || message;
    } catch {
      message = await response.text();
    }
    throw new Error(message || "Request failed");
  }
  return response.json();
}

export const getCandidateSession = () => api("/api/auth/me");
export const getAuthProviders = () => api("/api/auth/providers");
export const signupCandidate = (payload) => api("/api/auth/register", { method: "POST", body: JSON.stringify(payload) });
export const loginCandidate = (payload) => api("/api/auth/login", { method: "POST", body: JSON.stringify(payload) });
export const logoutCandidate = () => api("/api/auth/logout", { method: "POST", body: "{}" });
export const getPendingGoogleLink = () => api("/api/auth/google/pending-link");
export const linkGoogleCandidate = (password) => api("/api/auth/google/link", { method: "POST", body: JSON.stringify({ password }) });
export const getCandidateSessions = () => api("/api/auth/sessions");
export const revokeCandidateSession = (id) => api(`/api/auth/sessions/${encodeURIComponent(id)}`, { method: "DELETE", body: "{}" });
export const revokeAllCandidateSessions = () => api("/api/auth/sessions/revoke-all", { method: "POST", body: "{}" });
export const getBillingConfig = () => api("/api/billing/config");
export const createBillingCheckout = (planCode) => api("/api/billing/checkout", { method: "POST", body: JSON.stringify({ plan_code: planCode }) });
export const createBillingPortal = () => api("/api/billing/portal", { method: "POST", body: "{}" });

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
export const getMockConfig = (params = {}) => api(`/api/mock/config?${new URLSearchParams(params)}`);
export const startMockSession = (payload) => api("/api/mock/sessions", { method: "POST", body: JSON.stringify(payload) });
export const getActiveMockSession = (params = {}) => api(`/api/mock/sessions/active?${new URLSearchParams(params)}`);
export const getMockSession = (id) => api(`/api/mock/sessions/${encodeURIComponent(id)}`);
export const cancelMockSession = (id) => api(`/api/mock/session-control/${encodeURIComponent(id)}/cancel`, { method: "POST", body: "{}" });
export const saveMockAnswer = (sessionId, questionId, selected) => api(`/api/mock/sessions/${encodeURIComponent(sessionId)}/answers/${encodeURIComponent(questionId)}`, { method: "PUT", body: JSON.stringify({ selected }) });
export const saveMockFlag = (sessionId, questionId, flagged) => api(`/api/mock/sessions/${encodeURIComponent(sessionId)}/questions/${encodeURIComponent(questionId)}/flag`, { method: "PUT", body: JSON.stringify({ flagged }) });
export const submitMockSession = (sessionId, reason = "learner") => api(`/api/mock/sessions/${encodeURIComponent(sessionId)}/submit`, { method: "POST", body: JSON.stringify({ reason }) });
export const getMockResult = (sessionId) => api(`/api/mock/sessions/${encodeURIComponent(sessionId)}/result`);
export const getMockHistory = (params = {}) => api(`/api/mock/history?${new URLSearchParams(params)}`);
export const toggleBookmark = (id) => api(`/api/questions/${encodeURIComponent(id)}/bookmark`, { method: "POST", body: "{}" });
export const getBookmark = (id) => api(`/api/questions/${encodeURIComponent(id)}/bookmark`);
export const addQuestionNote = (id, body) => api(`/api/questions/${encodeURIComponent(id)}/notes`, { method: "POST", body: JSON.stringify({ body }) });

export const getLabs = (params = {}) => api(`/api/labs?${new URLSearchParams(params)}`);
export const getLab = (id) => api(`/api/labs/${encodeURIComponent(id)}`);
export const getLabsConfig = () => api("/api/labs/config");
export const submitLab = (id, sql) => api(`/api/labs/${encodeURIComponent(id)}/submit`, { method: "POST", body: JSON.stringify({ sql }) });
export const submitFeedback = (payload) => api("/api/feedback", { method: "POST", body: JSON.stringify(payload) });
export const getGlobeActivity = () => api("/api/activity/globe");

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
