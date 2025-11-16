# End User Requirements

## Overview
End user persona focuses on interaction with YouTube watch history data for analytical insights. User expects intuitive interface and straightforward navigation.

## V1 - Core Analytics (Minimum Viable Product)

### Channel-Centric Statistics
- First and last view date for each channel
- Total views per channel
- Unique videos watched per channel
- Rewatch tracking (same video watched multiple times)

### Temporal Analysis
- Views per year breakdown
- Views per month+year combination
- Histogram visualization of viewing patterns over time

### Global Usage Statistics
- Per-year metrics:
  - Total views
  - Unique videos watched
  - Unique channels watched

### Top Channels View
- Global top channels (by total view count)
- Per-year top channels (by view count for that year)

### Navigation and UX
- Landing page with navigation to different views
- Simple, performant UI with minimal frills
- Easy to use interface
- Dataset time span display (start and end date of data)

### Technical Constraints
- Fully self-contained (no external API calls)
- No internet dependency for core functionality

## V2 - Grouping, Enrichment, and Topic Analysis

### Channel Grouping
- Persistent channel grouping (multiple channels → one logical group)
- CRUD interface for managing groupings
- Rationale: Many creators have multiple channels; users follow creators, not channels

### Channel Info
- View all the statistics for a channel.
- Show per-month view history for a channel, and allow to see what videos were watched.
- Consdier doing Top-N rewatched videos ordered by number of times rewatched.
- Integrate with groups.

### Group Analytics
- Top groups view (aggregated stats across grouped channels)
- Per-channel stats within each group
- Group-level temporal breakdown

### YouTube API Integration
- On-demand thumbnail and metadata hydration
- User-initiated (e.g., "click button to load thumbnails")
- Fail quietly if API unavailable or returns errors
- Channel metadata includes standard thumbnail sizes

### Topic Analysis
- Cluster channels by topic (using API-provided topic data)
- Aggregate views by topic category

### Discovery Metrics
- New vs returning channels year-over-year
- Tracks exploration patterns vs comfort viewing

### Most Rewatched Videos
- Global most rewatched videos (ranked by rewatch count)
- Per-year most rewatched videos
- Display video title, channel name, total views, rewatch count

## Deferred Beyond V2

### Medium Priority
- Video-level drill-down (list all videos watched per channel)

### Low Priority
- Watch velocity/binge visualization (e.g., 20 videos in one week)
- Day-of-week/time-of-day viewing patterns

## Explicit Non-Requirements
- Semantic search over dataset
- Export functionality (CSV/JSON)
- Watch time tracking (only tracking that view occurred, not duration)

## Notes
- "View" definition: If it's recorded in YouTube history, it counts as a view (regardless of watch duration)
- Deleted/private videos: Present in dataset but lack channel association (handling deferred to architecture phase)
