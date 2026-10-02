"""Tests for manage_torrents.py"""
import pytest
import os
from unittest.mock import patch, MagicMock
from scripts.utilities import manage_torrents


class TestFixPaths:
    """Tests for fix_paths function."""

    def test_fix_paths_fixes_only_wrong(self):
        """Test fix_paths only fixes incorrect paths."""
        class DummyClient:
            def __init__(self):
                self.locations = []
            def get_torrents(self):
                return [
                    {'name': 'A', 'save_path': '/downloads/A', 'hash': 'abc'},
                    {'name': 'B', 'save_path': '/media/downloads', 'hash': 'def'}
                ]
            def set_location(self, h, p):
                self.locations.append((h, p))

        config = MagicMock()
        config.default_save_path = '/media/downloads'
        client = DummyClient()

        with patch('builtins.print'):
            manage_torrents.fix_paths(client, config)

        assert ('abc', '/media/downloads') in client.locations
        assert ('def', '/media/downloads') not in client.locations

    def test_fix_paths_no_torrents(self):
        """Test fix_paths with no torrents."""
        client = MagicMock()
        client.get_torrents.return_value = []
        config = MagicMock()
        config.default_save_path = '/media/downloads'

        with patch('builtins.print') as mock_print:
            manage_torrents.fix_paths(client, config)
            assert any('0 torrents' in str(call) for call in mock_print.call_args_list)

    def test_fix_paths_all_correct(self):
        """Test fix_paths when all paths are correct."""
        client = MagicMock()
        client.get_torrents.return_value = [
            {'name': 'A', 'save_path': '/media/downloads', 'hash': 'abc'},
            {'name': 'B', 'save_path': '/media/downloads', 'hash': 'def'}
        ]
        config = MagicMock()
        config.default_save_path = '/media/downloads'

        with patch('builtins.print') as mock_print:
            manage_torrents.fix_paths(client, config)
            assert any('0 torrents' in str(call) for call in mock_print.call_args_list)

        client.set_location.assert_not_called()


class TestAddMissing:
    """Tests for add_missing function."""

    def test_add_missing_adds(self, tmp_path):
        """Test add_missing successfully adds torrent files."""
        class DummyClient:
            def add_torrent_file(self, f, p):
                return True

        config = MagicMock()
        config.default_scan_path = str(tmp_path)
        config.default_save_path = '/media/downloads'

        # Create dummy .torrent files
        (tmp_path / 'a.torrent').write_text('x')
        (tmp_path / 'b.torrent').write_text('y')

        with patch('builtins.print') as mock_print:
            manage_torrents.add_missing(DummyClient(), config)
            assert any('Processed' in str(call) for call in mock_print.call_args_list)

    def test_add_missing_no_scan_path(self):
        """Test add_missing with no scan path configured."""
        client = MagicMock()
        config = MagicMock()
        config.default_scan_path = None

        with patch('builtins.print') as mock_print:
            manage_torrents.add_missing(client, config, scan_path=None)
            assert any('No scan path' in str(call) for call in mock_print.call_args_list)

    def test_add_missing_path_not_exists(self):
        """Test add_missing when path doesn't exist."""
        client = MagicMock()
        config = MagicMock()
        config.default_scan_path = '/nonexistent/path'

        with patch('builtins.print') as mock_print:
            manage_torrents.add_missing(client, config)
            assert any('not found' in str(call) for call in mock_print.call_args_list)

    def test_add_missing_no_files(self, tmp_path):
        """Test add_missing when no torrent files found."""
        client = MagicMock()
        config = MagicMock()
        config.default_scan_path = str(tmp_path)

        with patch('builtins.print') as mock_print:
            manage_torrents.add_missing(client, config)
            assert any('No .torrent files found' in str(call) for call in mock_print.call_args_list)

    def test_add_missing_custom_path(self, tmp_path):
        """Test add_missing with custom scan path."""
        custom_path = tmp_path / 'custom'
        custom_path.mkdir()
        (custom_path / 'test.torrent').write_text('data')

        client = MagicMock()
        client.add_torrent_file.return_value = True
        config = MagicMock()
        config.default_save_path = '/media/downloads'

        with patch('builtins.print'):
            manage_torrents.add_missing(client, config, scan_path=str(custom_path))

        client.add_torrent_file.assert_called_once()

    def test_add_missing_some_fail(self, tmp_path):
        """Test add_missing when some additions fail."""
        (tmp_path / 'success.torrent').write_text('x')
        (tmp_path / 'fail.torrent').write_text('y')

        client = MagicMock()
        # First call succeeds, second fails
        client.add_torrent_file.side_effect = [True, False]

        config = MagicMock()
        config.default_scan_path = str(tmp_path)
        config.default_save_path = '/media/downloads'

        with patch('builtins.print') as mock_print:
            manage_torrents.add_missing(client, config)
            assert any('1 .torrent files' in str(call) for call in mock_print.call_args_list)


