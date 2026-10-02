"""Tests for vpn_speedtest.py"""
import pytest
import json
import subprocess
from unittest.mock import patch, MagicMock, mock_open, call
from scripts.utilities import vpn_speedtest


class TestVPNSpeedTestInit:
    """Tests for VPNSpeedTest initialization."""

    def test_init_default_values(self):
        """Test initialization with default values."""
        tester = vpn_speedtest.VPNSpeedTest('test_container', json_output=False)

        assert tester.container_name == 'test_container'
        assert tester.json_output is False
        assert tester.results['container'] == 'test_container'
        assert tester.results['vpn_status'] == 'unknown'

    def test_init_json_mode(self):
        """Test initialization with JSON output mode."""
        tester = vpn_speedtest.VPNSpeedTest('qbittorrent', json_output=True)

        assert tester.json_output is True
        assert 'timestamp' in tester.results


class TestLog:
    """Tests for log method."""

    def test_log_prints_in_normal_mode(self, capsys):
        """Test log prints in normal mode."""
        tester = vpn_speedtest.VPNSpeedTest('dummy', json_output=False)
        tester.log('test message', color=vpn_speedtest.GREEN)

        captured = capsys.readouterr()
        assert 'test message' in captured.out

    def test_log_silent_in_json_mode(self, capsys):
        """Test log is silent in JSON mode."""
        tester = vpn_speedtest.VPNSpeedTest('dummy', json_output=True)
        tester.log('test message')

        captured = capsys.readouterr()
        assert captured.out == ''

    def test_log_with_color(self, capsys):
        """Test log with color codes."""
        tester = vpn_speedtest.VPNSpeedTest('dummy', json_output=False)
        tester.log('colored message', color=vpn_speedtest.RED)

        captured = capsys.readouterr()
        assert vpn_speedtest.RED in captured.out
        assert 'colored message' in captured.out


class TestCheckContainer:
    """Tests for check_container method."""

    @patch('subprocess.run')
    def test_check_container_running(self, mock_run):
        """Test when container is running."""
        mock_run.return_value = MagicMock(
            stdout='qbittorrent\ngluetun\nsonarr\n',
            returncode=0
        )

        tester = vpn_speedtest.VPNSpeedTest('qbittorrent', json_output=False)
        # Should not raise SystemExit
        tester.check_container()

    @patch('subprocess.run')
    def test_check_container_not_running_normal_mode(self, mock_run, capsys):
        """Test when container is not running (normal mode)."""
        mock_run.return_value = MagicMock(
            stdout='gluetun\nsonarr\n',
            returncode=0
        )

        tester = vpn_speedtest.VPNSpeedTest('qbittorrent', json_output=False)

        with pytest.raises(SystemExit) as exc:
            tester.check_container()

        assert exc.value.code == 1
        captured = capsys.readouterr()
        assert 'not running' in captured.out

    @patch('subprocess.run')
    def test_check_container_not_running_json_mode(self, mock_run, capsys):
        """Test when container is not running (JSON mode)."""
        mock_run.return_value = MagicMock(
            stdout='gluetun\n',
            returncode=0
        )

        tester = vpn_speedtest.VPNSpeedTest('missing', json_output=True)

        with pytest.raises(SystemExit) as exc:
            tester.check_container()

        assert exc.value.code == 1
        captured = capsys.readouterr()
        assert 'error' in captured.out.lower()


class TestGetHostIP:
    """Tests for get_host_ip method."""

    @patch('scripts.utilities.vpn_speedtest.requests.get')
    def test_get_host_ip_success(self, mock_get):
        """Test successful host IP retrieval."""
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {'ip': '1.2.3.4', 'city': 'Test City'}
        )

        tester = vpn_speedtest.VPNSpeedTest('dummy', json_output=True)
        ip = tester.get_host_ip()

        assert ip == '1.2.3.4'
        assert tester.results['host_ip'] == '1.2.3.4'

    @patch('scripts.utilities.vpn_speedtest.requests.get')
    def test_get_host_ip_failure(self, mock_get):
        """Test host IP retrieval failure."""
        mock_get.side_effect = Exception('Network error')

        tester = vpn_speedtest.VPNSpeedTest('dummy', json_output=True)
        ip = tester.get_host_ip()

        assert ip is None

    @patch('scripts.utilities.vpn_speedtest.requests.get')
    def test_get_host_ip_non_200_status(self, mock_get):
        """Test host IP with non-200 status."""
        mock_get.return_value = MagicMock(status_code=500)

        tester = vpn_speedtest.VPNSpeedTest('dummy', json_output=True)
        ip = tester.get_host_ip()

        assert ip is None


