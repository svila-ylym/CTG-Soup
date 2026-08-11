"""Phase-based entry point for the social-platform schema upgrades."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from typing import Callable, Sequence

from sqlalchemy import Text, inspect, text
from sqlalchemy.engine import Engine

from app.db import engine as default_engine
from app.migrations.competition_groups import ensure_competition_group_schema
from app.migrations.finalize_schema import finalize_schema
from app.migrations.soup_metadata import ensure_soup_metadata_schema


@dataclass(frozen=True)
class UpgradeReport:
    actions: tuple[str, ...]
    applied: bool
    counts: dict[str, int]


@dataclass(frozen=True)
class PhaseUpgradeResult:
    actions: tuple[str, ...]
    counts: dict[str, int]


PhaseUpgrade = Callable[[Engine, bool], PhaseUpgradeResult]


def _upgrade_foundation(engine: Engine, dry_run: bool) -> PhaseUpgradeResult:
    root_actions, promoted_root_users = _promote_skyunreal(engine, dry_run)
    metadata_report = ensure_soup_metadata_schema(engine, dry_run=dry_run)
    people_actions = _upgrade_people_columns(engine, dry_run)
    schema_report = finalize_schema(engine, dry_run=dry_run)
    competition_group_report = ensure_competition_group_schema(engine, dry_run=dry_run)
    return PhaseUpgradeResult(
        actions=(
            root_actions
            + metadata_report.actions
            + people_actions
            + schema_report.actions
            + competition_group_report.actions
        ),
        counts={"promoted_root_users": promoted_root_users},
    )


def _promote_skyunreal(engine: Engine, dry_run: bool) -> tuple[tuple[str, ...], int]:
    if "users" not in inspect(engine).get_table_names():
        return (), 0

    with engine.connect() as connection:
        matches = connection.execute(
            text(
                "SELECT uid, username, role FROM users "
                "WHERE username = :username"
            ),
            {"username": "SkyUnreal"},
        ).mappings().all()

    if not matches:
        raise RuntimeError("required user SkyUnreal was not found")
    if len(matches) != 1:
        raise RuntimeError("multiple users have the exact username SkyUnreal")

    user = matches[0]
    if user["role"] in {"root", "ROOT"}:
        return (), 0

    stored_root_role = "ROOT" if str(user["role"]).isupper() else "root"
    actions = (
        f"PROMOTE users uid={user['uid']} username=SkyUnreal role=root",
    )
    if dry_run:
        return actions, 1

    with engine.begin() as connection:
        result = connection.execute(
            text(
                "UPDATE users SET role = :role "
                "WHERE uid = :uid AND username = :username AND role != :role"
            ),
            {
                "uid": user["uid"],
                "username": "SkyUnreal",
                "role": stored_root_role,
            },
        )
        if result.rowcount != 1:
            raise RuntimeError("SkyUnreal role changed during migration")
    return actions, 1


def _upgrade_people_columns(engine: Engine, dry_run: bool) -> tuple[str, ...]:
    inspector = inspect(engine)
    if "soups" not in inspector.get_table_names():
        return ()
    people_columns = {"main_player_count", "secondary_player_count"}
    pending = tuple(
        column["name"]
        for column in inspector.get_columns("soups")
        if column["name"] in people_columns and not isinstance(column["type"], Text)
    )
    if not pending:
        return ()

    actions = ("CONVERT soups people count columns to TEXT",)
    if dry_run:
        return actions

    with engine.begin() as connection:
        if engine.dialect.name == "postgresql":
            for column in pending:
                connection.execute(
                    text(f"ALTER TABLE soups ALTER COLUMN {column} DROP DEFAULT")
                )
                connection.execute(
                    text(
                        f"ALTER TABLE soups ALTER COLUMN {column} "
                        f"TYPE TEXT USING {column}::text"
                    )
                )
                connection.execute(
                    text(f"UPDATE soups SET {column} = '' WHERE {column} IS NULL")
                )
                connection.execute(
                    text(f"ALTER TABLE soups ALTER COLUMN {column} SET DEFAULT ''")
                )
                connection.execute(
                    text(f"ALTER TABLE soups ALTER COLUMN {column} SET NOT NULL")
                )
        elif engine.dialect.name == "sqlite":
            for column in pending:
                temporary = f"__social_{column}_text"
                connection.execute(
                    text(
                        f"ALTER TABLE soups ADD COLUMN {temporary} "
                        "TEXT NOT NULL DEFAULT ''"
                    )
                )
                connection.execute(
                    text(
                        f"UPDATE soups SET {temporary} = "
                        f"COALESCE(CAST({column} AS TEXT), '')"
                    )
                )
                connection.execute(text(f"ALTER TABLE soups DROP COLUMN {column}"))
                connection.execute(
                    text(
                        f"ALTER TABLE soups RENAME COLUMN {temporary} TO {column}"
                    )
                )
        else:
            raise RuntimeError(
                f"unsupported database dialect for people column migration: "
                f"{engine.dialect.name}"
            )
    return actions


def _upgrade_accounts(engine: Engine, dry_run: bool) -> PhaseUpgradeResult:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    if "users" not in table_names:
        return PhaseUpgradeResult(
            actions=(),
            counts={"created_account_tables": 0, "created_account_columns": 0},
        )

    actions: list[str] = []
    create_assets_table = "uploaded_assets" not in table_names
    if create_assets_table:
        actions.append("CREATE TABLE uploaded_assets")

    user_columns = {
        column["name"] for column in inspector.get_columns("users")
    }
    account_columns = {
        "allow_bulk_email": "BOOLEAN NOT NULL DEFAULT FALSE",
        "theme_preference": "VARCHAR(10) NOT NULL DEFAULT 'system'",
        "token_version": "INTEGER NOT NULL DEFAULT 0",
        "avatar_asset_id": "INTEGER REFERENCES uploaded_assets(id)",
    }
    missing_columns = tuple(
        name for name in account_columns if name not in user_columns
    )
    actions.extend(f"ADD users.{name}" for name in missing_columns)

    user_indexes = {index["name"] for index in inspector.get_indexes("users")}
    create_bulk_email_index = (
        "allow_bulk_email" not in missing_columns
        and "ix_users_allow_bulk_email" not in user_indexes
    ) or "allow_bulk_email" in missing_columns
    if create_bulk_email_index:
        actions.append("CREATE INDEX ix_users_allow_bulk_email")

    if not dry_run and actions:
        with engine.begin() as connection:
            if create_assets_table:
                id_column = (
                    "INTEGER PRIMARY KEY AUTOINCREMENT"
                    if engine.dialect.name == "sqlite"
                    else "SERIAL PRIMARY KEY"
                )
                connection.execute(
                    text(
                        "CREATE TABLE uploaded_assets ("
                        f"id {id_column}, "
                        "owner_uid INTEGER NOT NULL REFERENCES users(uid), "
                        "kind VARCHAR(32) NOT NULL DEFAULT 'image', "
                        "storage_key VARCHAR(500) NOT NULL UNIQUE, "
                        "public_url VARCHAR(1000) NOT NULL, "
                        "mime_type VARCHAR(100) NOT NULL, "
                        "size INTEGER NOT NULL, "
                        "created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP"
                        ")"
                    )
                )
                connection.execute(
                    text(
                        "CREATE INDEX ix_uploaded_assets_owner_uid "
                        "ON uploaded_assets (owner_uid)"
                    )
                )
                connection.execute(
                    text(
                        "CREATE INDEX ix_uploaded_assets_kind "
                        "ON uploaded_assets (kind)"
                    )
                )
                connection.execute(
                    text(
                        "CREATE INDEX ix_uploaded_assets_created_at "
                        "ON uploaded_assets (created_at)"
                    )
                )
            for name in missing_columns:
                connection.execute(
                    text(
                        f"ALTER TABLE users ADD COLUMN {name} "
                        f"{account_columns[name]}"
                    )
                )
            if create_bulk_email_index:
                connection.execute(
                    text(
                        "CREATE INDEX ix_users_allow_bulk_email "
                        "ON users (allow_bulk_email)"
                    )
                )

    return PhaseUpgradeResult(
        actions=tuple(actions),
        counts={
            "created_account_tables": int(create_assets_table),
            "created_account_columns": len(missing_columns),
        },
    )


def _upgrade_community(engine: Engine, dry_run: bool) -> PhaseUpgradeResult:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    if "users" not in table_names:
        return PhaseUpgradeResult(
            actions=(),
            counts={
                "created_community_tables": 0,
                "created_signin_tables": 0,
                "created_signin_columns": 0,
            },
        )

    create_featured_soups = (
        "soups" in table_names and "featured_soups" not in table_names
    )
    create_signin_records = "signin_records" not in table_names
    create_mentions = (
        {"notifications", "comments"} <= table_names
        and "mentions" not in table_names
    )
    signin_columns = (
        {column["name"] for column in inspector.get_columns("signin_records")}
        if "signin_records" in table_names
        else set()
    )
    add_signin_day = (
        not create_signin_records
        and "signin_records" in table_names
        and "signin_day" not in signin_columns
    )
    drop_legacy_signin_date = (
        not create_signin_records
        and "signin_records" in table_names
        and "signin_date" in signin_columns
    )
    signin_unique = False
    if "signin_records" in table_names and not add_signin_day:
        expected = {"user_uid", "signin_day"}
        signin_unique = any(
            set(constraint.get("column_names") or ()) == expected
            for constraint in inspector.get_unique_constraints("signin_records")
        ) or any(
            index.get("unique")
            and set(index.get("column_names") or ()) == expected
            for index in inspector.get_indexes("signin_records")
        )
    add_signin_unique = (
        not create_signin_records
        and (add_signin_day or not signin_unique)
    )

    actions = list(
        action
        for action, needed in (
            ("CREATE TABLE featured_soups", create_featured_soups),
            ("CREATE TABLE signin_records", create_signin_records),
            ("ADD signin_records.signin_day", add_signin_day),
            ("ADD UNIQUE uq_signin_user_day", add_signin_unique),
            ("DROP signin_records.signin_date", drop_legacy_signin_date),
            ("CREATE TABLE mentions", create_mentions),
        )
        if needed
    )
    if not dry_run and actions:
        id_column = (
            "INTEGER PRIMARY KEY AUTOINCREMENT"
            if engine.dialect.name == "sqlite"
            else "SERIAL PRIMARY KEY"
        )
        with engine.begin() as connection:
            if create_featured_soups:
                connection.execute(
                    text(
                        "CREATE TABLE featured_soups ("
                        f"id {id_column}, "
                        "user_uid INTEGER NOT NULL REFERENCES users(uid), "
                        "soup_id INTEGER NOT NULL REFERENCES soups(id), "
                        "position INTEGER NOT NULL, "
                        "created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, "
                        "CONSTRAINT uq_featured_soups_user_soup "
                        "UNIQUE (user_uid, soup_id), "
                        "CONSTRAINT uq_featured_soups_user_position "
                        "UNIQUE (user_uid, position), "
                        "CONSTRAINT ck_featured_soups_position "
                        "CHECK (position >= 0 AND position < 5)"
                        ")"
                    )
                )
                connection.execute(
                    text(
                        "CREATE INDEX ix_featured_soups_user_uid "
                        "ON featured_soups (user_uid)"
                    )
                )
                connection.execute(
                    text(
                        "CREATE INDEX ix_featured_soups_soup_id "
                        "ON featured_soups (soup_id)"
                    )
                )
            if create_signin_records:
                connection.execute(
                    text(
                        "CREATE TABLE signin_records ("
                        f"id {id_column}, "
                        "user_uid INTEGER NOT NULL REFERENCES users(uid), "
                        "signin_day DATE NOT NULL, "
                        "points_earned INTEGER NOT NULL DEFAULT 10, "
                        "CONSTRAINT uq_signin_user_day "
                        "UNIQUE (user_uid, signin_day)"
                        ")"
                    )
                )
                connection.execute(
                    text(
                        "CREATE INDEX ix_signin_records_user_uid "
                        "ON signin_records (user_uid)"
                    )
                )
                connection.execute(
                    text(
                        "CREATE INDEX ix_signin_records_signin_day "
                        "ON signin_records (signin_day)"
                    )
                )
            if add_signin_day:
                connection.execute(
                    text("ALTER TABLE signin_records ADD COLUMN signin_day DATE")
                )
                if "signin_date" in signin_columns:
                    cast_expression = (
                        "DATE(signin_date)"
                        if engine.dialect.name == "sqlite"
                        else "CAST(signin_date AS DATE)"
                    )
                    connection.execute(
                        text(
                            "UPDATE signin_records SET signin_day = "
                            f"{cast_expression} WHERE signin_day IS NULL"
                        )
                    )
                else:
                    connection.execute(
                        text(
                            "UPDATE signin_records SET signin_day = CURRENT_DATE "
                            "WHERE signin_day IS NULL"
                        )
                    )
                if engine.dialect.name == "postgresql":
                    connection.execute(
                        text(
                            "ALTER TABLE signin_records "
                            "ALTER COLUMN signin_day SET NOT NULL"
                        )
                    )
                connection.execute(
                    text(
                        "CREATE INDEX ix_signin_records_signin_day "
                        "ON signin_records (signin_day)"
                    )
                )
            if add_signin_unique:
                connection.execute(
                    text(
                        "DELETE FROM signin_records WHERE id IN ("
                        "SELECT id FROM ("
                        "SELECT id, ROW_NUMBER() OVER ("
                        "PARTITION BY user_uid, signin_day ORDER BY id DESC"
                        ") AS duplicate_rank FROM signin_records"
                        ") AS ranked WHERE duplicate_rank > 1)"
                    )
                )
                connection.execute(
                    text(
                        "CREATE UNIQUE INDEX uq_signin_user_day "
                        "ON signin_records (user_uid, signin_day)"
                    )
                )
            if drop_legacy_signin_date:
                connection.execute(
                    text("ALTER TABLE signin_records DROP COLUMN signin_date")
                )
            if create_mentions:
                connection.execute(
                    text(
                        "CREATE TABLE mentions ("
                        f"id {id_column}, "
                        "actor_uid INTEGER NOT NULL REFERENCES users(uid), "
                        "mentioned_uid INTEGER NOT NULL REFERENCES users(uid), "
                        "target_type VARCHAR(20) NOT NULL, "
                        "target_id INTEGER NOT NULL, "
                        "start_offset INTEGER NOT NULL, "
                        "end_offset INTEGER NOT NULL, "
                        "created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, "
                        "CONSTRAINT uq_mentions_recipient_target UNIQUE ("
                        "mentioned_uid, target_type, target_id)"
                        ")"
                    )
                )
                for column in ("actor_uid", "mentioned_uid", "target_id"):
                    connection.execute(
                        text(
                            f"CREATE INDEX ix_mentions_{column} "
                            f"ON mentions ({column})"
                        )
                    )
    return PhaseUpgradeResult(
        actions=tuple(actions),
        counts={
            "created_community_tables": int(create_featured_soups),
            "created_signin_tables": int(create_signin_records),
            "created_signin_columns": int(add_signin_day),
            "created_mention_tables": int(create_mentions),
        },
    )


def _upgrade_chat(engine: Engine, dry_run: bool) -> PhaseUpgradeResult:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    if not {"users", "private_messages"} <= table_names:
        return PhaseUpgradeResult(
            actions=(),
            counts={"created_chat_tables": 0, "backfilled_conversations": 0},
        )

    create_conversations = "direct_conversations" not in table_names
    message_columns = {
        column["name"] for column in inspector.get_columns("private_messages")
    }
    add_conversation_id = "conversation_id" not in message_columns
    unmapped_filter = "" if add_conversation_id else "AND conversation_id IS NULL"
    with engine.connect() as connection:
        pairs = connection.execute(
            text(
                "SELECT DISTINCT "
                "CASE WHEN sender_uid < receiver_uid THEN sender_uid ELSE receiver_uid END AS low_uid, "
                "CASE WHEN sender_uid < receiver_uid THEN receiver_uid ELSE sender_uid END AS high_uid "
                "FROM private_messages WHERE sender_uid != receiver_uid "
                f"{unmapped_filter}"
            )
        ).all()

    actions: list[str] = []
    if create_conversations:
        actions.append("CREATE TABLE direct_conversations")
    if add_conversation_id:
        actions.append("ADD private_messages.conversation_id")
    if pairs:
        actions.append(f"BACKFILL {len(pairs)} direct conversation(s)")

    if not dry_run and actions:
        id_column = (
            "INTEGER PRIMARY KEY AUTOINCREMENT"
            if engine.dialect.name == "sqlite"
            else "SERIAL PRIMARY KEY"
        )
        with engine.begin() as connection:
            if create_conversations:
                connection.execute(
                    text(
                        "CREATE TABLE direct_conversations ("
                        f"id {id_column}, "
                        "low_uid INTEGER NOT NULL REFERENCES users(uid), "
                        "high_uid INTEGER NOT NULL REFERENCES users(uid), "
                        "last_message_at TIMESTAMP, "
                        "created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, "
                        "CONSTRAINT uq_direct_conversation_pair "
                        "UNIQUE (low_uid, high_uid), "
                        "CONSTRAINT ck_direct_conversation_order "
                        "CHECK (low_uid < high_uid)"
                        ")"
                    )
                )
                for column in ("low_uid", "high_uid", "last_message_at"):
                    connection.execute(
                        text(
                            f"CREATE INDEX ix_direct_conversations_{column} "
                            f"ON direct_conversations ({column})"
                        )
                    )
            if add_conversation_id:
                connection.execute(
                    text(
                        "ALTER TABLE private_messages ADD COLUMN conversation_id "
                        "INTEGER REFERENCES direct_conversations(id)"
                    )
                )
                connection.execute(
                    text(
                        "CREATE INDEX ix_private_messages_conversation_id "
                        "ON private_messages (conversation_id)"
                    )
                )
            for low_uid, high_uid in pairs:
                parameters = {"low_uid": low_uid, "high_uid": high_uid}
                conversation_id = connection.execute(
                    text(
                        "SELECT id FROM direct_conversations "
                        "WHERE low_uid = :low_uid AND high_uid = :high_uid"
                    ),
                    parameters,
                ).scalar_one_or_none()
                last_message_at = connection.execute(
                    text(
                        "SELECT MAX(created_at) FROM private_messages WHERE "
                        "(sender_uid = :low_uid AND receiver_uid = :high_uid) OR "
                        "(sender_uid = :high_uid AND receiver_uid = :low_uid)"
                    ),
                    parameters,
                ).scalar_one()
                if conversation_id is None:
                    conversation_id = connection.execute(
                        text(
                            "INSERT INTO direct_conversations "
                            "(low_uid, high_uid, last_message_at) "
                            "VALUES (:low_uid, :high_uid, :last_message_at) "
                            "RETURNING id"
                        ),
                        {**parameters, "last_message_at": last_message_at},
                    ).scalar_one()
                else:
                    connection.execute(
                        text(
                            "UPDATE direct_conversations "
                            "SET last_message_at = :last_message_at "
                            "WHERE id = :conversation_id"
                        ),
                        {
                            "last_message_at": last_message_at,
                            "conversation_id": conversation_id,
                        },
                    )
                connection.execute(
                    text(
                        "UPDATE private_messages "
                        "SET conversation_id = :conversation_id WHERE "
                        "(sender_uid = :low_uid AND receiver_uid = :high_uid) OR "
                        "(sender_uid = :high_uid AND receiver_uid = :low_uid)"
                    ),
                    {**parameters, "conversation_id": conversation_id},
                )

    return PhaseUpgradeResult(
        actions=tuple(actions),
        counts={
            "created_chat_tables": int(create_conversations),
            "backfilled_conversations": len(pairs),
        },
    )


def _upgrade_broadcast(engine: Engine, dry_run: bool) -> PhaseUpgradeResult:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    if "users" not in table_names:
        return PhaseUpgradeResult(
            actions=(),
            counts={"created_broadcast_tables": 0},
        )

    create_messages = "system_messages" not in table_names
    create_recipients = "system_message_recipients" not in table_names
    create_attachments = "message_attachments" not in table_names
    create_campaigns = "email_campaigns" not in table_names
    create_campaign_recipients = "email_campaign_recipients" not in table_names
    create_campaign_attachments = "email_campaign_attachments" not in table_names
    actions = tuple(
        action
        for action, needed in (
            ("CREATE TABLE system_messages", create_messages),
            ("CREATE TABLE system_message_recipients", create_recipients),
            ("CREATE TABLE message_attachments", create_attachments),
            ("CREATE TABLE email_campaigns", create_campaigns),
            ("CREATE TABLE email_campaign_recipients", create_campaign_recipients),
            ("CREATE TABLE email_campaign_attachments", create_campaign_attachments),
        )
        if needed
    )
    if not dry_run and actions:
        id_column = (
            "INTEGER PRIMARY KEY AUTOINCREMENT"
            if engine.dialect.name == "sqlite"
            else "SERIAL PRIMARY KEY"
        )
        with engine.begin() as connection:
            if create_messages:
                connection.execute(
                    text(
                        "CREATE TABLE system_messages ("
                        f"id {id_column}, "
                        "sender_uid INTEGER NOT NULL REFERENCES users(uid), "
                        "title VARCHAR(200) NOT NULL, "
                        "markdown TEXT NOT NULL, "
                        "rendered_html TEXT NOT NULL, "
                        "recipient_mode VARCHAR(10) NOT NULL, "
                        "created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP"
                        ")"
                    )
                )
                connection.execute(
                    text(
                        "CREATE INDEX ix_system_messages_sender_uid "
                        "ON system_messages (sender_uid)"
                    )
                )
                connection.execute(
                    text(
                        "CREATE INDEX ix_system_messages_created_at "
                        "ON system_messages (created_at)"
                    )
                )
            if create_recipients:
                connection.execute(
                    text(
                        "CREATE TABLE system_message_recipients ("
                        f"id {id_column}, "
                        "system_message_id INTEGER NOT NULL "
                        "REFERENCES system_messages(id), "
                        "user_uid INTEGER NOT NULL REFERENCES users(uid), "
                        "delivered_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, "
                        "read_at TIMESTAMP, "
                        "CONSTRAINT uq_system_message_recipient "
                        "UNIQUE (system_message_id, user_uid)"
                        ")"
                    )
                )
                connection.execute(
                    text(
                        "CREATE INDEX ix_system_message_recipients_message "
                        "ON system_message_recipients (system_message_id)"
                    )
                )
                connection.execute(
                    text(
                        "CREATE INDEX ix_system_message_recipients_user "
                        "ON system_message_recipients (user_uid)"
                    )
                )
            if create_attachments:
                connection.execute(
                    text(
                        "CREATE TABLE message_attachments ("
                        f"id {id_column}, "
                        "uploader_uid INTEGER NOT NULL REFERENCES users(uid), "
                        "system_message_id INTEGER REFERENCES system_messages(id), "
                        "storage_key VARCHAR(500) NOT NULL UNIQUE, "
                        "original_name VARCHAR(255) NOT NULL, "
                        "mime_type VARCHAR(100) NOT NULL, "
                        "size INTEGER NOT NULL, "
                        "sha256 VARCHAR(64) NOT NULL, "
                        "created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP"
                        ")"
                    )
                )
                for column in ("uploader_uid", "system_message_id", "created_at"):
                    connection.execute(
                        text(
                            f"CREATE INDEX ix_message_attachments_{column} "
                            f"ON message_attachments ({column})"
                        )
                    )
            if create_campaigns:
                connection.execute(
                    text(
                        "CREATE TABLE email_campaigns ("
                        f"id {id_column}, "
                        "creator_uid INTEGER NOT NULL REFERENCES users(uid), "
                        "subject VARCHAR(200) NOT NULL, "
                        "markdown TEXT NOT NULL, "
                        "rendered_html TEXT NOT NULL, "
                        "category VARCHAR(10) NOT NULL, "
                        "recipient_mode VARCHAR(10) NOT NULL, "
                        "recipient_uids JSON NOT NULL DEFAULT '[]', "
                        "attachment_ids JSON NOT NULL DEFAULT '[]', "
                        "status VARCHAR(10) NOT NULL DEFAULT 'draft', "
                        "selected_count INTEGER NOT NULL DEFAULT 0, "
                        "eligible_count INTEGER NOT NULL DEFAULT 0, "
                        "filtered_count INTEGER NOT NULL DEFAULT 0, "
                        "queued_count INTEGER NOT NULL DEFAULT 0, "
                        "queued_at TIMESTAMP, "
                        "completed_at TIMESTAMP, "
                        "created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP"
                        ")"
                    )
                )
                for column in ("creator_uid", "status", "created_at"):
                    connection.execute(
                        text(
                            f"CREATE INDEX ix_email_campaigns_{column} "
                            f"ON email_campaigns ({column})"
                        )
                    )
            if create_campaign_recipients:
                connection.execute(
                    text(
                        "CREATE TABLE email_campaign_recipients ("
                        f"id {id_column}, "
                        "email_campaign_id INTEGER NOT NULL REFERENCES email_campaigns(id), "
                        "user_uid INTEGER NOT NULL REFERENCES users(uid), "
                        "recipient_email VARCHAR(320) NOT NULL, "
                        "status VARCHAR(10) NOT NULL DEFAULT 'pending', "
                        "attempts INTEGER NOT NULL DEFAULT 0, "
                        "last_error TEXT, "
                        "delivered_at TIMESTAMP, "
                        "created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, "
                        "CONSTRAINT uq_email_campaign_recipient "
                        "UNIQUE (email_campaign_id, user_uid)"
                        ")"
                    )
                )
                for column in ("email_campaign_id", "user_uid", "status", "created_at"):
                    connection.execute(
                        text(
                            f"CREATE INDEX ix_email_campaign_recipients_{column} "
                            f"ON email_campaign_recipients ({column})"
                        )
                    )
            if create_campaign_attachments:
                connection.execute(
                    text(
                        "CREATE TABLE email_campaign_attachments ("
                        f"id {id_column}, "
                        "email_campaign_id INTEGER NOT NULL REFERENCES email_campaigns(id), "
                        "source_attachment_id INTEGER REFERENCES message_attachments(id), "
                        "storage_key VARCHAR(500) NOT NULL, "
                        "original_name VARCHAR(255) NOT NULL, "
                        "mime_type VARCHAR(100) NOT NULL, "
                        "size INTEGER NOT NULL, "
                        "sha256 VARCHAR(64) NOT NULL, "
                        "created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP"
                        ")"
                    )
                )
                for column in ("email_campaign_id", "source_attachment_id", "created_at"):
                    connection.execute(
                        text(
                            f"CREATE INDEX ix_email_campaign_attachments_{column} "
                            f"ON email_campaign_attachments ({column})"
                        )
                    )

    return PhaseUpgradeResult(
        actions=actions,
        counts={
            "created_broadcast_tables": sum(
                (
                    create_messages,
                    create_recipients,
                    create_attachments,
                    create_campaigns,
                    create_campaign_recipients,
                    create_campaign_attachments,
                )
            )
        },
    )


PHASES: dict[str, PhaseUpgrade] = {
    "foundation": _upgrade_foundation,
    "accounts": _upgrade_accounts,
    "community": _upgrade_community,
    "chat": _upgrade_chat,
    "broadcast": _upgrade_broadcast,
}


def upgrade_social_platform(
    engine: Engine = default_engine,
    dry_run: bool = False,
    phase: str = "all",
) -> UpgradeReport:
    """Apply one migration phase, or all phases in their declared order."""
    if phase != "all" and phase not in PHASES:
        raise ValueError(f"unknown social platform migration phase: {phase}")

    phase_names = tuple(PHASES) if phase == "all" else (phase,)
    phase_reports = tuple(
        PHASES[phase_name](engine, dry_run) for phase_name in phase_names
    )
    actions = tuple(action for report in phase_reports for action in report.actions)
    counts: dict[str, int] = {}
    for report in phase_reports:
        for name, value in report.counts.items():
            counts[name] = counts.get(name, 0) + value
    counts["actions"] = len(actions)
    return UpgradeReport(
        actions=actions,
        applied=bool(actions) and not dry_run,
        counts=counts,
    )


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--phase", choices=(*PHASES, "all"), default="all")
    args = parser.parse_args(argv)
    report = upgrade_social_platform(dry_run=args.dry_run, phase=args.phase)
    print(json.dumps(asdict(report), ensure_ascii=False))


if __name__ == "__main__":
    main()
