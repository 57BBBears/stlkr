def test_testing_config_is_used(app):
    config = app.config
    assert config["TESTING"]
