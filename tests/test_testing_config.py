import pytest


@pytest.mark.usefixtures('setup_app')
class TestConfig:
    def test_testing_config_is_used(self):
        config = self.app.config
        assert 'TESTING' in config
        assert config['TESTING']
