import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import date

GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")


def build_html(results: list[dict]) -> str:
    """
    요약 결과 목록을 받아 HTML 이메일 본문을 생성합니다.
    """
    today = date.today().strftime("%Y년 %m월 %d일")

    # 영상별 HTML 블록 생성
    items_html = ""
    for r in results:
        # Gemini가 반환한 요약(줄바꿈 포함)을 HTML에서도 줄바꿈이 보이도록 처리
        summary_html = r["summary"].replace("\n", "<br>")
        items_html += f"""
        <div style="
            margin-bottom: 32px;
            padding: 20px;
            background: #f9f9f9;
            border-left: 4px solid #ff0000;
            border-radius: 4px;
        ">
            <h3 style="margin: 0 0 6px;">
                <a href="{r['link']}" style="color: #333; text-decoration: none;">
                    {r['title']}
                </a>
            </h3>
            <p style="margin: 0 0 12px; color: #888; font-size: 13px;">
                📺 {r['channel']}
            </p>
            <div style="font-size: 14px; line-height: 1.7; color: #444;">
                {summary_html}
            </div>
        </div>
        """

    return f"""
    <html>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                 max-width: 680px; margin: auto; padding: 24px; color: #222;">
        <h2 style="border-bottom: 2px solid #ff0000; padding-bottom: 12px;">
            📬 오늘의 유튜브 요약 — {today}
        </h2>
        <p style="color: #666; font-size: 13px;">
            총 {len(results)}개 영상의 핵심 내용을 정리했습니다.
        </p>
        {items_html}
        <hr style="border: none; border-top: 1px solid #eee; margin-top: 40px;">
        <p style="font-size: 11px; color: #aaa; text-align: center;">
            자동 발송된 이메일입니다.
        </p>
    </body>
    </html>
    """


async def send_email(results: list[dict]):
    """
    Gmail SMTP를 통해 HTML 이메일을 발송합니다.
    """
    html_content = build_html(results)

    # 이메일 메시지 구성
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"📬 유튜브 요약 {date.today().strftime('%m/%d')} ({len(results)}개)"
    msg["From"] = GMAIL_USER
    msg["To"] = RECIPIENT_EMAIL

    # HTML 파트 추가
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    # Gmail SMTP 서버에 연결하여 발송
    # SMTP_SSL: 포트 465, TLS 암호화로 처음부터 연결
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_USER, RECIPIENT_EMAIL, msg.as_string())

    print(f"  → 이메일 발송 완료 (수신: {RECIPIENT_EMAIL})")