# -*- coding: utf-8 -*-
"""3. 리포트 — 자동 절(요약·방법·결과·한계) + 사람 절(배경·해석·제안) 조립,
게이트 3(발송, 되돌릴 수 없음). 제안서는 9주차 Day3부터 [5. 제안서] 독립
메뉴에 있다 — 이 페이지에는 리포트만 남는다."""
import os

import streamlit as st

from core import config, gates, load
from report import email as report_email
from report import pdf as report_pdf
from report import phrasing, sections
from viz import ui

st.set_page_config(page_title="3. 리포트", layout="wide")
ui.css()
ui.sidebar_nav()
st.title("3. 리포트")
ui.context_bar()

if not gates.latest_gate_passed(1):
    st.warning("게이트 1을 먼저 통과하십시오. [1. 실행] 화면으로 가십시오.")
    st.page_link("pages/1_실행.py", label="1. 실행으로 이동", icon="▶")
    st.stop()

if not gates.latest_gate_passed(2):
    st.warning("게이트 2를 먼저 통과하십시오. [2. 대시보드]에서 분석을 확정해야 리포트로 넘어옵니다.")
    st.page_link("pages/2_대시보드.py", label="2. 대시보드로 이동", icon="📊")
    st.stop()

run_id = st.session_state.get("run_id") or gates.latest_run_id()
st.session_state["run_id"] = run_id
tables = load.load_tables()

auto = sections.build_auto_sections(tables)
draft = sections.load_draft(run_id)

st.caption(f"현재 실행: {run_id}")

for name in sections.SECTION_ORDER:
    if name in sections.AUTO_SECTIONS:
        st.subheader(f"{name} (자동 생성)")
        st.markdown(auto[name].replace("\n", "  \n"))
    else:
        st.subheader(f"{name} (분석가 작성)")
        draft[name] = st.text_area(
            name, value=draft.get(name, ""), key=f"section_{name}",
            placeholder=f"{name}은 분석가가 직접 씁니다 — 인과·해석·제안은 여기서만 다룹니다.",
            label_visibility="collapsed",
        )

if st.button("임시 저장", key="save_report_draft"):
    sections.save_draft(run_id, {k: draft[k] for k in sections.HUMAN_SECTIONS})
    st.toast("저장했습니다.")

st.divider()
st.subheader("발송 전 점검")

auto_text = "\n".join(auto.values())
hits = phrasing.check_phrasing(auto_text)
missing_human = [s for s in sections.HUMAN_SECTIONS if not draft.get(s, "").strip()]

if hits:
    ui.callout("block", f"자동 생성 절에서 금지 표현 {len(hits)}건 발견 — 사실·변동만 서술해야 합니다.")
    st.dataframe(hits, hide_index=True, use_container_width=True)
else:
    ui.callout("ok", "자동 생성 절에 인과·제안·가치판단 표현이 없습니다.")

if missing_human:
    ui.callout("warn", f"아직 안 쓴 절: {', '.join(missing_human)}")
else:
    ui.callout("ok", "배경·해석·제안 세 절을 모두 작성했습니다.")

ready = not hits and not missing_human

st.divider()
st.subheader("게이트 3 — 발송 (되돌릴 수 없음)")
st.error("게이트 3을 통과시키면 PDF가 확정되고 발송 처리됩니다. 이후에는 되돌릴 수 없습니다 — 게이트 1·2와 다릅니다.")

if gates.latest_gate_passed(3):
    st.success("게이트 3 통과됨 — 이 실행의 리포트는 이미 발송 확정되었습니다.")
    pdf_path = os.path.join(config.RUNS_DIR, f"{run_id}_report.pdf")
    if os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            st.download_button("발송된 PDF 다시 받기", f.read(), file_name=f"{run_id}_report.pdf")
else:
    @st.dialog("게이트 3 확인 — 되돌릴 수 없음")
    def _gate3_dialog(run_id: str):
        st.error("이 작업은 되돌릴 수 없습니다. 계속하려면 아래에 정확히 \"발송\"이라고 입력하십시오.")
        confirm_text = st.text_input("확인 문구 입력")
        reason = st.text_area("판단 근거", placeholder="예: 배경·해석·제안 작성 완료, 자동 절 검사 통과")
        can_confirm = confirm_text.strip() == "발송" and reason.strip()
        if st.button("발송 확정", type="primary", disabled=not can_confirm):
            human = {k: draft[k] for k in sections.HUMAN_SECTIONS}
            sections.save_draft(run_id, human)
            pdf_path = os.path.join(config.RUNS_DIR, f"{run_id}_report.pdf")
            report_pdf.build_pdf(run_id, auto, human, pdf_path)
            mail_result = report_email.send_report(
                config.EMAIL_TO_EXAMPLE, f"{config.DATASET_NAME} 리포트", "첨부된 리포트를 확인하십시오.", pdf_path,
            )
            gates.record_gate(
                3, reason.strip() + f" (이메일: {mail_result['사유']})", run_id=run_id, reversible=False,
            )
            st.session_state["run_id"] = run_id
            st.rerun()

    if st.button("발송 확정 — 게이트 3 통과시키기", type="primary", disabled=not ready):
        _gate3_dialog(run_id)
    if not ready:
        st.caption("위 점검을 통과해야 발송 버튼이 열립니다.")
