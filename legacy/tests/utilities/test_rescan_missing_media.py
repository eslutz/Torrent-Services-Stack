"""Tests for rescan_missing_media.py script."""
import pytest
from unittest.mock import patch, MagicMock, call
import sys
import responses
from scripts.utilities import rescan_missing_media


class TestTriggerCommand:
    """Tests for trigger_command function."""

    @responses.activate
    def test_trigger_command_success(self):
        """Test successful command trigger."""
        responses.add(
            responses.POST,
            "http://localhost:8989/api/v3/command",
            json={"id": 123, "name": "RescanSeries"},
            status=200,
        )

        cmd_id = rescan_missing_media.trigger_command(
            "http://localhost:8989", "test_api_key", "RescanSeries"
        )

        assert cmd_id == 123
        assert len(responses.calls) == 1
        assert responses.calls[0].request.url == "http://localhost:8989/api/v3/command"

    @responses.activate
    def test_trigger_command_with_params(self):
        """Test command trigger with additional parameters."""
        responses.add(
            responses.POST,
            "http://localhost:8989/api/v3/command",
            json={"id": 456, "name": "RescanSeries"},
            status=200,
        )

        cmd_id = rescan_missing_media.trigger_command(
            "http://localhost:8989", "test_api_key", "RescanSeries", seriesId=123
        )

        assert cmd_id == 456
        # Verify seriesId was passed in request body
        assert "seriesId" in responses.calls[0].request.body.decode()

    @responses.activate
    def test_trigger_command_failure(self):
        """Test command trigger with API error."""
        responses.add(
            responses.POST,
            "http://localhost:8989/api/v3/command",
            json={"error": "Unauthorized"},
            status=401,
        )

        cmd_id = rescan_missing_media.trigger_command(
            "http://localhost:8989", "bad_key", "RescanSeries"
        )

        assert cmd_id is None


class TestCheckCommandStatus:
    """Tests for check_command_status function."""

    @responses.activate
    def test_check_status_completed(self):
        """Test checking completed command status."""
        responses.add(
            responses.GET,
            "http://localhost:8989/api/v3/command/123",
            json={"id": 123, "status": "completed", "message": "Success"},
            status=200,
        )

        status, msg = rescan_missing_media.check_command_status(
            "http://localhost:8989", "test_api_key", 123
        )

        assert status == "completed"
        assert msg == "Success"

    @responses.activate
    def test_check_status_queued(self):
        """Test checking queued command status."""
        responses.add(
            responses.GET,
            "http://localhost:8989/api/v3/command/456",
            json={"id": 456, "status": "queued", "message": ""},
            status=200,
        )

        status, msg = rescan_missing_media.check_command_status(
            "http://localhost:8989", "test_api_key", 456
        )

        assert status == "queued"
        assert msg == ""

    @responses.activate
    def test_check_status_failure(self):
        """Test handling API error when checking status."""
        responses.add(
            responses.GET,
            "http://localhost:8989/api/v3/command/789",
            status=500,
        )

        status, msg = rescan_missing_media.check_command_status(
            "http://localhost:8989", "test_api_key", 789
        )

        assert status is None
        assert "500" in msg or "Server Error" in msg or msg != ""


class TestGetMissingItems:
    """Tests for get_missing_items function."""

    @responses.activate
    def test_get_missing_series(self):
        """Test getting missing episodes for series."""
        responses.add(
            responses.GET,
            "http://localhost:8989/api/v3/wanted/missing",
            json={
                "records": [
                    {"id": 1, "title": "Episode 1"},
                    {"id": 2, "title": "Episode 2"},
                ],
                "totalRecords": 2,
            },
            status=200,
        )

        count, items = rescan_missing_media.get_missing_items(
            "http://localhost:8989", "test_api_key", "series"
        )

        assert count == 2
        assert len(items) == 2
        assert items[0]["title"] == "Episode 1"

    @responses.activate
    def test_get_missing_movies(self):
        """Test getting missing movies."""
        responses.add(
            responses.GET,
            "http://localhost:7878/api/v3/movie",
            json=[
                {"id": 1, "title": "Movie 1", "hasFile": False},
                {"id": 2, "title": "Movie 2", "hasFile": True},
                {"id": 3, "title": "Movie 3", "hasFile": False},
            ],
            status=200,
        )

        count, items = rescan_missing_media.get_missing_items(
            "http://localhost:7878", "test_api_key", "movie"
        )

        assert count == 2  # Only movies without files
        assert len(items) == 2
        assert all(not m["hasFile"] for m in items)

    @responses.activate
    def test_get_missing_items_empty(self):
        """Test getting missing items when none exist."""
        responses.add(
            responses.GET,
            "http://localhost:8989/api/v3/wanted/missing",
            json={"records": [], "totalRecords": 0},
            status=200,
        )

        count, items = rescan_missing_media.get_missing_items(
            "http://localhost:8989", "test_api_key", "series"
        )

        assert count == 0
        assert len(items) == 0


