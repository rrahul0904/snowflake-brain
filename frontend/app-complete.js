import { renderNav } from "./components/nav.js";
import { renderFeedback } from "./components/feedback.js";
import { activeTrack } from "./ui.js";
import { route } from "./router-complete.js";
import { refreshCandidate } from "./auth.js";
import { renderCandidateAccess } from "./components/candidate-access.js";

window.__SNOWFLAKE_BRAIN_CLIENT_ERRORS__=[];
window.addEventListener("error",e=>window.__SNOWFLAKE_BRAIN_CLIENT_ERRORS__.push(e.message||"Unknown client error"));
window.addEventListener("unhandledrejection",e=>window.__SNOWFLAKE_BRAIN_CLIENT_ERRORS__.push(e.reason?.message||String(e.reason||"Unhandled promise rejection")));

function applyTheme(theme){const next=theme==="light"?"light":"dark";document.documentElement.dataset.theme=next;localStorage.setItem("snowflake-certification.theme",next)}
function footer(){const path=(window.location.hash||"#/home").split("?")[0];let root=document.querySelector("#v26-footer");if(!root){root=document.createElement("footer");root.id="v26-footer";document.body.appendChild(root)}if(path==="#/mock/session"){root.hidden=true;return}root.hidden=false;const t=encodeURIComponent(activeTrack());root.innerHTML=`<div class="v26-footer-inner"><div class="v26-footer-brand"><strong>Snowflake Certified</strong><p>Blueprint-first SnowPro preparation with written lessons, deliberate practice, and timed mock exams.</p><small>Independent certification-prep software.</small></div><nav><div><span>Curriculum</span><a href="#/curriculum?track_id=${t}">Exam Domains</a><a href="#/progress?track_id=${t}">Progress</a><a href="#/exercises?track_id=${t}">Build Exercises</a></div><div><span>Practice</span><a href="#/practice?track_id=${t}&mode=diagnostic">Diagnostic</a><a href="#/practice?track_id=${t}&mode=drill">Drill</a><a href="#/mock?track_id=${t}">Mock Exam</a></div><div><span>Reference</span><a href="#/quick-reference?track_id=${t}">Quick Reference</a><a href="#/glossary?track_id=${t}">Glossary</a><a href="#/reference?track_id=${t}">Resources</a></div><div><span>Account</span><a href="#/membership">Membership</a><a href="#/about">About</a><a href="#/privacy">Privacy</a><a href="#/journal?track_id=${t}">Journal</a></div></nav></div>`}
async function handleRoute(){await route();await renderNav();footer();document.querySelector("#view-root")?.focus({preventScroll:true})}
window.__setSnowflakeTheme=applyTheme;applyTheme(localStorage.getItem("snowflake-certification.theme")||"dark");
async function boot(){await refreshCandidate().catch(()=>{});renderCandidateAccess();await renderNav();renderFeedback();window.addEventListener("hashchange",handleRoute);window.addEventListener("track-change",handleRoute);window.addEventListener("candidate-change",handleRoute);window.addEventListener("theme-toggle",e=>applyTheme(e.detail?.theme));if(!window.location.hash)window.location.hash="#/home";await handleRoute()}
boot();
