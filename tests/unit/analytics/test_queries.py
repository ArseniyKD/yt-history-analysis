"""Unit tests for analytics query functions."""

import pytest
import sqlite3

from src.db.schema import init_schema
from src.ingest.pipeline import load_json_file, ingest_records
from src.analytics.queries import (
    get_dataset_overview,
    get_top_channels,
    get_dataset_date_range,
    get_total_rewatches,
    get_channel_rewatches,
    get_year_rewatches,
    get_per_year_summary,
    get_top_channels_for_year,
    get_monthly_view_counts,
    get_videos_for_month,
    _generate_month_range,
)
from src.constants import SENTINEL_CHANNEL_NAME, SENTINEL_CHANNEL_ID


@pytest.fixture
def analytics_db():
    """In-memory database with analytics_sample.json loaded."""
    conn = sqlite3.connect(":memory:")
    init_schema(conn)

    records = load_json_file("tests/fixtures/analytics_sample.json")
    ingest_records(conn, records)

    yield conn
    conn.close()


@pytest.fixture
def empty_db():
    """Empty in-memory database."""
    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    yield conn
    conn.close()


# Dataset Overview Tests


def test_dataset_overview_normal(analytics_db):
    """Test dataset overview with normal data."""
    result = get_dataset_overview(analytics_db)

    assert result is not None
    assert result["total_views"] > 0
    assert result["unique_videos"] > 0
    assert result["unique_channels"] > 0
    assert result["total_rewatches"] >= 0
    assert result["first_view"] is not None
    assert result["last_view"] is not None

    # Verify date format (YYYY-MM-DD)
    import re

    assert re.match(r"\d{4}-\d{2}-\d{2}", result["first_view"])
    assert re.match(r"\d{4}-\d{2}-\d{2}", result["last_view"])

    # First view should be before or equal to last view
    assert result["first_view"] <= result["last_view"]


def test_dataset_overview_empty_database(empty_db):
    """Test dataset overview with empty database."""
    result = get_dataset_overview(empty_db)

    assert result is not None
    assert result["total_views"] == 0
    assert result["unique_videos"] == 0
    assert result["unique_channels"] == 0
    assert result["total_rewatches"] == 0
    assert result["first_view"] is None
    assert result["last_view"] is None


