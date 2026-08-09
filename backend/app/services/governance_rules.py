"""Pure authorization and reversible-punishment rules."""
from typing import Any, Mapping


class GovernanceError(ValueError):
    pass


def can_manage_role(operator_role: str, target_role: str) -> bool:
    if operator_role == "root":
        return True
    return operator_role == "admin" and target_role == "user"


def revoke_punishment(
    punishment: Mapping[str, Any], *, actor_uid: int, reason: str, now: Any
) -> dict[str, Any]:
    if punishment.get("is_revoked"):
        raise GovernanceError("处罚已撤销")
    if not reason.strip():
        raise GovernanceError("撤销原因不能为空")
    return {
        "is_revoked": True,
        "revoked_by": actor_uid,
        "revoke_reason": reason.strip(),
        "revoked_at": now,
    }


def decide_report(
    report: Mapping[str, Any], *, handler_uid: int, accepted: bool, result: str, now: Any
) -> dict[str, Any]:
    if report.get("status") != "pending":
        raise GovernanceError("举报已处理")
    if not result.strip():
        raise GovernanceError("处理结果不能为空")
    return {
        "status": "processed" if accepted else "rejected",
        "handler_uid": handler_uid,
        "handle_result": result.strip(),
        "handled_at": now,
    }


def status_from_active_punishments(types: set[str]) -> str:
    if "ban" in types:
        return "banned"
    if "silence" in types:
        return "silenced"
    return "active"
