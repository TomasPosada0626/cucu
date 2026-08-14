def test_create_app_registers_blueprint(app):
    rules = {rule.rule for rule in app.url_map.iter_rules()}
    assert "/geocode" in rules
    assert "/route" in rules
    assert "/health" in rules
