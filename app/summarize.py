import httpx
import os

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# 사용할 Gemini 모델 및 API 엔드포인트
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.5-flash:generateContent"
)

# 요약 프롬프트 템플릿
# {title}과 {transcript}는 실제 값으로 대체됩니다
PROMPT_TEMPLATE = """
다음은 유튜브 영상 "{title}"의 자막입니다.

핵심 내용을 3~5개의 불릿 포인트로 요약해주세요.
각 항목은 한 줄로 간결하게 작성해주세요.
독자가 영상을 보지 않아도 핵심을 파악할 수 있도록 구체적으로 작성해주세요.

---
{transcript}
"""


async def summarize(transcript: str, title: str) -> str:
    """
    Gemini API를 이용해 자막 텍스트를 불릿 포인트 요약으로 변환합니다.
    """
    # 자막이 너무 길면 앞 10,000자만 사용 (Gemini 토큰 한도 대응)
    # gemini-2.0-flash 기준 입력 토큰 한도는 약 1백만이지만
    # 무료 플랜에서는 처리 속도와 비용 효율을 위해 제한합니다
    truncated_transcript = transcript[:10000]

    # Gemini API 요청 바디 구성
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": PROMPT_TEMPLATE.format(
                            title=title,
                            transcript=truncated_transcript,
                        )
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.3,     # 낮을수록 일관되고 사실적인 응답 (0.0~1.0)
            "maxOutputTokens": 512, # 요약 결과 최대 토큰 수
        },
    }

    params = {"key": GEMINI_API_KEY}

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(GEMINI_URL, json=payload, params=params)
        response.raise_for_status()

    data = response.json()

    # Gemini 응답 구조에서 텍스트 추출
    # data["candidates"][0]["content"]["parts"][0]["text"]
    return data["candidates"][0]["content"]["parts"][0]["text"]