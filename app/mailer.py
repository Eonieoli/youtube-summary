import smtplib
import os
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import date

GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")


def markdown_to_html(text: str) -> str:
    """
    Gemini가 반환하는 마크다운 텍스트를 HTML로 변환합니다.
    """
    lines = text.split("\n")
    html_lines = []
    in_list = False  # 현재 <ul> 태그가 열려있는지 추적

    for line in lines:
        # --- 제목 처리 (## 제목) ---
        if line.startswith("## "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            content = line[3:].strip()
            html_lines.append(f'<h3 style="margin: 20px 0 8px; color: #111;">{content}</h3>')

        # --- 불릿 항목 처리 (- 항목 또는 * 항목) ---
        elif line.startswith("- ") or line.startswith("* "):
            if not in_list:
                html_lines.append('<ul style="margin: 8px 0; padding-left: 20px; line-height: 1.9;">')
                in_list = True
            content = line[2:].strip()
            # **굵게** 처리
            content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
            html_lines.append(f'<li style="margin-bottom: 6px;">{content}</li>')

        # --- 구분선 (---) ---
        elif line.strip() == "---":
            if in_list:
                html_lines.append("</ul>")
                in_list = False

        # --- 빈 줄 ---
        elif line.strip() == "":
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append("")

        # --- 일반 텍스트 ---
        else:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            content = line.strip()
            # **굵게** 처리
            content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
            if content:
                html_lines.append(f'<p style="margin: 6px 0; line-height: 1.8;">{content}</p>')

    # 마지막에 열린 <ul>이 있으면 닫기
    if in_list:
        html_lines.append("</ul>")

    return "\n".join(html_lines)


def build_html(results: list[dict]) -> str:
    today = date.today().strftime("%Y년 %m월 %d일")

    items_html = ""
    for r in results:
        summary_html = markdown_to_html(r["summary"])
        items_html += f"""
        <div style="
            margin-bottom: 40px;
            padding: 24px;
            background: #fafafa;
            border-left: 4px solid #ff0000;
            border-radius: 4px;
        ">
            <h3 style="margin: 0 0 6px; font-size: 18px;">
                <a href="{r['link']}" style="color: #222; text-decoration: none;">
                    {r['title']}
                </a>
            </h3>
            <p style="margin: 0 0 16px; color: #888; font-size: 13px;">
                📺 {r['channel']}
            </p>
            <div style="font-size: 14px; color: #333;">
                {summary_html}
            </div>
        </div>
        """

    return f"""
    <html>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                 max-width: 700px; margin: auto; padding: 24px; color: #222;">
        <h2 style="border-bottom: 2px solid #ff0000; padding-bottom: 12px;">
            📬 오늘의 유튜브 요약 — {today}
        </h2>
        <p style="color: #666; font-size: 13px; margin-bottom: 32px;">
            총 {len(results)}개 영상의 핵심 내용을 정리했습니다.
        </p>
        {items_html}
        <hr style="border: none; border-top: 1px solid #eee; margin-top: 40px;">
        <p style="font-size: 11px; color: #aaa; text-align: center;">자동 발송된 이메일입니다.</p>
    </body>
    </html>
    """


async def send_email(results: list[dict]):
    html_content = build_html(results)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"📬 유튜브 요약 {date.today().strftime('%m/%d')} ({len(results)}개)"
    msg["From"] = GMAIL_USER
    msg["To"] = RECIPIENT_EMAIL
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_USER, RECIPIENT_EMAIL, msg.as_string())

    print(f"  → 이메일 발송 완료 (수신: {RECIPIENT_EMAIL})")