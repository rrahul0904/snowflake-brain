from __future__ import annotations

from typing import Protocol


class BillingProvider(Protocol):
    name: str

    def create_customer(self, *, email: str, candidate_id: int) -> str: ...

    def create_checkout_session(
        self,
        *,
        customer_id: str,
        candidate_id: int,
        plan_code: str,
        price_id: str,
        mode: str,
        success_url: str,
        cancel_url: str,
    ) -> dict: ...

    def verify_webhook(self, payload: bytes, signature_header: str) -> dict: ...
