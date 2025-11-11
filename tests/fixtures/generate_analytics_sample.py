#!/usr/bin/env python3
"""
Generate synthetic YouTube watch history data for testing analytics features.

Creates a JSON file matching YouTube Takeout format with controlled characteristics
for testing analytics queries.

Usage:
    python -m tests.fixtures.generate_analytics_sample

Output:
    tests/fixtures/analytics_sample.json (~100-150 records)
"""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path


# Fixed seed for reproducibility
random.seed(42)

# Date range: 2020-01-01 to 2024-12-31
START_DATE = datetime(2020, 1, 1)
END_DATE = datetime(2024, 12, 31)

# Channel distributions: (category_name, count, min_views, max_views)
CHANNEL_DISTRIBUTIONS = [
    ("Low Activity", 5, 1, 2),        # 5 channels, 1-2 views each
    ("Medium Activity", 10, 3, 8),    # 10 channels, 3-8 views each
    ("High Activity", 10, 9, 15),     # 10 channels, 9-15 views each
    ("Very High Activity", 5, 16, 25) # 5 channels, 16-25 views each
]


def generate_channel_id(channel_name: str) -> str:
    """Generate a fake but realistic-looking YouTube channel ID."""
    # Use hash of name to get consistent channel ID
    hash_val = abs(hash(channel_name))
    # YouTube channel IDs are 24 characters, starting with UC
    return f"UC{str(hash_val)[:22]:0<22}"


def generate_video_id() -> str:
    """Generate a fake YouTube video ID (11 characters)."""
    chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
    return "".join(random.choice(chars) for _ in range(11))


def generate_timestamp() -> str:
    """Generate random timestamp between START_DATE and END_DATE."""
    time_delta = END_DATE - START_DATE
    random_days = random.randint(0, time_delta.days)
    random_seconds = random.randint(0, 86400)
    timestamp = START_DATE + timedelta(days=random_days, seconds=random_seconds)
    return timestamp.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def create_video_record(video_id: str, title: str, channel_name: str, channel_id: str,
                        timestamp: str, is_deleted: bool = False) -> dict:
    """Create a YouTube history record."""
    record = {
        "header": "YouTube",
        "title": f"Watched {title}",
        "titleUrl": f"https://www.youtube.com/watch?v={video_id}",
        "time": timestamp,
        "products": ["YouTube"],
        "activityControls": ["YouTube watch history"]
    }

    # Add channel info unless video is deleted
    if not is_deleted:
        record["subtitles"] = [{
            "name": channel_name,
            "url": f"https://www.youtube.com/channel/{channel_id}"
        }]

    return record


def generate_records() -> list[dict]:
    """Generate all test records."""
    records = []

    # Generate channels from distributions
    for category, count, min_views, max_views in CHANNEL_DISTRIBUTIONS:
        for i in range(count):
            channel_name = f"{category} Channel {i+1}"
            channel_id = generate_channel_id(channel_name)
            total_views = random.randint(min_views, max_views)

            # Create fewer unique videos than total views
            # This naturally creates rewatches (20-40% of views are rewatches)
            num_unique_videos = random.randint(2, min(5, max(2, total_views - 1)))

            # Generate unique videos for this channel
            videos = []
            for j in range(num_unique_videos):
                video_id = generate_video_id()
                title = f"{channel_name} - Video {j+1}"
                videos.append({"video_id": video_id, "title": title})

            # Generate views by randomly selecting from video pool
            # Videos get rewatched naturally
            for _ in range(total_views):
                video = random.choice(videos)
                timestamp = generate_timestamp()
                record = create_video_record(
                    video["video_id"],
                    video["title"],
                    channel_name,
                    channel_id,
                    timestamp
                )
                records.append(record)

    # Add deleted videos (5-10 records)
    num_deleted = random.randint(5, 10)
    for i in range(num_deleted):
        video_id = generate_video_id()
        title = f"Deleted Video {i+1}"
        timestamp = generate_timestamp()
        record = create_video_record(video_id, title, "", "", timestamp, is_deleted=True)
        records.append(record)

    # Sort by timestamp (newest first, matching typical export order)
    records.sort(key=lambda r: r["time"], reverse=True)

    return records


def main():
    """Generate and save analytics test fixture."""
    print("Generating analytics test fixture...")

    records = generate_records()

    # Count total channels
    total_channels = sum(count for _, count, _, _ in CHANNEL_DISTRIBUTIONS)

    print(f"Generated {len(records)} records")
    print(f"  - {total_channels} channels")
    print(f"  - Date range: {START_DATE.date()} to {END_DATE.date()}")

    # Save to file
    output_path = Path(__file__).parent / "analytics_sample.json"
    with open(output_path, "w") as f:
        json.dump(records, f, indent=2)

    print(f"Saved to: {output_path}")
    print(f"File size: {output_path.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
