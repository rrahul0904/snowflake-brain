export const VIEW_ID = "v26-clouding-practice";

import {
  escapeHtml,
  getHomeSummary,
  getSkillMap,
  getStudyLesson,
  scheduleTaskReview,
} from "../api.js";
import { activeTrack } from "../ui.js";
import { DOMAIN_COLORS, studyLayout } from "../components/study-shell.js";

export default async function mount(container, params = {}) {
  const trackId = params.track_id || activeTrack();
  const route = params.__route || "#/daily-session";
  if (route === "#/blitz") return blitz(container, trackId);
  if (route === "#/architecture-builder") return architectureBuilder(container, trackId);
  return dailySession(container, trackId);
}

async function base(trackId) {
  const map = await getSkillMap();
  const cert = (map.certifications || []).find(function (item) { return item.id === trackId; }) || (map.certifications || [])[0];
  if (!cert) throw new Error("Certification is not configured");
  const skills = [];
  (cert.domains || []).forEach(function (domain, domainIndex) {
    (domain.skills || []).forEach(function (skill) {
      skills.push(Object.assign({}, skill, { domain: domain, domainIndex: domainIndex }));
    });
  });
  return { cert: cert, skills: skills };
}

async function dailySession(container, trackId) {
  const data = await base(trackId);
  const home = await getHomeSummary({ track_id: trackId });
  const attempted = (home.summary && home.summary.skills) || [];
  const weak = attempted.slice().filter(function (item) { return Number(item.attempts || 0) > 0; }).sort(function (a, b) {
    return Number(a.accuracy_pct || 0) - Number(b.accuracy_pct || 0);
  })[0];
  const focus = data.skills.find(function (item) { return item.id === (weak && weak.skill_id); }) || data.skills[0];
  const completed = Number((home.progress && home.progress.completed_tasks) || 0);
  const attempts = attempted.reduce(function (sum, item) { return sum + Number(item.attempts || 0); }, 0);
  const xp = completed * 100 + attempts * 10;
  const level = Math.max(1, Math.floor(xp / 500) + 1);
  const due = Number((home.due && home.due.due_count) || 0);
  const readiness = Number((home.readiness && home.readiness.readiness_score) || 0);
  const domainIndex = focus ? Number(focus.domainIndex || 0) : 0;

  const body = [
    "<section class='v26-daily-head'><p class='v26-kicker'>Daily Certification Session</p><h1>One focused SnowPro session. No wandering.</h1><p>Today combines scheduled review, the weakest available task signal, and a short proof drill.</p></section>",
    "<section class='v26-daily-stats'>",
      stat("Level", String(level), xp + " XP from persisted progress"),
      stat("Readiness", readiness ? readiness + "/100" : "Building", "Evidence-based study signal"),
      stat("Due Today", String(due), due ? "Scheduled review is first" : "Review queue is clear"),
      stat("Tasks Complete", completed + "/" + data.skills.length, "Curriculum progression"),
    "</section>",
    "<section class='v26-daily-route'>",
      dailyStep("01", "Review", due ? due + " items due" : "Quick recall warm-up", due ? "#/due?track_id=" + encodeURIComponent(trackId) : "#/blitz?track_id=" + encodeURIComponent(trackId), "5 min"),
      dailyStep("02", "Focus", focus ? escapeHtml(focus.title) : "Next curriculum task", focus ? "#/skill?track_id=" + encodeURIComponent(trackId) + "&skill_id=" + encodeURIComponent(focus.id) : "#/curriculum?track_id=" + encodeURIComponent(trackId), "10 min", DOMAIN_COLORS[domainIndex % DOMAIN_COLORS.length]),
      dailyStep("03", "Prove", focus ? "5-question task drill" : "Targeted drill", focus ? "#/practice?track_id=" + encodeURIComponent(trackId) + "&mode=drill&skill_id=" + encodeURIComponent(focus.id) + "&start=1&count=5" : "#/practice?track_id=" + encodeURIComponent(trackId), "10 min"),
    "</section>",
    "<section class='v26-daily-actions'><a class='v26-btn primary' href='" + (due ? "#/due?track_id=" + encodeURIComponent(trackId) : "#/blitz?track_id=" + encodeURIComponent(trackId)) + "'>Start today's session</a><a class='v26-btn secondary' href='#/architecture-builder?track_id=" + encodeURIComponent(trackId) + "'>Architecture Builder</a></section>",
  ].join("");
  container.innerHTML = studyLayout(data.cert, "daily-session", body);
}

function stat(label, value, note) {
  return "<article><span>" + escapeHtml(label) + "</span><strong>" + escapeHtml(value) + "</strong><small>" + escapeHtml(note) + "</small></article>";
}

function dailyStep(n, title, body, href, minutes, color) {
  return "<a href='" + href + "' style='--domain:" + (color || "var(--accent)") + "'><b>" + n + "</b><div><span>" + escapeHtml(title) + "</span><strong>" + body + "</strong></div><em>" + escapeHtml(minutes) + " →</em></a>";
}

