export const VIEW_ID = "labs";
import { escapeHtml, getExperienceShell, getLab, getLabs, submitLab } from "../api.js?v=20260714-v20-ai-academy";
import { activeTrack, emptyState, setActiveTrack, skeleton, trackOptions } from "../ui.js?v=20260714-v20-ai-academy";
import { showToast } from "../components/toast.js?v=20260714-v20-ai-academy";

const state = { certification: "snowpro-core", labs: [], activeLab: null, result: null };

export default async function mount(container, params = {}) {
  state.certification = params.certification || params.track_id || activeTrack();
  setActiveTrack(state.certification);
  container.innerHTML = skeleton("Loading Snowflake lab studio...");
  try {
    const [experience, labsResponse] = await Promise.all([
      getExperienceShell({ track_id: state.certification }),
      getLabs({ certification: state.certification }),
    ]);
    state.labs = labsResponse.labs || [];
    const firstLabId = params.lab_id || state.labs[0]?.id;
    state.activeLab = firstLabId ? await getLab(firstLabId) : null;
    state.result = null;
    render(container, experience);
  } catch (error) {
    showToast(error.message, "error");
    container.innerHTML = emptyState("Lab studio unavailable", error.message, `<button onclick="location.reload()">Retry</button>`);
  }
}

function render(container, experience) {
  const lab = state.activeLab;
  container.innerHTML = `
    <section class="lab-studio page-shell">
      <header class="lab-topline">
        <div>
          <p class="eyebrow">Snowflake Lab Studio</p>
          <h1>Prove skills in a real challenge workspace.</h1>
          <p>Scenario on the left. SQL editor on the right. Validation tests at the bottom. Solutions unlock after an attempt.</p>
        </div>
        <label class="cert-filter"><span>Certification</span><select id="cert-select">${trackOptions(experience.certifications || [], state.certification)}</select></label>
      </header>
      ${lab ? labWorkspace(lab) : emptyState("No labs configured", "This certification does not have lab challenges yet.")}
    </section>
  `;
  bind(container);
}

function labWorkspace(lab) {
  return `
    <div class="lab-runner-frame">
      <aside class="lab-list-panel">
        <div class="lab-list-header"><span>${state.labs.length} challenges</span><strong>${escapeHtml(state.certification)}</strong></div>
        <div class="lab-list">${state.labs.map(labListItem).join("")}</div>
      </aside>

      <main class="lab-problem-panel">
        <div class="lab-tabs"><button class="active">Problem</button><button disabled>Solution 🔒</button><button disabled>Submissions</button></div>
        <div class="lab-problem-scroll">
          <h2>${escapeHtml(lab.title)}</h2>
          <p class="lab-scenario">${escapeHtml(lab.scenario || lab.why_it_matters || "Write Snowflake SQL that satisfies the challenge requirements.")}</p>
          <div class="lab-meta-row">
            <span>${escapeHtml(lab.domain || "Snowflake")}</span>
            <span>${escapeHtml(lab.difficulty || "challenge")}</span>
            <span>${lab.estimated_minutes || lab.minutes || 20} min</span>
          </div>
          <hr />
          <h3>Instructions</h3>
          <ol class="instruction-list">${(lab.instructions || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ol>
          <h3>Context</h3>
          <div class="lab-context-box">${escapeHtml(lab.input_context || "Offline validation. Write the SQL you would run in Snowflake.")}</div>
          <h3>Expected evidence</h3>
          <div class="expected-box">${escapeHtml(lab.expected_output || "The validation checks should pass.")}</div>
          ${lab.exam_traps?.length ? `<h3>Exam traps</h3><div class="trap-list">${lab.exam_traps.map((trap) => `<span>${escapeHtml(trap)}</span>`).join("")}</div>` : ""}
        </div>
      </main>

      <section class="lab-editor-panel">
        <div class="editor-header"><strong>worksheet.sql</strong><span>Offline validation mode</span></div>
        <textarea id="sql-editor" spellcheck="false">${escapeHtml(lab.starter_sql || "-- Write your Snowflake SQL here\n")}</textarea>
        <div class="editor-actions">
          <button id="run-validation" class="primary-btn">Run validation</button>
          <button id="reset-sql" class="secondary-btn">Reset</button>
          <button id="show-hint" class="secondary-btn">Hint</button>
        </div>
        <div id="hint-box" class="hint-box hidden">${escapeHtml((lab.hints || ["Read each requirement and map it to SQL keywords."])[0])}</div>
        <div id="validation-output" class="validation-output">${validationPlaceholder(lab)}</div>
        <details id="solution-box" class="solution-box ${state.result ? "" : "locked"}">
          <summary>${state.result ? "Solution SQL" : "Solution locked until you run validation"}</summary>
          <pre>${escapeHtml(lab.solution_sql || "No solution configured.")}</pre>
          ${lab.teardown_sql ? `<strong>Cleanup</strong><pre>${escapeHtml(lab.teardown_sql)}</pre>` : ""}
        </details>
      </section>
    </div>
  `;
}

