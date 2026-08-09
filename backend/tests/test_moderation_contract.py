from datetime import datetime

from app.schemas import PunishmentCreate, ReportResponse


def test_punishment_contract_uses_canonical_uids():
    item = PunishmentCreate(target_uid=9, punishment_type="silence", reason="违规")
    assert item.target_uid == 9


def test_report_response_uses_canonical_uids():
    item = ReportResponse(
        id=1, reporter_uid=3, target_type="soup", target_id=4,
        reason="违规", status="pending", created_at=datetime(2026, 8, 8)
    )
    assert item.reporter_uid == 3
    assert item.handler_uid is None