def test_dataset_overview_includes_deleted(analytics_db):
    """Test that dataset overview includes deleted videos."""
    result = get_dataset_overview(analytics_db)

    # Get count of deleted videos
    cursor = analytics_db.cursor()
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM views v
        WHERE v.channel_id = ?
    """,
        (SENTINEL_CHANNEL_ID,),
    )
    deleted_view_count = cursor.fetchone()[0]

    # Deleted videos should exist in test fixture
    assert deleted_view_count > 0

    # Total views in result should include deleted videos
    cursor.execute("SELECT COUNT(*) FROM views")
    total_in_db = cursor.fetchone()[0]
    assert result["total_views"] == total_in_db
    assert result["total_views"] >= deleted_view_count


# Top Channels Tests


def test_top_channels_ordering(analytics_db):
    """Test that top channels are ordered by view count descending."""
    channels = get_top_channels(analytics_db, limit=10)

    assert len(channels) > 0

    # Verify descending order
    for i in range(len(channels) - 1):
        assert channels[i]["total_views"] >= channels[i + 1]["total_views"]


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
        assert channel["channel_id"] != SENTINEL_CHANNEL_ID
        assert channel["channel_name"] != SENTINEL_CHANNEL_NAME


def test_top_channels_exclude_deleted_implicit(analytics_db):
    """Test that deleted videos are excluded when include_deleted not specified."""
    channels = get_top_channels(analytics_db, limit=100)

    # Sentinel channel should NOT be in results
    for channel in channels:
        assert channel["channel_id"] != SENTINEL_CHANNEL_ID
        assert channel["channel_name"] != SENTINEL_CHANNEL_NAME


def test_top_channels_include_deleted_explicit(analytics_db):
    """Test that deleted videos are included when include_deleted=True."""
    channels = get_top_channels(analytics_db, limit=100, include_deleted=True)

    # Sentinel channel MUST be in results
    channel_ids = [ch["channel_id"] for ch in channels]
    channel_names = [ch["channel_name"] for ch in channels]
    assert SENTINEL_CHANNEL_ID in channel_ids
    assert SENTINEL_CHANNEL_NAME in channel_names


def test_top_channels_include_deleted_count_difference(analytics_db):
    """Test that include_deleted affects the channel count."""
    channels_without_deleted = get_top_channels(
        analytics_db, limit=100, include_deleted=False
    )
    channels_with_deleted = get_top_channels(
        analytics_db, limit=100, include_deleted=True
    )

    # with_deleted should have exactly one more channel (the sentinel)
    assert len(channels_with_deleted) == len(channels_without_deleted) + 1


def test_top_channels_aggregates_correct(analytics_db):
    """Test that per-channel aggregates are correct."""
    channels = get_top_channels(analytics_db, limit=1)

    assert len(channels) > 0
    top_channel = channels[0]

    # Verify aggregates match database
    cursor = analytics_db.cursor()
    cursor.execute(
        """
        SELECT COUNT(*), COUNT(DISTINCT v.video_id)
        FROM views v
        JOIN channels c ON v.channel_id = c.channel_id
        WHERE c.channel_name = ?
    """,
        (top_channel["channel_name"],),
    )

    row = cursor.fetchone()
    assert top_channel["total_views"] == row[0]
    assert top_channel["unique_videos"] == row[1]


def test_top_channels_date_format(analytics_db):
    """Test that dates are formatted as YYYY-MM."""
    channels = get_top_channels(analytics_db, limit=10)

    assert len(channels) > 0

    import re

    for channel in channels:
        assert re.match(r"\d{4}-\d{2}", channel["first_view"])
        assert re.match(r"\d{4}-\d{2}", channel["last_view"])


def test_top_channels_includes_channel_id(analytics_db):
    """Test that channel_id is included in results."""
    channels = get_top_channels(analytics_db, limit=10)

    assert len(channels) > 0

    for channel in channels:
        assert "channel_id" in channel
        assert channel["channel_id"] is not None
        assert isinstance(channel["channel_id"], str)
        assert len(channel["channel_id"]) > 0


def test_top_channels_empty_database(empty_db):
    """Test top channels with empty database."""
    channels = get_top_channels(empty_db, limit=10)

    assert channels == []


def test_top_channels_single_channel(empty_db):
    """Test top channels with single channel."""
    # Insert a single view
    cursor = empty_db.cursor()
    cursor.execute(
        "INSERT INTO channels (channel_id, channel_name) VALUES (?, ?)",
        ("TEST_ID", "Test Channel"),
    )
    cursor.execute(
        "INSERT INTO videos (video_id, title, channel_id) VALUES (?, ?, ?)",
        ("vid123", "Test Video", "TEST_ID"),
    )
    cursor.execute(
        "INSERT INTO views (video_id, channel_id, timestamp) VALUES (?, ?, ?)",
        ("vid123", "TEST_ID", "2024-01-01T00:00:00Z"),
    )
    empty_db.commit()

    channels = get_top_channels(empty_db, limit=10)

    assert len(channels) == 1
    assert channels[0]["channel_id"] == "TEST_ID"
    assert channels[0]["channel_name"] == "Test Channel"
    assert channels[0]["total_views"] == 1


def test_top_channels_limit_larger_than_count(analytics_db):
    """Test that requesting more channels than exist returns all channels."""
    channels = get_top_channels(analytics_db, limit=1000)

    # Should return all channels (30 in analytics_sample.json, minus deleted by default)
    cursor = analytics_db.cursor()
    cursor.execute(
        "SELECT COUNT(DISTINCT channel_id) FROM channels WHERE channel_id != ?",
        (SENTINEL_CHANNEL_ID,),
    )
    expected_count = cursor.fetchone()[0]

    assert len(channels) == expected_count


def test_top_channels_includes_rewatches(analytics_db):
    """Test that top channels include rewatches field."""
    channels = get_top_channels(analytics_db, limit=10)

    assert len(channels) > 0
    for channel in channels:
        assert "rewatches" in channel
        assert channel["rewatches"] >= 0


# Dataset Date Range Tests


def test_dataset_date_range_normal(analytics_db):
    """Test dataset date range with normal data."""
    from datetime import datetime

    first_dt, last_dt = get_dataset_date_range(analytics_db)

    assert first_dt is not None
    assert last_dt is not None
    assert isinstance(first_dt, datetime)
    assert isinstance(last_dt, datetime)
    assert first_dt <= last_dt


def test_dataset_date_range_empty(empty_db):
    """Test dataset date range with empty database."""
    first_dt, last_dt = get_dataset_date_range(empty_db)

    assert first_dt is None
    assert last_dt is None


# Rewatch Tests


def test_total_rewatches_normal(analytics_db):
    """Test total rewatches with normal data."""
    count = get_total_rewatches(analytics_db)

    assert count >= 0
    # Should be less than or equal to total unique videos
    cursor = analytics_db.cursor()
    cursor.execute("SELECT COUNT(DISTINCT video_id) FROM views")
    unique_videos = cursor.fetchone()[0]
    assert count <= unique_videos


def test_total_rewatches_empty(empty_db):
    """Test total rewatches with empty database."""
    count = get_total_rewatches(empty_db)
    assert count == 0


def test_total_rewatches_no_rewatches(empty_db):
    """Test total rewatches when all videos watched once."""
    cursor = empty_db.cursor()

    # Insert test channel
    cursor.execute(
        "INSERT INTO channels (channel_id, channel_name) VALUES (?, ?)",
        ("TEST", "Test Channel"),
    )

    # Insert 5 videos, each watched once
    for i in range(5):
        cursor.execute(
            "INSERT INTO videos (video_id, title, channel_id) VALUES (?, ?, ?)",
            (f"vid{i}", f"Video {i}", "TEST"),
        )
        cursor.execute(
            "INSERT INTO views (video_id, channel_id, timestamp) VALUES (?, ?, ?)",
            (f"vid{i}", "TEST", f"2024-01-0{i+1}T00:00:00Z"),
        )
    empty_db.commit()

    count = get_total_rewatches(empty_db)
    assert count == 0


def test_total_rewatches_with_rewatches(empty_db):
    """Test total rewatches when some videos watched multiple times."""
    cursor = empty_db.cursor()

    # Insert test channel
    cursor.execute(
        "INSERT INTO channels (channel_id, channel_name) VALUES (?, ?)",
        ("TEST", "Test Channel"),
    )

    # Insert video watched 3 times
    cursor.execute(
        "INSERT INTO videos (video_id, title, channel_id) VALUES (?, ?, ?)",
        ("vid1", "Video 1", "TEST"),
    )
    for i in range(3):
        cursor.execute(
            "INSERT INTO views (video_id, channel_id, timestamp) VALUES (?, ?, ?)",
            ("vid1", "TEST", f"2024-01-0{i+1}T00:00:00Z"),
        )

    # Insert video watched twice
    cursor.execute(
        "INSERT INTO videos (video_id, title, channel_id) VALUES (?, ?, ?)",
        ("vid2", "Video 2", "TEST"),
    )
    for i in range(2):
        cursor.execute(
            "INSERT INTO views (video_id, channel_id, timestamp) VALUES (?, ?, ?)",
            ("vid2", "TEST", f"2024-02-0{i+1}T00:00:00Z"),
        )

    # Insert video watched once
    cursor.execute(
        "INSERT INTO videos (video_id, title, channel_id) VALUES (?, ?, ?)",
        ("vid3", "Video 3", "TEST"),
    )
    cursor.execute(
        "INSERT INTO views (video_id, channel_id, timestamp) VALUES (?, ?, ?)",
        ("vid3", "TEST", "2024-03-01T00:00:00Z"),
    )

    empty_db.commit()

    # Should count 2 videos as rewatched (vid1 and vid2), not 3 total extra views
    count = get_total_rewatches(empty_db)
    assert count == 2


def test_channel_rewatches_normal(analytics_db):
    """Test channel rewatches with normal data."""
    # Get first channel from top channels
    channels = get_top_channels(analytics_db, limit=1)
    assert len(channels) == 1

    channel_id = channels[0]["channel_id"]
    count = get_channel_rewatches(analytics_db, channel_id)

    assert count >= 0


def test_channel_rewatches_with_year_filter(analytics_db):
    """Test channel rewatches with year filter."""
    channels = get_top_channels(analytics_db, limit=1)
    assert len(channels) == 1

    channel_id = channels[0]["channel_id"]

    # Get rewatches for 2023
    count_2023 = get_channel_rewatches(analytics_db, channel_id, year=2023)
    assert count_2023 >= 0

    # Total rewatches should be >= any single year
    count_total = get_channel_rewatches(analytics_db, channel_id)
    assert count_total >= count_2023


def test_year_rewatches_normal(analytics_db):
    """Test year rewatches with normal data."""
    # Get a year from the dataset
    first_dt, last_dt = get_dataset_date_range(analytics_db)
    assert first_dt is not None

    year = first_dt.year
    count = get_year_rewatches(analytics_db, year)

    assert count >= 0


# Per-Year Summary Tests


def test_per_year_summary_normal(analytics_db):
    """Test per-year summary with normal data."""
    summary = get_per_year_summary(analytics_db)

    assert len(summary) > 0

    # Verify structure of each year entry
    for year_data in summary:
        assert "year" in year_data
        assert "total_views" in year_data
        assert "unique_videos" in year_data
        assert "unique_channels" in year_data
        assert "rewatches" in year_data
        assert "first_view" in year_data
        assert "last_view" in year_data

        assert year_data["total_views"] >= 0
        assert year_data["unique_videos"] >= 0
        assert year_data["unique_channels"] >= 0
        assert year_data["rewatches"] >= 0

    # Verify ordering (most recent first)
    for i in range(len(summary) - 1):
        assert summary[i]["year"] > summary[i + 1]["year"]


def test_per_year_summary_empty(empty_db):
    """Test per-year summary with empty database."""
    summary = get_per_year_summary(empty_db)
    assert len(summary) == 0


def test_per_year_summary_year_range(analytics_db):
    """Test that per-year summary covers full year range."""
    first_dt, last_dt = get_dataset_date_range(analytics_db)
    assert first_dt is not None
    assert last_dt is not None

    min_year = first_dt.year
    max_year = last_dt.year
    expected_years = list(range(min_year, max_year + 1))

    summary = get_per_year_summary(analytics_db)
    actual_years = [y["year"] for y in summary]

    assert sorted(actual_years) == sorted(expected_years)


# Top Channels for Year Tests


def test_top_channels_for_year_normal(analytics_db):
    """Test top channels for year with normal data."""
    # Get a year from the dataset
    first_dt, last_dt = get_dataset_date_range(analytics_db)
    assert first_dt is not None

    year = first_dt.year
    channels = get_top_channels_for_year(analytics_db, year, limit=10)

    assert len(channels) >= 0

    # Verify structure
    for channel in channels:
        assert "channel_id" in channel
        assert "channel_name" in channel
        assert "total_views" in channel
        assert "unique_videos" in channel
        assert "rewatches" in channel
        assert "first_view" in channel
        assert "last_view" in channel

        assert channel["total_views"] > 0
        assert channel["unique_videos"] > 0
        assert channel["rewatches"] >= 0

    # Verify ordering (descending by views)
    for i in range(len(channels) - 1):
        assert channels[i]["total_views"] >= channels[i + 1]["total_views"]


def test_top_channels_for_year_exclude_deleted(analytics_db):
    """Test that deleted videos are excluded by default for year filtering."""
    first_dt, last_dt = get_dataset_date_range(analytics_db)
    assert first_dt is not None

    year = first_dt.year
    channels = get_top_channels_for_year(
        analytics_db, year, limit=100, include_deleted=False
    )

    # Sentinel channel should NOT be in results
    for channel in channels:
        assert channel["channel_id"] != SENTINEL_CHANNEL_ID


def test_top_channels_for_year_include_deleted(analytics_db):
    """Test that deleted videos are included when include_deleted=True for year filtering."""
    first_dt, last_dt = get_dataset_date_range(analytics_db)
    assert first_dt is not None

    year = last_dt.year  # Use most recent year for better chance of deleted videos
    channels = get_top_channels_for_year(
        analytics_db, year, limit=100, include_deleted=True
    )

    # Check if sentinel channel exists in this year
    cursor = analytics_db.cursor()
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM views
        WHERE channel_id = ? AND strftime('%Y', timestamp) = ?
    """,
        (SENTINEL_CHANNEL_ID, str(year)),
    )
    deleted_count_in_year = cursor.fetchone()[0]

    if deleted_count_in_year > 0:
        # Sentinel channel MUST be in results if it has views in this year
        channel_ids = [ch["channel_id"] for ch in channels]
        assert SENTINEL_CHANNEL_ID in channel_ids
    # else: if no deleted videos in this year, test still passes


