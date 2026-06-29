import {
  createStudyGoal,
  escapeHtml,
  formatNumber,
  getContentAudit,
  getProgressSummary,
  getStudyReadiness,
  getSummary,
  getStudyGoals,
  getTodayPlan,
  getTopicProgress,
  getTracks,
} from "../api.js";
import { showToast } from "../components/toast.js";

const DEFAULT_TRACK = "snowpro-core";

export default async function mount(container) {
  container.innerHTML = `
    <section class="coach-page today-page">
      <div id="coach-root" class="loading-state">Loading certification coach...</div>
    </section>
  `;

  try {
    const [tracks, goals, today, progress, topics, readiness, summary, audit] = await Promise.all([
      getTracks(),
      getStudyGoals().catch(() => ({ goals: [] })),
      getTodayPlan().catch(() => ({ goals: [], items: [] })),
      getProgressSummary().catch(() => null),
      getTopicProgress().catch(() => ({ topics: [] })),
      getStudyReadiness().catch(() => ({ tracks: [] })),
      getSummary().catch(() => null),
      getContentAudit().catch(() => null),
    ]);

    const activeGoal = (goals.goals || [])[0] || (today.goals || [])[0];
    if (!activeGoal) {
      renderGoalSetup(container, tracks.tracks || [], summary);
      return;
    }

    renderTodayCoach(container, { goal: activeGoal, today, progress, topics, readiness, summary, audit });
  } catch (error) {
    container.querySelector("#coach-root").innerHTML = `<div class="error-state">${escapeHtml(error.message)}</div>`;
    showToast(error.message, "error");
  }
}

function renderGoalSetup(container, tracks, summary) {
  const root = container.querySelector("#coach-root");
  const defaultDate = dateDaysFromNow(60);
  const usefulTracks = [...tracks]
    .filter((track) => (track.question_count || 0) > 0 || (track.lesson_count || 0) > 0)
    .sort((a, b) => (b.question_count || 0) - (a.question_count || 0));
  const preferred = usefulTracks.find((track) => track.id === DEFAULT_TRACK) || usefulTracks[0];

  root.className = "coach-onboarding";
  root.innerHTML = `
    <section class="coach-hero panel coach-hero-tight">
      <div>
        <p class="eyebrow">Certification coach</p>
        <h1>Turn your videos and practice papers into a pass-the-exam plan.</h1>
        <p class="page-subtitle">Pick the exam, set a target date, then start with a diagnostic. The app will drive lessons, drills, mistakes, and readiness from your local content.</p>
      </div>
      <div class="coach-library-stats">
        <div><strong>${formatNumber(summary?.stats?.questions || 0)}</strong><span>questions indexed</span></div>
        <div><strong>${formatNumber(summary?.stats?.lessons || 0)}</strong><span>lessons indexed</span></div>
        <div><strong>${formatNumber(usefulTracks.length)}</strong><span>certification paths</span></div>
      </div>
    </section>

    <section class="coach-grid coach-grid-setup">
      <form id="goal-form" class="panel coach-setup-panel">
        <p class="eyebrow">Step 1</p>
        <h2>Choose your certification goal</h2>
        <label class="field"><span>Certification</span><select id="goal-track">
          ${usefulTracks.map((track) => `<option value="${escapeHtml(track.id)}" ${track.id === preferred?.id ? "selected" : ""}>${escapeHtml(track.title)} · ${formatNumber(track.question_count)} questions · ${formatNumber(track.lesson_count)} lessons</option>`).join("")}
        </select></label>
        <div class="two-field-row">
          <label class="field"><span>Target exam date</span><input id="goal-date" type="date" value="${defaultDate}" /></label>
          <label class="field"><span>Study hours / week</span><input id="goal-hours" type="number" min="1" max="80" value="8" /></label>
        </div>
        <label class="field"><span>Daily question target</span><input id="goal-questions" type="number" min="5" max="300" value="30" /></label>
        <button class="primary-btn wide" type="submit">Create my exam plan</button>
        <p class="muted small-copy">After this, start a 30-question diagnostic so the coach can find weak areas.</p>
      </form>

      <aside class="panel coach-explainer">
        <p class="eyebrow">How this will work</p>
        <ol class="coach-steps">
          <li><strong>Diagnostic first</strong><span>Measure your baseline instead of guessing.</span></li>
          <li><strong>Daily mission</strong><span>Get exactly what to watch, practice, and review today.</span></li>
          <li><strong>Repair loop</strong><span>Missed questions become drills, flashcards, and lesson recommendations.</span></li>
          <li><strong>Readiness gate</strong><span>The app tells you when you are not ready and why.</span></li>
        </ol>
      </aside>
    </section>

    <section class="panel track-picker-panel">
      <div class="panel-header"><div><p class="eyebrow">Available content</p><h2>Pick the exam with the strongest material</h2></div></div>
      <div class="track-card-grid">
        ${usefulTracks.slice(0, 8).map((track) => `
          <button class="coach-track-card ${track.id === preferred?.id ? "active" : ""}" data-track-id="${escapeHtml(track.id)}" type="button">
            <strong>${escapeHtml(track.title)}</strong>
            <span>${formatNumber(track.question_count)} questions · ${formatNumber(track.lesson_count)} lessons · ${formatNumber(track.practice_test_count || 0)} tests</span>
          </button>`).join("")}
      </div>
    </section>
  `;

  root.querySelectorAll(".coach-track-card").forEach((card) => {
    card.addEventListener("click", () => {
      root.querySelector("#goal-track").value = card.dataset.trackId;
      root.querySelectorAll(".coach-track-card").forEach((item) => item.classList.toggle("active", item === card));
    });
  });

  root.querySelector("#goal-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = root.querySelector("#goal-form button");
    button.disabled = true;
    button.textContent = "Creating plan...";
    try {
      const payload = {
        track_id: root.querySelector("#goal-track").value,
        target_exam_date: root.querySelector("#goal-date").value,
        weekly_hours: Number(root.querySelector("#goal-hours").value || 8),
        daily_question_target: Number(root.querySelector("#goal-questions").value || 30),
        auto_generate: true,
      };
      await createStudyGoal(payload);
      showToast("Study goal created. Start with your diagnostic.", "success");
      window.location.hash = `#/practice?mode=diagnostic&track_id=${encodeURIComponent(payload.track_id)}`;
    } catch (error) {
      showToast(error.message, "error");
      button.disabled = false;
      button.textContent = "Create my exam plan";
    }
  });
}

