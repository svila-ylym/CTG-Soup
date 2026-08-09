import subprocess
import sys


def test_fastapi_application_imports_successfully():
    result = subprocess.run(
        [sys.executable, "-c", "import app.main"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