def test_top_channels_for_year_limit_respected(analytics_db):
    """Test that limit parameter is respected for year filtering."""
    first_dt, last_dt = get_dataset_date_range(analytics_db)
    assert first_dt is not None

    year = first_dt.year

    for limit in [5, 10, 20]:
        channels = get_top_channels_for_year(analytics_db, year, limit=limit)
        assert len(channels) <= limit


# Monthly View Count Tests


def test_generate_month_range_single_month():
    """Test month range generation for single month."""
    from datetime import datetime

    start = datetime(2024, 1, 15)
    end = datetime(2024, 1, 20)

    months = _generate_month_range(start, end)

    assert months == ["2024-01"]


def test_generate_month_range_multiple_months():
    """Test month range generation across multiple months."""
    from datetime import datetime

    start = datetime(2024, 1, 15)
    end = datetime(2024, 3, 20)

    months = _generate_month_range(start, end)

    assert months == ["2024-03", "2024-02", "2024-01"]


def test_generate_month_range_year_boundary():
    """Test month range generation across year boundary."""
    from datetime import datetime

    start = datetime(2023, 11, 15)
    end = datetime(2024, 2, 20)

    months = _generate_month_range(start, end)

    assert months == ["2024-02", "2024-01", "2023-12", "2023-11"]


