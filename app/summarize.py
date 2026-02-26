import httpx
import os

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent"
)

PROMPT_TEMPLATE = """
당신은 유튜브 영상을 분석해 독자에게 영상의 모든 핵심을 전달하는 전문 에디터입니다.
아래는 영상 "{title}"의 자막 전문입니다.

이 영상을 보지 않은 사람도 내용을 완전히 이해할 수 있도록 아래 형식으로 작성해주세요.

## 📌 한 줄 요약
영상 전체를 한 문장으로 압축해주세요.

## 🗂 배경 및 맥락
이 영상이 다루는 주제의 배경, 사회적/경제적 맥락, 왜 지금 이 주제가 중요한지 설명해주세요. (3~5문장)

## 🔍 핵심 내용
영상에서 다루는 핵심 논점, 주장, 데이터, 사례를 빠짐없이 정리해주세요.
각 항목은 소제목과 함께 구체적으로 작성해주세요. (최소 5개 항목)

## 💡 인사이트 및 시사점
이 영상이 전달하려는 메시지, 시청자가 얻어갈 수 있는 교훈이나 관점을 정리해주세요. (3~5문장)

---
{transcript}
"""


async def summarize(transcript: str, title: str) -> str:
    # 자막 길이를 20,000자로 확대 (더 풍부한 요약을 위해)
    truncated_transcript = transcript[:20000]

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
            "temperature": 0.4,
            "maxOutputTokens": 2048,  # 512 → 2048으로 확대
        },
    }

    params = {"key": GEMINI_API_KEY}

    async with httpx.AsyncClient(timeout=60) as client:  # 30 → 60초로 확대
        response = await client.post(GEMINI_URL, json=payload, params=params)
        response.raise_for_status()

    data = response.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]