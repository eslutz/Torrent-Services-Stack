"""Tests for check_torrent_status.py"""
import pytest
from unittest.mock import patch, MagicMock
from scripts.utilities import check_torrent_status


class TestPrintTable:
    """Tests for print_table function."""

    def test_print_table_formats_correctly(self):
        """Test print_table formats output correctly."""
        headers = ['Col1', 'Col2']
        rows = [['val1', 'val2'], ['val3', 'val4']]

        with patch('builtins.print') as mock_print:
            check_torrent_status.print_table(headers, rows)
            # Should print header, separator, and rows
            assert mock_print.call_count >= 3

    def test_print_table_handles_long_values(self):
        """Test print_table with long values."""
        headers = ['Name', 'Status']
        rows = [['Very Long Name That Exceeds Width', 'OK']]

        with patch('builtins.print') as mock_print:
            check_torrent_status.print_table(headers, rows)
            assert mock_print.call_count >= 2

    def test_print_table_empty_rows(self):
        """Test print_table with empty rows."""
        headers = ['Col1', 'Col2']
        rows = []

        with patch('builtins.print') as mock_print:
            check_torrent_status.print_table(headers, rows)
            assert mock_print.call_count >= 2


class TestCheckAll:
    """Tests for check_all function."""

    def test_check_all_prints_table(self):
        """Test check_all prints torrent table."""
        class DummyClient:
            def get_torrents(self):
                return [
                    {'name': 'A', 'state': 'error', 'progress': 0.5, 'error_type': 'Disk'},
                    {'name': 'B', 'state': 'stalledDL', 'progress': 0.1},
                    {'name': 'C', 'state': 'missingFiles', 'progress': 0.9}
                ]

        with patch('builtins.print') as mock_print:
            check_torrent_status.check_all(DummyClient())
            assert any('A' in str(call) for call in mock_print.call_args_list)

    def test_check_all_no_torrents(self):
        """Test check_all with no torrents."""
        client = MagicMock()
        client.get_torrents.return_value = []

        with patch('builtins.print') as mock_print:
            check_torrent_status.check_all(client)
            assert any('No torrents found' in str(call) for call in mock_print.call_args_list)

    def test_check_all_various_states(self):
        """Test check_all with various torrent states."""
        client = MagicMock()
        client.get_torrents.return_value = [
            {'name': 'Downloading', 'state': 'downloading', 'progress': 0.5},
            {'name': 'Seeding', 'state': 'seeding', 'progress': 1.0},
            {'name': 'Paused', 'state': 'pausedDL', 'progress': 0.3}
        ]

        with patch('builtins.print') as mock_print:
            check_torrent_status.check_all(client)
            assert any('Downloading' in str(call) for call in mock_print.call_args_list)


class TestInspectTorrent:
    """Tests for inspect_torrent function."""

    def test_inspect_torrent_prints(self):
        """Test inspect_torrent prints torrent details."""
        class DummyClient:
            def get_torrents(self):
                return [{
                    'hash': 'abc',
                    'name': 'Test',
                    'state': 'downloading',
                    'progress': 0.5,
                    'save_path': '/media',
                    'content_path': '/media/file',
                    'dlspeed': 1000,
                    'num_seeds': 5,
                    'num_complete': 10,
                    'num_leechs': 2,
                    'num_incomplete': 3
                }]
            def get_trackers(self, h):
                return [{
                    'url': 'http://tracker.example.com',
                    'status': 2,
                    'msg': 'Working',
                    'num_peers': 5
                }]

        with patch('builtins.print') as mock_print:
            check_torrent_status.inspect_torrent(DummyClient(), 'abc')
            assert any('Inspecting' in str(call) for call in mock_print.call_args_list)

    def test_inspect_torrent_not_found(self):
        """Test inspect_torrent with non-existent torrent."""
        class DummyClient:
            def get_torrents(self):
                return [{'hash': 'abc', 'name': 'Test'}]

        with patch('builtins.print') as mock_print:
            check_torrent_status.inspect_torrent(DummyClient(), 'nonexistent')
            assert any('not found' in str(call) for call in mock_print.call_args_list)

    def test_inspect_torrent_by_name(self):
        """Test inspect_torrent finding torrent by name."""
        class DummyClient:
            def get_torrents(self):
                return [{
                    'hash': 'abc',
                    'name': 'Ubuntu ISO',
                    'state': 'seeding',
                    'progress': 1.0,
                    'save_path': '/media',
                    'content_path': '/media/ubuntu.iso',
                    'dlspeed': 0,
                    'num_seeds': 10,
                    'num_complete': 100,
                    'num_leechs': 0,
                    'num_incomplete': 5
                }]
            def get_trackers(self, h):
                return []

        with patch('builtins.print') as mock_print:
            check_torrent_status.inspect_torrent(DummyClient(), 'ubuntu')
            assert any('Inspecting' in str(call) for call in mock_print.call_args_list)

    def test_inspect_torrent_multiple_trackers(self):
        """Test inspect_torrent with multiple trackers."""
        client = MagicMock()
        client.get_torrents.return_value = [{
            'hash': 'abc',
            'name': 'Test',
            'state': 'downloading',
            'progress': 0.5,
            'save_path': '/media',
            'content_path': '/media/file',
            'dlspeed': 1000,
            'num_seeds': 5,
            'num_complete': 10,
            'num_leechs': 2,
            'num_incomplete': 3
        }]
        client.get_trackers.return_value = [
            {'url': 'tracker1', 'status': 2, 'msg': 'OK', 'num_peers': 5},
            {'url': 'tracker2', 'status': 0, 'msg': 'Failed', 'num_peers': 0}
        ]

        with patch('builtins.print') as mock_print:
            check_torrent_status.inspect_torrent(client, 'abc')
            calls_str = ' '.join(str(call) for call in mock_print.call_args_list)
            assert 'tracker1' in calls_str
            assert 'tracker2' in calls_str


