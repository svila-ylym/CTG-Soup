import pytest

from app.services.tag_rules import normalize_tag_name


def test_tag_name_collapses_whitespace_and_builds_casefolded_slug():
    assert normalize_tag_name("  Story   TAG  ") == ("Story TAG", "story-tag")
    assert normalize_tag_name("  剧情   推理  ") == ("剧情 推理", "剧情-推理")


@pytest.mark.parametrize(
    "value",
    ["", " ", "x" * 31, "危险<script>", "换行\n标签", "控制\x00符"],
)
def test_tag_name_rejects_invalid_text(value):
    with pytest.raises(ValueError):
        normalize_tag_name(value)
