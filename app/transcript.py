import httpx
import os

SUPADATA_API_KEY = os.getenv("SUPADATA_API_KEY")
SUPADATA_URL = "https://api.supadata.ai/v1/youtube/transcript"


async def get_transcript(video_id: str) -> str | None:
    """
    Supadata API를 통해 유튜브 영상의 자막 텍스트를 가져옵니다.
    자막이 없거나 오류 발생 시 None을 반환합니다.
    """
    headers = {"x-api-key": SUPADATA_API_KEY}
    params = {
        "videoId": video_id,
        "lang": "ko",   # 한국어 자막 우선 요청. 없으면 다른 언어도 반환될 수 있음
        "text": "true", # 타임스탬프 없이 텍스트만 반환
    }

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(SUPADATA_URL, headers=headers, params=params)

    # 자막이 없는 경우 404를 반환하므로, 예외로 처리하지 않고 None 반환
    if response.status_code == 404:
        return None

    # 그 외 에러(인증 실패, 서버 오류 등)는 예외 발생
    if response.status_code != 200:
        print(f"  Supadata 오류: {response.status_code} - {response.text}")
        return None

    data = response.json()
    content = data.get("content", "")

    # content가 빈 문자열이면 None 반환
    return content if content else None