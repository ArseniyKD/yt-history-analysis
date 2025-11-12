"""Unit tests for analytics query functions."""

import pytest
import sqlite3

from src.db.schema import init_schema
from src.ingest.pipeline import load_json_file, ingest_records
from src.analytics.queries import get_dataset_overview, get_top_channels
from src.constants import SENTINEL_CHANNEL_NAME, SENTINEL_CHANNEL_ID


@pytest.fixture
def analytics_db():
    """In-memory database with analytics_sample.json loaded."""
    conn = sqlite3.connect(':memory:')
    init_schema(conn)

    records = load_json_file('tests/fixtures/analytics_sample.json')
    ingest_records(conn, records)

    yield conn
    conn.close()


@pytest.fixture
def empty_db():
    """Empty in-memory database."""
    conn = sqlite3.connect(':memory:')
    init_schema(conn)
    yield conn
    conn.close()


# Dataset Overview Tests

def test_dataset_overview_normal(analytics_db):
    """Test dataset overview with normal data."""
    result = get_dataset_overview(analytics_db)

    assert result is not None
    assert result['total_views'] > 0
    assert result['unique_videos'] > 0
    assert result['unique_channels'] > 0
    assert result['first_view'] is not None
    assert result['last_view'] is not None

    # Verify date format (YYYY-MM-DD)
    import re
    assert re.match(r'\d{4}-\d{2}-\d{2}', result['first_view'])
    assert re.match(r'\d{4}-\d{2}-\d{2}', result['last_view'])

    # First view should be before or equal to last view
    assert result['first_view'] <= result['last_view']


def test_dataset_overview_empty_database(empty_db):
    """Test dataset overview with empty database."""
    result = get_dataset_overview(empty_db)

    assert result is not None
    assert result['total_views'] == 0
    assert result['unique_videos'] == 0
    assert result['unique_channels'] == 0
    assert result['first_view'] is None
    assert result['last_view'] is None


def test_dataset_overview_includes_deleted(analytics_db):
    """Test that dataset overview includes deleted videos."""
    result = get_dataset_overview(analytics_db)

    # Get count of deleted videos
    cursor = analytics_db.cursor()
    cursor.execute("""
        SELECT COUNT(*)
        FROM views v
        WHERE v.channel_id = ?
    """, (SENTINEL_CHANNEL_ID,))
    deleted_view_count = cursor.fetchone()[0]

    # Deleted videos should exist in test fixture
    assert deleted_view_count > 0

    # Total views in result should include deleted videos
    cursor.execute("SELECT COUNT(*) FROM views")
    total_in_db = cursor.fetchone()[0]
    assert result['total_views'] == total_in_db
    assert result['total_views'] >= deleted_view_count


# Top Channels Tests

def test_top_channels_ordering(analytics_db):
    """Test that top channels are ordered by view count descending."""
    channels = get_top_channels(analytics_db, limit=10)

    assert len(channels) > 0

    # Verify descending order
    for i in range(len(channels) - 1):
        assert channels[i]['total_views'] >= channels[i + 1]['total_views']


def test_top_channels_limit_respected(analytics_db):
    """Test that limit parameter is respected."""
    # Test various limits
    for limit in [5, 10, 20, 100]:
        channels = get_top_channels(analytics_db, limit=limit)
        assert len(channels) <= limit


def test_top_channels_exclude_deleted_by_default(analytics_db):
    """Test that deleted videos are excluded by default (include_deleted=False)."""
    channels = get_top_channels(analytics_db, limit=100, include_deleted=False)

    # Sentinel channel should NOT be in results
    for channel in channels:
        assert channel['channel_id'] != SENTINEL_CHANNEL_ID
        assert channel['channel_name'] != SENTINEL_CHANNEL_NAME


def test_top_channels_exclude_deleted_implicit(analytics_db):
    """Test that deleted videos are excluded when include_deleted not specified."""
    channels = get_top_channels(analytics_db, limit=100)

    # Sentinel channel should NOT be in results
    for channel in channels:
        assert channel['channel_id'] != SENTINEL_CHANNEL_ID
        assert channel['channel_name'] != SENTINEL_CHANNEL_NAME


