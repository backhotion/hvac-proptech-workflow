# -*- coding: utf-8 -*-
"""4. 아카이브 — 게이트 통과 이력."""
import streamlit as st

from core import gates
from viz import ui

st.set_page_config(page_title="4. 아카이브", layout="wide")
ui.css()
ui.sidebar_nav()
st.title("4. 아카이브")
ui.context_bar()

runs = gates.list_runs()
if not runs:
    st.info("아직 통과된 게이트가 없습니다.")
    st.stop()

for run in runs:
    with st.container(border=True):
        st.markdown(f"**{run['run_id']}**")
        for g in run.get("gates", []):
            되돌림 = "가능" if g["되돌림가능"] else "불가"
            st.write(f"- 게이트 {g['게이트']} · {g['시각']} · 되돌림 {되돌림}")
            st.caption(f"근거: {g['근거']}")
