from app.services.governance_rules import status_from_active_punishments


def test_ban_wins_when_multiple_punishments_remain():
    assert status_from_active_punishments({"silence", "ban"}) == "banned"


def test_silence_remains_after_ban_is_revoked():
    assert status_from_active_punishments({"silence"}) == "silenced"


def test_user_is_active_when_no_punishment_remains():
    assert status_from_active_punishments(set()) == "active"
