import pytest

from app.services.governance_rules import (
    GovernanceError,
    can_manage_role,
    revoke_punishment,
)


@pytest.mark.parametrize(
    ("operator", "target", "allowed"),
    [
        ("root", "root", True),
        ("root", "admin", True),
        ("root", "user", True),
        ("admin", "root", False),
        ("admin", "admin", False),
        ("admin", "user", True),
        ("user", "user", False),
    ],
)
def test_role_hierarchy(operator, target, allowed):
    assert can_manage_role(operator, target) is allowed


def test_revoke_punishment_records_actor_reason_and_time():
    state = {"is_revoked": False}
    result = revoke_punishment(state, actor_uid=7, reason="证据不足", now="2026-08-07T12:00:00Z")
    assert result == {
        "is_revoked": True,
        "revoked_by": 7,
        "revoke_reason": "证据不足",
        "revoked_at": "2026-08-07T12:00:00Z",
    }


def test_cannot_revoke_punishment_twice():
    with pytest.raises(GovernanceError, match="已撤销"):
        revoke_punishment({"is_revoked": True}, actor_uid=7, reason="重复", now="now")
