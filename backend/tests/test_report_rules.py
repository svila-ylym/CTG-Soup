import pytest

from app.services.governance_rules import GovernanceError, decide_report


def test_decide_pending_report_records_handler_result_and_time():
    result = decide_report(
        {"status": "pending"},
        handler_uid=8,
        accepted=True,
        result="已处理",
        now="2026-08-08T10:00:00Z",
    )
    assert result == {
        "status": "processed",
        "handler_uid": 8,
        "handle_result": "已处理",
        "handled_at": "2026-08-08T10:00:00Z",
    }


def test_decide_report_can_reject_with_reason():
    result = decide_report({"status": "pending"}, handler_uid=8, accepted=False, result="证据不足", now="now")
    assert result["status"] == "rejected"


def test_decide_report_rejects_duplicate_decision():
    with pytest.raises(GovernanceError, match="已处理"):
        decide_report({"status": "processed"}, handler_uid=8, accepted=True, result="重复", now="now")
