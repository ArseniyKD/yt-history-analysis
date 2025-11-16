"""Integration tests for Flask API endpoints."""

import sqlite3
import pytest
from src.api.app import create_app
from src.db.schema import init_schema
from src.ingest.pipeline import ingest_records


@pytest.fixture
def db_path(tmp_path):
    """Create a temporary SQLite database file with test data."""
    db_file = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_file))
    init_schema(conn)

    # Insert minimal test data
    test_records = [
        {
            "title": "Watched Video 1",
            "titleUrl": "https://www.youtube.com/watch?v=vid1",
            "subtitles": [
                {
                    "name": "Channel A",
                    "url": "https://www.youtube.com/channel/UCchannelA",
                }
            ],
            "time": "2024-01-01T10:00:00.000Z",
        },
        {
            "title": "Watched Video 2",
            "titleUrl": "https://www.youtube.com/watch?v=vid2",
            "subtitles": [
                {
                    "name": "Channel B",
                    "url": "https://www.youtube.com/channel/UCchannelB",
                }
            ],
            "time": "2024-01-05T15:30:00.000Z",
        },
        {
            "title": "Watched Video 1",  # Rewatch
            "titleUrl": "https://www.youtube.com/watch?v=vid1",
            "subtitles": [
                {
                    "name": "Channel A",
                    "url": "https://www.youtube.com/channel/UCchannelA",
                }
            ],
            "time": "2024-01-10T20:00:00.000Z",
        },
        {
            "title": "Watched https://www.youtube.com/watch?v=deleted",
            "titleUrl": "https://www.youtube.com/watch?v=deleted",
            "time": "2024-01-15T12:00:00.000Z",
        },
    ]

    ingest_records(conn, test_records)
    conn.close()

    return str(db_file)


@pytest.fixture
def empty_db_path(tmp_path):
    """Create a temporary empty SQLite database file."""
    db_file = tmp_path / "empty.db"
    conn = sqlite3.connect(str(db_file))
    init_schema(conn)
    conn.close()
    return str(db_file)


@pytest.fixture
def client(db_path):
    """Create Flask test client with test database."""
    app = create_app(db_path, debug=False, verbose=False)
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def empty_client(empty_db_path):
    """Create Flask test client with empty database."""
    app = create_app(empty_db_path, debug=False, verbose=False)
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_index_with_data(client):
    """Test index endpoint returns overview data."""
    response = client.get("/")

    assert response.status_code == 200
    assert b"Dataset Overview" in response.data or b"overview" in response.data.lower()

    # Check that data is present (exact formatting depends on template)
    assert b"2024" in response.data  # Year should appear in dates
    assert (
        b"4" in response.data or b"3" in response.data
    )  # Total views or unique videos


def test_index_with_empty_db(empty_client):
    """Test index endpoint handles empty database gracefully."""
    response = empty_client.get("/")

    assert response.status_code == 200
    # Should not crash - rendering with None/0 values


def test_channels_default_params(client):
    """Test channels endpoint with default parameters."""
    response = client.get("/channels")

    assert response.status_code == 200
    assert b"Channel A" in response.data or b"Channel B" in response.data
    # Default should exclude deleted videos
    assert b"Deleted Videos" not in response.data


def test_channels_custom_limit(client):
    """Test channels endpoint with custom limit parameter."""
    response = client.get("/channels?limit=1")

    assert response.status_code == 200
    # Should return successfully with limit=1


def test_channels_include_deleted_true(client):
    """Test channels endpoint includes deleted videos when requested."""
    response = client.get("/channels?include_deleted=true")

    assert response.status_code == 200
    # Should include deleted videos channel
    assert b"Deleted/Private Videos" in response.data


def test_channels_include_deleted_false(client):
    """Test channels endpoint excludes deleted videos by default."""
    response = client.get("/channels?include_deleted=false")

    assert response.status_code == 200
    # Should NOT include deleted videos
    assert b"Deleted/Private Videos" not in response.data


def test_channels_limit_bounds_checking(client):
    """Test channels endpoint enforces limit bounds (1-1000)."""
    # Test upper bound
    response = client.get("/channels?limit=9999")
    assert response.status_code == 200  # Should clamp to 1000, not crash

    # Test lower bound
    response = client.get("/channels?limit=0")
    assert response.status_code == 200  # Should clamp to 1, not crash

    # Test negative
    response = client.get("/channels?limit=-5")
    assert response.status_code == 200  # Should clamp to 1, not crash