function labListItem(lab) {
  const active = state.activeLab?.id === lab.id;
  return `<button class="lab-list-item ${active ? "active" : ""}" data-id="${escapeHtml(lab.id)}" type="button">
    <span><strong>${escapeHtml(lab.title || "Lab")}</strong><small>${escapeHtml(lab.domain || "Skill")} · ${escapeHtml(lab.difficulty || "")}</small></span>
    ${lab.completed ? "<b>✓</b>" : "<b>›</b>"}
  </button>`;
}

function validationPlaceholder(lab) {
  const tests = lab.validation_tests || [];
  return `<div class="testcase-title">Validation tests</div>${tests.map((test) => `<div class="testcase"><span>○</span><p>${escapeHtml(test.name || "Validation")}</p></div>`).join("")}`;
}

function renderValidation(result) {
  const rows = result.results || result.checks || [];
  return `<div class="result-banner ${result.passed ? "passed" : "failed"}"><strong>${result.passed ? "Lab passed" : "Keep going"}</strong><span>${result.passed_count || 0}/${result.total || rows.length || 0} checks · ${result.score_pct || 0}%</span></div>
  ${rows.map((row) => `<div class="testcase ${row.passed ? "passed" : "failed"}"><span>${row.passed ? "✓" : "×"}</span><p>${escapeHtml(row.name || row.test || "Validation")}${row.message ? `<small>${escapeHtml(row.message)}</small>` : ""}</p></div>`).join("")}
  ${result.hint ? `<div class="hint-box">${escapeHtml(result.hint)}</div>` : ""}`;
}

function bind(container) {
  container.querySelector("#cert-select")?.addEventListener("change", (event) => {
    setActiveTrack(event.target.value);
    window.location.hash = `#/labs?certification=${encodeURIComponent(event.target.value)}`;
  });
  container.querySelectorAll(".lab-list-item").forEach((button) => {
    button.addEventListener("click", async () => {
      try {
        state.activeLab = await getLab(button.dataset.id);
        state.result = null;
        const experience = await getExperienceShell({ track_id: state.certification });
        render(container, experience);
      } catch (error) {
        showToast(error.message, "error");
      }
    });
  });
  container.querySelector("#reset-sql")?.addEventListener("click", () => {
    container.querySelector("#sql-editor").value = state.activeLab?.starter_sql || "";
  });
  container.querySelector("#show-hint")?.addEventListener("click", () => container.querySelector("#hint-box")?.classList.toggle("hidden"));
  container.querySelector("#run-validation")?.addEventListener("click", async () => {
    const sql = container.querySelector("#sql-editor")?.value || "";
    const button = container.querySelector("#run-validation");
    button.disabled = true;
    button.textContent = "Validating...";
    try {
      state.result = await submitLab(state.activeLab.id, sql);
      container.querySelector("#validation-output").innerHTML = renderValidation(state.result);
      const solution = container.querySelector("#solution-box");
      solution.classList.remove("locked");
      solution.querySelector("summary").textContent = "Solution SQL";
      showToast(state.result.passed ? "Lab passed" : "Validation completed", state.result.passed ? "success" : "warning");
    } catch (error) {
      showToast(error.message, "error");
    } finally {
      button.disabled = false;
      button.textContent = "Run validation";
    }
  });
}
