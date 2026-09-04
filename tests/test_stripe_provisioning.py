from __future__ import annotations

from unittest.mock import patch

import pytest

import scripts.provision_stripe_billing as provision


def _products(*, livemode: bool = False) -> list[dict]:
    return [
        {
            "id": "product-premium-20",
            "active": True,
            "livemode": livemode,
            "default_price": "price-premium-20",
            "metadata": {"app": "snowflake-brain", "plan": "premium_20"},
        },
        {
            "id": "product-premium-40",
            "active": True,
            "livemode": livemode,
            "default_price": "price-premium-40",
            "metadata": {"app": "snowflake-brain", "plan": "premium_40"},
        },
        {
            "id": "product-premium-100",
            "active": True,
            "livemode": livemode,
            "default_price": "price-premium-100",
            "metadata": {"app": "snowflake-brain", "plan": "premium_100"},
        },
        {
            "id": "product-exam-pack",
            "active": True,
            "livemode": livemode,
            "default_price": "price-exam-pack",
            "metadata": {"app": "snowflake-brain", "plan": "exam_pack_35"},
        },
    ]


def _prices(*, livemode: bool = False) -> dict[str, dict]:
    return {
        "price-premium-20": {"active": True, "livemode": livemode, "currency": "usd", "unit_amount": 2000, "recurring": {"interval": "month"}},
        "price-premium-40": {"active": True, "livemode": livemode, "currency": "usd", "unit_amount": 4000, "recurring": {"interval": "month"}},
        "price-premium-100": {"active": True, "livemode": livemode, "currency": "usd", "unit_amount": 10000, "recurring": {"interval": "month"}},
        "price-exam-pack": {"active": True, "livemode": livemode, "currency": "usd", "unit_amount": 3500, "recurring": None},
    }


def _portal(*, livemode: bool = False) -> dict:
    return {
        "id": "portal-snowflake",
        "active": True,
        "livemode": livemode,
        "metadata": {"app": "snowflake-brain", "environment": "live" if livemode else "test"},
        "features": {
            "payment_method_update": {"enabled": True},
            "subscription_cancel": {"enabled": True, "mode": "at_period_end", "proration_behavior": "none"},
            "subscription_update": {"enabled": False},
            "invoice_history": {"enabled": True},
        },
    }


def test_catalog_discovery_enforces_exact_test_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(provision, "STRIPE_MODE", "test")
    prices = _prices(livemode=False)

    def fake_request(_client, _method, path, **_kwargs):
        if path == "/products":
            return {"data": _products(livemode=False)}
        return prices[path.removeprefix("/prices/")]

    with patch.object(provision, "stripe_request", side_effect=fake_request):
        resolved = provision.discover_catalog(object())

    assert resolved == {
        "STRIPE_PRICE_PREMIUM_100": "price-premium-20",
        "STRIPE_PRICE_PREMIUM_250": "price-premium-40",
        "STRIPE_PRICE_PREMIUM_500": "price-premium-100",
        "STRIPE_PRICE_EXAM_PACK": "price-exam-pack",
    }


def test_catalog_discovery_rejects_live_product_in_test_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(provision, "STRIPE_MODE", "test")

    def fake_request(_client, _method, path, **_kwargs):
        if path == "/products":
            return {"data": _products(livemode=True)}
        raise AssertionError("price lookup should not occur after mode mismatch")

    with patch.object(provision, "stripe_request", side_effect=fake_request):
        with pytest.raises(RuntimeError, match="mode mismatch"):
            provision.discover_catalog(object())


def test_catalog_discovery_rejects_wrong_amount(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(provision, "STRIPE_MODE", "test")
    prices = _prices(livemode=False)
    prices["price-premium-20"] = {**prices["price-premium-20"], "unit_amount": 1999}

    def fake_request(_client, _method, path, **_kwargs):
        if path == "/products":
            return {"data": _products(livemode=False)}
        return prices[path.removeprefix("/prices/")]

    with patch.object(provision, "stripe_request", side_effect=fake_request):
        with pytest.raises(RuntimeError, match="amount mismatch"):
            provision.discover_catalog(object())


def test_existing_webhook_fails_closed_without_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(provision, "STRIPE_MODE", "test")
    monkeypatch.setattr(provision, "STRIPE_WEBHOOK_URL", "https://preview.example.test/api/billing/webhook")
    monkeypatch.setattr(provision, "EXISTING_WEBHOOK_SECRET", "")

    webhook = {
        "id": "webhook-existing",
        "url": provision.STRIPE_WEBHOOK_URL,
        "status": "enabled",
        "livemode": False,
        "enabled_events": list(provision.WEBHOOK_EVENTS),
    }

    with patch.object(provision, "stripe_request", return_value={"data": [webhook]}):
        with pytest.raises(RuntimeError, match="signing secret is not available"):
            provision.reconcile_webhook(object())


def test_existing_webhook_is_reused_only_with_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(provision, "STRIPE_MODE", "test")
    monkeypatch.setattr(provision, "STRIPE_WEBHOOK_URL", "https://preview.example.test/api/billing/webhook")
    monkeypatch.setattr(provision, "EXISTING_WEBHOOK_SECRET", "secret-from-approved-store")

    webhook = {
        "id": "webhook-existing",
        "url": provision.STRIPE_WEBHOOK_URL,
        "status": "enabled",
        "livemode": False,
        "enabled_events": list(provision.WEBHOOK_EVENTS),
    }

    with patch.object(provision, "stripe_request", return_value={"data": [webhook]}):
        secret, created = provision.reconcile_webhook(object())

    assert secret == "secret-from-approved-store"
    assert created is False


def test_existing_app_portal_is_reused_when_launch_policy_is_safe(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(provision, "STRIPE_MODE", "test")
    with patch.object(provision, "stripe_request", return_value={"data": [_portal(livemode=False)]}):
        portal_id, created = provision.reconcile_portal_configuration(object())

    assert portal_id == "portal-snowflake"
    assert created is False


def test_portal_rejects_plan_switching_at_launch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(provision, "STRIPE_MODE", "test")
    unsafe = _portal(livemode=False)
    unsafe["features"]["subscription_update"]["enabled"] = True

    with patch.object(provision, "stripe_request", return_value={"data": [unsafe]}):
        with pytest.raises(RuntimeError, match="plan switching must remain disabled"):
            provision.reconcile_portal_configuration(object())
