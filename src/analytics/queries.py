"""Analytics query functions for YouTube watch history data."""

import logging
import sqlite3
from datetime import datetime

from src.constants import SENTINEL_CHANNEL_ID

logger = logging.getLogger(__name__)


def get_dataset_overview(db_conn: sqlite3.Connection) -> dict:
    """
    Get high-level dataset statistics.

    ALWAYS includes all records (including deleted videos) - this is the
    ground truth of what's in the dataset.

    Args:
        db_conn: SQLite database connection

    Returns:
        dict with keys:
            - first_view: str (YYYY-MM-DD format) or None if empty
            - last_view: str (YYYY-MM-DD format) or None if empty
            - total_views: int
            - unique_videos: int
            - unique_channels: int

        Returns None values if database is empty.
    """
    logger.debug("get_dataset_overview()")

    query = """
        SELECT
            MIN(timestamp) as first_view,
            MAX(timestamp) as last_view,
            COUNT(*) as total_views,
            COUNT(DISTINCT video_id) as unique_videos,
            COUNT(DISTINCT channel_id) as unique_channels
        FROM views
    """

    try:
        cursor = db_conn.cursor()
        cursor.execute(query)
        row = cursor.fetchone()

        # Handle empty database
        if row is None or row[2] == 0:
            logger.debug("Empty database, returning None values")
            return {
                "first_view": None,
                "last_view": None,
                "total_views": 0,
                "unique_videos": 0,
                "unique_channels": 0,
            }

        # Format dates (YYYY-MM-DD)
        first_view = None
        last_view = None
        if row[0]:
            first_view = datetime.fromisoformat(row[0].replace('Z', '+00:00')).strftime('%Y-%m-%d')
        if row[1]:
            last_view = datetime.fromisoformat(row[1].replace('Z', '+00:00')).strftime('%Y-%m-%d')

        result = {
            "first_view": first_view,
            "last_view": last_view,
            "total_views": row[2],
            "unique_videos": row[3],
            "unique_channels": row[4],
        }

        logger.debug(f"Retrieved overview: {result['total_views']} views, "
                    f"{result['first_view']} to {result['last_view']}")

        return result

    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise


def get_top_channels(db_conn: sqlite3.Connection,
                     limit: int,
                     include_deleted: bool = False) -> list[dict]:
    """
    Get top N channels ranked by total view count.

    Args:
        db_conn: SQLite database connection
        limit: Maximum number of channels to return (will be bounds-checked by caller)
        include_deleted: If True, include sentinel "Deleted Videos" pseudo-channel.
                        If False, exclude it from results.

    Returns:
        List of dicts, each containing:
            - channel_id: str
            - channel_name: str
            - total_views: int
            - unique_videos: int
            - first_view: str (YYYY-MM format)
            - last_view: str (YYYY-MM format)

        Ordered by total_views DESC, limited to `limit` rows.
    """
    logger.debug(f"get_top_channels(limit={limit}, include_deleted={include_deleted})")

    query = """
        SELECT
            c.channel_id,
            c.channel_name,
            COUNT(*) as total_views,
            COUNT(DISTINCT v.video_id) as unique_videos,
            MIN(v.timestamp) as first_view,
            MAX(v.timestamp) as last_view
        FROM views v
        JOIN channels c ON v.channel_id = c.channel_id
        WHERE (c.channel_id != ? OR ? = 1)
        GROUP BY c.channel_id, c.channel_name
        ORDER BY total_views DESC
        LIMIT ?
    """

    try:
        cursor = db_conn.cursor()
        cursor.execute(query, (SENTINEL_CHANNEL_ID, int(include_deleted), limit))
        rows = cursor.fetchall()

        results = []
        for row in rows:
            # Format dates (YYYY-MM)
            first_view = None
            last_view = None
            if row[4]:
                first_view = datetime.fromisoformat(row[4].replace('Z', '+00:00')).strftime('%Y-%m')
            if row[5]:
                last_view = datetime.fromisoformat(row[5].replace('Z', '+00:00')).strftime('%Y-%m')

            results.append({
                "channel_id": row[0],
                "channel_name": row[1],
                "total_views": row[2],
                "unique_videos": row[3],
                "first_view": first_view,
                "last_view": last_view,
            })

        logger.debug(f"Retrieved {len(results)} channels")

        return results

    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise
