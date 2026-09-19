# -*- coding: utf-8 -*-
"""리포트를 PDF로 굳힌다. 게이트 3(발송)에서만 호출한다 — 그 전까지는 화면
미리보기로만 본다.

한글 폰트: fonts/NanumGothic(.ttf/Bold.ttf) — SIL OFL 라이선스라 저장소에
그대로 넣어 재배포한다(맑은고딕은 마이크로소프트 라이선스라 못 넣는다).
"""
import os

from fpdf import FPDF

from core import config
from report.sections import HUMAN_SECTIONS, SECTION_ORDER

FONT_DIR = os.path.join(config.APP_DIR, "fonts")


def _pdf_with_font() -> FPDF:
    pdf = FPDF()
    pdf.add_font("Nanum", "", os.path.join(FONT_DIR, "NanumGothic.ttf"))
    pdf.add_font("Nanum", "B", os.path.join(FONT_DIR, "NanumGothicBold.ttf"))
    return pdf


def _render_sections(pdf: FPDF, secs: list) -> None:
    """[{"title","kind"("auto"|"human"),"body"}, ...] 형태를 그대로 훑어 찍는다."""
    for sec in secs:
        text = (sec.get("body") or "").strip()
        is_human = sec["kind"] == "human"
        pdf.set_font("Nanum", "B", 13)
        label = f'{sec["title"]} ({"분석가 작성" if is_human else "자동 생성"})'
        pdf.cell(0, 9, label, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Nanum", "", 10)
        pdf.multi_cell(0, 6, text if text else "(내용 없음)")
        pdf.ln(3)


def build_pdf(run_id: str, auto_sections: dict, human_sections: dict, out_path: str) -> str:
    """auto_sections(요약/방법/결과/한계) + human_sections(배경/해석/제안)을
    report.sections.SECTION_ORDER 순서로 묶어 PDF 한 장짜리 문서로 만든다."""
    all_sections = {**auto_sections, **human_sections}
    secs = [
        {"title": name, "kind": "human" if name in HUMAN_SECTIONS else "auto", "body": all_sections.get(name)}
        for name in SECTION_ORDER
    ]

    pdf = _pdf_with_font()
    pdf.add_page()
    pdf.set_font("Nanum", "B", 16)
    pdf.cell(0, 10, config.DATASET_NAME, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Nanum", "", 10)
    pdf.cell(0, 7, f"{config.PERIOD[0]} ~ {config.PERIOD[1]} · 그레인: {config.GRAIN}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    _render_sections(pdf, secs)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    pdf.output(out_path)
    return out_path
