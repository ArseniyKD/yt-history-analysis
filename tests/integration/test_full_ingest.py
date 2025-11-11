"""Integration tests for full ingest pipeline."""

import sqlite3
import pytest
from src.ingest.pipeline import ingest_records, load_json_file
from src.db.schema import init_schema
from src.constants import SENTINEL_CHANNEL_ID


@pytest.fixture
def db_conn():
    """Create an in-memory SQLite database for testing."""
    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    yield conn
    conn.close()


def test_ingest_sample_data_file(db_conn):
    """Test ingesting the committed sample data file."""
    # Load test fixture
    records = load_json_file("tests/fixtures/data_sample.json")

    # Ingest records
    stats = ingest_records(db_conn, records)

    # Verify statistics
    assert stats["records_total"] == 9
    assert stats["records_processed"] == 7  # 7 videos, 2 posts
    assert stats["records_skipped"] == 2  # 2 posts

    # Verify data was inserted
    cursor = db_conn.cursor()

    # Check channel count (unique channels + NO_CHANNEL sentinel)
    cursor.execute("SELECT COUNT(*) FROM channels")
    channel_count = cursor.fetchone()[0]
    assert channel_count >= 1  # At least sentinel channel

    # Check video count
    cursor.execute("SELECT COUNT(*) FROM videos")
    video_count = cursor.fetchone()[0]
    assert video_count == stats["videos_inserted"]

    # Check view count
    cursor.execute("SELECT COUNT(*) FROM views")
    view_count = cursor.fetchone()[0]
    assert view_count == stats["views_inserted"]
    assert view_count == 7  # All 7 video records should have views


def test_ingest_records_with_deleted_video(db_conn):
    """Test that deleted videos (no channel info) use sentinel channel."""
    records = [
        {
            "title": "Watched https://www.youtube.com/watch?v=deletedvid",
            "titleUrl": "https://www.youtube.com/watch?v=deletedvid",
            "time": "2017-07-22T18:19:06.589Z"
        }
    ]

    stats = ingest_records(db_conn, records)

    assert stats["records_processed"] == 1
    assert stats["views_inserted"] == 1

    # Verify sentinel channel was used
    cursor = db_conn.cursor()
    cursor.execute("""
        SELECT channel_id FROM views WHERE video_id = 'deletedvid'
    """)
    channel_id = cursor.fetchone()[0]
    assert channel_id == SENTINEL_CHANNEL_ID


def test_ingest_records_with_duplicate_videos(db_conn):
    """Test that watching the same video multiple times creates multiple views."""
    records = [
        {
            "title": "Watched Test Video",
            "titleUrl": "https://www.youtube.com/watch?v=test123",
            "subtitles": [{"name": "Test Channel", "url": "https://www.youtube.com/channel/UCtest123"}],
            "time": "2024-01-01T10:00:00.000Z"
        },
        {
            "title": "Watched Test Video",
            "titleUrl": "https://www.youtube.com/watch?v=test123",
            "subtitles": [{"name": "Test Channel", "url": "https://www.youtube.com/channel/UCtest123"}],
            "time": "2024-01-02T15:30:00.000Z"
        }
    ]

    stats = ingest_records(db_conn, records)

    assert stats["records_processed"] == 2
    assert stats["channels_inserted"] == 1  # Only one unique channel
    assert stats["videos_inserted"] == 1  # Only one unique video
    assert stats["views_inserted"] == 2  # Two distinct views

    # Verify two views exist for the same video
    cursor = db_conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM views WHERE video_id = 'test123'")
    view_count = cursor.fetchone()[0]
    assert view_count == 2


def test_ingest_records_filters_posts(db_conn):
    """Test that post records are filtered out and not ingested."""
    records = [
        {
            "title": "Viewed A fantastic day with fellow tech creators!",
            "titleUrl": "https://www.youtube.com/post/UgkxJ9sgOk6qEOPECSGXqFaqqGdiKrgG5uJJ",
            "subtitles": [{"name": "Linus Tech Tips", "url": "https://www.youtube.com/channel/UCtest"}],
            "time": "2025-08-01T23:57:08.949Z"
        }
    ]

    stats = ingest_records(db_conn, records)

    assert stats["records_total"] == 1
    assert stats["records_processed"] == 0
    assert stats["records_skipped"] == 1

    # Verify nothing was inserted (except sentinel channel from init_schema)
    cursor = db_conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM videos")
    assert cursor.fetchone()[0] == 0
    cursor.execute("SELECT COUNT(*) FROM views")
    assert cursor.fetchone()[0] == 0


def test_ingest_records_denormalizes_channel_id(db_conn):
    """Test that channel_id is denormalized in views table."""
    records = [
        {
            "title": "Watched Test Video",
            "titleUrl": "https://www.youtube.com/watch?v=test123",
            "subtitles": [{"name": "Test Channel", "url": "https://www.youtube.com/channel/UCtest"}],
            "time": "2024-01-01T10:00:00.000Z"
        }
    ]

    ingest_records(db_conn, records)

    cursor = db_conn.cursor()

    # Verify channel_id is in views table (denormalized)
    cursor.execute("SELECT channel_id FROM views WHERE video_id = 'test123'")
    channel_id = cursor.fetchone()[0]
    assert channel_id == "UCtest"

    # Verify it matches the channel in videos table
    cursor.execute("SELECT channel_id FROM videos WHERE video_id = 'test123'")
    video_channel_id = cursor.fetchone()[0]
    assert channel_id == video_channel_id


def test_ingest_records_rollback_on_error(db_conn):
    """Test that transaction rolls back on error."""
    # Malformed record that will cause an error during processing
    records = [
        {
            "title": "Watched Valid Video",
            "titleUrl": "https://www.youtube.com/watch?v=valid123",
            "subtitles": [{"name": "Test", "url": "https://www.youtube.com/channel/UCtest"}],
            "time": "2024-01-01T10:00:00.000Z"
        },
        {
            "title": "Watched Invalid",
            "titleUrl": "https://www.youtube.com/watch?v=invalid",
            # Missing time field - will cause error
        }
    ]

    # Should raise ValueError from missing timestamp
    with pytest.raises(ValueError, match="Missing time field"):
        ingest_records(db_conn, records)

    # Verify nothing was committed (rollback occurred)
    cursor = db_conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM views")
    view_count = cursor.fetchone()[0]
    assert view_count == 0  # No views should exist due to rollback
