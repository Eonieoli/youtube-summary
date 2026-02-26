import httpx
import os
import re
from datetime import datetime, timedelta, timezone

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"


def parse_duration_seconds(iso_duration: str) -> int:
    """
    ISO 8601 형식의 duration 문자열을 초 단위 정수로 변환합니다.
    예: "PT1M30S" → 90, "PT30S" → 30, "PT10M" → 600
    """
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', iso_duration)
    if not match:
        return 0
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds


async def is_shorts_by_redirect(video_id: str) -> bool:
    """
    URL 리다이렉트로 쇼츠 여부를 확인합니다.
    200 → 쇼츠, 3xx → 일반 영상
    """
    url = f"https://www.youtube.com/shorts/{video_id}"
    async with httpx.AsyncClient(follow_redirects=False) as client:
        response = await client.get(url)
    return response.status_code == 200


async def filter_shorts(video_ids: list[str]) -> set[str]:
    """
    영상 ID 목록을 받아서 쇼츠에 해당하는 ID 집합을 반환합니다.
    - 60초 이하 → duration만으로 쇼츠 판정
    - 60초 초과 ~ 3분 이하 → 리다이렉트로 2차 확인 (쇼츠 최대 길이 3분)
    - 3분 초과 → 일반 영상으로 판정, 추가 확인 없음
    """
    params = {
        "key": YOUTUBE_API_KEY,
        "id": ",".join(video_ids),  # 한 번에 최대 50개까지 조회 가능
        "part": "contentDetails",
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(YOUTUBE_VIDEOS_URL, params=params)
        response.raise_for_status()

    data = response.json()
    shorts_ids = set()

    for item in data.get("items", []):
        video_id = item["id"]
        duration_str = item["contentDetails"]["duration"]
        duration_sec = parse_duration_seconds(duration_str)

        if duration_sec <= 60:
            # 60초 이하 → 무조건 쇼츠
            shorts_ids.add(video_id)
        elif duration_sec <= 180:
            # 60초 초과 ~ 3분 이하 → 리다이렉트로 2차 확인
            if await is_shorts_by_redirect(video_id):
                shorts_ids.add(video_id)
        # 3분 초과 → 무조건 일반 영상, 체크 안 함

    return shorts_ids


async def get_recent_videos(channel_id: str) -> list[dict]:
    """
    주어진 채널 ID에서 최근 24시간 내 업로드된 영상 목록을 반환합니다.
    쇼츠는 자동으로 제외됩니다.
    """
    since = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

    params = {
        "key": YOUTUBE_API_KEY,
        "channelId": channel_id,
        "part": "snippet",
        "order": "date",
        "publishedAfter": since,
        "maxResults": 5,
        "type": "video",
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(YOUTUBE_SEARCH_URL, params=params)
        response.raise_for_status()

    data = response.json()
    items = data.get("items", [])

    if not items:
        return []

    # 쇼츠 필터링
    video_ids = [item["id"]["videoId"] for item in items]
    shorts_ids = await filter_shorts(video_ids)

    videos = []
    for item in items:
        video_id = item["id"]["videoId"]
        if video_id in shorts_ids:
            print(f"     → ⏭ 쇼츠 제외: {item['snippet']['title']}")
            continue
        snippet = item["snippet"]
        videos.append({
            "video_id": video_id,
            "title": snippet["title"],
            "channel": snippet["channelTitle"],
            "link": f"https://www.youtube.com/watch?v={video_id}",
        })

    return videos