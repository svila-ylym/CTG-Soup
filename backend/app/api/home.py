from pathlib import Path

from fastapi import APIRouter

router = APIRouter()

DEFAULT_HOME_LINE = "一碗汤，一群人，一场从“为什么”开始的推理冒险。读故事、问线索、把藏起来的真相一点点拼完整。"
HOME_COPY_PATH = Path(__file__).resolve().parents[3] / "home.txt"


@router.get("/lines")
async def get_home_lines() -> dict[str, list[str]]:
    try:
        content = HOME_COPY_PATH.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return {"lines": [DEFAULT_HOME_LINE]}

    lines = [line for raw_line in content.splitlines() if (line := raw_line.strip())]
    return {"lines": lines or [DEFAULT_HOME_LINE]}
