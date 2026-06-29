import { addFlashcard, deleteFlashcard, escapeHtml, getAllFlashcards, getDueFlashcards, reviewFlashcard } from "../api.js";
import { showToast } from "../components/toast.js";

let cards = [];
let current = 0;
let flipped = false;

export default async function mount(container) {
  container.innerHTML = `
    <section class="page-heading">
      <div><p class="eyebrow">Flashcards</p><h1>Spaced repetition</h1><p>Review cards due today or manage the whole deck.</p></div>
    </section>
    <section class="flashcard-layout">
      <div class="panel">
        <div class="panel-title"><div><p class="eyebrow">Due today</p><h2 id="due-count">0 cards</h2></div><button id="reload" class="secondary-btn">Reload</button></div>
        <div id="study-card" class="study-card empty-box">No card loaded.</div>
      </div>
      <div class="panel">
        <p class="eyebrow">Add card</p>
        <label class="field"><span>Front</span><textarea id="front"></textarea></label>
        <label class="field"><span>Back</span><textarea id="back"></textarea></label>
        <button id="add" class="primary-btn">Add card</button>
        <div id="deck" class="deck-list"></div>
      </div>
    </section>
  `;
  container.querySelector("#reload").addEventListener("click", () => load(container));
  container.querySelector("#add").addEventListener("click", async () => {
    const front = container.querySelector("#front").value;
    const back = container.querySelector("#back").value;
    await addFlashcard({ front, back, tags: [] });
    container.querySelector("#front").value = "";
    container.querySelector("#back").value = "";
    showToast("Flashcard added", "success");
    await load(container);
  });
  await load(container);
}

async function load(container) {
  try {
    const [due, all] = await Promise.all([getDueFlashcards(), getAllFlashcards()]);
    cards = due.cards || [];
    current = 0;
    flipped = false;
    container.querySelector("#due-count").textContent = `${due.due_today} cards`;
    renderStudy(container);
    container.querySelector("#deck").innerHTML = (all.cards || [])
      .slice(0, 40)
      .map(
        (card) => `<div class="deck-item">
          <strong>${escapeHtml(card.front).slice(0, 120)}</strong>
          <span>Next: ${escapeHtml(card.next_review)}</span>
          <button class="icon-btn" data-delete="${card.id}" type="button">Delete</button>
        </div>`,
      )
      .join("");
    container.querySelectorAll("[data-delete]").forEach((button) =>
      button.addEventListener("click", async () => {
        await deleteFlashcard(button.dataset.delete);
        await load(container);
      }),
    );
  } catch (error) {
    showToast(error.message, "error");
  }
}

function renderStudy(container) {
  const host = container.querySelector("#study-card");
  const card = cards[current];
  if (!card) {
    host.className = "study-card empty-box";
    host.textContent = "No cards due today.";
    return;
  }
  host.className = "study-card";
  host.innerHTML = `
    <div class="card-inner ${flipped ? "flipped" : ""}">
      <div class="card-face card-front"><p class="eyebrow">Front</p><h2>${escapeHtml(card.front)}</h2></div>
      <div class="card-face card-back"><p class="eyebrow">Back</p><h2>${escapeHtml(card.back)}</h2></div>
    </div>
    <div class="grade-row ${flipped ? "" : "hidden"}">
      ${[
        [0, "Forgot"],
        [2, "Hard"],
        [4, "Good"],
        [5, "Easy"],
      ]
        .map(([grade, label]) => `<button data-grade="${grade}" type="button">${label}</button>`)
        .join("")}
    </div>`;
  host.querySelector(".card-inner").addEventListener("click", () => {
    flipped = !flipped;
    renderStudy(container);
  });
  host.querySelectorAll("[data-grade]").forEach((button) =>
    button.addEventListener("click", async () => {
      await reviewFlashcard(card.id, Number(button.dataset.grade));
      current += 1;
      flipped = false;
      renderStudy(container);
    }),
  );
}
