def test_create_app_registers_blueprint_and_service(app):
    assert "market_service" in app.config
    rules = {rule.rule for rule in app.url_map.iter_rules()}
    assert "/api/v3/publications" in rules
    assert "/health" in rules
