"""Idempotent schema upgrade for the turtle soup hall of fame."""

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

MIGRATION_LOCK_NAMESPACE = 0x435447
MIGRATION_LOCK_ID = 1002


def ensure_hall_of_fame_schema(engine: Engine, dry_run: bool = False) -> tuple[str, ...]:
    if engine.dialect.name == "postgresql" and not dry_run:
        with engine.connect() as lock_connection:
            lock_connection.execute(
                text("SELECT pg_advisory_lock(:namespace, :migration_id)"),
                {
                    "namespace": MIGRATION_LOCK_NAMESPACE,
                    "migration_id": MIGRATION_LOCK_ID,
                },
            )
            try:
                return _ensure_hall_of_fame_schema(engine, dry_run=False)
            finally:
                lock_connection.execute(
                    text("SELECT pg_advisory_unlock(:namespace, :migration_id)"),
                    {
                        "namespace": MIGRATION_LOCK_NAMESPACE,
                        "migration_id": MIGRATION_LOCK_ID,
                    },
                )
    return _ensure_hall_of_fame_schema(engine, dry_run=dry_run)


def _ensure_hall_of_fame_schema(
    engine: Engine,
    dry_run: bool,
) -> tuple[str, ...]:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    actions: list[str] = []
    soup_columns = {column["name"] for column in inspector.get_columns("soups")} if "soups" in tables else set()
    columns = {
        "is_hall_of_fame": "BOOLEAN NOT NULL DEFAULT FALSE",
        "hall_of_fame_entered_at": "TIMESTAMP NULL",
        "hall_of_fame_removed_at": "TIMESTAMP NULL",
        "hall_of_fame_removal_reason": "TEXT NULL",
        "hall_of_fame_removed_by_uid": "INTEGER NULL",
    }
    missing = [name for name in columns if name not in soup_columns]
    actions.extend(f"ADD soups.{name}" for name in missing)
    soup_indexes = {index["name"] for index in inspector.get_indexes("soups")} if "soups" in tables else set()
    if "soups" in tables and "ix_soups_is_hall_of_fame" not in soup_indexes:
        actions.append("CREATE INDEX ix_soups_is_hall_of_fame")
    settings_table_missing = "hall_of_fame_settings" not in tables
    settings_row_missing = settings_table_missing
    if settings_table_missing:
        actions.append("CREATE TABLE hall_of_fame_settings")
    else:
        with engine.connect() as connection:
            settings_row_missing = connection.execute(text(
                "SELECT 1 FROM hall_of_fame_settings WHERE id = 1"
            )).first() is None
        if settings_row_missing:
            actions.append("INSERT default hall_of_fame_settings")
    clear_bie_hall = False
    if {
        "genre",
        "is_hall_of_fame",
        "hall_of_fame_entered_at",
    }.issubset(soup_columns):
        with engine.connect() as connection:
            clear_bie_hall = connection.execute(text(
                "SELECT 1 FROM soups "
                "WHERE genre = :genre AND is_hall_of_fame = TRUE LIMIT 1"
            ), {"genre": "鳖汤"}).first() is not None
        if clear_bie_hall:
            actions.append("CLEAR hall of fame status from 鳖汤 soups")
    if dry_run or not actions:
        return tuple(actions)

    with engine.begin() as connection:
        for name in missing:
            connection.execute(text(f"ALTER TABLE soups ADD COLUMN {name} {columns[name]}"))
        if "soups" in tables:
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_soups_is_hall_of_fame ON soups (is_hall_of_fame)"))
        if settings_table_missing:
            updated_by_fk = " REFERENCES users(uid)" if "users" in tables else ""
            connection.execute(text(
                "CREATE TABLE hall_of_fame_settings ("
                "id INTEGER PRIMARY KEY, "
                "score_threshold REAL NOT NULL DEFAULT 9.85, "
                "rating_coverage_ratio REAL NOT NULL DEFAULT 0.5, "
                "updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, "
                f"updated_by_uid INTEGER NULL{updated_by_fk}"
                ")"
            ))
        if settings_row_missing:
            connection.execute(text(
                "INSERT INTO hall_of_fame_settings "
                "(id, score_threshold, rating_coverage_ratio, updated_at) "
                "VALUES (1, 9.85, 0.5, CURRENT_TIMESTAMP)"
            ))
        if clear_bie_hall:
            connection.execute(text(
                "UPDATE soups SET is_hall_of_fame = FALSE, "
                "hall_of_fame_entered_at = NULL "
                "WHERE genre = :genre AND is_hall_of_fame = TRUE"
            ), {"genre": "鳖汤"})
    return tuple(actions)