class TestAnalyzeStalled:
    """Tests for analyze_stalled function."""

    def test_analyze_stalled_with_stalled_torrents(self):
        """Test analyze_stalled with stalled torrents."""
        client = MagicMock()
        client.get_torrents.return_value = [
            {
                'name': 'Stalled1',
                'state': 'stalledDL',
                'hash': 'abc',
                'dlspeed': 0,
                'num_seeds': 0,
                'num_complete': 5,
                'num_leechs': 0,
                'num_incomplete': 2
            },
            {
                'name': 'Downloading',
                'state': 'downloading',
                'hash': 'def',
                'dlspeed': 1000,
                'num_seeds': 5,
                'num_complete': 10,
                'num_leechs': 2,
                'num_incomplete': 3
            }
        ]
        client.get_trackers.return_value = [
            {'status': 2, 'msg': 'Working', 'num_peers': 5}
        ]

        with patch('builtins.print') as mock_print:
            check_torrent_status.analyze_stalled(client)
            assert any('Found 1 stalled' in str(call) for call in mock_print.call_args_list)

    def test_analyze_stalled_no_stalled_torrents(self):
        """Test analyze_stalled with no stalled torrents."""
        client = MagicMock()
        client.get_torrents.return_value = [
            {'name': 'Active', 'state': 'downloading', 'hash': 'abc'}
        ]

        with patch('builtins.print') as mock_print:
            check_torrent_status.analyze_stalled(client)
            assert any('Found 0 stalled' in str(call) for call in mock_print.call_args_list)

    def test_analyze_stalled_no_trackers(self):
        """Test analyze_stalled with no trackers."""
        client = MagicMock()
        client.get_torrents.return_value = [{
            'name': 'Stalled',
            'state': 'stalledDL',
            'hash': 'abc',
            'dlspeed': 0,
            'num_seeds': 0,
            'num_complete': 0,
            'num_leechs': 0,
            'num_incomplete': 0
        }]
        client.get_trackers.return_value = []

        with patch('builtins.print') as mock_print:
            check_torrent_status.analyze_stalled(client)
            calls_str = ' '.join(str(call) for call in mock_print.call_args_list)
            assert 'No trackers' in calls_str

    def test_analyze_stalled_working_trackers(self):
        """Test analyze_stalled with working trackers."""
        client = MagicMock()
        client.get_torrents.return_value = [{
            'name': 'Stalled',
            'state': 'metaDL',
            'hash': 'abc',
            'dlspeed': 0,
            'num_seeds': 0,
            'num_complete': 0,
            'num_leechs': 0,
            'num_incomplete': 0
        }]
        client.get_trackers.return_value = [
            {'status': 2, 'msg': 'Working'},
            {'status': 2, 'msg': 'Also working'}
        ]

        with patch('builtins.print') as mock_print:
            check_torrent_status.analyze_stalled(client)
            calls_str = ' '.join(str(call) for call in mock_print.call_args_list)
            assert 'Working (2)' in calls_str

    def test_analyze_stalled_failed_tracker_with_message(self):
        """Test analyze_stalled with failed tracker that has message."""
        client = MagicMock()
        client.get_torrents.return_value = [{
            'name': 'Stalled',
            'state': 'stalledDL',
            'hash': 'abc',
            'dlspeed': 0,
            'num_seeds': 0,
            'num_complete': 0,
            'num_leechs': 0,
            'num_incomplete': 0
        }]
        client.get_trackers.return_value = [
            {'status': 0, 'msg': 'Tracker unreachable'}
        ]

        with patch('builtins.print') as mock_print:
            check_torrent_status.analyze_stalled(client)
            calls_str = ' '.join(str(call) for call in mock_print.call_args_list)
            assert 'Tracker unreachable' in calls_str

    def test_analyze_stalled_failed_tracker_no_message(self):
        """Test analyze_stalled with failed tracker without message."""
        client = MagicMock()
        client.get_torrents.return_value = [{
            'name': 'Stalled',
            'state': 'stalledDL',
            'hash': 'abc',
            'dlspeed': 0,
            'num_seeds': 0,
            'num_complete': 0,
            'num_leechs': 0,
            'num_incomplete': 0
        }]
        client.get_trackers.return_value = [
            {'status': 0, 'msg': ''}
        ]

        with patch('builtins.print') as mock_print:
            check_torrent_status.analyze_stalled(client)
            calls_str = ' '.join(str(call) for call in mock_print.call_args_list)
            assert 'Status: 0' in calls_str


