from datetime import datetime
from types import SimpleNamespace

from app.schemas import UserResponse


def test_user_response_matches_canonical_user_model():
    user = SimpleNamespace(
        uid=42,
        username="测试用户",
        nickname="小龟",
        email="user@example.com",
        role="user",
        status="active",
        avatar_url=None,
        bio=None,
        points=15,
        consecutive_signin_days=3,
        created_at=datetime(2026, 8, 8),
    )

    response = UserResponse.model_validate(user)

    assert response.uid == 42
    assert response.points == 15
    assert not hasattr(response, "id")
