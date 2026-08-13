import { getSkillMap } from "../api.js";
import { activeTrack } from "../ui.js";

const domainColors = ["#e6a36b", "#7aa6d8", "#a98bd4", "#78b887", "#d7776d"];

export async function enhanceStudyLayout(container) {
  const main = container.querySelector("main.guide-page");
  if (!main || main.closest(".v26-study-shell")) return;
  const trackId = activeTrack();
  let cert = null;
  try {
    const map = await getSkillMap();
    cert = (map.certifications || []).find((item) => item.id === trackId) || (map.certifications || [])[0];
  } catch {}
  if (!cert) return;
  const raw = (window.location.hash || "#/curriculum").split("?")[0];
  const sidebar = document.createElement("aside");
  sidebar.className = "v26-study-sidebar";
  sidebar.innerHTML = `<div class="v26-study-group"><span>Study Tools</span>${link("#/progress", "Progress Dashboard", raw)}${link("#/drill", "Drill Mode", raw)}</div><div class="v26-study-group"><span>Curriculum</span><a class="v26-study-overview ${raw === "#/curriculum" ? "active" : ""}" href="#/curriculum?track_id=${trackId}">Exam Domains</a>${(cert.domains || []).map((domain, index) => `<a class="v26-study-domain" href="#/domain?track_id=${trackId}&domain_id=${encodeURIComponent(domain.id)}"><i style="--domain:${domainColors[index % domainColors.length]}"></i><b>${index + 1}</b><span>${domain.title}</span><em>${Number(domain.weight || 0)}%</em></a>`).join("")}</div><div class="v26-study-group"><span>Practice</span>${link("#/exercises", "Build Exercises", raw)}${link("#/diagnostic", "Diagnostic Test", raw)}</div><div class="v26-study-group"><span>Look Up</span>${link("#/quick-reference", "Quick Reference", raw)}${link("#/glossary", "Glossary", raw)}</div>`;
  const shell = document.createElement("div");
  shell.className = "v26-study-shell";
  main.parentNode.insertBefore(shell, main);
  shell.append(sidebar, main);
}

function link(href, label, raw) {
  return `<a class="${raw === href ? "active" : ""}" href="${href}?track_id=${activeTrack()}">${label}</a>`;
}