function renderTodayCoach(container, data) {
  const { goal, today, progress, topics, readiness, summary, audit } = data;
  const root = container.querySelector("#coach-root");
  const attempts = progress?.total_attempted || 0;
  const weak = weakestTopic(topics);
  const dueItems = today.items || [];
  const trackReadiness = (readiness.tracks || []).find((track) => track.track_id === goal.track_id) || (readiness.tracks || [])[0] || {};
  const next = nextAction({ goal, attempts, weak, dueItems });

  root.className = "coach-dashboard";
  root.innerHTML = `
    <header class="coach-header">
      <div>
        <p class="eyebrow">Today</p>
        <h1>${escapeHtml(goal.track_title)} exam mission</h1>
        <p class="page-subtitle">Target ${escapeHtml(goal.target_exam_date || "not set")} · ${goal.days_remaining ?? "?"} days left · ${goal.completion_pct || 0}% plan complete</p>
      </div>
      <a class="secondary-btn" href="#/readiness?track_id=${encodeURIComponent(goal.track_id)}">Readiness details</a>
    </header>

    <section class="coach-mission panel">
      <div>
        <p class="eyebrow">Do this next</p>
        <h2>${escapeHtml(next.title)}</h2>
        <p>${escapeHtml(next.description)}</p>
      </div>
      <a class="primary-btn mission-cta" href="${next.href}">${escapeHtml(next.cta)}</a>
    </section>

    <section class="coach-grid">
      <article class="panel readiness-card">
        <div class="panel-header"><div><p class="eyebrow">Readiness</p><h2>${readinessStatus(progress, trackReadiness)}</h2></div><div class="score-pill big">${progress?.exam_readiness_pct || 0}%</div></div>
        <div class="simple-meter"><span style="width:${Math.max(0, Math.min(100, progress?.exam_readiness_pct || 0))}%"></span></div>
        <div class="warning-list">${readinessWarnings(progress, trackReadiness).map((warning) => `<div class="warning">${escapeHtml(warning)}</div>`).join("")}</div>
      </article>

      <article class="panel coach-repair-card">
        <p class="eyebrow">Weakest repair</p>
        ${weak ? `
          <h2>${escapeHtml(weak.tag)}</h2>
          <p>${weak.accuracy}% accuracy from ${weak.attempted} attempts.</p>
          <a class="primary-btn" href="#/practice?mode=weak&track_id=${encodeURIComponent(goal.track_id)}&tag=${encodeURIComponent(weak.tag)}">Repair this topic</a>` : `
          <h2>No weak topic yet</h2>
          <p>Take the diagnostic so the coach can identify what to fix.</p>
          <a class="primary-btn" href="#/practice?mode=diagnostic&track_id=${encodeURIComponent(goal.track_id)}">Take diagnostic</a>`}
      </article>
    </section>

    <section class="coach-grid coach-grid-wide">
      <article class="panel">
        <div class="panel-header"><div><p class="eyebrow">Today's queue</p><h2>Planned work</h2></div><a class="secondary-btn" href="#/plan">Full plan</a></div>
        <div class="task-list coach-task-list">${renderPlanItems(goal, dueItems)}</div>
      </article>
      <article class="panel">
        <div class="panel-header"><div><p class="eyebrow">Content trust</p><h2>What the coach knows</h2></div></div>
        ${renderContentTrust(summary, audit)}
      </article>
    </section>
  `;
}

