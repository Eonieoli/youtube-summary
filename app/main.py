from fastapi import FastAPI
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from app.scheduler import run_daily_summary
import pytz

# 스케줄러 인스턴스 생성 (타임존을 서울로 고정)
scheduler = AsyncIOScheduler(timezone=pytz.timezone("Asia/Seoul"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI 서버의 시작과 종료 시점에 실행되는 코드를 정의합니다.
    with 블록 앞(yield 이전)은 서버 시작 시, 뒤(yield 이후)는 서버 종료 시 실행됩니다.
    """
    # --- 서버 시작 시 실행 ---
    scheduler.add_job(
        run_daily_summary,                    # 실행할 함수
        CronTrigger(hour=7, minute=0),        # 매일 07:00 KST
        id="daily_summary",                   # 잡 식별자 (중복 방지)
        replace_existing=True,                # 같은 id가 있으면 덮어씀
    )
    scheduler.start()
    print("✅ APScheduler 시작됨. 매일 07:00 KST에 실행됩니다.")

    yield  # ← 이 지점에서 FastAPI 서버가 실제로 실행됨

    # --- 서버 종료 시 실행 ---
    scheduler.shutdown()
    print("🛑 APScheduler 종료됨.")


app = FastAPI(lifespan=lifespan)


@app.get("/health")
def health():
    """서버 상태 확인 엔드포인트"""
    return {"status": "ok"}


@app.post("/run-now")
async def run_now():
    """
    테스트용 즉시 실행 엔드포인트.
    스케줄 시간을 기다리지 않고 파이프라인을 바로 실행합니다.
    curl -X POST http://<서버IP>:8000/run-now 으로 호출 가능
    """
    await run_daily_summary()
    return {"status": "done"}