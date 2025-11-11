"""Data ingestion pipeline for YouTube history JSON."""

import json
import sqlite3
from pathlib import Path
from typing import Dict, List

from src.db.schema import init_schema
from src.ingest.parsers import parse_record


def load_json_file(json_path: str) -> List[dict]:
    """
    Load and parse YouTube history JSON file.

    Returns list of record dictionaries.

    Raises:
    - FileNotFoundError: If JSON file doesn't exist
    - json.JSONDecodeError: If JSON is malformed
    """
    json_file = Path(json_path)
    if not json_file.exists():
        raise FileNotFoundError(f"JSON file not found: {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def ingest_records(conn: sqlite3.Connection, records: List[dict]) -> Dict[str, int]:
    """
    Ingest YouTube history records into database.

    Process:
    1. Filter and parse records (videos only, skip posts)
    2. Insert into DB (channels → videos → views)
    3. Transaction handling (commit all or rollback)

    Parameters:
    - conn: Active SQLite connection (schema must be initialized)
    - records: List of YouTube history record dictionaries

    Returns dict with ingestion statistics:
    - records_total: Total records provided
    - records_processed: Video records successfully ingested
    - records_skipped: Non-video records (posts, etc.)
    - channels_inserted: Unique channels added
    - videos_inserted: Unique videos added
    - views_inserted: Total views added

    Raises:
    - sqlite3.Error: If database operation fails
    """
    # Track statistics
    stats = {
        "records_total": len(records),
        "records_processed": 0,
        "records_skipped": 0,
        "channels_inserted": 0,
        "videos_inserted": 0,
        "views_inserted": 0,
    }

    # Track unique channels and videos for INSERT OR IGNORE counting
    channels_seen = set()
    videos_seen = set()

    cursor = conn.cursor()

    try:
        # Process each record within a transaction
        for record in records:
            parsed = parse_record(record)

            # Skip non-video records (posts, etc.)
            if parsed is None:
                stats["records_skipped"] += 1
                continue

            video_id, title, channel_id, channel_name, timestamp = parsed

            # Insert channel (if not exists)
            if channel_id not in channels_seen:
                cursor.execute(
                    "INSERT OR IGNORE INTO channels (channel_id, channel_name) VALUES (?, ?)",
                    (channel_id, channel_name),
                )
                if cursor.rowcount > 0:
                    stats["channels_inserted"] += 1
                channels_seen.add(channel_id)

            # Insert video (if not exists)
            if video_id not in videos_seen:
                cursor.execute(
                    "INSERT OR IGNORE INTO videos (video_id, title, channel_id) VALUES (?, ?, ?)",
                    (video_id, title, channel_id),
                )
                if cursor.rowcount > 0:
                    stats["videos_inserted"] += 1
                videos_seen.add(video_id)

            # Insert view (always insert - every watch is a distinct view)
            cursor.execute(
                "INSERT INTO views (video_id, channel_id, timestamp) VALUES (?, ?, ?)",
                (video_id, channel_id, timestamp),
            )
            stats["views_inserted"] += 1
            stats["records_processed"] += 1

        # Commit transaction
        conn.commit()

        return stats

    except Exception as e:
        # Rollback on any error
        conn.rollback()
        raise


def ingest_json_file(db_path: str, json_path: str) -> None:
    """
    Convenience function: Load JSON file and ingest into database.

    Combines load_json_file() and ingest_records() with database setup.
    Suitable for command-line tools and high-level operations.

    Prints ingestion statistics to stdout.

    Raises:
    - FileNotFoundError: If JSON file doesn't exist
    - json.JSONDecodeError: If JSON is malformed
    - sqlite3.Error: If database operation fails
    """
    records = load_json_file(json_path)

    conn = sqlite3.connect(db_path)
    try:
        init_schema(conn)
        stats = ingest_records(conn, records)

        # Print statistics
        print(f"Ingestion complete:")
        print(f"  Total records: {stats['records_total']}")
        print(f"  Videos processed: {stats['records_processed']}")
        print(f"  Records skipped: {stats['records_skipped']}")
        print(f"  Channels inserted: {stats['channels_inserted']}")
        print(f"  Videos inserted: {stats['videos_inserted']}")
        print(f"  Views inserted: {stats['views_inserted']}")
    finally:
        conn.close()
