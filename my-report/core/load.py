# -*- coding: utf-8 -*-
"""data/ 아래 CSV를 읽어 들인다. 골격 전용 함수는 없다 — 파일이 없으면 빈 dict를 돌려주고,
화면(todo.py)이 그 신호를 받아 안내 카드를 그린다."""
import os

import pandas as pd
import streamlit as st

from core import config


def _data_fingerprint() -> tuple:
    """data/*.csv의 (경로, mtime, 크기)를 모아 캐시 키로 쓴다. 인자 없이 캐시하면
    파일이 바뀌어도 첫 호출 결과를 계속 돌려주는 버그가 된다 — 실제로 실습E(깨진
    파일 넣기)에서 이 버그를 발견해 고쳤다(2026-08-29)."""
    out = []
    for filename in config.TABLES.values():
        path = os.path.join(config.DATA_DIR, f"{filename}.csv")
        if os.path.exists(path):
            st_ = os.stat(path)
            out.append((path, st_.st_mtime, st_.st_size))
        else:
            out.append((path, None, None))
    return tuple(out)


@st.cache_data(show_spinner=False)
def _load_tables_cached(fingerprint: tuple) -> dict:
    tables = {}
    for key, filename in config.TABLES.items():
        path = os.path.join(config.DATA_DIR, f"{filename}.csv")
        if not os.path.exists(path):
            continue
        tables[key] = pd.read_csv(path)
    return tables


def load_tables() -> dict:
    """config.TABLES에 있는 이름 기준으로 my-report/data/*.csv를 전부 읽는다.
    파일이 없는 테이블은 결과 dict에서 빠진다 — 에러를 내지 않는다."""
    return _load_tables_cached(_data_fingerprint())


def profile_tables(tables: dict) -> pd.DataFrame:
    """테이블별 행수·컬럼수·기간을 표로 정리한다. 실습 C 프롬프트5 형식."""
    rows = []
    for name, df in tables.items():
        date_cols = [c for c in df.columns if "일" in c or "날짜" in c]
        min_d = max_d = None
        for c in date_cols:
            try:
                s = pd.to_datetime(df[c], errors="coerce").dropna()
            except Exception:
                continue
            if s.empty:
                continue
            min_d = min(min_d, s.min()) if min_d is not None else s.min()
            max_d = max(max_d, s.max()) if max_d is not None else s.max()
        missing = {c: int(df[c].isna().sum()) for c in df.columns if df[c].isna().any()}
        rows.append({
            "테이블": name, "행수": len(df), "컬럼수": len(df.columns),
            "기간_최소": min_d, "기간_최대": max_d,
            "결측컬럼수": len(missing),
        })
    return pd.DataFrame(rows)