def test_generate_month_range_multiple_years():
    """Test month range generation across multiple years."""
    from datetime import datetime

    start = datetime(2022, 10, 1)
    end = datetime(2024, 3, 31)

    months = _generate_month_range(start, end)

    # Should have 18 months total (Oct 2022 - Mar 2024)
    assert len(months) == 18
    assert months[0] == "2024-03"  # Most recent first
    assert months[-1] == "2022-10"  # Oldest last


def test_monthly_view_counts_normal(analytics_db):
    """Test monthly view counts with normal data."""
    results = get_monthly_view_counts(analytics_db)

    assert len(results) > 0

    # Verify structure
    for month_data in results:
        assert "month" in month_data
        assert "count" in month_data
        assert month_data["count"] >= 0

        # Verify month format (YYYY-MM)
        import re

        assert re.match(r"\d{4}-\d{2}", month_data["month"])

    # Verify ordering (DESC - most recent first)
    for i in range(len(results) - 1):
        assert results[i]["month"] > results[i + 1]["month"]


def test_monthly_view_counts_empty(empty_db):
    """Test monthly view counts with empty database."""
    results = get_monthly_view_counts(empty_db)
    assert results == []


def test_monthly_view_counts_fills_gaps(empty_db):
    """Test that monthly view counts fills gaps with zeros."""
    cursor = empty_db.cursor()

    # Insert test channel and video
    cursor.execute(
        "INSERT INTO channels (channel_id, channel_name) VALUES (?, ?)",
        ("TEST", "Test Channel"),
    )
    cursor.execute(
        "INSERT INTO videos (video_id, title, channel_id) VALUES (?, ?, ?)",
        ("vid1", "Video 1", "TEST"),
    )

    # Insert views only in Jan and Mar 2024 (skip Feb)
    cursor.execute(
        "INSERT INTO views (video_id, channel_id, timestamp) VALUES (?, ?, ?)",
        ("vid1", "TEST", "2024-01-15T00:00:00Z"),
    )
    cursor.execute(
        "INSERT INTO views (video_id, channel_id, timestamp) VALUES (?, ?, ?)",
        ("vid1", "TEST", "2024-03-15T00:00:00Z"),
    )
    empty_db.commit()

    results = get_monthly_view_counts(empty_db)

    # Should have 3 months: Jan, Feb (gap), Mar
    assert len(results) == 3
    assert results[0]["month"] == "2024-03"
    assert results[0]["count"] == 1
    assert results[1]["month"] == "2024-02"
    assert results[1]["count"] == 0  # Gap filled with zero
    assert results[2]["month"] == "2024-01"
    assert results[2]["count"] == 1


