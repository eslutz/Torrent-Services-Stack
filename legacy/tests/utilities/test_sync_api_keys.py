import pytest
from unittest.mock import patch, MagicMock
from scripts.utilities import sync_api_keys

def test_fix_indexers_updates(monkeypatch):
    dummy_indexer = {
        'id': 1,
        'name': 'Prowlarr',
        'fields': [
            {'name': 'baseUrl', 'value': 'http://prowlarr:9696'},
            {'name': 'apiKey', 'value': 'WRONG'}
        ],
        'implementation': 'Torznab'
    }
    called = {}
    def dummy_get(url, headers):
        class Resp:
            def raise_for_status(self): pass
            def json(self): return [dummy_indexer]
        called['get'] = True
        return Resp()
    def dummy_put(url, headers, json):
        called['put'] = True
        class Resp:
            def raise_for_status(self): pass
            status_code = 200
            text = ''
        return Resp()
    def dummy_post(url, headers, json):
        called['post'] = True
        class Resp:
            status_code = 200
            text = ''
        return Resp()
    monkeypatch.setattr(sync_api_keys.requests, 'get', dummy_get)
    monkeypatch.setattr(sync_api_keys.requests, 'put', dummy_put)
    monkeypatch.setattr(sync_api_keys.requests, 'post', dummy_post)
    with patch('builtins.print'):
        sync_api_keys.fix_indexers('Sonarr', 'url', 'API', 'CORRECT')
    assert called.get('put') and called.get('post')
