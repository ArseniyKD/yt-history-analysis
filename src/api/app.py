"""Flask web application for YouTube watch history analytics."""

import argparse
import logging
import sqlite3
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


def get_db_connection():
    """Get database connection with Row factory for dict-like access."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# Module-level app instance for decorator syntax
app = Flask(__name__, template_folder='../frontend/templates')


@app.route('/')
def index():
    """
    Landing page showing dataset summary statistics.
    """
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

    return render_template('index.html', overview=overview_data)


@app.route('/channels', methods=['GET'])
def channels():
    """
    Top channels page with configurable filtering.

    Query parameters:
        - limit: Number of top channels to show (default: 10, range: 1-1000)
        - include_deleted: 'true' to include deleted videos (default: false)
    """
    # Parse and validate query parameters
    limit = int(request.args.get('limit', 10))
    limit = max(1, min(limit, 1000))  # Bounds check

    include_deleted_param = request.args.get('include_deleted', 'false').lower()
    include_deleted = include_deleted_param == 'true'

    logger.debug(f"Channels request: limit={limit}, include_deleted={include_deleted}")

    # Execute query
    conn = get_db_connection()
    try:
        top_channels = queries.get_top_channels(conn, limit, include_deleted)
        logger.debug(f"Retrieved {len(top_channels)} channels")

        # Add channel URLs to each channel
        for channel in top_channels:
            channel['channel_url'] = get_channel_url(channel['channel_id'])

    except Exception as e:
        logger.error(f"Query execution failed: {e}")
        if DEBUG_MODE:
            breakpoint()
        conn.close()
        raise
    finally:
        conn.close()

    return render_template('channels.html',
                          channels=top_channels,
                          current_limit=limit,
                          include_deleted=include_deleted)


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
        level=log_level,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    )

    # Configure Flask debug mode
    app.config['DEBUG'] = debug

    return app


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='YouTube Watch History Analysis Web Server')
    parser.add_argument('--db', required=True, help='Path to SQLite database')
    parser.add_argument('--port', type=int, default=8000, help='Port number (default: 8000)')
    parser.add_argument('--debug', action='store_true',
                       help='Enable Flask debug mode and breakpoint() on errors')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose logging (DEBUG level)')
    args = parser.parse_args()

    application = create_app(args.db, debug=args.debug, verbose=args.verbose)
    application.run(host='127.0.0.1', port=args.port, debug=args.debug)
