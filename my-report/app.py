# -*- coding: utf-8 -*-
import streamlit as st

from core import config
from viz import ui

st.set_page_config(page_title=config.DATASET_NAME, layout="wide")
ui.css()
ui.sidebar_nav()

st.title(config.DATASET_NAME)
ui.context_bar()

st.write("왼쪽 메뉴에서 화면을 고르십시오. 1. 실행부터 시작합니다.")
st.page_link("pages/1_실행.py", label="1. 실행으로 이동", icon="▶")
