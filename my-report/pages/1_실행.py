# -*- coding: utf-8 -*-
"""1. 실행 — 데이터 적재 + 게이트 1(입구)."""
import streamlit as st

from core import config, gates, load, validate
from viz import ui

st.set_page_config(page_title="1. 실행", layout="wide")
ui.css()
ui.sidebar_nav()
st.title("1. 실행")
ui.context_bar()

tables = load.load_tables()

if not tables:
    ui.todo_card("Day1 준비", "data/ 폴더가 비어 있습니다. my-report/data/에 CSV를 넣으십시오.")
    st.stop()

st.subheader("적재된 데이터")
st.dataframe(load.profile_tables(tables), hide_index=True, use_container_width=True)

st.subheader("검증 3건 (게이트 1)")
results = validate.run_checks(tables)
for r in results:
    ui.callout(r["판정"], f"**{r['이름']}** — {r['메시지']}" + (f" ({r['상세']})" if r["상세"] else ""))

blocked = validate.has_block(results)

st.divider()
st.subheader("게이트 1 — 이 데이터로 분석을 시작해도 되는가")

if blocked:
    st.error("차단 항목이 있습니다. [통과시키기] 버튼이 잠깁니다.")

reason = st.text_area(
    "판단 근거 (경고가 있다면 왜 진행해도 되는지, 없다면 '경고 없음. 검증 3건 전부 통과'를 적으십시오)",
    placeholder="예: 경고 없음. 검증 3건 전부 통과",
)

if st.button("통과시키기", type="primary", disabled=blocked or not reason.strip()):
    run_id = gates.record_gate(1, reason.strip())
    st.session_state["run_id"] = run_id
    st.success(f"게이트 1 통과 기록됨 (run_id={run_id})")
    st.rerun()

if "run_id" in st.session_state and gates.latest_gate_passed(1):
    st.caption(f"현재 실행: {st.session_state['run_id']} — 게이트 1 통과됨")
