export const VIEW_ID = "v26-question-explorer";

import {
  addQuestionNote,
  escapeHtml,
  getQuestionCoach,
  getQuestionExplorerHistory,
  getSkillMap,
  reportQuestionIssue,
  toggleBookmark,
} from "../api.js";
import { activeTrack } from "../ui.js";
import { DOMAIN_COLORS, studyLayout } from "../components/study-shell.js";

const state = { trackId: "snowpro-core", map: null, items: [], filters: {} };

export default async function mount(container, params = {}) {
  state.trackId = params.track_id || activeTrack();
  state.filters = {
    domain_id: params.domain_id || "",
    skill_id: params.skill_id || "",
    difficulty: params.difficulty || "",
    bookmarked_only: params.bookmarked_only === "1",
    unanswered_only: params.unanswered_only === "1",
  };
  const [map, history] = await Promise.all([
    getSkillMap(),
    getQuestionExplorerHistory({ track_id: state.trackId, ...state.filters, limit: 60 }),
  ]);
  state.map = map;
  state.items = history.items || [];
  const cert = (map.certifications || []).find((item) => item.id === state.trackId) || (map.certifications || [])[0];
  if (!cert) throw new Error("Certification is not configured");
  container.innerHTML = studyLayout(cert, "question-explorer", page(cert, history));
  bind(container, cert);
}

function page(cert, history) {
  const domains = cert.domains || [];
  const selectedDomain = domains.find((domain) => domain.id === state.filters.domain_id);
  const taskOptions = selectedDomain ? selectedDomain.skills || [] : domains.flatMap((domain) => domain.skills || []);
  return [
    "<section class='v26-explorer-head'>",
      "<p class='v26-kicker'>Question Explorer</p>",
      "<h1>Turn every question you have seen into a study asset.</h1>",
      "<p>Browse only questions previously served to your account. Build a new targeted session, bookmark a question, add a private note, ask for concept-level coaching, or flag content for review.</p>",
    "</section>",
    "<section class='v26-explorer-builder'>",
      "<div><p class='v26-kicker'>Custom Quiz</p><h2>Build the next session.</h2><p>The existing entitlement-aware allocator still chooses the questions; this composer only sets the scope.</p></div>",
      "<form data-custom-session>",
        select("Domain", "domain_id", [{ id: "", title: "All domains" }, ...domains], state.filters.domain_id),
        select("Task", "skill_id", [{ id: "", title: "All tasks" }, ...taskOptions], state.filters.skill_id),
        "<label><span>Difficulty</span><select name='difficulty'><option value=''>Any difficulty</option>" +
          ["easy","medium","hard"].map((value) => "<option value='"+value+"' "+(state.filters.difficulty===value?"selected":"")+">"+value[0].toUpperCase()+value.slice(1)+"</option>").join("") +
        "</select></label>",
        "<label><span>Questions</span><select name='count'>" +
          [5,10,15,20].map((count) => "<option value='"+count+"' "+(count===15?"selected":"")+">"+count+"</option>").join("") +
        "</select></label>",
        "<label class='v26-explorer-check'><input type='checkbox' name='unanswered_only' "+(state.filters.unanswered_only?"checked":"")+"><span>Unanswered only</span></label>",
        "<button class='v26-btn primary' type='submit'>Start custom session</button>",
      "</form>",
    "</section>",
    "<section class='v26-explorer-history'>",
      "<header><div><p class='v26-kicker'>Your Seen Questions</p><h2>"+escapeHtml(String(history.returned || 0))+" matching questions</h2></div>",
      "<form data-explorer-filter>",
        select("Domain", "domain_id", [{ id: "", title: "All domains" }, ...domains], state.filters.domain_id),
        "<label><span>Difficulty</span><select name='difficulty'><option value=''>Any</option>"+["easy","medium","hard"].map((value) => "<option value='"+value+"' "+(state.filters.difficulty===value?"selected":"")+">"+value+"</option>").join("")+"</select></label>",
        "<label class='v26-explorer-check'><input type='checkbox' name='bookmarked_only' "+(state.filters.bookmarked_only?"checked":"")+"><span>Bookmarked</span></label>",
        "<label class='v26-explorer-check'><input type='checkbox' name='unanswered_only' "+(state.filters.unanswered_only?"checked":"")+"><span>Unanswered</span></label>",
        "<button class='v26-btn secondary' type='submit'>Apply</button>",
      "</form></header>",
      state.items.length ? "<div class='v26-explorer-list'>"+state.items.map(questionCard).join("")+"</div>" :
        "<div class='v26-no-progress'><strong>No previously served questions match these filters.</strong><p>Start a drill or diagnostic first; the explorer never enumerates unseen private-bank content.</p><a class='v26-btn primary' href='#/practice?track_id="+encodeURIComponent(state.trackId)+"'>Open Practice</a></div>",
    "</section>",
    "<aside class='v26-explorer-coach' data-coach hidden aria-live='polite'></aside>",
  ].join("");
}

function select(label, name, rows, selected) {
  return "<label><span>"+escapeHtml(label)+"</span><select name='"+escapeHtml(name)+"'>"+
    rows.map((row) => "<option value='"+escapeHtml(row.id || "")+"' "+((row.id || "")===selected?"selected":"")+">"+escapeHtml(row.title || row.id || "All")+"</option>").join("")+
    "</select></label>";
}