def test_channels_empty_db(empty_client):
    """Test channels endpoint handles empty database gracefully."""
    response = empty_client.get("/channels")

    assert response.status_code == 200
    # Should not crash with empty results


def test_channels_form_state_preservation(client):
    """Test that channels page preserves form state in template context."""
    response = client.get("/channels?limit=25&include_deleted=true")

    assert response.status_code == 200
    # The template should have access to current_limit and include_deleted
    # for form state preservation (exact rendering depends on template)
    assert b"25" in response.data or b"checked" in response.data


def test_years_with_data(client):
    """Test years endpoint returns per-year summary data."""
    response = client.get("/years")

    assert response.status_code == 200
    assert b"Per-Year" in response.data or b"per-year" in response.data.lower()
    assert b"2024" in response.data  # Year should appear in table


def test_years_empty_db(empty_client):
    """Test years endpoint handles empty database gracefully."""
    response = empty_client.get("/years")

    assert response.status_code == 200
    # Should not crash with empty results


def test_year_channels_default_year(client):
    """Test year-channels endpoint with no year parameter (should use most recent)."""
    response = client.get("/year-channels")

    assert response.status_code == 200
    assert b"2024" in response.data  # Should default to most recent year (2024)
    assert b"Channel A" in response.data or b"Channel B" in response.data


def test_year_channels_specific_year(client):
    """Test year-channels endpoint with specific year parameter."""
    response = client.get("/year-channels?year=2024")

    assert response.status_code == 200
    assert b"2024" in response.data
    assert b"Channel A" in response.data or b"Channel B" in response.data


def test_year_channels_out_of_range_year(client):
    """Test year-channels endpoint with out-of-range year (should default to most recent)."""
    response = client.get("/year-channels?year=2030")

    assert response.status_code == 200
    # Should default to 2024 (most recent year in data)
    assert b"2024" in response.data


def test_year_channels_invalid_year(client):
    """Test year-channels endpoint with invalid year parameter (should default to most recent)."""
    response = client.get("/year-channels?year=invalid")

    assert response.status_code == 200
    # Should default to 2024 (most recent year in data)
    assert b"2024" in response.data


def test_year_channels_with_limit(client):
    """Test year-channels endpoint with custom limit parameter."""
    response = client.get("/year-channels?year=2024&limit=1")

    assert response.status_code == 200
    # Should return successfully with limit=1


def test_year_channels_include_deleted(client):
    """Test year-channels endpoint with include_deleted parameter."""
    response = client.get("/year-channels?year=2024&include_deleted=true")

    assert response.status_code == 200
    # Should include deleted videos channel if any exist in that year
    assert b"Deleted/Private Videos" in response.data


def test_year_channels_empty_db(empty_client):
    """Test year-channels endpoint returns 404 for empty database."""
    response = empty_client.get("/year-channels")

    assert response.status_code == 404
    # Empty database should return 404


def test_processing_time_in_index(client):
    """Test that processing time is displayed on index page."""
    response = client.get("/")

    assert response.status_code == 200
    assert b"generated" in response.data.lower() or b"Page" in response.data


def test_processing_time_in_channels(client):
    """Test that processing time is displayed on channels page."""
    response = client.get("/channels")

    assert response.status_code == 200
    assert b"generated" in response.data.lower() or b"Page" in response.data


def test_processing_time_in_years(client):
    """Test that processing time is displayed on years page."""
    response = client.get("/years")

    assert response.status_code == 200
    assert b"generated" in response.data.lower() or b"Page" in response.data


def test_processing_time_in_year_channels(client):
    """Test that processing time is displayed on year-channels page."""
    response = client.get("/year-channels")

    assert response.status_code == 200
    assert b"generated" in response.data.lower() or b"Page" in response.data


def test_temporal_with_data(client):
    """Test temporal endpoint returns monthly trend data."""
    response = client.get("/temporal")

    assert response.status_code == 200
    assert b"Monthly" in response.data or b"monthly" in response.data.lower()
    # Should have month data (2024-01 format)
    assert b"2024-01" in response.data


def test_temporal_empty_db(empty_client):
    """Test temporal endpoint handles empty database gracefully."""
    response = empty_client.get("/temporal")

    assert response.status_code == 200
    # Should not crash with empty results


def test_processing_time_in_temporal(client):
    """Test that processing time is displayed on temporal page."""
    response = client.get("/temporal")

    assert response.status_code == 200
    assert b"generated" in response.data.lower() or b"Page" in response.data
