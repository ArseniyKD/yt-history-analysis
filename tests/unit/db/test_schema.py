"""Unit tests for database schema initialization."""

import sqlite3
import pytest
from src.db.schema import init_schema, drop_all_tables, SENTINEL_CHANNEL_ID, SENTINEL_CHANNEL_NAME


@pytest.fixture
def db_conn():
    """Create an in-memory SQLite database for testing."""
    conn = sqlite3.connect(":memory:")
    yield conn
    conn.close()


def test_init_schema_creates_all_tables(db_conn):
    """Test that init_schema creates all required tables."""
    init_schema(db_conn)

    cursor = db_conn.cursor()

    # Query sqlite_master to check tables exist
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name IN ('channels', 'videos', 'views')
        ORDER BY name
    """)

    tables = [row[0] for row in cursor.fetchall()]
    assert tables == ['channels', 'videos', 'views']


def test_init_schema_creates_indexes(db_conn):
    """Test that init_schema creates all required indexes."""
    init_schema(db_conn)

    cursor = db_conn.cursor()

    # Query sqlite_master to check indexes exist
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='index' AND name LIKE 'idx_views_%'
        ORDER BY name
    """)

    indexes = [row[0] for row in cursor.fetchall()]
    expected = ['idx_views_channel', 'idx_views_channel_timestamp', 'idx_views_timestamp']
    assert indexes == expected


def test_init_schema_inserts_sentinel_channel(db_conn):
    """Test that init_schema creates the sentinel NO_CHANNEL record."""
    init_schema(db_conn)

    cursor = db_conn.cursor()
    cursor.execute("SELECT channel_id, channel_name FROM channels WHERE channel_id = ?",
                   (SENTINEL_CHANNEL_ID,))

    row = cursor.fetchone()
    assert row is not None
    assert row[0] == SENTINEL_CHANNEL_ID
    assert row[1] == SENTINEL_CHANNEL_NAME


def test_init_schema_idempotent(db_conn):
    """Test that init_schema can be called multiple times safely."""
    init_schema(db_conn)
    init_schema(db_conn)  # Second call should not fail

    cursor = db_conn.cursor()

    # Verify only one sentinel channel exists
    cursor.execute("SELECT COUNT(*) FROM channels WHERE channel_id = ?",
                   (SENTINEL_CHANNEL_ID,))
    count = cursor.fetchone()[0]
    assert count == 1


def test_drop_all_tables(db_conn):
    """Test that drop_all_tables removes all tables."""
    init_schema(db_conn)
    drop_all_tables(db_conn)

    cursor = db_conn.cursor()
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name IN ('channels', 'videos', 'views')
    """)

    tables = cursor.fetchall()
    assert len(tables) == 0


def test_drop_all_tables_removes_indexes(db_conn):
    """Test that dropping tables also removes associated indexes."""
    init_schema(db_conn)
    drop_all_tables(db_conn)

    cursor = db_conn.cursor()
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='index' AND name LIKE 'idx_views_%'
    """)

    indexes = cursor.fetchall()
    assert len(indexes) == 0


def test_channels_table_schema(db_conn):
    """Test channels table has correct columns."""
    init_schema(db_conn)

    cursor = db_conn.cursor()
    cursor.execute("PRAGMA table_info(channels)")
    columns = {row[1]: row[2] for row in cursor.fetchall()}  # name: type

    assert 'channel_id' in columns
    assert 'channel_name' in columns
    assert columns['channel_id'] == 'TEXT'
    assert columns['channel_name'] == 'TEXT'


def test_videos_table_schema(db_conn):
    """Test videos table has correct columns."""
    init_schema(db_conn)

    cursor = db_conn.cursor()
    cursor.execute("PRAGMA table_info(videos)")
    columns = {row[1]: row[2] for row in cursor.fetchall()}  # name: type

    assert 'video_id' in columns
    assert 'title' in columns
    assert 'channel_id' in columns
    assert columns['video_id'] == 'TEXT'
    assert columns['title'] == 'TEXT'
    assert columns['channel_id'] == 'TEXT'


def test_views_table_schema(db_conn):
    """Test views table has correct columns."""
    init_schema(db_conn)

    cursor = db_conn.cursor()
    cursor.execute("PRAGMA table_info(views)")
    columns = {row[1]: row[2] for row in cursor.fetchall()}  # name: type

    assert 'view_id' in columns
    assert 'video_id' in columns
    assert 'channel_id' in columns
    assert 'timestamp' in columns
    assert columns['view_id'] == 'INTEGER'
    assert columns['video_id'] == 'TEXT'
    assert columns['channel_id'] == 'TEXT'
    assert columns['timestamp'] == 'TEXT'