def test_monthly_view_counts_multiple_views_per_month(empty_db):
    """Test monthly view counts with multiple views in same month."""
    cursor = empty_db.cursor()

    # Insert test channel and videos
    cursor.execute(
        "INSERT INTO channels (channel_id, channel_name) VALUES (?, ?)",
        ("TEST", "Test Channel"),
    )
    cursor.execute(
        "INSERT INTO videos (video_id, title, channel_id) VALUES (?, ?, ?)",
        ("vid1", "Video 1", "TEST"),
    )
    cursor.execute(
        "INSERT INTO videos (video_id, title, channel_id) VALUES (?, ?, ?)",
        ("vid2", "Video 2", "TEST"),
    )

    # Insert 3 views in Jan 2024
    cursor.execute(
        "INSERT INTO views (video_id, channel_id, timestamp) VALUES (?, ?, ?)",
        ("vid1", "TEST", "2024-01-05T00:00:00Z"),
    )
    cursor.execute(
        "INSERT INTO views (video_id, channel_id, timestamp) VALUES (?, ?, ?)",
        ("vid2", "TEST", "2024-01-15T00:00:00Z"),
    )
    cursor.execute(
        "INSERT INTO views (video_id, channel_id, timestamp) VALUES (?, ?, ?)",
        ("vid1", "TEST", "2024-01-25T00:00:00Z"),
    )
    empty_db.commit()

    results = get_monthly_view_counts(empty_db)

    assert len(results) == 1
    assert results[0]["month"] == "2024-01"
    assert results[0]["count"] == 3


