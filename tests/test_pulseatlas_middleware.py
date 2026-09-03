from app.pulseatlas_middleware import event_for_request


def test_pulseatlas_maps_only_safe_route_outcomes():
    assert event_for_request("GET", "/api/health", 200) == (
        "health_check", "health", {"component": "snowflake-brain", "status": "ok"}
    )
    assert event_for_request("POST", "/api/quiz/grade", 200) == (
        "practice_session_completed", "product", {"mode": "practice"}
    )
    assert event_for_request("POST", "/api/mock/sessions/123/submit", 200) == (
        "mock_completed", "product", {}
    )
    assert event_for_request("POST", "/api/questions/private-id/attempt", 200) is None
    assert event_for_request("POST", "/api/quiz/grade", 400) is None
