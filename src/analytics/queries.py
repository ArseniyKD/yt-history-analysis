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
            - total_rewatches: int (unique videos that were watched 2+ times)

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
                "total_rewatches": 0,
            }

        # Format dates (YYYY-MM-DD)
        first_view = None
        last_view = None
        if row[0]:
            first_view = datetime.fromisoformat(row[0].replace("Z", "+00:00")).strftime(
                "%Y-%m-%d"
            )
        if row[1]:
            last_view = datetime.fromisoformat(row[1].replace("Z", "+00:00")).strftime(
                "%Y-%m-%d"
            )

        # Get total rewatches
        total_rewatches = get_total_rewatches(db_conn)

        result = {
            "first_view": first_view,
            "last_view": last_view,
            "total_views": row[2],
            "unique_videos": row[3],
            "unique_channels": row[4],
            "total_rewatches": total_rewatches,
        }

        logger.debug(
            f"Retrieved overview: {result['total_views']} views, "
            f"{result['first_view']} to {result['last_view']}"
        )

        return result

    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise


def get_top_channels(
    db_conn: sqlite3.Connection, limit: int, include_deleted: bool = False
) -> list[dict]:
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
            - rewatches: int (unique videos rewatched from this channel)
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
            # Get rewatch count for this channel
            rewatch_count = get_channel_rewatches(db_conn, row[0])

            # Format dates (YYYY-MM)
            first_view = None
            last_view = None
            if row[4]:
                first_view = datetime.fromisoformat(
                    row[4].replace("Z", "+00:00")
                ).strftime("%Y-%m")
            if row[5]:
                last_view = datetime.fromisoformat(
                    row[5].replace("Z", "+00:00")
                ).strftime("%Y-%m")

            results.append(
                {
                    "channel_id": row[0],
                    "channel_name": row[1],
                    "total_views": row[2],
                    "unique_videos": row[3],
                    "rewatches": rewatch_count,
                    "first_view": first_view,
                    "last_view": last_view,
                }
            )

        logger.debug(f"Retrieved {len(results)} channels")

        return results

    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise


def get_dataset_date_range(
    db_conn: sqlite3.Connection,
) -> tuple[datetime | None, datetime | None]:
    """
    Get the earliest and latest timestamps in the dataset as datetime objects.

    Args:
        db_conn: SQLite database connection

    Returns:
        tuple: (first_datetime, last_datetime)
            Both are datetime objects, or (None, None) if database is empty
    """
    logger.debug("get_dataset_date_range()")

    query = "SELECT MIN(timestamp), MAX(timestamp) FROM views"

    try:
        cursor = db_conn.cursor()
        cursor.execute(query)
        row = cursor.fetchone()

        if not row or not row[0] or not row[1]:
            logger.debug("Empty database, returning (None, None)")
            return (None, None)

        first_dt = datetime.fromisoformat(row[0].replace("Z", "+00:00"))
        last_dt = datetime.fromisoformat(row[1].replace("Z", "+00:00"))

        logger.debug(f"Date range: {first_dt} to {last_dt}")
        return (first_dt, last_dt)

    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise


def _count_rewatches(
    db_conn: sqlite3.Connection, channel_id: str | None = None, year: int | None = None
) -> int:
    """
    Helper to count unique videos that were watched multiple times.

    Args:
        db_conn: SQLite database connection
        channel_id: Optional channel filter
        year: Optional year filter

    Returns:
        int: Number of unique videos that were rewatched
    """
    # Build WHERE clause based on filters
    where_clauses = []
    params = []

    if channel_id is not None:
        where_clauses.append("channel_id = ?")
        params.append(channel_id)

    if year is not None:
        where_clauses.append("strftime('%Y', timestamp) = ?")
        params.append(str(year))

    where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

    query = f"""
        SELECT COUNT(*) as rewatch_count
        FROM (
            SELECT video_id
            FROM views
            {where_sql}
            GROUP BY video_id
            HAVING COUNT(*) > 1
        )
    """

    try:
        cursor = db_conn.cursor()
        cursor.execute(query, params)
        row = cursor.fetchone()
        return row[0] if row and row[0] is not None else 0

    except Exception as e:
        filter_desc = []
        if channel_id:
            filter_desc.append(f"channel_id={channel_id}")
        if year:
            filter_desc.append(f"year={year}")
        filters = ", ".join(filter_desc) if filter_desc else "no filters"
        logger.error(f"Failed to count rewatches ({filters}): {e}")
        raise


def get_total_rewatches(db_conn: sqlite3.Connection) -> int:
    """
    Get count of unique videos that were watched multiple times across entire dataset.

    Returns:
        int: Number of unique videos that were rewatched
    """
    logger.debug("get_total_rewatches()")
    count = _count_rewatches(db_conn)
    logger.debug(f"Total unique videos rewatched: {count}")
    return count


def get_channel_rewatches(
    db_conn: sqlite3.Connection, channel_id: str, year: int | None = None
) -> int:
    """
    Get count of unique videos rewatched for a specific channel.

    Args:
        db_conn: SQLite database connection
        channel_id: Channel ID to query
        year: Optional year filter

    Returns:
        int: Number of unique videos from this channel that were rewatched
    """
    logger.debug(f"get_channel_rewatches(channel_id={channel_id}, year={year})")
    count = _count_rewatches(db_conn, channel_id=channel_id, year=year)
    logger.debug(f"Channel {channel_id} unique videos rewatched: {count}")
    return count


