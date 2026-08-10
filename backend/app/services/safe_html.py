"""Small, conservative sanitizer for competition rich text."""

import bleach

RICH_HTML_TAGS = {
    "a", "blockquote", "br", "code", "del", "em", "h2", "h3", "h4",
    "hr", "img", "li", "ol", "p", "pre", "strong", "u", "ul",
}
RICH_HTML_ATTRIBUTES = {
    "a": ["href", "title"],
    "img": ["src", "alt", "title"],
}


def sanitize_rich_html(value: str) -> str:
    return bleach.clean(
        value,
        tags=RICH_HTML_TAGS,
        attributes=RICH_HTML_ATTRIBUTES,
        protocols={"http", "https", "mailto"},
        strip=True,
    ).strip()