class TestMain:
    """Tests for main function."""

    @patch('sys.argv', ['check_torrent_status.py', 'all'])
    @patch.object(check_torrent_status, 'check_all')
    @patch.object(check_torrent_status, 'Config')
    @patch.object(check_torrent_status, 'QBitClient')
    def test_main_all_action(self, mock_client, mock_config, mock_check_all):
        """Test main with 'all' action."""
        check_torrent_status.main()
        mock_check_all.assert_called_once()

    @patch('sys.argv', ['check_torrent_status.py', 'inspect', '--query', 'abc123'])
    @patch.object(check_torrent_status, 'inspect_torrent')
    @patch.object(check_torrent_status, 'Config')
    @patch.object(check_torrent_status, 'QBitClient')
    def test_main_inspect_action(self, mock_client, mock_config, mock_inspect):
        """Test main with 'inspect' action."""
        check_torrent_status.main()
        mock_inspect.assert_called_once()

    @patch('sys.argv', ['check_torrent_status.py', 'inspect'])
    @patch.object(check_torrent_status, 'Config')
    @patch.object(check_torrent_status, 'QBitClient')
    def test_main_inspect_no_query(self, mock_client, mock_config):
        """Test main with 'inspect' but no query."""
        with patch('builtins.print') as mock_print:
            check_torrent_status.main()
            assert any('query is required' in str(call) for call in mock_print.call_args_list)

    @patch('sys.argv', ['check_torrent_status.py', 'stalled'])
    @patch.object(check_torrent_status, 'analyze_stalled')
    @patch.object(check_torrent_status, 'Config')
    @patch.object(check_torrent_status, 'QBitClient')
    def test_main_stalled_action(self, mock_client, mock_config, mock_analyze):
        """Test main with 'stalled' action."""
        check_torrent_status.main()
        mock_analyze.assert_called_once()

    @patch('sys.argv', ['check_torrent_status.py'])
    @patch.object(check_torrent_status, 'check_all')
    @patch.object(check_torrent_status, 'Config')
    @patch.object(check_torrent_status, 'QBitClient')
    def test_main_default_action(self, mock_client, mock_config, mock_check_all):
        """Test main with default action (all)."""
        check_torrent_status.main()
        mock_check_all.assert_called_once()

    @patch('sys.argv', ['check_torrent_status.py', 'inspect', '-q', 'test_hash'])
    @patch.object(check_torrent_status, 'inspect_torrent')
    @patch.object(check_torrent_status, 'Config')
    @patch.object(check_torrent_status, 'QBitClient')
    def test_main_inspect_short_flag(self, mock_client, mock_config, mock_inspect):
        """Test main with 'inspect' using short -q flag."""
        check_torrent_status.main()
        args = mock_inspect.call_args[0]
        assert args[1] == 'test_hash'