class TestGetContainerIP:
    """Tests for get_container_ip method."""

    def test_get_container_ip_success(self):
        """Test successful container IP retrieval."""
        tester = vpn_speedtest.VPNSpeedTest('dummy', json_output=True)

        mock_result = MagicMock(
            returncode=0,
            stdout='{"ip": "5.6.7.8", "city": "Amsterdam", "country": "NL", "org": "VPN Provider"}'
        )

        with patch.object(tester, '_run_docker_cmd', return_value=mock_result):
            data = tester.get_container_ip()

        assert data['ip'] == '5.6.7.8'
        assert tester.results['container_ip'] == '5.6.7.8'
        assert tester.results['location']['city'] == 'Amsterdam'

    def test_get_container_ip_failure(self):
        """Test container IP retrieval failure."""
        tester = vpn_speedtest.VPNSpeedTest('dummy', json_output=True)

        mock_result = MagicMock(returncode=1, stdout='')

        with patch.object(tester, '_run_docker_cmd', return_value=mock_result):
            data = tester.get_container_ip()

        assert data is None

    def test_get_container_ip_invalid_json(self):
        """Test container IP with invalid JSON response."""
        tester = vpn_speedtest.VPNSpeedTest('dummy', json_output=True)

        mock_result = MagicMock(returncode=0, stdout='invalid json')

        with patch.object(tester, '_run_docker_cmd', return_value=mock_result):
            data = tester.get_container_ip()

        assert data is None


class TestRunDockerCmd:
    """Tests for _run_docker_cmd method."""

    @patch('subprocess.run')
    def test_run_docker_cmd_success(self, mock_run):
        """Test successful docker command execution."""
        mock_run.return_value = MagicMock(returncode=0, stdout='output', stderr='')

        tester = vpn_speedtest.VPNSpeedTest('test', json_output=False)
        result = tester._run_docker_cmd(['echo', 'test'])

        assert result.returncode == 0
        assert result.stdout == 'output'
        mock_run.assert_called_once()

    @patch('subprocess.run')
    def test_run_docker_cmd_with_stream_stderr(self, mock_run):
        """Test docker command with stderr streaming."""
        mock_run.return_value = MagicMock(returncode=0)

        tester = vpn_speedtest.VPNSpeedTest('test', json_output=False)
        tester._run_docker_cmd(['curl', 'url'], stream_stderr=True)

        # Verify -t flag is added for streaming
        call_args = mock_run.call_args[0][0]
        assert '-t' in call_args

    @patch('subprocess.run')
    def test_run_docker_cmd_exception(self, mock_run, capsys):
        """Test docker command with exception."""
        mock_run.side_effect = Exception('Docker error')

        tester = vpn_speedtest.VPNSpeedTest('test', json_output=False)
        result = tester._run_docker_cmd(['test'])

        assert result is None
        captured = capsys.readouterr()
        assert 'Docker execution error' in captured.out


class TestRunDownloadTest:
    """Tests for run_download_test method."""

    def test_run_download_test_success(self):
        """Test successful download test."""
        tester = vpn_speedtest.VPNSpeedTest('test', json_output=True)

        # Mock curl output with JSON stats
        curl_json = '{"speed_download": 12500000}'  # 12.5 MB/s = 100 Mbps
        mock_result = MagicMock(returncode=0, stdout=curl_json)

        with patch.object(tester, '_run_docker_cmd', return_value=mock_result):
            tester.run_download_test('100MB')

        assert tester.results['download']['status'] == 'success'
        assert tester.results['download']['speed_mbps'] == 100.0
        assert tester.results['download']['size'] == '100MB'

    def test_run_download_test_failure(self):
        """Test failed download test."""
        tester = vpn_speedtest.VPNSpeedTest('test', json_output=True)

        mock_result = MagicMock(returncode=1, stdout='')

        with patch.object(tester, '_run_docker_cmd', return_value=mock_result):
            tester.run_download_test('100MB')

        assert tester.results['download']['status'] == 'failed'

    def test_run_download_test_invalid_json(self):
        """Test download test with invalid JSON response."""
        tester = vpn_speedtest.VPNSpeedTest('test', json_output=True)

        mock_result = MagicMock(returncode=0, stdout='not json')

        with patch.object(tester, '_run_docker_cmd', return_value=mock_result):
            tester.run_download_test('100MB')

        assert tester.results['download']['status'] == 'failed'


class TestRunUploadTest:
    """Tests for run_upload_test method."""

    def test_run_upload_test_success(self):
        """Test successful upload test."""
        tester = vpn_speedtest.VPNSpeedTest('test', json_output=True)

        # Mock curl output with JSON stats
        curl_json = '{"speed_upload": 6250000}'  # 6.25 MB/s = 50 Mbps

        mock_results = [
            MagicMock(returncode=0),  # dd command
            MagicMock(returncode=0, stdout=curl_json),  # curl upload
            MagicMock(returncode=0)   # rm cleanup
        ]

        with patch.object(tester, '_run_docker_cmd', side_effect=mock_results):
            tester.run_upload_test('25MB')

        assert tester.results['upload']['status'] == 'success'
        assert tester.results['upload']['speed_mbps'] == 50.0

    def test_run_upload_test_failure(self):
        """Test failed upload test."""
        tester = vpn_speedtest.VPNSpeedTest('test', json_output=True)

        mock_results = [
            MagicMock(returncode=0),  # dd
            MagicMock(returncode=1, stdout=''),  # curl fails
            MagicMock(returncode=0)   # rm
        ]

        with patch.object(tester, '_run_docker_cmd', side_effect=mock_results):
            tester.run_upload_test('25MB')

        assert tester.results['upload']['status'] == 'failed'

    def test_run_upload_test_invalid_size(self):
        """Test upload test with invalid size format."""
        tester = vpn_speedtest.VPNSpeedTest('test', json_output=True)

        mock_results = [
            MagicMock(returncode=0),  # dd with fallback size
            MagicMock(returncode=0, stdout='{"speed_upload": 0}'),  # curl
            MagicMock(returncode=0)   # rm
        ]

        with patch.object(tester, '_run_docker_cmd', side_effect=mock_results):
            tester.run_upload_test('invalid')  # Should fallback to 10MB