def test_top_channels_include_deleted_explicit(analytics_db):
    """Test that deleted videos are included when include_deleted=True."""
    channels = get_top_channels(analytics_db, limit=100, include_deleted=True)

    # Sentinel channel MUST be in results
    channel_ids = [ch['channel_id'] for ch in channels]
    channel_names = [ch['channel_name'] for ch in channels]
    assert SENTINEL_CHANNEL_ID in channel_ids
    assert SENTINEL_CHANNEL_NAME in channel_names


def test_top_channels_include_deleted_count_difference(analytics_db):
    """Test that include_deleted affects the channel count."""
    channels_without_deleted = get_top_channels(analytics_db, limit=100, include_deleted=False)
    channels_with_deleted = get_top_channels(analytics_db, limit=100, include_deleted=True)

    # with_deleted should have exactly one more channel (the sentinel)
    assert len(channels_with_deleted) == len(channels_without_deleted) + 1


def test_top_channels_aggregates_correct(analytics_db):
    """Test that per-channel aggregates are correct."""
    channels = get_top_channels(analytics_db, limit=1)

    assert len(channels) > 0
    top_channel = channels[0]

    # Verify aggregates match database
    cursor = analytics_db.cursor()
    cursor.execute("""
        SELECT COUNT(*), COUNT(DISTINCT v.video_id)
        FROM views v
        JOIN channels c ON v.channel_id = c.channel_id
        WHERE c.channel_name = ?
    """, (top_channel['channel_name'],))

    row = cursor.fetchone()
    assert top_channel['total_views'] == row[0]
    assert top_channel['unique_videos'] == row[1]


def test_top_channels_date_format(analytics_db):
    """Test that dates are formatted as YYYY-MM."""
    channels = get_top_channels(analytics_db, limit=10)

    assert len(channels) > 0

    import re
    for channel in channels:
        assert re.match(r'\d{4}-\d{2}', channel['first_view'])
        assert re.match(r'\d{4}-\d{2}', channel['last_view'])


def test_top_channels_includes_channel_id(analytics_db):
    """Test that channel_id is included in results."""
    channels = get_top_channels(analytics_db, limit=10)

    assert len(channels) > 0

    for channel in channels:
        assert 'channel_id' in channel
        assert channel['channel_id'] is not None
        assert isinstance(channel['channel_id'], str)
        assert len(channel['channel_id']) > 0


def test_top_channels_empty_database(empty_db):
    """Test top channels with empty database."""
    channels = get_top_channels(empty_db, limit=10)

    assert channels == []


def test_top_channels_single_channel(empty_db):
    """Test top channels with single channel."""
    # Insert a single view
    cursor = empty_db.cursor()
    cursor.execute("INSERT INTO channels (channel_id, channel_name) VALUES (?, ?)",
                  ("TEST_ID", "Test Channel"))
    cursor.execute("INSERT INTO videos (video_id, title, channel_id) VALUES (?, ?, ?)",
                  ("vid123", "Test Video", "TEST_ID"))
    cursor.execute("INSERT INTO views (video_id, channel_id, timestamp) VALUES (?, ?, ?)",
                  ("vid123", "TEST_ID", "2024-01-01T00:00:00Z"))
    empty_db.commit()

    channels = get_top_channels(empty_db, limit=10)

    assert len(channels) == 1
    assert channels[0]['channel_id'] == "TEST_ID"
    assert channels[0]['channel_name'] == "Test Channel"
    assert channels[0]['total_views'] == 1


def test_top_channels_limit_larger_than_count(analytics_db):
    """Test that requesting more channels than exist returns all channels."""
    channels = get_top_channels(analytics_db, limit=1000)

    # Should return all channels (30 in analytics_sample.json, minus deleted by default)
    cursor = analytics_db.cursor()
    cursor.execute("SELECT COUNT(DISTINCT channel_id) FROM channels WHERE channel_id != ?",
                  (SENTINEL_CHANNEL_ID,))
    expected_count = cursor.fetchone()[0]

    assert len(channels) == expected_count