# Month Drill-Down Tests


def test_videos_for_month_normal(analytics_db):
    """Test get videos for month with normal data."""
    # Get a month from the dataset
    monthly_counts = get_monthly_view_counts(analytics_db)
    assert len(monthly_counts) > 0

    # Pick first month (most recent)
    test_month = monthly_counts[0]["month"]
    year, month = test_month.split("-")

    results = get_videos_for_month(analytics_db, int(year), int(month))

    assert len(results) > 0

    # Verify structure
    for video in results:
        assert "timestamp" in video
        assert "video_id" in video
        assert "title" in video
        assert "channel_id" in video
        assert "channel_name" in video

        assert isinstance(video["timestamp"], str)
        assert isinstance(video["video_id"], str)
        assert isinstance(video["title"], str)
        assert isinstance(video["channel_id"], str)
        assert isinstance(video["channel_name"], str)

    # Verify chronological ordering
    for i in range(len(results) - 1):
        assert results[i]["timestamp"] <= results[i + 1]["timestamp"]


def test_videos_for_month_empty(empty_db):
    """Test get videos for month with empty database."""
    results = get_videos_for_month(empty_db, 2024, 1)
    assert results == []


def test_videos_for_month_no_videos_in_month(empty_db):
    """Test get videos for month when no videos exist in that month."""
    cursor = empty_db.cursor()

    # Insert test data for March 2024
    cursor.execute(
        "INSERT INTO channels (channel_id, channel_name) VALUES (?, ?)",
        ("TEST", "Test Channel"),
    )
    cursor.execute(
        "INSERT INTO videos (video_id, title, channel_id) VALUES (?, ?, ?)",
        ("vid1", "Video 1", "TEST"),
    )
    cursor.execute(
        "INSERT INTO views (video_id, channel_id, timestamp) VALUES (?, ?, ?)",
        ("vid1", "TEST", "2024-03-15T00:00:00Z"),
    )
    empty_db.commit()

    # Query for January (no data)
    results = get_videos_for_month(empty_db, 2024, 1)
    assert results == []


