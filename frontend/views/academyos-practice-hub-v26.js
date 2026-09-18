export const VIEW_ID = "v26-practice-hub";

import {
  escapeHtml,
  getHomeSummary,
  getMockConfig,
  getMockHistory,
  getSkillMap,
  getSkillSummary,
  getStudyLesson,
  getTaskProgress,
  scheduleTaskReview,
} from "../api.js";
import { activeTrack } from "../ui.js";
import { DOMAIN_COLORS, studyLayout } from "../components/study-shell.js";

export default async function mount(container, params = {}) {
  const trackId = params.track_id || activeTrack();
  const [map, summary, progress, config, history, home] = await Promise.all([
    getSkillMap(),
    getSkillSummary({ track_id: trackId }),
    getTaskProgress({ track_id: trackId }),
    getMockConfig({ track_id: trackId }),
    getMockHistory({ track_id: trackId }).catch(function () { return { history: [] }; }),
    getHomeSummary({ track_id: trackId }),
  ]);
  const cert = (map.certifications || []).find(function (item) { return item.id === trackId; }) || (map.certifications || [])[0];
  if (!cert) throw new Error("Certification is not configured");
  const skills = [];
  (cert.domains || []).forEach(function (domain, domainIndex) {
    (domain.skills || []).forEach(function (skill) {
      skills.push(Object.assign({}, skill, { domain: domain, domainIndex: domainIndex }));
    });
  });
  const totalAttempts = (summary.skills || []).reduce(function (sum, item) { return sum + Number(item.attempts || 0); }, 0);
  const recentMock = ((history && history.history) || [])[0] || null;
  const readiness = Number((home.readiness && home.readiness.readiness_score) || 0);
  const xp = Number(progress.completed_tasks || 0) * 100 + totalAttempts * 10 + Number(((history && history.history) || []).length) * 50;
  const level = Math.max(1, Math.floor(xp / 500) + 1);
  const body = [
    "<section class='v26-hub-head'><p class='v26-kicker'>Practice Hub</p><h1>One place for every kind of SnowPro evidence.</h1><p>Choose practice by purpose, see domain-level results, continue persisted progress, and move directly from recall to simulation to build work.</p></section>",
    "<section class='v26-hub-kpis'>",
      kpi("Level", String(level), xp + " XP from saved evidence"),
      kpi("Tasks", Number(progress.completed_tasks || 0) + "/" + Number(progress.total_tasks || skills.length), "Persisted curriculum completion"),
      kpi("Readiness", readiness ? readiness + "/100" : "Building", "Adaptive evidence signal"),
      kpi("Latest Mock", recentMock ? String(recentMock.scaled_score || "—") : "None yet", recentMock ? String(recentMock.mode || "mock").replaceAll("_", " ") : "Start a timed sitting"),
    "</section>",
    "<section class='v26-hub-modes'>",
      modeCard("Diagnostic", "Find the gaps", "Balanced baseline across all five domains.", "#/practice?track_id=" + encodeURIComponent(trackId) + "&mode=diagnostic", "Untimed"),
      modeCard("Targeted Drill", "Repair one weakness", "Filter by domain, task, difficulty, or unanswered history.", "#/practice?track_id=" + encodeURIComponent(trackId) + "&mode=drill", "5–20 questions"),
      modeCard("Quick Mock", "Timed checkpoint", "Short exam rehearsal in the persisted mock player.", "#/mock/start?track_id=" + encodeURIComponent(trackId) + "&type=quick-mock", Number((config.quick_mock || {}).question_count || 30) + " questions"),
      modeCard("Full Mock", "Complete simulation", "Full sitting with navigation, flags, autosave, resume, and remediation.", "#/mock/start?track_id=" + encodeURIComponent(trackId) + "&type=full-mock", Number((config.full_mock || {}).question_count || 100) + " questions"),
    "</section>",
    domainScoreboard(cert, summary.domains || []),
    "<section class='v26-hub-two'><div data-hub-blitz></div><div data-hub-architecture></div></section>",
    "<section class='v26-hub-resume'><div><p class='v26-kicker'>Persistent Progression</p><h2>Resume from account evidence, not browser state.</h2><p>Lessons, attempts, due reviews, mistakes, confidence, study plan, and timed mock history already persist against the candidate account.</p></div><div><a class='v26-btn primary' href='#/progress?track_id=" + encodeURIComponent(trackId) + "'>Open Progress</a><a class='v26-btn secondary' href='#/due?track_id=" + encodeURIComponent(trackId) + "'>Due Today</a><a class='v26-btn secondary' href='#/mistakes?track_id=" + encodeURIComponent(trackId) + "'>Mistakes</a></div></section>",
  ].join("");
  container.innerHTML = studyLayout(cert, "practice-hub", body);
  await mountBlitz(container.querySelector("[data-hub-blitz]"), trackId, skills);
  await mountArchitecture(container.querySelector("[data-hub-architecture]"), trackId, skills);
}

function kpi(label, value, note) {
  return "<article><span>" + escapeHtml(label) + "</span><strong>" + escapeHtml(value) + "</strong><small>" + escapeHtml(note) + "</small></article>";
}

function modeCard(kicker, title, body, href, meta) {
  return "<a href='" + href + "'><span>" + escapeHtml(kicker) + "</span><h2>" + escapeHtml(title) + "</h2><p>" + escapeHtml(body) + "</p><footer><b>" + escapeHtml(meta) + "</b><em>Start →</em></footer></a>";
}