class TestRecheckAll:
    """Tests for recheck_all function."""

    def test_recheck_all_rechecks_all_torrents(self):
        """Test recheck_all rechecks all torrents."""
        client = MagicMock()
        client.get_torrents.return_value = [
            {'hash': 'abc', 'name': 'Test1'},
            {'hash': 'def', 'name': 'Test2'}
        ]

        with patch('builtins.print'):
            manage_torrents.recheck_all(client)

        client.recheck_torrent.assert_called_once_with('abc|def')

    def test_recheck_all_empty_torrents(self):
        """Test recheck_all with no torrents."""
        client = MagicMock()
        client.get_torrents.return_value = []

        with patch('builtins.print'):
            manage_torrents.recheck_all(client)

        client.recheck_torrent.assert_not_called()


class TestAnnounceAll:
    """Tests for announce_all function."""

    def test_announce_all_reannounces_all(self):
        """Test announce_all reannounces all torrents."""
        client = MagicMock()
        client.get_torrents.return_value = [
            {'hash': 'abc', 'name': 'Test1'},
            {'hash': 'def', 'name': 'Test2'}
        ]

        with patch('builtins.print'):
            manage_torrents.announce_all(client)

        client.reannounce_torrent.assert_called_once_with('abc|def')

    def test_announce_all_empty(self):
        """Test announce_all with no torrents."""
        client = MagicMock()
        client.get_torrents.return_value = []

        with patch('builtins.print'):
            manage_torrents.announce_all(client)

        client.reannounce_torrent.assert_not_called()


class TestDeleteBroken:
    """Tests for delete_broken function."""

    def test_delete_broken_deletes_stalled_with_no_working_trackers(self):
        """Test delete_broken deletes stalled torrents without working trackers."""
        client = MagicMock()
        client.get_torrents.return_value = [
            {'hash': 'abc', 'name': 'Broken', 'state': 'stalledDL'},
            {'hash': 'def', 'name': 'Working', 'state': 'downloading'}
        ]
        client.get_trackers.return_value = [
            {'status': 0},  # Not working
            {'status': 1}   # Not working
        ]

        with patch('builtins.print'):
            manage_torrents.delete_broken(client, delete_files=False)

        client.delete_torrents.assert_called_once()
        args = client.delete_torrents.call_args[0]
        assert 'abc' in args[0]
        assert args[1] == False

    def test_delete_broken_no_broken_torrents(self):
        """Test delete_broken when no broken torrents found."""
        client = MagicMock()
        client.get_torrents.return_value = [
            {'hash': 'abc', 'name': 'Working', 'state': 'stalledDL'}
        ]
        client.get_trackers.return_value = [
            {'status': 2}  # Working tracker
        ]

        with patch('builtins.print') as mock_print:
            manage_torrents.delete_broken(client, delete_files=False)
            assert any('No broken torrents' in str(call) for call in mock_print.call_args_list)

        client.delete_torrents.assert_not_called()

    def test_delete_broken_with_delete_files(self):
        """Test delete_broken with delete_files flag."""
        client = MagicMock()
        client.get_torrents.return_value = [
            {'hash': 'abc', 'name': 'Broken', 'state': 'stalledDL'}
        ]
        client.get_trackers.return_value = [{'status': 0}]

        with patch('builtins.print'):
            manage_torrents.delete_broken(client, delete_files=True)

        args = client.delete_torrents.call_args[0]
        assert args[1] == True

    def test_delete_broken_mixed_states(self):
        """Test delete_broken with mixed torrent states."""
        client = MagicMock()
        client.get_torrents.return_value = [
            {'hash': 'abc', 'name': 'Stalled1', 'state': 'stalledDL'},
            {'hash': 'def', 'name': 'Stalled2', 'state': 'metaDL'},
            {'hash': 'ghi', 'name': 'Downloading', 'state': 'downloading'},
            {'hash': 'jkl', 'name': 'Seeding', 'state': 'seeding'}
        ]
        client.get_trackers.return_value = [{'status': 0}]

        with patch('builtins.print'):
            manage_torrents.delete_broken(client, delete_files=False)

        # Should only analyze stalled ones
        assert client.get_trackers.call_count == 2


