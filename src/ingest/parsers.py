"""Parsing utilities for YouTube history records."""

from typing import Optional
from urllib.parse import urlparse, parse_qs

from src.constants import SENTINEL_CHANNEL_ID, SENTINEL_CHANNEL_NAME


def is_video_record(record: dict) -> bool:
    """
    Check if a record is a video (not a post or other content).

    Uses URL structure to determine content type:
    - Videos contain '/watch?v=' in titleUrl
    - Posts contain '/post/' in titleUrl

    Returns True for video records, False otherwise.
    """
    title_url = record.get("titleUrl", "")
    return "/watch?v=" in title_url


def clean_title(title: str) -> str:
    """
    Remove 'Watched ' prefix from video titles.

    All video records should have 'Watched ' prefix. Posts (with 'Viewed ' prefix)
    should be filtered out before calling this function.

    Raises AssertionError if 'Viewed ' prefix is found (indicates filtering bug).
    """
    VIDEO_PREFIX = "Watched "

    if title.startswith(VIDEO_PREFIX):
        return title[len(VIDEO_PREFIX) :]

    # If we see "Viewed", posts weren't filtered properly
    if title.startswith("Viewed "):
        raise AssertionError(f"Unexpected 'Viewed' prefix in video title: {title}")

    # No recognized prefix - unexpected but not fatal, return as-is
    return title


def extract_video_id(url: str) -> str:
    """
    Extract video ID from YouTube watch URL.

    Example: https://www.youtube.com/watch?v=dQw4w9WgXcQ
    Returns: dQw4w9WgXcQ

    Raises ValueError if URL is malformed or doesn't contain video ID.
    """
    parsed = urlparse(url)

    # Ensure this is a YouTube watch URL
    if "/watch" not in parsed.path:
        raise ValueError(f"Not a valid YouTube watch URL: {url}")

    # Extract video ID from query parameters
    query_params = parse_qs(parsed.query)
    video_ids = query_params.get("v", [])

    if len(video_ids) != 1:
        raise ValueError(
            f"Expected exactly one video ID, found {len(video_ids)}: {url}"
        )

    return video_ids[0]


def extract_channel_id(url: str) -> str:
    """
    Extract channel ID from YouTube channel URL.

    Example: https://www.youtube.com/channel/UCXuqSBlHAE6Xw-yeJA0Tunw
    Returns: UCXuqSBlHAE6Xw-yeJA0Tunw

    Raises ValueError if URL is malformed or doesn't contain channel ID.
    """
    parsed = urlparse(url)

    # Ensure this is a YouTube channel URL
    if "/channel/" not in parsed.path:
        raise ValueError(f"Not a valid YouTube channel URL: {url}")

    # Extract channel ID from path (format: /channel/<channel_id>)
    path_parts = parsed.path.split("/")

    if "channel" not in path_parts:
        raise ValueError(f"Invalid channel URL structure: {url}")

    channel_idx = path_parts.index("channel")
    if channel_idx + 1 >= len(path_parts):
        raise ValueError(f"Channel ID not found in URL: {url}")

    channel_id = path_parts[channel_idx + 1]
    if not channel_id:
        raise ValueError(f"Channel ID not found in URL: {url}")

    return channel_id


def parse_record(record: dict) -> Optional[tuple[str, str, str, str, str]]:
    """
    Parse a single YouTube history record.

    Returns tuple of (video_id, title, channel_id, channel_name, timestamp) if record is a video.
    Returns None if record is not a video (e.g., it's a post).

    Tuple contents:
    - video_id: Extracted from titleUrl
    - title: Cleaned title (action prefix stripped)
    - channel_id: Extracted from subtitles[0].url, or sentinel if missing
    - channel_name: Extracted from subtitles[0].name, or sentinel if missing
    - timestamp: ISO8601 timestamp from 'time' field

    Raises ValueError if:
    - Required fields are missing
    - URLs are malformed
    """
    # Check if this is a video record
    if not is_video_record(record):
        return None

    # Extract video ID
    title_url = record.get("titleUrl")
    if not title_url:
        raise ValueError("Missing titleUrl field")
    video_id = extract_video_id(title_url)

    # Clean title
    raw_title = record.get("title")
    if not raw_title:
        raise ValueError("Missing title field")
    title = clean_title(raw_title)

    # Initialize to sentinel values (default for deleted/private videos)
    channel_id = SENTINEL_CHANNEL_ID
    channel_name = SENTINEL_CHANNEL_NAME

    # Update if channel info exists
    subtitles = record.get("subtitles", [])
    if subtitles and len(subtitles) > 0:
        channel_url = subtitles[0].get("url")
        channel_name_raw = subtitles[0].get("name")

        if channel_url and channel_name_raw:
            channel_id = extract_channel_id(channel_url)
            channel_name = channel_name_raw

    # Extract timestamp
    timestamp = record.get("time")
    if not timestamp:
        raise ValueError("Missing time field")

    return (video_id, title, channel_id, channel_name, timestamp)