function domainScoreboard(cert, domainRows) {
  const byId = {};
  domainRows.forEach(function (row) { byId[row.domain_id || row.domain] = row; });
  return "<section class='v26-hub-domains'><header><p class='v26-kicker'>Domain Scoring</p><h2>Practice evidence by exam domain</h2></header><div>" +
    (cert.domains || []).map(function (domain, index) {
      const row = byId[domain.id] || domainRows.find(function (item) { return item.domain === domain.title; }) || {};
      const attempts = Number(row.attempts || 0);
      const accuracy = attempts ? Number(row.accuracy_pct || 0) : 0;
      return "<article style='--domain:" + DOMAIN_COLORS[index % DOMAIN_COLORS.length] + "'><i></i><div><span>Domain " + (index + 1) + " · " + Number(domain.weight || 0) + "%</span><strong>" + escapeHtml(domain.title) + "</strong><small>" + attempts + " attempts</small></div><b>" + (attempts ? accuracy + "%" : "—") + "</b><a href='#/practice?track_id=" + encodeURIComponent(cert.id) + "&mode=drill&domain_id=" + encodeURIComponent(domain.id) + "'>Drill →</a></article>";
    }).join("") + "</div></section>";
}

async function mountBlitz(root, trackId, skills) {
  if (!root || !skills.length) return;
  const cards = skills.slice(0, Math.min(5, skills.length));
  const lessons = await Promise.all(cards.map(function (skill) { return getStudyLesson(skill.id, { track_id: trackId }); }));
  const state = { index: 0, revealed: false, strong: 0, review: 0 };

  function draw() {
    const skill = cards[state.index];
    const lesson = lessons[state.index] || {};
    if (!skill) {
      root.innerHTML = "<section class='v26-hub-mini done'><p class='v26-kicker'>Blitz</p><h2>" + state.strong + " strong · " + state.review + " review</h2><p>Use the scheduled reviews to close weak recall before your next mock.</p><a href='#/due?track_id=" + encodeURIComponent(trackId) + "'>Open Due Today →</a></section>";
      return;
    }
    const concept = ((lesson.content || {}).key_concept || (lesson.content || {}).summary || skill.objective || skill.title);
    root.innerHTML = "<section class='v26-hub-mini'><p class='v26-kicker'>Blitz</p><span>Card " + (state.index + 1) + "/" + cards.length + "</span><h2>" + escapeHtml(skill.title) + "</h2>" +
      (state.revealed ? "<p class='answer'>" + escapeHtml(concept) + "</p><footer><button type='button' data-hub-rate='again'>Again</button><button type='button' data-hub-rate='good'>Good</button></footer>" : "<p>State the decision boundary before you reveal the concept.</p><button class='v26-btn primary' type='button' data-hub-reveal>Reveal</button>") +
      "</section>";
    root.querySelector("[data-hub-reveal]")?.addEventListener("click", function () { state.revealed = true; draw(); });
    root.querySelectorAll("[data-hub-rate]").forEach(function (button) {
      button.addEventListener("click", async function () {
        if (button.dataset.hubRate === "again") {
          state.review += 1;
          await scheduleTaskReview({ track_id: trackId, skill_id: skill.id }).catch(function () {});
        } else state.strong += 1;
        state.index += 1;
        state.revealed = false;
        draw();
      });
    });
  }
  draw();
}

async function mountArchitecture(root, trackId, skills) {
  if (!root || !skills.length) return;
  const selected = skills.slice(0, Math.min(5, skills.length));
  const lessons = await Promise.all(selected.map(function (skill) { return getStudyLesson(skill.id, { track_id: trackId }); }));
  const scenarios = [];
  lessons.forEach(function (lesson, index) {
    const rule = (((lesson || {}).content || {}).decision_rules || [])[0];
    if (rule && rule.when && rule.choose) scenarios.push({ skill: selected[index], when: rule.when, choose: rule.choose, why: rule.why || "It matches the requirement." });
  });
  let index = 0;

  function draw(message) {
    const scenario = scenarios[index];
    if (!scenario) {
      root.innerHTML = "<section class='v26-hub-mini done'><p class='v26-kicker'>Architecture Builder</p><h2>Scenario set complete.</h2><p>Continue into build exercises for implementation-level practice.</p><a href='#/exercises?track_id=" + encodeURIComponent(trackId) + "'>Open Build Exercises →</a></section>";
      return;
    }
    const options = [scenario.choose, "Use the broadest administrative role", "Scale compute before identifying the bottleneck", "Move the workload outside Snowflake by default"];
    root.innerHTML = "<section class='v26-hub-mini'><p class='v26-kicker'>Architecture Builder</p><span>Scenario " + (index + 1) + "/" + scenarios.length + "</span><h2>" + escapeHtml(scenario.when) + "</h2><select data-hub-arch><option value=''>Choose capability</option>" + options.map(function (option) { return "<option value='" + escapeHtml(option) + "'>" + escapeHtml(option) + "</option>"; }).join("") + "</select><button class='v26-btn primary' type='button' data-hub-arch-check>Validate</button>" + (message ? "<p class='answer'>" + escapeHtml(message) + "</p>" : "") + "</section>";
    root.querySelector("[data-hub-arch-check]")?.addEventListener("click", function () {
      const chosen = String(root.querySelector("[data-hub-arch]")?.value || "");
      if (!chosen) return draw("Choose an option first.");
      if (chosen === String(scenario.choose)) {
        index += 1;
        draw("Correct. " + scenario.why);
      } else {
        draw("Review the requirement boundary: " + scenario.why);
      }
    });
  }
  draw("");
}