class TestRescanSonarr:
    """Tests for rescan_sonarr function."""

    @responses.activate
    @patch("scripts.utilities.rescan_missing_media.time.sleep")
    def test_rescan_sonarr_success(self, mock_sleep):
        """Test successful Sonarr rescan without search."""
        # Mock getting missing count before rescan
        responses.add(
            responses.GET,
            "http://localhost:8989/api/v3/wanted/missing",
            json={"records": [{"id": 1}], "totalRecords": 1},
            status=200,
        )

        # Mock triggering rescan command
        responses.add(
            responses.POST,
            "http://localhost:8989/api/v3/command",
            json={"id": 123, "name": "RescanSeries"},
            status=200,
        )

        # Mock checking command status (completed)
        responses.add(
            responses.GET,
            "http://localhost:8989/api/v3/command/123",
            json={"id": 123, "status": "completed", "message": "Done"},
            status=200,
        )

        # Mock getting missing count after rescan
        responses.add(
            responses.GET,
            "http://localhost:8989/api/v3/wanted/missing",
            json={"records": [], "totalRecords": 0},
            status=200,
        )

        rescan_missing_media.rescan_sonarr("test_api_key", search_missing=False)

        # Verify all API calls were made
        assert len(responses.calls) == 4

    @responses.activate
    @patch("scripts.utilities.rescan_missing_media.time.sleep")
    def test_rescan_sonarr_with_search(self, mock_sleep):
        """Test Sonarr rescan with automatic search."""
        # Mock getting missing count before
        responses.add(
            responses.GET,
            "http://localhost:8989/api/v3/wanted/missing",
            json={"records": [{"id": 1}, {"id": 2}], "totalRecords": 2},
            status=200,
        )

        # Mock rescan command
        responses.add(
            responses.POST,
            "http://localhost:8989/api/v3/command",
            json={"id": 123, "name": "RescanSeries"},
            status=200,
        )

        # Mock command status check
        responses.add(
            responses.GET,
            "http://localhost:8989/api/v3/command/123",
            json={"id": 123, "status": "completed"},
            status=200,
        )

        # Mock getting missing count after (still missing)
        responses.add(
            responses.GET,
            "http://localhost:8989/api/v3/wanted/missing",
            json={"records": [{"id": 1}, {"id": 2}], "totalRecords": 2},
            status=200,
        )

        # Mock search command
        responses.add(
            responses.POST,
            "http://localhost:8989/api/v3/command",
            json={"id": 124, "name": "MissingEpisodeSearch"},
            status=200,
        )

        rescan_missing_media.rescan_sonarr("test_api_key", search_missing=True)

        # Verify search was triggered
        assert len(responses.calls) == 5
        assert any("MissingEpisodeSearch" in str(c.request.body) for c in responses.calls)