function nextAction({ goal, attempts, weak, dueItems }) {
  if (!attempts) {
    return {
      title: "Start with a 30-question diagnostic",
      description: "Before watching more videos, measure your baseline. This creates your weak-topic map.",
      cta: "Take diagnostic",
      href: `#/practice?mode=diagnostic&track_id=${encodeURIComponent(goal.track_id)}`,
    };
  }
  const first = dueItems[0];
  if (first) {
    return {
      title: first.title || first.lesson_title || first.practice_test_title || "Continue today's plan",
      description: `${first.track_title || goal.track_title} · due ${first.due_date || "today"}`,
      cta: "Continue task",
      href: hrefForTask(first),
    };
  }
  if (weak) {
    return {
      title: `Repair ${weak.tag}`,
      description: `${weak.accuracy}% accuracy. Fix this before the next mock exam.`,
      cta: "Start repair drill",
      href: `#/practice?mode=weak&track_id=${encodeURIComponent(goal.track_id)}&tag=${encodeURIComponent(weak.tag)}`,
    };
  }
  return {
    title: "Continue learning from the next lesson",
    description: "No overdue work. Keep moving through the course path.",
    cta: "Open Learn",
    href: `#/learn?track_id=${encodeURIComponent(goal.track_id)}`,
  };
}

function renderPlanItems(goal, items) {
  if (!items.length) {
    return `<div class="empty-state">No due items. Start a practice session or continue Learn.</div>`;
  }
  return items.slice(0, 6).map((item) => `
    <a class="coach-task-row" href="${hrefForTask(item)}">
      <span>${escapeHtml(labelForType(item.item_type))}</span>
      <strong>${escapeHtml(item.title || item.lesson_title || item.practice_test_title || "Study task")}</strong>
      <small>${escapeHtml(item.course_title || goal.track_title || "")}</small>
      <b>Start</b>
    </a>`).join("");
}

function renderContentTrust(summary, audit) {
  const transcript = audit?.transcript_quality || {};
  const practice = audit?.practice_quality || {};
  return `
    <div class="coach-stat-list">
      <div><strong>${formatNumber(summary?.stats?.questions || 0)}</strong><span>practice questions available</span></div>
      <div><strong>${formatNumber(summary?.stats?.lessons || 0)}</strong><span>video lessons indexed</span></div>
      <div><strong>${formatNumber(transcript.generated_notes || 0)}</strong><span>lessons use generated notes</span></div>
      <div><strong>${formatNumber(practice.empty_shell || practice.empty || 0)}</strong><span>empty practice shells hidden from exam flow</span></div>
    </div>`;
}

function readinessStatus(progress, track) {
  const score = progress?.exam_readiness_pct || 0;
  if (!progress?.total_attempted) return "Diagnostic needed";
  if ((track.practice_accuracy || 0) < 70) return "Needs repair";
  if (score >= 80) return "Close to ready";
  if (score >= 50) return "Learning";
  return "Insufficient data";
}

function readinessWarnings(progress, track) {
  const warnings = [];
  if (!progress?.total_attempted) warnings.push("No diagnostic or practice attempts recorded yet.");
  if ((progress?.total_attempted || 0) < 100) warnings.push("Question coverage is under 100 questions.");
  if ((track.full_mock_tests || 0) < 1) warnings.push("No completed full mock exam is recorded yet.");
  if ((track.practice_accuracy || progress?.accuracy_pct || 0) < 75) warnings.push("Accuracy is below the safe exam buffer.");
  return warnings.length ? warnings : ["No major blockers detected from current data."];
}

function weakestTopic(topics) {
  return (topics.topics || []).filter((topic) => topic.attempted).sort((a, b) => a.accuracy - b.accuracy || b.attempted - a.attempted)[0];
}

function hrefForTask(item) {
  if (item.lesson_id) return `#/learn?track_id=${encodeURIComponent(item.track_id || "")}&course_id=${encodeURIComponent(item.course_id || "")}&lesson_id=${encodeURIComponent(item.lesson_id)}`;
  if (item.practice_test_id) return `#/practice?track_id=${encodeURIComponent(item.track_id || "")}&course_id=${encodeURIComponent(item.course_id || "")}&test_id=${encodeURIComponent(item.practice_test_id)}`;
  if (item.item_type === "lab") return "#/labs";
  if (item.item_type === "flashcards") return "#/flashcards";
  return `#/practice?track_id=${encodeURIComponent(item.track_id || "")}`;
}

function labelForType(type) {
  return {
    lesson: "Learn",
    review: "Drill",
    practice_test: "Practice",
    mock_exam: "Mock exam",
    lab: "Lab",
    flashcards: "Review cards",
  }[type] || "Task";
}

function dateDaysFromNow(days) {
  const date = new Date();
  date.setDate(date.getDate() + days);
  return date.toISOString().slice(0, 10);
}