function questionCard(item) {
  const labels = [];
  if (item.domain_id) labels.push("Domain "+escapeHtml(item.domain_id.replace(/^domain-?/i, "")));
  if (item.skill_id) labels.push(escapeHtml(item.skill_id));
  labels.push(escapeHtml(item.difficulty || "medium"));
  if (item.attempt_count) labels.push(String(item.attempt_count)+" attempt"+(Number(item.attempt_count)===1?"":"s"));
  return [
    "<article class='v26-explorer-card' data-question-id='"+escapeHtml(item.id)+"'>",
      "<div class='v26-explorer-meta'><span>"+labels.join(" · ")+"</span><em>"+(item.bookmarked?"★ Bookmarked":"Seen "+Number(item.served_count || 1)+"×")+"</em></div>",
      "<h3>"+escapeHtml(item.question)+"</h3>",
      "<ol>"+(item.options || []).map((option, index) => "<li><span>"+String.fromCharCode(65+index)+"</span>"+escapeHtml(option)+"</li>").join("")+"</ol>",
      "<footer>",
        "<button type='button' data-coach-question='"+escapeHtml(item.id)+"'>Ask Snowflake Coach</button>",
        "<button type='button' data-bookmark-question='"+escapeHtml(item.id)+"'>"+(item.bookmarked?"Remove bookmark":"Bookmark")+"</button>",
        "<button type='button' data-note-question='"+escapeHtml(item.id)+"'>Private note</button>",
        "<button type='button' data-report-question='"+escapeHtml(item.id)+"'>Flag content</button>",
        item.skill_id ? "<a href='#/practice?track_id="+encodeURIComponent(state.trackId)+"&mode=drill&skill_id="+encodeURIComponent(item.skill_id)+"'>Practice task →</a>" : "",
      "</footer>",
    "</article>",
  ].join("");
}

function bind(container, cert) {
  container.querySelector("[data-custom-session]")?.addEventListener("submit", (event) => {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const query = new URLSearchParams({ track_id: state.trackId, mode: "drill", start: "1", count: String(data.get("count") || 15) });
    ["domain_id","skill_id","difficulty"].forEach((key) => { const value = String(data.get(key) || ""); if (value) query.set(key, value); });
    if (data.get("unanswered_only")) query.set("unanswered_only", "1");
    window.location.hash = "#/practice?"+query.toString();
  });
  container.querySelector("[data-explorer-filter]")?.addEventListener("submit", (event) => {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const query = new URLSearchParams({ track_id: state.trackId });
    ["domain_id","difficulty"].forEach((key) => { const value = String(data.get(key) || ""); if (value) query.set(key, value); });
    if (data.get("bookmarked_only")) query.set("bookmarked_only", "1");
    if (data.get("unanswered_only")) query.set("unanswered_only", "1");
    window.location.hash = "#/question-explorer?"+query.toString();
  });
  container.querySelectorAll("[data-coach-question]").forEach((button) => button.addEventListener("click", async () => {
    button.disabled = true;
    try {
      const guidance = await getQuestionCoach(button.dataset.coachQuestion, { track_id: state.trackId });
      const panel = container.querySelector("[data-coach]");
      panel.hidden = false;
      panel.innerHTML = "<button type='button' data-close-coach aria-label='Close coach'>×</button><p class='v26-kicker'>Snowflake Coach · Socratic mode</p><h2>"+escapeHtml(guidance.concept || "Reason from the requirement.")+"</h2><p>"+escapeHtml(guidance.prompt || "")+"</p>"+(guidance.decision_rule?"<div><strong>Decision rule</strong><span>"+escapeHtml(guidance.decision_rule)+"</span></div>":"")+(guidance.trap?"<div><strong>Exam trap</strong><span>"+escapeHtml(guidance.trap)+"</span></div>":"")+(guidance.next_action?"<a class='v26-btn primary' href='"+escapeHtml(guidance.next_action)+"'>Review mapped lesson</a>":"")+"<small>No answer or option is revealed by coaching.</small>";
      panel.querySelector("[data-close-coach]")?.addEventListener("click", () => { panel.hidden = true; });
    } catch (error) {
      button.textContent = error.message || "Coach unavailable";
    } finally {
      button.disabled = false;
    }
  }));
  container.querySelectorAll("[data-bookmark-question]").forEach((button) => button.addEventListener("click", async () => {
    button.disabled = true;
    try {
      const result = await toggleBookmark(button.dataset.bookmarkQuestion);
      button.textContent = result.bookmarked ? "Remove bookmark" : "Bookmark";
    } finally { button.disabled = false; }
  }));
  container.querySelectorAll("[data-note-question]").forEach((button) => button.addEventListener("click", async () => {
    const note = window.prompt("Write the rule, distinction, or reminder you want to keep for this question.");
    if (!note) return;
    button.disabled = true;
    try { await addQuestionNote(button.dataset.noteQuestion, note); button.textContent = "Note saved"; }
    finally { button.disabled = false; }
  }));
  container.querySelectorAll("[data-report-question]").forEach((button) => button.addEventListener("click", async () => {
    const description = window.prompt("What looks wrong or unclear? This goes to content review.");
    if (description === null) return;
    button.disabled = true;
    try {
      await reportQuestionIssue(button.dataset.reportQuestion, { reason: "other", description });
      button.textContent = "Flagged for review";
    } finally { button.disabled = false; }
  }));
}