async function blitz(container, trackId) {
  const data = await base(trackId);
  const offset = new Date().getUTCDate() % Math.max(1, data.skills.length);
  const selected = [];
  for (let i = 0; i < Math.min(8, data.skills.length); i += 1) selected.push(data.skills[(offset + i) % data.skills.length]);
  const lessons = await Promise.all(selected.map(function (skill) { return getStudyLesson(skill.id, { track_id: trackId }); }));
  const cards = selected.map(function (skill, index) {
    const lesson = lessons[index] || {};
    const content = lesson.content || {};
    return {
      skill: skill,
      prompt: "Explain the decision boundary for " + skill.title + ".",
      answer: content.key_concept || content.summary || skill.objective || "Explain what requirement this Snowflake capability owns.",
    };
  });
  const state = { index: 0, good: 0, again: 0, revealed: false };

  function draw() {
    const card = cards[state.index];
    if (!card) {
      container.innerHTML = studyLayout(data.cert, "blitz", "<section class='v26-blitz-finish'><p class='v26-kicker'>Blitz Complete</p><h1>" + state.good + " strong recalls · " + state.again + " queued for review.</h1><p>Use the misses immediately while the distinction is still fresh.</p><div><a class='v26-btn primary' href='#/due?track_id=" + encodeURIComponent(trackId) + "'>Open review queue</a><a class='v26-btn secondary' href='#/practice?track_id=" + encodeURIComponent(trackId) + "&mode=drill'>Start targeted drill</a></div></section>");
      return;
    }
    const body = [
      "<section class='v26-blitz-head'><p class='v26-kicker'>Blitz Recall</p><h1>Fast retrieval before recognition.</h1><div><span>Card " + (state.index + 1) + " / " + cards.length + "</span><b>" + state.good + " strong</b><b>" + state.again + " review</b></div></section>",
      "<section class='v26-blitz-card'>",
        "<div><span>" + escapeHtml(card.skill.task_code || "Task") + "</span><em>" + escapeHtml(card.skill.domain.title) + "</em></div>",
        "<h2>" + escapeHtml(card.prompt) + "</h2>",
        state.revealed ? "<p class='v26-blitz-answer'>" + escapeHtml(card.answer) + "</p>" : "<button class='v26-btn primary' type='button' data-reveal>Reveal concept</button>",
        state.revealed ? "<footer><button type='button' data-rate='again'>Again</button><button type='button' data-rate='good'>Good</button><button type='button' data-rate='easy'>Easy</button></footer>" : "",
      "</section>",
      "<p class='v26-blitz-note'>Again schedules the mapped task into your account review queue. Good/Easy advance this Blitz without changing exam evidence.</p>",
    ].join("");
    container.innerHTML = studyLayout(data.cert, "blitz", body);
    container.querySelector("[data-reveal]")?.addEventListener("click", function () { state.revealed = true; draw(); });
    container.querySelectorAll("[data-rate]").forEach(function (button) {
      button.addEventListener("click", async function () {
        if (button.dataset.rate === "again") {
          state.again += 1;
          await scheduleTaskReview({ track_id: trackId, skill_id: card.skill.id }).catch(function () {});
        } else {
          state.good += 1;
        }
        state.index += 1;
        state.revealed = false;
        draw();
      });
    });
  }
  draw();
}

async function architectureBuilder(container, trackId) {
  const data = await base(trackId);
  const candidateSkills = data.skills.filter(function (skill) { return skill.objective; }).slice(0, 8);
  const lessons = await Promise.all(candidateSkills.map(function (skill) { return getStudyLesson(skill.id, { track_id: trackId }); }));
  const scenarios = [];
  lessons.forEach(function (lesson, index) {
    const rule = (((lesson || {}).content || {}).decision_rules || [])[0];
    if (!rule || !rule.when || !rule.choose) return;
    scenarios.push({
      skill: candidateSkills[index],
      requirement: rule.when,
      answer: rule.choose,
      why: rule.why || "It directly matches the requirement.",
    });
  });
  const state = { answers: {} };

  function draw(result) {
    const body = [
      "<section class='v26-arch-head'><p class='v26-kicker'>Architecture Builder</p><h1>Map requirements to the Snowflake capability that owns them.</h1><p>These scenarios are generated from the curated task decision rules already used by the certification curriculum.</p></section>",
      "<form class='v26-arch-grid' data-arch-form>",
        scenarios.map(function (scenario, index) {
          const generic = [
            scenario.answer,
            "Use the broadest administrative role",
            "Scale the warehouse before identifying the bottleneck",
            "Move the workload outside Snowflake by default",
          ];
          return "<article><div><b>Scenario " + (index + 1) + "</b><span>" + escapeHtml(scenario.skill.task_code || "") + "</span></div><p>" + escapeHtml(scenario.requirement) + "</p><select name='scenario-" + index + "'><option value=''>Choose capability</option>" + generic.map(function (choice) { return "<option value='" + escapeHtml(choice) + "'>" + escapeHtml(choice) + "</option>"; }).join("") + "</select>" + (result ? "<small class='" + (result[index] ? "correct" : "incorrect") + "'>" + (result[index] ? "Correct — " : "Review — ") + escapeHtml(scenario.why) + "</small>" : "") + "</article>";
        }).join(""),
        "<button class='v26-btn primary' type='submit'>Validate architecture</button>",
      "</form>",
    ].join("");
    container.innerHTML = studyLayout(data.cert, "architecture-builder", body);
    container.querySelector("[data-arch-form]")?.addEventListener("submit", function (event) {
      event.preventDefault();
      const form = new FormData(event.currentTarget);
      const outcomes = scenarios.map(function (scenario, index) { return String(form.get("scenario-" + index) || "") === String(scenario.answer); });
      draw(outcomes);
    });
  }
  draw(null);
}
