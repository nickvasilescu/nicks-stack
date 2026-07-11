# Composio YouTube: own-channel recent video stats

When user asks for views / latest upload on **their** connected YouTube (operator Composio connection is Nick’s channel unless noted).

## Workflow

1. `COMPOSIO_SEARCH_TOOLS` session `generate_id: true`, use cases naming YouTube (list channel videos, get statistics, video details batch).
2. Confirm `toolkit_connection_statuses.youtube.has_active_connection` and channel handle from connection user_info (e.g. `@nickvasiles`).
3. Parallel via `COMPOSIO_MULTI_EXECUTE_TOOL` + `session_id`:
   - `YOUTUBE_GET_CHANNEL_STATISTICS` `{mine: true, part: "snippet,statistics,contentDetails"}`
   - `YOUTUBE_LIST_CHANNEL_VIDEOS` `{mine: true, maxResults: 5}`
4. Extract video ids from `items[].snippet.resourceId.videoId` (not playlist item id).
5. `YOUTUBE_GET_VIDEO_DETAILS_BATCH` `{id: […], parts: ["snippet","statistics","contentDetails"]}`
6. Report title, views, likes, comments, publishedAt, URL. Label “most recent” by `publishedAt` / playlist position 0.

## Pitfalls

- Operator Composio YouTube ≠ customer channel (Budgetdog, etc.). Do not upload or claim customer stats without their OAuth.
- `viewCount` arrives as string; cast for comparisons.
- Channel stats counters are aggregate lifetime, not “this video.”
