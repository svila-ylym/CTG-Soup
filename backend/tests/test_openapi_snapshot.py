from app.main import app


def test_openapi_contains_core_workflow_routes():
    paths = set(app.openapi()["paths"])
    required = {
        "/api/auth/register",
        "/api/auth/login",
        "/api/turtle-soups",
        "/api/turtle-soups/{soup_id}",
        "/api/turtle-soups/{soup_id}/comments",
        "/api/tags",
        "/api/competitions",
        "/api/competitions/{competition_id}",
        "/api/announcements",
        "/api/posts",
        "/api/messages",
        "/api/notifications",
        "/api/search/users",
        "/api/admin/tags",
        "/api/admin/announcements",
    }
    assert required <= paths, f"missing OpenAPI paths: {sorted(required - paths)}"


def test_openapi_canonical_schemas_do_not_expose_legacy_identity_fields():
    schemas = app.openapi()["components"]["schemas"]
    canonical_names = {
        "CompetitionResponse",
        "PostResponse",
        "PrivateMessageResponse",
        "UserAchievementResponse",
    }
    for name in canonical_names:
        properties = schemas[name]["properties"]
        assert "creator_id" not in properties
        assert "author_id" not in properties
        assert "sender_id" not in properties
        assert "receiver_id" not in properties