def test_videos_for_month_chronological_order(empty_db):
    """Test that videos are returned in chronological order."""
    cursor = empty_db.cursor()

    # Insert test channel and videos
    cursor.execute(
        "INSERT INTO channels (channel_id, channel_name) VALUES (?, ?)",
        ("TEST", "Test Channel"),
    )
    for i in range(3):
        cursor.execute(
            "INSERT INTO videos (video_id, title, channel_id) VALUES (?, ?, ?)",
            (f"vid{i}", f"Video {i}", "TEST"),
        )

    # Insert views out of order
    cursor.execute(
        "INSERT INTO views (video_id, channel_id, timestamp) VALUES (?, ?, ?)",
        ("vid0", "TEST", "2024-01-20T00:00:00Z"),
    )
    cursor.execute(
        "INSERT INTO views (video_id, channel_id, timestamp) VALUES (?, ?, ?)",
        ("vid1", "TEST", "2024-01-05T00:00:00Z"),
    )
    cursor.execute(
        "INSERT INTO views (video_id, channel_id, timestamp) VALUES (?, ?, ?)",
        ("vid2", "TEST", "2024-01-15T00:00:00Z"),
    )
    empty_db.commit()

    results = get_videos_for_month(empty_db, 2024, 1)

    # Should be ordered chronologically
    assert len(results) == 3
    assert results[0]["video_id"] == "vid1"  # Jan 5
    assert results[1]["video_id"] == "vid2"  # Jan 15
    assert results[2]["video_id"] == "vid0"  # Jan 20


def test_videos_for_month_includes_ids(empty_db):
    """Test that video and channel IDs are included for URL construction."""
    cursor = empty_db.cursor()

    # Insert test data
    cursor.execute(
        "INSERT INTO channels (channel_id, channel_name) VALUES (?, ?)",
        ("CHAN123", "Test Channel"),
    )
    cursor.execute(
        "INSERT INTO videos (video_id, title, channel_id) VALUES (?, ?, ?)",
        ("VID456", "Test Video", "CHAN123"),
    )
    cursor.execute(
        "INSERT INTO views (video_id, channel_id, timestamp) VALUES (?, ?, ?)",
        ("VID456", "CHAN123", "2024-01-15T00:00:00Z"),
    )
    empty_db.commit()

    results = get_videos_for_month(empty_db, 2024, 1)

    assert len(results) == 1
    assert results[0]["video_id"] == "VID456"
    assert results[0]["channel_id"] == "CHAN123"