class TestRun:
    """Tests for run method (main execution)."""

    @patch.object(vpn_speedtest.VPNSpeedTest, 'check_container')
    @patch.object(vpn_speedtest.VPNSpeedTest, 'get_host_ip')
    @patch.object(vpn_speedtest.VPNSpeedTest, 'get_container_ip')
    @patch.object(vpn_speedtest.VPNSpeedTest, 'run_download_test')
    @patch.object(vpn_speedtest.VPNSpeedTest, 'run_upload_test')
    def test_run_vpn_secure(self, mock_ul, mock_dl, mock_container_ip, mock_host_ip, mock_check, capsys):
        """Test run with secure VPN (different IPs)."""
        mock_host_ip.return_value = '1.2.3.4'
        mock_container_ip.return_value = {'ip': '5.6.7.8', 'city': 'Amsterdam', 'country': 'NL', 'org': 'VPN'}

        tester = vpn_speedtest.VPNSpeedTest('test', json_output=False)
        tester.run('100MB', '25MB')

        assert tester.results['vpn_status'] == 'secure'
        captured = capsys.readouterr()
        assert 'SECURE' in captured.out

    @patch.object(vpn_speedtest.VPNSpeedTest, 'check_container')
    @patch.object(vpn_speedtest.VPNSpeedTest, 'get_host_ip')
    @patch.object(vpn_speedtest.VPNSpeedTest, 'get_container_ip')
    @patch.object(vpn_speedtest.VPNSpeedTest, 'run_download_test')
    @patch.object(vpn_speedtest.VPNSpeedTest, 'run_upload_test')
    def test_run_vpn_leaking(self, mock_ul, mock_dl, mock_container_ip, mock_host_ip, mock_check, capsys):
        """Test run with VPN leak (same IPs)."""
        mock_host_ip.return_value = '1.2.3.4'
        mock_container_ip.return_value = {'ip': '1.2.3.4'}

        tester = vpn_speedtest.VPNSpeedTest('test', json_output=False)
        tester.run('100MB', '25MB')

        assert tester.results['vpn_status'] == 'leaking'
        captured = capsys.readouterr()
        assert 'WARNING' in captured.out

    @patch.object(vpn_speedtest.VPNSpeedTest, 'check_container')
    @patch.object(vpn_speedtest.VPNSpeedTest, 'get_host_ip')
    @patch.object(vpn_speedtest.VPNSpeedTest, 'get_container_ip')
    @patch.object(vpn_speedtest.VPNSpeedTest, 'run_download_test')
    @patch.object(vpn_speedtest.VPNSpeedTest, 'run_upload_test')
    def test_run_json_output(self, mock_ul, mock_dl, mock_container_ip, mock_host_ip, mock_check, capsys):
        """Test run with JSON output mode."""
        mock_host_ip.return_value = '1.2.3.4'
        mock_container_ip.return_value = {'ip': '5.6.7.8'}

        tester = vpn_speedtest.VPNSpeedTest('test', json_output=True)
        tester.run('100MB', '25MB')

        captured = capsys.readouterr()
        # Should output valid JSON
        result = json.loads(captured.out)
        assert result['vpn_status'] == 'secure'

    @patch.object(vpn_speedtest.VPNSpeedTest, 'check_container')
    def test_run_keyboard_interrupt(self, mock_check, capsys):
        """Test run handles KeyboardInterrupt."""
        mock_check.side_effect = KeyboardInterrupt()

        tester = vpn_speedtest.VPNSpeedTest('test', json_output=False)

        with pytest.raises(SystemExit) as exc:
            tester.run('100MB', '25MB')

        assert exc.value.code == 130


class TestMain:
    """Tests for main function."""

    @patch('sys.argv', ['vpn_speedtest.py'])
    @patch.object(vpn_speedtest.VPNSpeedTest, 'run')
    def test_main_default_args(self, mock_run):
        """Test main with default arguments."""
        vpn_speedtest.main()

        mock_run.assert_called_once_with(
            vpn_speedtest.DEFAULT_DL_SIZE,
            vpn_speedtest.DEFAULT_UL_SIZE
        )

    @patch('sys.argv', ['vpn_speedtest.py', '--container', 'gluetun', '--dl-size', '200MB', '--ul-size', '50MB', '--json'])
    @patch.object(vpn_speedtest.VPNSpeedTest, 'run')
    def test_main_custom_args(self, mock_run):
        """Test main with custom arguments."""
        vpn_speedtest.main()

        mock_run.assert_called_once_with('200MB', '50MB')
