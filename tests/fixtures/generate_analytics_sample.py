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

# Channel definitions: (name, view_count)
CHANNEL_SPECS = [
    # 5 channels with 1-2 views (low activity)
    ("Low Activity Channel 1", 1),
    ("Low Activity Channel 2", 2),
    ("Low Activity Channel 3", 1),
    ("Low Activity Channel 4", 2),
    ("Low Activity Channel 5", 2),
    # 10 channels with 3-8 views (medium activity)
    ("Medium Activity Channel 1", 3),
    ("Medium Activity Channel 2", 5),
    ("Medium Activity Channel 3", 4),
    ("Medium Activity Channel 4", 6),
    ("Medium Activity Channel 5", 7),
    ("Medium Activity Channel 6", 8),
    ("Medium Activity Channel 7", 5),
    ("Medium Activity Channel 8", 6),
    ("Medium Activity Channel 9", 4),
    ("Medium Activity Channel 10", 3),
    # 10 channels with 9-15 views (high activity)
    ("High Activity Channel 1", 9),
    ("High Activity Channel 2", 12),
    ("High Activity Channel 3", 10),
    ("High Activity Channel 4", 15),
    ("High Activity Channel 5", 11),
    ("High Activity Channel 6", 13),
    ("High Activity Channel 7", 14),
    ("High Activity Channel 8", 10),
    ("High Activity Channel 9", 12),
    ("High Activity Channel 10", 9),
    # 5 channels with 16-25 views (very high activity)
    ("Very High Activity Channel 1", 16),
    ("Very High Activity Channel 2", 20),
    ("Very High Activity Channel 3", 25),
    ("Very High Activity Channel 4", 18),
    ("Very High Activity Channel 5", 22),
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
    video_registry = {}  # Track videos for rewatch generation

    # Generate records for each channel
    for channel_name, total_views in CHANNEL_SPECS:
        channel_id = generate_channel_id(channel_name)

        # Determine number of unique videos (2-5 per channel)
        num_videos = random.randint(2, 5)

        # Create videos for this channel
        videos = []
        for i in range(num_videos):
            video_id = generate_video_id()
            title = f"{channel_name} - Video {i+1}"
            videos.append({"video_id": video_id, "title": title})

        # Distribute views across videos
        # First, give each video at least one view
        view_counts = [1] * num_videos
        remaining_views = total_views - num_videos

        # Distribute remaining views randomly
        for _ in range(remaining_views):
            video_idx = random.randint(0, num_videos - 1)
            view_counts[video_idx] += 1

        # Generate records for each video's views
        for video, count in zip(videos, view_counts):
            for _ in range(count):
                timestamp = generate_timestamp()
                record = create_video_record(
                    video["video_id"],
                    video["title"],
                    channel_name,
                    channel_id,
                    timestamp
                )
                records.append(record)

                # Register for potential rewatches
                video_key = (video["video_id"], video["title"], channel_name, channel_id)
                if video_key not in video_registry:
                    video_registry[video_key] = []
                video_registry[video_key].append(record)

    # Add rewatches (20-30% of total records)
    current_count = len(records)
    target_rewatch_count = random.randint(int(current_count * 0.2), int(current_count * 0.3))

    # Select videos to rewatch (prefer videos with more existing views)
    rewatch_candidates = [(key, len(records_list)) for key, records_list in video_registry.items()]
    rewatch_candidates.sort(key=lambda x: x[1], reverse=True)

    # Create at least one video with 5+ rewatches
    if rewatch_candidates:
        popular_video = rewatch_candidates[0][0]
        video_id, title, channel_name, channel_id = popular_video
        for _ in range(5):
            timestamp = generate_timestamp()
            record = create_video_record(video_id, title, channel_name, channel_id, timestamp)
            records.append(record)

        target_rewatch_count -= 5

    # Generate remaining rewatches
    for _ in range(target_rewatch_count):
        # Weighted random selection (favor videos with more views)
        weights = [count for _, count in rewatch_candidates]
        selected_key = random.choices([key for key, _ in rewatch_candidates], weights=weights, k=1)[0]
        video_id, title, channel_name, channel_id = selected_key

        timestamp = generate_timestamp()
        record = create_video_record(video_id, title, channel_name, channel_id, timestamp)
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

    print(f"Generated {len(records)} records")
    print(f"  - {len(CHANNEL_SPECS)} channels")
    print(f"  - Date range: {START_DATE.date()} to {END_DATE.date()}")

    # Save to file
    output_path = Path(__file__).parent / "analytics_sample.json"
    with open(output_path, "w") as f:
        json.dump(records, f, indent=2)

    print(f"Saved to: {output_path}")
    print(f"File size: {output_path.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
