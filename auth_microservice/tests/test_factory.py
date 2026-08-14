def test_create_app_registers_blueprint_and_service(app):
    assert "auth_service" in app.config
    rules = {rule.rule for rule in app.url_map.iter_rules()}
    assert "/api/v3/auth/register" in rules
    assert "/health" in rules
