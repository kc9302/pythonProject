# Profile Analytics Plan

This document outlines the planned analytics functions for each xAPI profile.
The goal is to provide a range of functions from basic statistics (counts) to high-level metrics (indicators).

## 1. Session Profile
**Goal**: Analyze user login sessions, duration, and platform usage.

| Function Name | Type | Description |
| :--- | :--- | :--- |
| `count_total_sessions` | Basic | Total number of valid `service-session` contexts. |
| `calc_avg_session_duration` | Metric | Average time between `initialized` and `terminated`. |
| `count_active_days` | Metric | Number of unique days with at least one session. |
| `analyze_login_times` | Advanced | Distribution of login times (hour of day). |
| `get_platform_usage` | Basic | Count of sessions per `platform` (e.g., PC, Mobile). |

## 2. Assessment Profile
**Goal**: Analyze assessment performance, completion rates, and item interactions.

| Function Name | Type | Description |
| :--- | :--- | :--- |
| `count_attempts` | Basic | Total assessment attempts (started). |
| `calc_completion_rate` | Metric | Ratio of `completed` vs `started`. |
| `calc_avg_score` | Metric | Average `result.score.scaled` for completed assessments. |
| `calc_pass_rate` | Metric | Ratio of attempts with `result.success=true`. |
| `analyze_item_responses` | Advanced | Success rate per specific check-list item or question. |

## 3. Media Profile
**Goal**: Analyze video/audio consumption behavior.

| Function Name | Type | Description |
| :--- | :--- | :--- |
| `count_media_plays` | Basic | Total `played` interactions. |
| `calc_avg_watch_time` | Metric | Average duration of media consumption sessions. |
| `identify_drop_off_points` | Advanced | Timestamp where users most frequently `paused` or `terminated`. |
| `calc_completion_rate` | Metric | Ratio of `completed` verbs (finished watching). |
| `analyze_seek_behavior` | Advanced | Frequency and direction of `seek` verbs. |

## 4. Navigation Profile
**Goal**: Analyze page views and navigation flow.

| Function Name | Type | Description |
| :--- | :--- | :--- |
| `count_page_views` | Basic | Total `viewed` verbs (or equivalent). |
| `find_popular_paths` | Advanced | Most common sequences of visited pages. |
| `calc_avg_time_on_page` | Metric | Average time spent between navigation events. |
| `identify_exit_pages` | Metric | Last page visited before session end. |

## Next Steps
1. **Approve**: Confirm this list of functions.
2. **Prioritize**: Choose which profile to start with (Recommendation: **Session** or **Assessment**).
3. **Implement**: Create `src/xapi_tools/analytics/<profile>.py` and corresponding tests.
