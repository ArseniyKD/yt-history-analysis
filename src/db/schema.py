"""Database schema definition and initialization."""

import sqlite3

from src.constants import SENTINEL_CHANNEL_ID, SENTINEL_CHANNEL_NAME


def init_schema(conn: sqlite3.Connection) -> None:
    """
    Initialize database schema with all tables and indexes.

    Creates:
    - channels table
    - videos table
    - views table
    - Indexes for query optimization
    - Sentinel channel record

    Safe to call multiple times (uses CREATE TABLE IF NOT EXISTS).
    """
    cursor = conn.cursor()

    # Create channels table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS channels (
            channel_id TEXT PRIMARY KEY,
            channel_name TEXT NOT NULL
        )
    """
    )

    # Create videos table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS videos (
            video_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            channel_id TEXT NOT NULL,
            FOREIGN KEY (channel_id) REFERENCES channels(channel_id)
        )
    """
    )

    # Create views table (denormalized channel_id for query performance)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS views (
            view_id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id TEXT NOT NULL,
            channel_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (video_id) REFERENCES videos(video_id),
            FOREIGN KEY (channel_id) REFERENCES channels(channel_id)
        )
    """
    )

    # Create indexes for query optimization
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_views_channel
        ON views(channel_id)
    """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_views_channel_timestamp
        ON views(channel_id, timestamp)
    """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_views_timestamp
        ON views(timestamp)
    """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_views_year
        ON views(strftime('%Y', timestamp))
    """
    )

    # Insert sentinel channel (if not exists)
    cursor.execute(
        """
        INSERT OR IGNORE INTO channels (channel_id, channel_name)
        VALUES (?, ?)
    """,
        (SENTINEL_CHANNEL_ID, SENTINEL_CHANNEL_NAME),
    )

    conn.commit()


def drop_all_tables(conn: sqlite3.Connection) -> None:
    """
    Drop all tables from database.

    Used for re-ingest scenarios in V1.
    Order matters: drop child tables before parent tables to avoid FK violations.
    Indexes are automatically dropped with their associated tables.
    """
    cursor = conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS views")
    cursor.execute("DROP TABLE IF EXISTS videos")
    cursor.execute("DROP TABLE IF EXISTS channels")

    conn.commit()
