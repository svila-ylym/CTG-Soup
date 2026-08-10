import subprocess
import sys

from sqlmodel import SQLModel


def test_fastapi_application_imports_successfully():
    result = subprocess.run(
        [sys.executable, "-c", "import app.main"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr


def test_new_account_and_soup_image_tables_are_registered():
    import app.models.database  # noqa: F401

    assert {
        "soup_images",
        "user_uid_allocator",
        "reusable_user_uids",
    }.issubset(SQLModel.metadata.tables)
