import os
from app.youtube import get_recent_videos
from app.transcript import get_transcript
from app.summarize import summarize
from app.mailer import send_email

# 환경 변수에서 채널 ID 목록을 읽어옴
# "UCxxx,UCyyy,UCzzz" → ["UCxxx", "UCyyy", "UCzzz"]
CHANNEL_IDS = [cid.strip() for cid in os.getenv("CHANNEL_IDS", "").split(",") if cid.strip()]


async def run_daily_summary():
    """
    매일 실행되는 메인 파이프라인.
    채널 목록을 순회하며 영상 수집 → 자막 → 요약 → 이메일 발송까지 처리합니다.
    """
    print("=" * 40)
    print("📺 유튜브 요약 파이프라인 시작")
    print("=" * 40)

    results = []  # 최종 이메일에 담길 요약 결과 목록

    for channel_id in CHANNEL_IDS:
        print(f"\n📡 채널 처리 중: {channel_id}")

        # 1단계: 해당 채널의 최근 24시간 영상 조회
        videos = await get_recent_videos(channel_id)
        print(f"  → 신규 영상 {len(videos)}개 발견")

        if not videos:
            continue  # 이 채널에 새 영상이 없으면 다음 채널로

        for video in videos:
            print(f"\n  🎬 처리: {video['title']}")

            # 2단계: 자막 가져오기
            transcript = await get_transcript(video["video_id"])

            if not transcript:
                print(f"     → ⚠️ 자막 없음, 스킵")
                continue  # 자막이 없으면 요약 불가 → 다음 영상으로

            print(f"     → 자막 {len(transcript)}자 수집 완료")

            # 3단계: AI 요약
            summary = await summarize(transcript, video["title"])
            print(f"     → 요약 완료")

            # 결과 저장
            results.append({
                "title": video["title"],
                "link": video["link"],
                "channel": video["channel"],
                "summary": summary,
            })

    # 4단계: 이메일 발송
    print(f"\n📧 총 {len(results)}개 영상 요약 완료")

    if results:
        await send_email(results)
        print("✅ 이메일 발송 완료")
    else:
        print("ℹ️ 발송할 내용 없음 (오늘 새 영상 없거나 모두 자막 없음)")

    print("=" * 40)