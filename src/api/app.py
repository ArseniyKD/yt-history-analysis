"""Flask web application for YouTube watch history analytics."""

import argparse
import logging
import sqlite3
import time
from flask import Flask, render_template, request

from src.analytics import queries
from src.constants import SENTINEL_CHANNEL_ID

logger = logging.getLogger(__name__)

# Global configuration (set by create_app factory)
DB_PATH = None
DEBUG_MODE = False


def get_channel_url(channel_id: str) -> str | None:
    """
    Construct YouTube channel URL from channel ID.

    Returns None for sentinel channel (deleted videos have no URL).
    """
    if channel_id == SENTINEL_CHANNEL_ID:
        return None
    return f"https://www.youtube.com/channel/{channel_id}"


def get_video_url(video_id: str) -> str | None:
    """
    Construct YouTube video URL from video ID.

    Returns None for deleted videos (no valid video_id).
    """
    if not video_id or video_id == "deleted":
        return None
    return f"https://www.youtube.com/watch?v={video_id}"


def get_db_connection():
    """Get database connection with Row factory for dict-like access."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# Module-level app instance for decorator syntax
app = Flask(
    __name__,
    template_folder="../frontend/templates",
    static_folder="../frontend/static",
    static_url_path="/static",
)


@app.route("/")
def index():
    """
    Landing page showing dataset summary statistics.
    """
    start_time = time.time()
    logger.debug("Index request")

    # Execute query
    conn = get_db_connection()
    try:
        overview_data = queries.get_dataset_overview(conn)
        logger.debug(f"Retrieved overview: {overview_data['total_views']} total views")
    except Exception as e:
        logger.error(f"Query execution failed: {e}")
        if DEBUG_MODE:
            breakpoint()
        conn.close()
        raise
    finally:
        conn.close()

    processing_time = time.time() - start_time
    return render_template(
        "index.html", overview=overview_data, processing_time=processing_time
    )


@app.route("/channels", methods=["GET"])
def channels():
    """
    Top channels page with configurable filtering.

    Query parameters:
        - limit: Number of top channels to show (default: 10, range: 1-1000)
        - include_deleted: 'true' to include deleted videos (default: false)
    """
    start_time = time.time()

    # Parse and validate query parameters
    limit = int(request.args.get("limit", 10))
    limit = max(1, min(limit, 1000))  # Bounds check

    include_deleted_param = request.args.get("include_deleted", "false").lower()
    include_deleted = include_deleted_param == "true"

    logger.debug(f"Channels request: limit={limit}, include_deleted={include_deleted}")

    # Execute query
    conn = get_db_connection()
    try:
        top_channels = queries.get_top_channels(conn, limit, include_deleted)
        logger.debug(f"Retrieved {len(top_channels)} channels")

        # Add channel URLs to each channel
        for channel in top_channels:
            channel["channel_url"] = get_channel_url(channel["channel_id"])

    except Exception as e:
        logger.error(f"Query execution failed: {e}")
        if DEBUG_MODE:
            breakpoint()
        conn.close()
        raise
    finally:
        conn.close()

    processing_time = time.time() - start_time
    return render_template(
        "channels.html",
        channels=top_channels,
        current_limit=limit,
        include_deleted=include_deleted,
        processing_time=processing_time,
    )


@app.route("/years")
def years():
    """
    Per-year analysis page showing summary statistics for each year.
    """
    start_time = time.time()
    logger.debug("Years request")

    # Execute query
    conn = get_db_connection()
    try:
        per_year_data = queries.get_per_year_summary(conn)
        logger.debug(f"Retrieved {len(per_year_data)} years of data")
    except Exception as e:
        logger.error(f"Query execution failed: {e}")
        if DEBUG_MODE:
            breakpoint()
        conn.close()
        raise
    finally:
        conn.close()

    processing_time = time.time() - start_time
    return render_template(
        "years.html", years=per_year_data, processing_time=processing_time
    )


@app.route("/temporal")
def temporal():
    """
    Monthly trends page showing view counts aggregated by month.
    """
    start_time = time.time()
    logger.debug("Temporal request")

    # Execute query
    conn = get_db_connection()
    try:
        monthly_data = queries.get_monthly_view_counts(conn)
        logger.debug(f"Retrieved {len(monthly_data)} months of data")
    except Exception as e:
        logger.error(f"Query execution failed: {e}")
        if DEBUG_MODE:
            breakpoint()
        conn.close()
        raise
    finally:
        conn.close()

    processing_time = time.time() - start_time
    return render_template(
        "temporal.html", monthly_data=monthly_data, processing_time=processing_time
    )


@app.route("/month-views")
def month_views():
    """
    Monthly views page showing all views for a specific month.

    Query parameters:
        - year: Year to filter by (optional, defaults to most recent month)
        - month: Month to filter by (1-12) (optional, defaults to most recent month)
    """
    from datetime import datetime

    start_time = time.time()

    # Get date range from dataset to determine valid range and default
    conn = get_db_connection()
    try:
        first_dt, last_dt = queries.get_dataset_date_range(conn)
    except Exception as e:
        logger.error(f"Failed to get dataset date range: {e}")
        if DEBUG_MODE:
            breakpoint()
        conn.close()
        raise

    # Handle empty database
    if first_dt is None or last_dt is None:
        conn.close()
        return "No data available in database", 404

    # Default to most recent month
    default_year = last_dt.year
    default_month = last_dt.month

    # Parse year parameter
    year = default_year
    year_param = request.args.get("year")
    if year_param:
        try:
            year = int(year_param)
        except ValueError:
            logger.warning(f"Invalid year: {year_param}, using default {default_year}")
            year = default_year

    # Parse month parameter
    month = default_month
    month_param = request.args.get("month")
    if month_param:
        try:
            month = int(month_param)
        except ValueError:
            logger.warning(
                f"Invalid month: {month_param}, using default {default_month}"
            )
            month = default_month

    # Validate month is 1-12
    if month < 1 or month > 12:
        logger.warning(
            f"Month {month} out of range (1-12), using default {default_month}"
        )
        month = default_month

    # Validate year/month is within dataset range
    requested_date = datetime(year, month, 1)
    first_month = datetime(first_dt.year, first_dt.month, 1)
    last_month = datetime(last_dt.year, last_dt.month, 1)

    if requested_date < first_month or requested_date > last_month:
        logger.warning(
            f"Requested {year}-{month:02d} out of dataset range "
            f"({first_dt.year}-{first_dt.month:02d} to {last_dt.year}-{last_dt.month:02d}), "
            f"using default {default_year}-{default_month:02d}"
        )
        year = default_year
        month = default_month

    logger.debug(f"Month-views request: year={year}, month={month}")

    # Execute query
    try:
        views = queries.get_videos_for_month(conn, year, month)
        logger.debug(f"Retrieved {len(views)} views for {year}-{month:02d}")

        # Add URLs to each view
        for view in views:
            view["video_url"] = get_video_url(view["video_id"])
            view["channel_url"] = get_channel_url(view["channel_id"])

    except Exception as e:
        logger.error(f"Query execution failed: {e}")
        if DEBUG_MODE:
            breakpoint()
        conn.close()
        raise
    finally:
        conn.close()

    # Build year range for dropdown
    min_year = first_dt.year
    max_year = last_dt.year
    available_years = list(range(min_year, max_year + 1))
    available_years.reverse()  # Most recent first

    processing_time = time.time() - start_time
    return render_template(
        "month_views.html",
        year=year,
        month=month,
        views=views,
        available_years=available_years,
        processing_time=processing_time,
    )


@app.route("/year-channels")
def year_channels():
    """
    Top channels for a specific year with configurable filtering.

    Query parameters:
        - year: Year to filter by (optional, defaults to most recent year)
        - limit: Number of top channels to show (default: 10, range: 1-1000)
        - include_deleted: 'true' to include deleted videos (default: false)
    """
    start_time = time.time()

    # Get year range from dataset to determine valid years and default
    conn = get_db_connection()
    try:
        first_dt, last_dt = queries.get_dataset_date_range(conn)
    except Exception as e:
        logger.error(f"Failed to get dataset date range: {e}")
        if DEBUG_MODE:
            breakpoint()
        conn.close()
        raise

    # Handle empty database
    if first_dt is None or last_dt is None:
        conn.close()
        return "No data available in database", 404

    min_year = first_dt.year
    max_year = last_dt.year
    default_year = max_year  # Default to most recent year

    # Parse and validate year parameter
    year_param = request.args.get("year")
    if year_param:
        try:
            year = int(year_param)
            # Validate year is in range, use default if out of range
            if year < min_year or year > max_year:
                logger.warning(
                    f"Year {year} out of range ({min_year}-{max_year}), using default {default_year}"
                )
                year = default_year
        except ValueError:
            logger.warning(
                f"Invalid year parameter: {year_param}, using default {default_year}"
            )
            year = default_year
    else:
        year = default_year

    # Parse and validate other query parameters
    limit = int(request.args.get("limit", 10))
    limit = max(1, min(limit, 1000))  # Bounds check

    include_deleted_param = request.args.get("include_deleted", "false").lower()
    include_deleted = include_deleted_param == "true"

    logger.debug(
        f"Year-channels request: year={year}, limit={limit}, include_deleted={include_deleted}"
    )

    # Execute query
    try:
        top_channels = queries.get_top_channels_for_year(
            conn, year, limit, include_deleted
        )
        logger.debug(f"Retrieved {len(top_channels)} channels for year {year}")

        # Add channel URLs to each channel
        for channel in top_channels:
            channel["channel_url"] = get_channel_url(channel["channel_id"])

    except Exception as e:
        logger.error(f"Query execution failed: {e}")
        if DEBUG_MODE:
            breakpoint()
        conn.close()
        raise
    finally:
        conn.close()

    # Build year range for dropdown (all years in dataset range)
    available_years = list(range(min_year, max_year + 1))
    available_years.reverse()  # Most recent first

    processing_time = time.time() - start_time
    return render_template(
        "year_channels.html",
        year=year,
        channels=top_channels,
        current_limit=limit,
        include_deleted=include_deleted,
        available_years=available_years,
        processing_time=processing_time,
    )


def create_app(db_path: str, debug: bool = False, verbose: bool = False):
    """
    Factory function to create configured Flask app.

    Args:
        db_path: Path to SQLite database file
        debug: Enable Flask debug mode and breakpoint() on errors
        verbose: Enable verbose logging (DEBUG level for all loggers)

    Returns:
        Configured Flask application instance
    """
    global DB_PATH, DEBUG_MODE
    DB_PATH = db_path
    DEBUG_MODE = debug

    # Configure logging level based on verbose flag
    log_level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=log_level, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    # Configure Flask debug mode
    app.config["DEBUG"] = debug

    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="YouTube Watch History Analysis Web Server"
    )
    parser.add_argument("--db", required=True, help="Path to SQLite database")
    parser.add_argument(
        "--port", type=int, default=8000, help="Port number (default: 8000)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable Flask debug mode and breakpoint() on errors",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Enable verbose logging (DEBUG level)"
    )
    args = parser.parse_args()

    application = create_app(args.db, debug=args.debug, verbose=args.verbose)
    application.run(host="127.0.0.1", port=args.port, debug=args.debug)
