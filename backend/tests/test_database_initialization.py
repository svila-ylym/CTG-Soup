from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

import app.db as database


def test_database_provisioning_is_disabled_by_default(monkeypatch):
    connect = Mock()
    monkeypatch.setattr(database, "psycopg2", SimpleNamespace(connect=connect), raising=False)

    database.ensure_database_exists(
        "postgresql://postgres:secret@localhost:5432/turtle_soup",
        enabled=False,
    )

    connect.assert_not_called()


def test_database_provisioning_ignores_non_postgresql_urls(monkeypatch):
    connect = Mock()
    monkeypatch.setattr(database, "psycopg2", SimpleNamespace(connect=connect), raising=False)

    database.ensure_database_exists("sqlite:///local.db", enabled=True)

    connect.assert_not_called()


def test_existing_database_is_not_created(monkeypatch):
    cursor = Mock()
    cursor.fetchone.return_value = (1,)
    connection = MagicMock()
    connection.cursor.return_value.__enter__.return_value = cursor
    connect = Mock(return_value=connection)
    monkeypatch.setattr(database, "psycopg2", SimpleNamespace(connect=connect), raising=False)

    database.ensure_database_exists(
        "postgresql://postgres:secret@localhost:5432/turtle_soup",
        enabled=True,
    )

    assert connection.autocommit is True
    cursor.execute.assert_called_once_with(
        "SELECT 1 FROM pg_database WHERE datname = %s",
        ("turtle_soup",),
    )
    connection.close.assert_called_once_with()


def test_missing_database_is_created_with_a_quoted_identifier(monkeypatch):
    cursor = Mock()
    cursor.fetchone.return_value = None
    connection = MagicMock()
    connection.cursor.return_value.__enter__.return_value = cursor
    connect = Mock(return_value=connection)
    monkeypatch.setattr(database, "psycopg2", SimpleNamespace(connect=connect), raising=False)

    database.ensure_database_exists(
        "postgresql://postgres:secret@localhost:5432/turtle_soup",
        enabled=True,
    )

    assert cursor.execute.call_count == 2
    create_statement = cursor.execute.call_args_list[1].args[0]
    assert repr(create_statement) == (
        "Composed([SQL('CREATE DATABASE '), Identifier('turtle_soup')])"
    )
    connect.assert_called_once_with(
        host="localhost",
        port=5432,
        user="postgres",
        password="secret",
        dbname="postgres",
    )
