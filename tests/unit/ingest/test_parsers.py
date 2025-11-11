"""Unit tests for YouTube history record parsers."""

import pytest
from src.ingest.parsers import (
    is_video_record,
    clean_title,
    extract_video_id,
    extract_channel_id,
    parse_record,
)
from src.constants import SENTINEL_CHANNEL_ID, SENTINEL_CHANNEL_NAME


def test_is_video_record_with_video():
    """Test that video records are correctly identified."""
    record = {"titleUrl": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}
    assert is_video_record(record) is True


def test_is_video_record_with_post():
    """Test that post records are correctly identified."""
    record = {"titleUrl": "https://www.youtube.com/post/UgkxJ9sgOk6qEOPECSGXqFaqqGdiKrgG5uJJ"}
    assert is_video_record(record) is False


def test_is_video_record_with_missing_url():
    """Test that records with missing titleUrl are not identified as videos."""
    record = {}
    assert is_video_record(record) is False


def test_clean_title_with_watched_prefix():
    """Test that 'Watched ' prefix is removed from video titles."""
    assert clean_title("Watched Amazing Video Title") == "Amazing Video Title"


def test_clean_title_with_viewed_prefix():
    """Test that 'Viewed ' prefix raises AssertionError (indicates filtering bug)."""
    with pytest.raises(AssertionError, match="Unexpected 'Viewed' prefix"):
        clean_title("Viewed Some Post Title")


def test_clean_title_without_prefix():
    """Test that titles without prefix are returned as-is."""
    assert clean_title("No Prefix Title") == "No Prefix Title"


def test_extract_video_id_valid():
    """Test extracting video ID from valid YouTube watch URL."""
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert extract_video_id(url) == "dQw4w9WgXcQ"


def test_extract_video_id_with_extra_params():
    """Test extracting video ID when URL has additional query parameters."""
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42s"
    assert extract_video_id(url) == "dQw4w9WgXcQ"


def test_extract_video_id_missing_v_param():
    """Test that missing 'v' parameter raises ValueError."""
    url = "https://www.youtube.com/watch?foo=bar"
    with pytest.raises(ValueError, match="Expected exactly one video ID"):
        extract_video_id(url)


def test_extract_video_id_not_watch_url():
    """Test that non-watch URLs raise ValueError."""
    url = "https://www.youtube.com/post/UgkxJ9sgOk6qEOPECSGXqFaqqGdiKrgG5uJJ"
    with pytest.raises(ValueError, match="Not a valid YouTube watch URL"):
        extract_video_id(url)


def test_extract_channel_id_valid():
    """Test extracting channel ID from valid YouTube channel URL."""
    url = "https://www.youtube.com/channel/UCXuqSBlHAE6Xw-yeJA0Tunw"
    assert extract_channel_id(url) == "UCXuqSBlHAE6Xw-yeJA0Tunw"


def test_extract_channel_id_missing_id():
    """Test that channel URL without ID raises ValueError."""
    url = "https://www.youtube.com/channel/"
    with pytest.raises(ValueError, match="Channel ID not found"):
        extract_channel_id(url)


def test_extract_channel_id_not_channel_url():
    """Test that non-channel URLs raise ValueError."""
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    with pytest.raises(ValueError, match="Not a valid YouTube channel URL"):
        extract_channel_id(url)


def test_parse_record_normal_video():
    """Test parsing a normal video record with all fields present."""
    record = {
        "title": "Watched Amazing Video",
        "titleUrl": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "subtitles": [
            {
                "name": "Test Channel",
                "url": "https://www.youtube.com/channel/UCXuqSBlHAE6Xw-yeJA0Tunw"
            }
        ],
        "time": "2025-01-15T12:30:45.123Z"
    }

    result = parse_record(record)
    assert result is not None
    video_id, title, channel_id, channel_name, timestamp = result

    assert video_id == "dQw4w9WgXcQ"
    assert title == "Amazing Video"
    assert channel_id == "UCXuqSBlHAE6Xw-yeJA0Tunw"
    assert channel_name == "Test Channel"
    assert timestamp == "2025-01-15T12:30:45.123Z"


def test_parse_record_deleted_video_no_subtitles():
    """Test parsing a video with no subtitles (deleted/private video)."""
    record = {
        "title": "Watched https://www.youtube.com/watch?v=deletedvid",
        "titleUrl": "https://www.youtube.com/watch?v=deletedvid",
        "time": "2017-07-22T18:19:06.589Z"
    }

    result = parse_record(record)
    assert result is not None
    video_id, title, channel_id, channel_name, timestamp = result

    assert video_id == "deletedvid"
    assert channel_id == SENTINEL_CHANNEL_ID
    assert channel_name == SENTINEL_CHANNEL_NAME


def test_parse_record_deleted_video_empty_subtitles():
    """Test parsing a video with empty subtitles list."""
    record = {
        "title": "Watched Some Video",
        "titleUrl": "https://www.youtube.com/watch?v=test123",
        "subtitles": [],
        "time": "2020-01-01T00:00:00.000Z"
    }

    result = parse_record(record)
    assert result is not None
    video_id, title, channel_id, channel_name, timestamp = result

    assert channel_id == SENTINEL_CHANNEL_ID
    assert channel_name == SENTINEL_CHANNEL_NAME


def test_parse_record_post_returns_none():
    """Test that parsing a post record returns None."""
    record = {
        "title": "Viewed A fantastic day with fellow tech creators!",
        "titleUrl": "https://www.youtube.com/post/UgkxJ9sgOk6qEOPECSGXqFaqqGdiKrgG5uJJ",
        "subtitles": [
            {
                "name": "Linus Tech Tips",
                "url": "https://www.youtube.com/channel/UCXuqSBlHAE6Xw-yeJA0Tunw"
            }
        ],
        "time": "2025-08-01T23:57:08.949Z"
    }

    result = parse_record(record)
    assert result is None


def test_parse_record_missing_title_url():
    """Test that missing titleUrl returns None (not a video)."""
    record = {
        "title": "Watched Some Video",
        "time": "2020-01-01T00:00:00.000Z"
    }

    result = parse_record(record)
    assert result is None


def test_parse_record_missing_title():
    """Test that missing title raises ValueError."""
    record = {
        "titleUrl": "https://www.youtube.com/watch?v=test123",
        "time": "2020-01-01T00:00:00.000Z"
    }

    with pytest.raises(ValueError, match="Missing title field"):
        parse_record(record)


def test_parse_record_missing_timestamp():
    """Test that missing timestamp raises ValueError."""
    record = {
        "title": "Watched Some Video",
        "titleUrl": "https://www.youtube.com/watch?v=test123"
    }

    with pytest.raises(ValueError, match="Missing time field"):
        parse_record(record)
