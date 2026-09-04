export const VIEW_ID = "v26-confidence-calibration";

import { escapeHtml, getConfidenceCalibration, getSkillMap } from "../api.js";
import { activeTrack } from "../ui.js";
import { studyLayout } from "../components/study-shell.js";
import { emptyState, evidenceNotice } from "../components/learning-widgets.js";

export default async function mount(container, params = {}) {
  const trackId = params.track_id || activeTrack();
  const [map, calibration] = await Promise.all([
    getSkillMap(),
    getConfidenceCalibration({ track_id: trackId }).catch(() => ({ sample_size: 0, status: "insufficient_data", per_level: [] })),
  ]);
  const cert = (map.certifications || []).find((item) => item.id === trackId) || (map.certifications || [])[0];
  if (!cert) throw new Error("Certification is not configured");
  const sample = Number(calibration.sample_size || 0);
  const status = String(calibration.status || "insufficient_data").replaceAll("_", " ");
  const levels = calibration.per_level || [];
  const groups = aggregate(levels);
  const danger = Number(calibration.overconfident_misses || 0);

  container.innerHTML = studyLayout(cert, "confidence", `<a class="v26-study-back" href="#/progress?track_id=${encodeURIComponent(trackId)}" aria-label="Back">‹</a><header class="v26-recording-progress-head"><p class="v26-kicker">Exam-risk insight</p><h1>Confidence Calibration</h1><p>Knowing the answer is useful. Knowing when you might be wrong is a different skill. Confidence is recorded with practice so the system can separate uncertainty from dangerous overconfidence.</p>${evidenceNotice("Calibration is based only on answers where you supplied a confidence rating. It does not infer confidence from behavior you did not record.")}</header>${sample ? `<section class="v26-learning-command"><div><span>Rated answers</span><strong>${sample}</strong><small>Calibration sample</small></div><div><span>Calibration</span><strong>${Math.round(Number(calibration.calibration_score || 0))}</strong><small>/100 · ${escapeHtml(status)}</small></div><div class="${danger ? "risk" : ""}"><span>High confidence + wrong</span><strong>${danger}</strong><small>${danger ? "Priority exam risk" : "No recorded cases"}</small></div><div><span>Low confidence + correct</span><strong>${Number(calibration.underconfident_correct || 0)}</strong><small>Knowledge you may underrate</small></div></section><section class="v26-progress-section"><div class="v26-section-heading"><p class="v26-kicker">Confidence matrix</p><h2>How belief compares with correctness.</h2><p>The most dangerous zone is high confidence paired with low accuracy.</p></div><div class="v26-confidence-matrix">${groups.map(groupCard).join("")}</div></section><section class="v26-progress-section"><div class="v26-section-heading"><p class="v26-kicker">Interpretation</p><h2>${interpretation(calibration)}</h2><p>${interpretationDetail(calibration)}</p></div><div class="v26-result-actions"><a class="v26-btn primary" href="#/adaptive?track_id=${encodeURIComponent(trackId)}">Start confidence-rated adaptive session</a><a class="v26-btn secondary" href="#/practice?track_id=${encodeURIComponent(trackId)}&mode=drill">Targeted drill</a></div></section>` : emptyState("Calibration needs more evidence", "Rate confidence on at least five practice answers. Low, Medium, and High ratings help distinguish uncertainty from overconfidence.", `#/adaptive?track_id=${encodeURIComponent(trackId)}`, "Start adaptive practice")}`, "", []);
}

function aggregate(levels) {
  const buckets = [
    { label: "Low", min: 1, max: 2, expected: "20–40%" },
    { label: "Medium", min: 3, max: 3, expected: "≈60%" },
    { label: "High", min: 4, max: 5, expected: "80–100%" },
  ];
  return buckets.map((bucket) => {
    const rows = levels.filter((row) => Number(row.confidence) >= bucket.min && Number(row.confidence) <= bucket.max);
    const attempts = rows.reduce((sum, row) => sum + Number(row.attempts || 0), 0);
    const correct = rows.reduce((sum, row) => sum + Number(row.correct || 0), 0);
    const accuracy = attempts ? Math.round(correct / attempts * 100) : 0;
    return { ...bucket, attempts, correct, accuracy };
  });
}

function groupCard(group) {
  const risk = group.label === "High" && group.attempts >= 2 && group.accuracy < 70;
  return `<article class="${risk ? "risk" : ""}"><span>${escapeHtml(group.label)} confidence</span><strong>${group.attempts ? `${group.accuracy}%` : "—"}</strong><div class="bar"><i style="width:${group.accuracy}%"></i></div><p>${group.attempts} rated answer${group.attempts === 1 ? "" : "s"} · expected confidence range ${group.expected}</p>${risk ? `<b>High-confidence errors deserve immediate remediation.</b>` : ""}</article>`;
}

function interpretation(calibration) {
  const status = String(calibration.status || "");
  if (status === "overconfident") return "Your biggest risk is being certain when you are wrong.";
  if (status === "underconfident") return "You know more than your confidence suggests.";
  if (status === "well_calibrated") return "Your confidence is tracking your actual performance well.";
  if (status === "mixed") return "Confidence varies by situation; keep collecting evidence.";
  return "Keep rating confidence to sharpen the signal.";
}

function interpretationDetail(calibration) {
  const over = Number(calibration.overconfident_misses || 0);
  const under = Number(calibration.underconfident_correct || 0);
  if (over > under) return "Prioritize high-confidence misses in the Mistake Notebook. They are more dangerous than a guess you already knew was uncertain.";
  if (under > over) return "Review low-confidence correct answers so fragile knowledge becomes deliberate, repeatable reasoning.";
  return "Use calibration alongside mastery, retention, coverage, and mock evidence rather than as a standalone readiness score.";
}
