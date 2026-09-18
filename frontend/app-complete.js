import { renderNav } from "./components/nav.js";
import { renderFeedback } from "./components/feedback.js";
import { activeTrack } from "./ui.js";
import { route } from "./router-complete.js";
import { refreshCandidate } from "./auth.js";
import { renderCandidateAccess } from "./components/candidate-access.js";

const PUBLIC_PATH_ROUTES={"/certifications":"#/certifications","/pricing":"#/pricing","/about":"#/about","/exam-guide":"#/exam-guide?track_id=snowpro-core","/content-integrity":"#/content-integrity"};
const PUBLIC_META={
  "#/home":["Snowflake Certification Guide","Independent SnowPro Core COF-C03 preparation with written lessons, practice, adaptive readiness, and timed mock exams."],
  "#/certifications":["SnowPro Certification Paths | Snowflake Brain","Explore source-verified SnowPro certification paths and the available COF-C03 preparation experience."],
  "#/pricing":["Snowflake Brain Membership","Compare free and paid SnowPro practice and mock-exam allowances."],
  "#/about":["About Snowflake Brain","Learn how this independent SnowPro certification preparation product is built and governed."],
  "#/exam-guide":["SnowPro Core COF-C03 Exam Guide","Review source-verified SnowPro Core COF-C03 certification facts, blueprint coverage, and preparation resources."],
  "#/content-integrity":["Content Integrity | Snowflake Brain","Read the independent-authoring, source-provenance, exam-integrity, and content-governance standards for Snowflake Brain."]
};
function promotePublicPath(){if(!window.location.hash&&PUBLIC_PATH_ROUTES[window.location.pathname])window.location.hash=PUBLIC_PATH_ROUTES[window.location.pathname]}
function updateDiscoveryMeta(){const route=(window.location.hash||"#/home").split("?")[0];const meta=PUBLIC_META[route]||PUBLIC_META["#/home"];document.title=meta[0];const description=document.querySelector('meta[name="description"]');if(description)description.setAttribute("content",meta[1]);const canonical=document.querySelector('link[rel="canonical"]');if(canonical)canonical.href=window.location.origin+(Object.entries(PUBLIC_PATH_ROUTES).find(([,hash])=>hash.split("?")[0]===route)?.[0]||"/")}

window.__SNOWFLAKE_BRAIN_CLIENT_ERRORS__=[];
window.addEventListener("error",e=>window.__SNOWFLAKE_BRAIN_CLIENT_ERRORS__.push(e.message||"Unknown client error"));
window.addEventListener("unhandledrejection",e=>window.__SNOWFLAKE_BRAIN_CLIENT_ERRORS__.push(e.reason?.message||String(e.reason||"Unhandled promise rejection")));

function applyTheme(theme){const next=theme==="light"?"light":"dark";document.documentElement.dataset.theme=next;localStorage.setItem("snowflake-certification.theme",next)}
function footer(){const path=(window.location.hash||"#/home").split("?")[0];let root=document.querySelector("#v26-footer");if(!root){root=document.createElement("footer");root.id="v26-footer";document.body.appendChild(root)}if(path==="#/mock/session"){root.hidden=true;return}root.hidden=false;const t=encodeURIComponent(activeTrack());root.innerHTML=`<div class="v26-footer-inner"><div class="v26-footer-brand"><strong>Snowflake Certified</strong><p>Independent SnowPro certification preparation.</p><small>Not affiliated with, sponsored by, approved by, or endorsed by Snowflake Inc.</small></div><nav aria-label="Footer navigation"><div><a href="#/certifications">Certifications</a><a href="#/exam-guide?track_id=snowpro-core">Exam Guide</a><a href="#/curriculum?track_id=${t}">Curriculum</a><a href="#/practice?track_id=${t}">Practice</a><a href="#/mistakes?track_id=${t}">Mistakes</a><a href="#/reference?track_id=${t}">Reference</a><a href="#/journal?track_id=${t}">Journal</a><a href="#/community?track_id=${t}">Community</a><a href="#/about">About</a><a href="#/content-integrity">Content Integrity</a><a href="#/terms">Terms</a><a href="#/changelog">Changelog</a><a href="#/privacy">Privacy</a></div></nav></div>`}
async function handleRoute(){await route();updateDiscoveryMeta();footer();document.querySelector("#view-root")?.focus({preventScroll:true})}
window.__setSnowflakeTheme=applyTheme;applyTheme(localStorage.getItem("snowflake-certification.theme")||"dark");
async function boot(){promotePublicPath();await refreshCandidate().catch(()=>{});renderCandidateAccess();await renderNav();renderFeedback();window.addEventListener("hashchange",handleRoute);window.addEventListener("track-change",()=>{renderNav();handleRoute()});window.addEventListener("candidate-change",()=>{renderNav();handleRoute()});window.addEventListener("theme-toggle",e=>{applyTheme(e.detail?.theme);renderNav()});if(!window.location.hash)window.location.hash="#/home";await handleRoute()}
boot();
