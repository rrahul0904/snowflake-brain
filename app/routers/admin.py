from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ..admin_operations import audit, audit_log, deployments, finops, overview, question_bank, registrations, require_admin, subscriptions, system_status, usage, users
from ..auth import require_candidate

router = APIRouter(prefix="/admin", tags=["admin-operations"])


def _admin(candidate: dict = Depends(require_candidate)) -> dict:
    return require_admin(candidate)


@router.get("/overview")
def get_overview(candidate: dict = Depends(_admin)) -> dict:
    audit(candidate["id"], "admin.overview.viewed")
    return overview()


@router.get("/registrations")
def get_registrations(period: str = Query("daily", pattern="^(daily|weekly|monthly)$"), candidate: dict = Depends(_admin)) -> dict:
    return registrations(period)


@router.get("/users")
def get_users(page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100), plan: str = "", provider: str = "", active: str = "", candidate: dict = Depends(_admin)) -> dict:
    return users(page, page_size, {"plan": plan, "provider": provider, "active": active})


@router.get("/subscriptions")
def get_subscriptions(page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=100), candidate: dict = Depends(_admin)) -> dict:
    return subscriptions(page, page_size)


@router.get("/revenue")
def get_revenue(candidate: dict = Depends(_admin)) -> dict:
    data = subscriptions()["kpis"]
    return {"subscription_revenue": data["mrr"], "exam_pack_revenue": None, "refunds": None, "failed_payments": None, "net_revenue": data["mrr"], "evidence": "LOCAL_BILLING_RECORDS"}


@router.get("/usage")
def get_usage(candidate: dict = Depends(_admin)) -> dict:
    return usage()


@router.get("/finops")
def get_finops(page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=100), candidate: dict = Depends(_admin)) -> dict:
    return finops(page, page_size)


@router.get("/question-bank")
def get_question_bank(candidate: dict = Depends(_admin)) -> dict:
    return question_bank()


@router.get("/learning")
def get_learning(candidate: dict = Depends(_admin)) -> dict:
    return usage()


@router.get("/mocks")
def get_mocks(candidate: dict = Depends(_admin)) -> dict:
    data = overview()["learning"]
    return {"starts_today": data["mocks_started"], "completed_today": data["mocks_completed"], "stuck_active": 0, "submission_failures": 0}


@router.get("/auth")
def get_auth(candidate: dict = Depends(_admin)) -> dict:
    data = overview()["users"]
    return {"registrations_today": data["today"], "google_users": data["google"], "password_users": data["password"], "sensitive_logs_excluded": True}


@router.get("/system")
def get_system(candidate: dict = Depends(_admin)) -> dict:
    return system_status()


@router.get("/database")
def get_database(candidate: dict = Depends(_admin)) -> dict:
    data = system_status()
    return {"backend": data["database_backend"], "health": data["database"], "runtime_role": data["runtime_role"], "secrets_excluded": True}


@router.get("/deployments")
def get_deployments(page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=100), candidate: dict = Depends(_admin)) -> dict:
    return deployments(page, page_size)


@router.get("/audit")
def get_audit(page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=100), candidate: dict = Depends(_admin)) -> dict:
    return audit_log(page, page_size)


@router.get("/configuration")
def get_configuration(candidate: dict = Depends(_admin)) -> dict:
    data = system_status()
    return {"billing_enabled": data["billing"] == "enabled", "google_auth_enabled": data["google_auth"] == "enabled", "observability": data["observability"], "environment": data["database_backend"], "secrets_excluded": True}