class TestMain:
    """Tests for main function."""

    @patch('sys.argv', ['manage_torrents.py', 'fix-paths'])
    @patch.object(manage_torrents, 'fix_paths')
    @patch.object(manage_torrents, 'Config')
    @patch.object(manage_torrents, 'QBitClient')
    def test_main_fix_paths(self, mock_client, mock_config, mock_fix):
        """Test main with fix-paths command."""
        manage_torrents.main()
        mock_fix.assert_called_once()

    @patch('sys.argv', ['manage_torrents.py', 'recheck'])
    @patch.object(manage_torrents, 'recheck_all')
    @patch.object(manage_torrents, 'Config')
    @patch.object(manage_torrents, 'QBitClient')
    def test_main_recheck(self, mock_client, mock_config, mock_recheck):
        """Test main with recheck command."""
        manage_torrents.main()
        mock_recheck.assert_called_once()

    @patch('sys.argv', ['manage_torrents.py', 'announce'])
    @patch.object(manage_torrents, 'announce_all')
    @patch.object(manage_torrents, 'Config')
    @patch.object(manage_torrents, 'QBitClient')
    def test_main_announce(self, mock_client, mock_config, mock_announce):
        """Test main with announce command."""
        manage_torrents.main()
        mock_announce.assert_called_once()

    @patch('sys.argv', ['manage_torrents.py', 'delete-broken'])
    @patch.object(manage_torrents, 'delete_broken')
    @patch.object(manage_torrents, 'Config')
    @patch.object(manage_torrents, 'QBitClient')
    def test_main_delete_broken(self, mock_client, mock_config, mock_delete):
        """Test main with delete-broken command."""
        manage_torrents.main()
        mock_delete.assert_called_once()
        args = mock_delete.call_args[0]
        assert args[1] == False  # delete_files should be False by default

    @patch('sys.argv', ['manage_torrents.py', 'delete-broken', '--delete-files'])
    @patch.object(manage_torrents, 'delete_broken')
    @patch.object(manage_torrents, 'Config')
    @patch.object(manage_torrents, 'QBitClient')
    def test_main_delete_broken_with_files(self, mock_client, mock_config, mock_delete):
        """Test main with delete-broken --delete-files."""
        manage_torrents.main()
        args = mock_delete.call_args[0]
        assert args[1] == True

    @patch('sys.argv', ['manage_torrents.py', 'add-missing'])
    @patch.object(manage_torrents, 'add_missing')
    @patch.object(manage_torrents, 'Config')
    @patch.object(manage_torrents, 'QBitClient')
    def test_main_add_missing(self, mock_client, mock_config, mock_add):
        """Test main with add-missing command."""
        manage_torrents.main()
        mock_add.assert_called_once()

    @patch('sys.argv', ['manage_torrents.py', 'add-missing', '--path', '/custom/path'])
    @patch.object(manage_torrents, 'add_missing')
    @patch.object(manage_torrents, 'Config')
    @patch.object(manage_torrents, 'QBitClient')
    def test_main_add_missing_custom_path(self, mock_client, mock_config, mock_add):
        """Test main with add-missing --path."""
        manage_torrents.main()
        args = mock_add.call_args[0]
        assert args[2] == '/custom/path'


