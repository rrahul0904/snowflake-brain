export const VIEW_ID = "flashcards";
import { addFlashcard, deleteFlashcard, escapeHtml, generateFlashcards, getAllFlashcards, getDueFlashcards, reviewFlashcard } from "../api.js?v=20260714-v20-ai-academy";
import { emptyState, skeleton } from "../ui.js?v=20260714-v20-ai-academy";
import { showToast } from "../components/toast.js?v=20260714-v20-ai-academy";

export default async function mount(container) {
  container.innerHTML = skeleton("Loading memory deck...");
  try {
    const [due, all] = await Promise.all([getDueFlashcards().catch(() => ({ cards: [] })), getAllFlashcards().catch(() => ({ cards: [] }))]);
    render(container, due.cards || [], all.cards || []);
  } catch (error) {
    container.innerHTML = emptyState("Memory deck unavailable", error.message);
  }
}

function render(container, due, all) {
  container.innerHTML = `
    <section class="page-shell cards-page-v8">
      <header class="page-hero split-hero"><div><p class="eyebrow">Memory Deck</p><h1>Spaced recall for exam traps and repeated misses.</h1><p>Cards should come from mistakes, lab failures, and concepts that need retention — not random note taking.</p></div><button id="generate-missed" class="primary-btn xl">Generate from missed questions</button></header>
      <section class="cards-grid-v8">
        <article class="panel due-card-panel"><div class="panel-header"><div><p class="eyebrow">Due now</p><h2>${due.length} cards</h2></div><button id="reload" class="secondary-btn">Reload</button></div><div id="due-list" class="due-list-v8">${due.length ? due.map(cardReview).join("") : emptyState("No cards due", "Mistakes and generated cards will appear here.")}</div></article>
        <article class="panel add-card-panel"><div class="panel-header"><div><p class="eyebrow">Create card</p><h2>Manual memory item</h2></div></div><label>Front<textarea id="front"></textarea></label><label>Back<textarea id="back"></textarea></label><button id="add" class="primary-btn">Add card</button></article>
      </section>
      <section class="panel"><div class="panel-header"><div><p class="eyebrow">Deck inventory</p><h2>${all.length} total cards</h2></div></div><div class="deck-list-v8">${all.slice(0, 50).map(deckRow).join("") || emptyState("Deck is empty", "Generate cards from missed questions after practice.")}</div></section>
    </section>
  `;
  container.querySelector("#reload")?.addEventListener("click", () => mount(container));
  container.querySelector("#add")?.addEventListener("click", () => add(container));
  container.querySelector("#generate-missed")?.addEventListener("click", () => generate(container));
  container.querySelectorAll("[data-grade]").forEach((button) => button.addEventListener("click", () => review(container, button.dataset.id, button.dataset.grade)));
  container.querySelectorAll("[data-delete]").forEach((button) => button.addEventListener("click", () => remove(container, button.dataset.delete)));
}

function cardReview(card) {
  return `<article class="review-card"><strong>${escapeHtml(card.front || "")}</strong><p>${escapeHtml(card.back || "")}</p><div>${["again", "hard", "good", "easy"].map((grade) => `<button data-id="${card.id}" data-grade="${grade}" class="secondary-btn">${grade}</button>`).join("")}</div></article>`;
}

function deckRow(card) {
  return `<div class="deck-row"><span><strong>${escapeHtml(card.front || "")}</strong><small>${escapeHtml(card.back || "")}</small></span><button data-delete="${card.id}" class="secondary-btn">Delete</button></div>`;
}

async function add(container) {
  const front = container.querySelector("#front").value.trim();
  const back = container.querySelector("#back").value.trim();
  if (!front || !back) return;
  try { await addFlashcard({ front, back, tags: ["manual"] }); showToast("Card added", "success"); mount(container); } catch (error) { showToast(error.message, "error"); }
}
async function review(container, id, grade) { try { await reviewFlashcard(id, grade); mount(container); } catch (error) { showToast(error.message, "error"); } }
async function remove(container, id) { try { await deleteFlashcard(id); mount(container); } catch (error) { showToast(error.message, "error"); } }
async function generate(container) { try { const res = await generateFlashcards({ source: "missed", count: 12 }); showToast(`Generated ${res.created || 0} cards`, "success"); mount(container); } catch (error) { showToast(error.message, "error"); } }
