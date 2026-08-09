import re
import unicodedata


_WHITESPACE = re.compile(r"\s+")


def normalize_tag_name(value: str) -> tuple[str, str]:
    """Return a normalized display name and stable case-insensitive slug."""
    if not isinstance(value, str):
        raise ValueError("标签名称必须是字符串")

    normalized = unicodedata.normalize("NFKC", value)
    if any(unicodedata.category(char).startswith("C") for char in normalized):
        raise ValueError("标签不能包含控制字符")
    if "<" in normalized or ">" in normalized:
        raise ValueError("标签不能包含 HTML")

    name = _WHITESPACE.sub(" ", normalized).strip()
    if not 1 <= len(name) <= 30:
        raise ValueError("标签长度必须为1到30个字符")

    slug = name.casefold().replace(" ", "-")
    return name, slug
