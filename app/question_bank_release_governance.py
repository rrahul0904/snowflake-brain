from __future__ import annotations

import json
from typing import Any

from .database import connect
from .question_bank_releases import get_release, promote_release


GENERIC_APPROVER_IDENTITIES = {
    "admin",
    "operator",
    "release-operator",
    "system",
}
PLACEHOLDER_EVIDENCE = {
    "",
    "n/a",
    "na",
    "none",
    "pending",
    "todo",
    "tbd",
}


def _normalized(value: object) -> str:
    return str(value or "").strip()


def validate_sme_approval(
    release: dict[str, Any],
    *,
    actor: str,
    approval_evidence_ref: str,
) -> tuple[str, str]:
    """Validate the human approval boundary without pretending to verify review content.

    This function deliberately validates only auditable release mechanics:
    a named independent approver and a stable evidence reference. It does not
    claim that the referenced review is substantively correct; that remains a
    genuine human/SME responsibility.
    """

    approver = _normalized(actor)
    evidence_ref = _normalized(approval_evidence_ref)
    creator = _normalized(release.get("created_by"))

    if str(release.get("status") or "") != "qa_passed":
        raise ValueError("SME approval requires a qa_passed release")
    if not approver:
        raise ValueError("SME approver identity is required")
    if approver.casefold() in GENERIC_APPROVER_IDENTITIES:
        raise ValueError("SME approver must be a named independent reviewer, not a generic operator identity")
    if creator and approver.casefold() == creator.casefold():
        raise ValueError("SME approver must be independent from the release creator/import operator")
    if evidence_ref.casefold() in PLACEHOLDER_EVIDENCE:
        raise ValueError("Stable SME approval evidence is required")
    if len(evidence_ref) < 8:
        raise ValueError("SME approval evidence reference is too short to be auditable")
    if len(evidence_ref) > 1000:
        raise ValueError("SME approval evidence reference exceeds the supported audit length")

    return approver, evidence_ref


def _record_sme_evidence(
    release_id: int,
    *,
    approver: str,
    creator: str,
    evidence_ref: str,
) -> None:
    metadata = {
        "approval_evidence_ref": evidence_ref,
        "release_created_by": creator,
        "separation_of_duties": creator.casefold() != approver.casefold(),
    }
    encoded = json.dumps(metadata, separators=(",", ":"), sort_keys=True)

    with connect() as conn:
        existing = conn.execute(
            """
            SELECT 1
              FROM question_bank_release_events
             WHERE release_id=?
               AND action='sme_approval_evidence_submitted'
               AND actor=?
               AND metadata_json=?
             LIMIT 1
            """,
            (release_id, approver, encoded),
        ).fetchone()
        if existing:
            return
        conn.execute(
            """
            INSERT INTO question_bank_release_events(release_id,action,actor,metadata_json)
            VALUES (?, 'sme_approval_evidence_submitted', ?, ?)
            """,
            (release_id, approver, encoded),
        )


def promote_release_governed(
    release_key: str,
    target_status: str,
    *,
    actor: str = "system",
    approval_evidence_ref: str = "",
) -> dict[str, Any]:
    """Apply the operational release policy before changing release status.

    QA and staging transitions retain the existing state-machine behavior.
    SME approval additionally requires a named independent approver and a
    durable evidence reference that is recorded in the release audit trail.
    """

    if target_status != "sme_approved":
        return promote_release(release_key, target_status, actor=actor)

    release = get_release(release_key)
    approver, evidence_ref = validate_sme_approval(
        release,
        actor=actor,
        approval_evidence_ref=approval_evidence_ref,
    )
    creator = _normalized(release.get("created_by"))
    _record_sme_evidence(
        int(release["id"]),
        approver=approver,
        creator=creator,
        evidence_ref=evidence_ref,
    )
    return promote_release(release_key, target_status, actor=approver)