class TestRescanRadarr:
    """Tests for rescan_radarr function."""

    @responses.activate
    @patch("scripts.utilities.rescan_missing_media.time.sleep")
    def test_rescan_radarr_success(self, mock_sleep):
        """Test successful Radarr rescan."""
        # Mock getting movies before rescan
        responses.add(
            responses.GET,
            "http://localhost:7878/api/v3/movie",
            json=[{"id": 1, "hasFile": False}, {"id": 2, "hasFile": True}],
            status=200,
        )

        # Mock rescan command
        responses.add(
            responses.POST,
            "http://localhost:7878/api/v3/command",
            json={"id": 456, "name": "RescanMovie"},
            status=200,
        )

        # Mock command status
        responses.add(
            responses.GET,
            "http://localhost:7878/api/v3/command/456",
            json={"id": 456, "status": "completed"},
            status=200,
        )

        # Mock getting movies after rescan (file found)
        responses.add(
            responses.GET,
            "http://localhost:7878/api/v3/movie",
            json=[{"id": 1, "hasFile": True}, {"id": 2, "hasFile": True}],
            status=200,
        )

        rescan_missing_media.rescan_radarr("test_api_key", search_missing=False)

        assert len(responses.calls) == 4


class TestMainFunction:
    """Tests for main function and CLI argument parsing."""

    @patch("scripts.utilities.rescan_missing_media.rescan_sonarr")
    @patch("scripts.utilities.rescan_missing_media.rescan_radarr")
    @patch("scripts.utilities.rescan_missing_media.get_api_key")
    def test_main_both_services(self, mock_get_key, mock_radarr, mock_sonarr):
        """Test main with both services."""
        mock_get_key.side_effect = ["sonarr_key", "radarr_key"]

        with patch("sys.argv", ["rescan_missing_media.py"]):
            rescan_missing_media.main()

        mock_sonarr.assert_called_once_with("sonarr_key", False)
        mock_radarr.assert_called_once_with("radarr_key", False)

    @patch("scripts.utilities.rescan_missing_media.rescan_sonarr")
    @patch("scripts.utilities.rescan_missing_media.get_api_key")
    def test_main_sonarr_only(self, mock_get_key, mock_sonarr):
        """Test main with Sonarr only."""
        mock_get_key.return_value = "sonarr_key"

        with patch("sys.argv", ["rescan_missing_media.py", "--service", "sonarr"]):
            rescan_missing_media.main()

        mock_sonarr.assert_called_once_with("sonarr_key", False)

    @patch("scripts.utilities.rescan_missing_media.rescan_radarr")
    @patch("scripts.utilities.rescan_missing_media.get_api_key")
    def test_main_radarr_only(self, mock_get_key, mock_radarr):
        """Test main with Radarr only."""
        mock_get_key.return_value = "radarr_key"

        with patch("sys.argv", ["rescan_missing_media.py", "--service", "radarr"]):
            rescan_missing_media.main()

        mock_radarr.assert_called_once_with("radarr_key", False)

    @patch("scripts.utilities.rescan_missing_media.rescan_sonarr")
    @patch("scripts.utilities.rescan_missing_media.get_api_key")
    def test_main_with_search_flag(self, mock_get_key, mock_sonarr):
        """Test main with --search flag."""
        mock_get_key.return_value = "sonarr_key"

        with patch("sys.argv", ["rescan_missing_media.py", "--service", "sonarr", "--search"]):
            rescan_missing_media.main()

        mock_sonarr.assert_called_once_with("sonarr_key", True)

    @patch("scripts.utilities.rescan_missing_media.rescan_sonarr")
    @patch("scripts.utilities.rescan_missing_media.get_api_key")
    def test_main_keyboard_interrupt(self, mock_get_key, mock_sonarr):
        """Test main handles KeyboardInterrupt gracefully."""
        mock_get_key.return_value = "sonarr_key"
        mock_sonarr.side_effect = KeyboardInterrupt()

        with patch("sys.argv", ["rescan_missing_media.py", "--service", "sonarr"]):
            with pytest.raises(SystemExit) as exc:
                rescan_missing_media.main()
            assert exc.value.code == 130

    @patch("scripts.utilities.rescan_missing_media.rescan_sonarr")
    @patch("scripts.utilities.rescan_missing_media.get_api_key")
    def test_main_unexpected_error(self, mock_get_key, mock_sonarr):
        """Test main handles unexpected errors."""
        mock_get_key.return_value = "sonarr_key"
        mock_sonarr.side_effect = Exception("Something went wrong")

        with patch("sys.argv", ["rescan_missing_media.py", "--service", "sonarr"]):
            with pytest.raises(SystemExit) as exc:
                rescan_missing_media.main()
            assert exc.value.code == 1
