import { escapeHtml } from "./api.js";

export async function getAffiliateResources() {
  const response = await fetch("/api/resources/affiliate", { credentials: "same-origin" });
  if (!response.ok) return { enabled: false, books: [] };
  return response.json();
}

export function affiliateBookSection(payload = {}) {
  if (!payload.enabled || !(payload.books || []).length) return "";
  const books = (payload.books || []).map((book) => `
    <article class="v26-resource-card v26-book-resource">
      <div>
        <span class="v26-kicker">Recommended book</span>
        <h3>${escapeHtml(book.title)}</h3>
        <p>${escapeHtml(book.author)} · ${escapeHtml(book.publisher)} · ${escapeHtml(book.year)}</p>
        <p>${escapeHtml(book.fit)}</p>
        <small>${escapeHtml(book.note)}</small>
      </div>
      <a href="${escapeHtml(book.url)}" target="_blank" rel="sponsored noopener noreferrer">View on Amazon <span>(${escapeHtml(book.link_disclosure || "Paid link")})</span> ↗</a>
    </article>
  `).join("");
  return `<section class="v26-section v26-resource-section v26-affiliate-books">
    <div class="v26-section-heading"><h2>Recommended books</h2></div>
    <div class="v26-affiliate-disclosure" role="note">
      <strong>${escapeHtml(payload.disclosure || "")}</strong>
      <span>${escapeHtml(payload.commission_disclosure || "")}</span>
    </div>
    <div class="v26-resource-grid">${books}</div>
  </section>`;
}
