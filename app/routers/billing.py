from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from ..auth import require_candidate
from ..billing.service import billing_public_config, create_checkout, process_stripe_webhook


router = APIRouter()


class CheckoutRequest(BaseModel):
    plan_code: str


@router.get("/billing/config")
def billing_config() -> dict:
    return billing_public_config()


@router.post("/billing/checkout")
def billing_checkout(payload: CheckoutRequest, candidate: dict = Depends(require_candidate)) -> dict:
    return create_checkout(candidate, payload.plan_code)


@router.post("/billing/webhook")
async def billing_webhook(request: Request) -> dict:
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")
    return process_stripe_webhook(payload, signature)
