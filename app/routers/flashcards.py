import json
from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..database import connect

router = APIRouter()


class FlashcardCreate(BaseModel):
    front: str
    back: str
    source: str = "manual"
    source_id: str | None = None
    tags: list[str] = []


class FlashcardReview(BaseModel):
    grade: int


@router.get("/flashcards")
def due_flashcards() -> dict[str, Any]:
    today = date.today().isoformat()
    with connect() as conn:
        rows = [dict(row) for row in conn.execute("SELECT * FROM flashcards WHERE next_review <= ? ORDER BY next_review, id", (today,))]
    cards = [_card(row) for row in rows]
    return {"due_today": len(cards), "cards": cards}


@router.get("/flashcards/all")
def all_flashcards() -> dict[str, Any]:
    with connect() as conn:
        rows = [dict(row) for row in conn.execute("SELECT * FROM flashcards ORDER BY next_review, id")]
    cards = [_card(row) for row in rows]
    return {"total": len(cards), "cards": cards}


@router.post("/flashcards")
def create_flashcard(payload: FlashcardCreate) -> dict[str, Any]:
    front = payload.front.strip()
    back = payload.back.strip()
    if not front or not back:
        raise HTTPException(status_code=400, detail="Front and back are required")
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO flashcards(front, back, source, source_id, tags)
            VALUES (?, ?, ?, ?, ?)
            """,
            (front, back, payload.source, payload.source_id, json.dumps(payload.tags)),
        )
    return {"ok": True, "id": cursor.lastrowid}


@router.post("/flashcards/generate")
def generate_flashcards(payload: dict[str, Any]) -> dict[str, Any]:
    lesson_id = payload.get("lesson_id")
    count = max(1, min(int(payload.get("count") or 5), 20))
    if not lesson_id:
        raise HTTPException(status_code=400, detail="lesson_id is required")
    with connect() as conn:
        chunks = [
            row["text"]
            for row in conn.execute(
                "SELECT text FROM transcript_chunks WHERE lesson_id = ? ORDER BY chunk_idx LIMIT 80",
                (lesson_id,),
            )
        ]
        if not chunks:
            lesson = conn.execute("SELECT title, transcript_text FROM lessons WHERE id = ?", (lesson_id,)).fetchone()
            if lesson:
                chunks = [lesson["title"], lesson["transcript_text"] or ""]
        text = " ".join(chunks)
        cards = _fallback_cards(text, count, lesson_id)
        for card in cards:
            conn.execute(
                "INSERT INTO flashcards(front, back, source, source_id, tags) VALUES (?, ?, 'ai_generated', ?, ?)",
                (card["front"], card["back"], lesson_id, json.dumps(["lesson"])),
            )
    return {"ok": True, "cards": cards}


@router.post("/flashcards/{card_id}/review")
def review_flashcard(card_id: int, payload: FlashcardReview) -> dict[str, Any]:
    grade = max(0, min(payload.grade, 5))
    with connect() as conn:
        row = conn.execute("SELECT * FROM flashcards WHERE id = ?", (card_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Flashcard not found")
        easiness, interval, repetitions = sm2(row["easiness"], row["interval"], row["repetitions"], grade)
        next_review = (date.today() + timedelta(days=interval)).isoformat()
        conn.execute(
            """
            UPDATE flashcards
            SET easiness = ?, interval = ?, repetitions = ?, next_review = ?
            WHERE id = ?
            """,
            (easiness, interval, repetitions, next_review, card_id),
        )
    return {"ok": True, "next_review": next_review, "interval": interval}


@router.delete("/flashcards/{card_id}")
def delete_flashcard(card_id: int) -> dict[str, bool]:
    with connect() as conn:
        conn.execute("DELETE FROM flashcards WHERE id = ?", (card_id,))
    return {"ok": True}


def sm2(easiness: float, interval: int, repetitions: int, grade: int) -> tuple[float, int, int]:
    if grade >= 3:
        if repetitions == 0:
            new_interval = 1
        elif repetitions == 1:
            new_interval = 6
        else:
            new_interval = round(interval * easiness)
        new_repetitions = repetitions + 1
    else:
        new_interval = 1
        new_repetitions = 0
    new_easiness = max(1.3, easiness + 0.1 - (5 - grade) * (0.08 + (5 - grade) * 0.02))
    return new_easiness, new_interval, new_repetitions


def _card(row: dict[str, Any]) -> dict[str, Any]:
    row["tags"] = json.loads(row.get("tags") or "[]")
    return row


def _fallback_cards(text: str, count: int, lesson_id: str) -> list[dict[str, str]]:
    words = " ".join(text.split())[:1600]
    seed = words or f"Lesson {lesson_id}"
    cards = []
    templates = [
        ("What is the core exam idea in this lesson?", seed[:260]),
        ("Which Snowflake feature should you recognize here?", seed[:260]),
        ("What should you remember for SnowPro Core?", seed[:260]),
        ("Which command or object is most relevant?", seed[:260]),
        ("What is the exam trap for this topic?", seed[:260]),
    ]
    for idx in range(count):
        front, back = templates[idx % len(templates)]
        cards.append({"front": front, "back": back})
    return cards
