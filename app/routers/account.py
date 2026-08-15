from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ..account_lifecycle import (
    AccountDeletionBlocked,
    AccountLifecycleError,
    account_export_payload,
    account_status,
    change_password,
    confirm_email_change,
    confirm_email_verification,
    confirm_password_reset,
    delete_account,
    list_identities,
    request_email_change,
    request_password_reset,
    resend_email_verification,
    unlink_identity,
)
from ..auth import COOKIE_NAME, get_current_candidate
from ..config import AUTH_COOKIE_SECURE


router = APIRouter(tags=["account-lifecycle"])


class TokenRequest(BaseModel):
    token: str


class PasswordResetRequest(BaseModel):
    email: str


class PasswordResetConfirmRequest(BaseModel):
    token: str
    new_password: str


class ChangePasswordRequest(BaseModel):
    current_password: str | None = None
    new_password: str


class ChangeEmailRequest(BaseModel):
    new_email: str


class DeleteAccountRequest(BaseModel):
    confirmation: str
    password: str | None = None


def _candidate_id(candidate: dict[str, Any]) -> int:
    return int(candidate["id"])


def _lifecycle_error(exc: AccountLifecycleError, status_code: int = 400) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": "account_lifecycle_error", "message": str(exc)})


@router.get("/account/status")
def status(candidate: dict[str, Any] = Depends(get_current_candidate)) -> dict[str, Any]:
    try:
        return account_status(_candidate_id(candidate))
    except AccountLifecycleError as exc:
        raise _lifecycle_error(exc) from exc


@router.post("/account/email-verification/resend")
def resend_verification(candidate: dict[str, Any] = Depends(get_current_candidate)) -> dict[str, Any]:
    try:
        return resend_email_verification(_candidate_id(candidate))
    except AccountLifecycleError as exc:
        raise _lifecycle_error(exc) from exc


@router.post("/auth/email-verification/confirm")
def verify_email(payload: TokenRequest) -> dict[str, Any]:
    try:
        return confirm_email_verification(payload.token)
    except AccountLifecycleError as exc:
        raise _lifecycle_error(exc) from exc


@router.post("/auth/password-reset/request", status_code=202)
def password_reset_request(payload: PasswordResetRequest) -> dict[str, Any]:
    # The service intentionally returns the same shape for known and unknown
    # email addresses so this endpoint cannot be used for account enumeration.
    return request_password_reset(payload.email)


@router.post("/auth/password-reset/confirm")
def password_reset_confirm(payload: PasswordResetConfirmRequest, response: Response) -> dict[str, Any]:
    try:
        result = confirm_password_reset(payload.token, payload.new_password)
    except AccountLifecycleError as exc:
        raise _lifecycle_error(exc) from exc
    response.delete_cookie(COOKIE_NAME, path="/", secure=AUTH_COOKIE_SECURE, samesite="lax")
    return result


@router.post("/account/change-password")
def password_change(
    payload: ChangePasswordRequest,
    response: Response,
    candidate: dict[str, Any] = Depends(get_current_candidate),
) -> dict[str, Any]:
    try:
        result = change_password(_candidate_id(candidate), payload.current_password, payload.new_password)
    except AccountLifecycleError as exc:
        raise _lifecycle_error(exc) from exc
    response.delete_cookie(COOKIE_NAME, path="/", secure=AUTH_COOKIE_SECURE, samesite="lax")
    return result


@router.post("/account/change-email/request")
def email_change_request(
    payload: ChangeEmailRequest,
    candidate: dict[str, Any] = Depends(get_current_candidate),
) -> dict[str, Any]:
    try:
        return request_email_change(_candidate_id(candidate), payload.new_email)
    except AccountLifecycleError as exc:
        raise _lifecycle_error(exc) from exc


@router.post("/auth/change-email/confirm")
def email_change_confirm(payload: TokenRequest, response: Response) -> dict[str, Any]:
    try:
        result = confirm_email_change(payload.token)
    except AccountLifecycleError as exc:
        raise _lifecycle_error(exc) from exc
    response.delete_cookie(COOKIE_NAME, path="/", secure=AUTH_COOKIE_SECURE, samesite="lax")
    return result


@router.get("/account/identities")
def identities(candidate: dict[str, Any] = Depends(get_current_candidate)) -> list[dict[str, Any]]:
    return list_identities(_candidate_id(candidate))


@router.delete("/account/identities/{identity_id}")
def identity_unlink(identity_id: int, candidate: dict[str, Any] = Depends(get_current_candidate)) -> dict[str, Any]:
    try:
        return unlink_identity(_candidate_id(candidate), identity_id)
    except AccountLifecycleError as exc:
        raise _lifecycle_error(exc) from exc


@router.get("/account/export")
def export_account(candidate: dict[str, Any] = Depends(get_current_candidate)) -> JSONResponse:
    try:
        payload = account_export_payload(_candidate_id(candidate))
    except AccountLifecycleError as exc:
        raise _lifecycle_error(exc) from exc
    response = JSONResponse(payload)
    response.headers["Content-Disposition"] = 'attachment; filename="snowflake-certification-account-export.json"'
    response.headers["Cache-Control"] = "private, no-store"
    return response


@router.delete("/account")
def remove_account(
    payload: DeleteAccountRequest,
    candidate: dict[str, Any] = Depends(get_current_candidate),
) -> JSONResponse:
    try:
        result = delete_account(
            _candidate_id(candidate),
            confirmation=payload.confirmation,
            password=payload.password,
        )
    except AccountDeletionBlocked as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    except AccountLifecycleError as exc:
        raise _lifecycle_error(exc) from exc
    response = JSONResponse(result)
    response.delete_cookie(COOKIE_NAME, path="/", secure=AUTH_COOKIE_SECURE, samesite="lax")
    response.headers["Cache-Control"] = "private, no-store"
    return response
