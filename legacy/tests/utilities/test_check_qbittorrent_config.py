import pytest
from unittest.mock import patch, MagicMock
from scripts.utilities import check_qbittorrent_config

def test_main_prints_relevant_settings(monkeypatch):
    class DummyClient:
        def get_preferences(self):
            return {
                'save_path': '/media/downloads',
                'temp_path': '/media/incomplete',
                'auto_delete_mode': 1,
                'random_other': 42
            }
    monkeypatch.setattr(check_qbittorrent_config, 'Config', lambda: MagicMock())
    monkeypatch.setattr(check_qbittorrent_config, 'QBitClient', lambda *a, **kw: DummyClient())
    with patch('builtins.print') as mock_print:
        check_qbittorrent_config.main()
        # Should print relevant settings
        found = any('save_path' in str(call) for call in mock_print.call_args_list)
        assert found
