# -*- coding: utf-8 -*-
"""이메일 발송. config.EMAIL_ENABLED가 False면 실제로 아무 것도 보내지 않는다
(SMTP 서버·자격증명이 이 환경에 없다 — 실제로 보내려면 별도로 서버 설정을
채우고 EMAIL_ENABLED를 켜야 한다. 켠 채로 커밋하지 않는다, CLAUDE.md).
"""
import smtplib
from email.message import EmailMessage

from core import config


def send_report(to: str, subject: str, body: str, attachment_path: str) -> dict:
    if not config.EMAIL_ENABLED:
        return {"발송": False, "사유": "config.EMAIL_ENABLED=False — 이메일 발송이 꺼져 있다"}

    msg = EmailMessage()
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    with open(attachment_path, "rb") as f:
        msg.add_attachment(
            f.read(), maintype="application", subtype="pdf",
            filename=attachment_path.split("/")[-1].split("\\")[-1],
        )

    with smtplib.SMTP("localhost") as s:
        s.send_message(msg)
    return {"발송": True, "사유": f"{to}로 발송함"}
