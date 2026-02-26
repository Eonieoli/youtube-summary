import httpx
import os
from datetime import datetime, timedelta, timezone

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"


async def get_recent_videos(channel_id: str) -> list[dict]:
    """
    주어진 채널 ID에서 최근 24시간 내 업로드된 영상 목록을 반환합니다.
    
    반환 형식:
    [
        {
            "video_id": "dQw4w9WgXcQ",
            "title": "영상 제목",
            "channel": "채널명",
            "link": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        },
        ...
    ]
    """
    # 24시간 전 시각을 RFC 3339 형식으로 계산
    # YouTube API의 publishedAfter 파라미터는 이 형식을 요구합니다
    since = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

    params = {
        "key": YOUTUBE_API_KEY,
        "channelId": channel_id,
        "part": "snippet",          # snippet = 제목, 설명, 채널명 등 기본 정보
        "order": "date",            # 최신순 정렬
        "publishedAfter": since,    # 이 시각 이후 업로드된 영상만 조회
        "maxResults": 5,            # 채널당 최대 5개
        "type": "video",            # 영상만 (재생목록, 채널 제외)
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(YOUTUBE_SEARCH_URL, params=params)
        response.raise_for_status()  # HTTP 에러(4xx, 5xx)면 예외 발생

    data = response.json()

    videos = []
    for item in data.get("items", []):
        snippet = item["snippet"]
        video_id = item["id"]["videoId"]
        videos.append({
            "video_id": video_id,
            "title": snippet["title"],
            "channel": snippet["channelTitle"],
            "link": f"https://www.youtube.com/watch?v={video_id}",
        })

    return videos