def get_year_rewatches(db_conn: sqlite3.Connection, year: int) -> int:
    """
    Get count of unique videos rewatched in a specific year.

    Args:
        db_conn: SQLite database connection
        year: Year to query

    Returns:
        int: Number of unique videos rewatched in that year
    """
    logger.debug(f"get_year_rewatches(year={year})")
    count = _count_rewatches(db_conn, year=year)
    logger.debug(f"Year {year} unique videos rewatched: {count}")
    return count


def get_per_year_summary(db_conn: sqlite3.Connection) -> list[dict]:
    """
    Get summary statistics for each year in the dataset.

    Calculates year range from dataset date range, then returns stats
    for all years in that range (even if no data for a specific year).

    Returns:
        List of dicts, each containing:
            - year: int
            - total_views: int
            - unique_videos: int
            - unique_channels: int
            - rewatches: int (unique videos rewatched in that year)
            - first_view: str (YYYY-MM-DD format) or None if no data for year
            - last_view: str (YYYY-MM-DD format) or None if no data for year

        Ordered by year DESC (most recent first).
        Returns empty list if database is empty.
    """
    logger.debug("get_per_year_summary()")

    # Get year range from dataset
    first_dt, last_dt = get_dataset_date_range(db_conn)

    if first_dt is None or last_dt is None:
        logger.debug("Empty database, returning empty year summary")
        return []

    min_year = first_dt.year
    max_year = last_dt.year
    logger.debug(f"Year range: {min_year} to {max_year}")

    # Build summary for each year
    results = []
    for year in range(min_year, max_year + 1):
        year_query = """
            SELECT
                COUNT(*) as total_views,
                COUNT(DISTINCT video_id) as unique_videos,
                COUNT(DISTINCT channel_id) as unique_channels,
                MIN(timestamp) as first_view,
                MAX(timestamp) as last_view
            FROM views
            WHERE strftime('%Y', timestamp) = ?
        """

        try:
            cursor = db_conn.cursor()
            cursor.execute(year_query, (str(year),))
            year_row = cursor.fetchone()
        except Exception as e:
            logger.error(f"Failed to query year statistics for year {year}: {e}")
            raise

        # Get rewatch count for this year
        try:
            rewatch_count = get_year_rewatches(db_conn, year)
        except Exception as e:
            logger.error(f"Failed to query rewatch count for year {year}: {e}")
            raise

        # Format dates if data exists
        first_view = None
        last_view = None
        if year_row and year_row[3]:
            first_view = datetime.fromisoformat(
                year_row[3].replace("Z", "+00:00")
            ).strftime("%Y-%m-%d")
        if year_row and year_row[4]:
            last_view = datetime.fromisoformat(
                year_row[4].replace("Z", "+00:00")
            ).strftime("%Y-%m-%d")

        results.append(
            {
                "year": year,
                "total_views": year_row[0] if year_row else 0,
                "unique_videos": year_row[1] if year_row else 0,
                "unique_channels": year_row[2] if year_row else 0,
                "rewatches": rewatch_count,
                "first_view": first_view,
                "last_view": last_view,
            }
        )

    # Sort by year descending (most recent first)
    results.sort(key=lambda x: x["year"], reverse=True)

    logger.debug(f"Retrieved summary for {len(results)} years")
    return results


def get_top_channels_for_year(
    db_conn: sqlite3.Connection, year: int, limit: int, include_deleted: bool = False
) -> list[dict]:
    """
    Get top N channels for a specific year, ranked by total view count.

    Args:
        db_conn: SQLite database connection
        year: Year to filter by
        limit: Maximum number of channels to return
        include_deleted: If True, include sentinel "Deleted Videos" pseudo-channel

    Returns:
        List of dicts, each containing:
            - channel_id: str
            - channel_name: str
            - total_views: int
            - unique_videos: int
            - rewatches: int (unique videos rewatched from this channel in this year)
            - first_view: str (YYYY-MM format)
            - last_view: str (YYYY-MM format)

        Ordered by total_views DESC, limited to `limit` rows.
    """
    logger.debug(
        f"get_top_channels_for_year(year={year}, limit={limit}, include_deleted={include_deleted})"
    )

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
        WHERE strftime('%Y', v.timestamp) = ?
          AND (c.channel_id != ? OR ? = 1)
        GROUP BY c.channel_id, c.channel_name
        ORDER BY total_views DESC
        LIMIT ?
    """

    try:
        cursor = db_conn.cursor()
        cursor.execute(
            query, (str(year), SENTINEL_CHANNEL_ID, int(include_deleted), limit)
        )
        rows = cursor.fetchall()
    except Exception as e:
        logger.error(
            f"Failed to query top channels for year {year} "
            f"(limit={limit}, include_deleted={include_deleted}): {e}"
        )
        raise

    results = []
    for row in rows:
        # Get rewatch count for this channel in this year
        try:
            rewatch_count = get_channel_rewatches(db_conn, row[0], year=year)
        except Exception as e:
            logger.error(
                f"Failed to query rewatch count for channel {row[0]} in year {year}: {e}"
            )
            raise

        # Format dates (YYYY-MM)
        first_view = None
        last_view = None
        if row[4]:
            first_view = datetime.fromisoformat(row[4].replace("Z", "+00:00")).strftime(
                "%Y-%m"
            )
        if row[5]:
            last_view = datetime.fromisoformat(row[5].replace("Z", "+00:00")).strftime(
                "%Y-%m"
            )

        results.append(
            {
                "channel_id": row[0],
                "channel_name": row[1],
                "total_views": row[2],
                "unique_videos": row[3],
                "rewatches": rewatch_count,
                "first_view": first_view,
                "last_view": last_view,
            }
        )

    logger.debug(f"Retrieved {len(results)} channels for year {year}")
    return results
