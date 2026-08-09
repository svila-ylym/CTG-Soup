"""Markdown rendering with a deliberately small HTML surface."""

from markdown_it import MarkdownIt
import bleach


ALLOWED_TAGS = {
    "a",
    "blockquote",
    "br",
    "code",
    "del",
    "em",
    "h1",
    "h2",
    "h3",
    "h4",
    "hr",
    "li",
    "ol",
    "p",
    "pre",
    "strong",
    "ul",
}
ALLOWED_ATTRIBUTES = {
    "a": ["href", "title"],
}
ALLOWED_PROTOCOLS = {"http", "https", "mailto"}

_renderer = MarkdownIt(
    "commonmark",
    {"html": False, "linkify": True, "typographer": False},
)


def render_safe_markdown(markdown: str) -> str:
    rendered = _renderer.render(markdown)
    return bleach.clean(
        rendered,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )
