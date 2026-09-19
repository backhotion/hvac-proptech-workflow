# -*- coding: utf-8 -*-
"""게이트 1(입구) 검증. 8주차 Day1 실습D.

세 규칙만 만든다. 12건을 다 만들지 않는 이유: 차단을 늘리면 실무 데이터가 늘 어딘가
깨져 있어 앱이 자꾸 멈추고, 결국 사람이 차단을 하나씩 꺼서 검증 전체가 무력해진다.
"""
import pandas as pd

from core import config

# 판정 기준: "이 규칙이 깨진 채로 계산하면 값이 틀리는가?" → 틀리면 차단, 해석만
# 조심하면 되면 경고.
MIN_ROWS = 100          # 근거: 이보다 적으면 퍼널 비율 자체가 요동쳐 분석이 무의미하다
REQUIRED_COLS = ["주문번호", "거래선코드", "주문접수일"]  # 없으면 그레인·조인·기간 계산 불가


def _r(name, level, message, detail=""):
    return {"이름": name, "판정": level, "메시지": message, "상세": detail}


def run_checks(tables: dict) -> list:
    results = []
    fe = tables.get("funnel_events")

    # 규칙 1 — 행 수. 근거: MIN_ROWS 미만이면 비율 계산 자체가 못 믿을 수준이다.
    if fe is None:
        results.append(_r("행 수", "block", "funnel_events 테이블이 없음", "데이터를 연결하십시오"))
    else:
        n = len(fe)
        if n < MIN_ROWS:
            results.append(_r("행 수", "block", f"funnel_events {n}행 (최소 {MIN_ROWS})",
                             "행이 모자라 분석 자체가 무의미합니다"))
        else:
            results.append(_r("행 수", "ok", f"funnel_events {n:,}행 (최소 {MIN_ROWS} 이상)"))

    # 규칙 2 — 필수 컬럼. 근거: 이 셋이 없으면 그레인(주문번호)·거래선 조인·기간 판정이
    # 전부 불가능하다.
    if fe is not None:
        missing = [c for c in REQUIRED_COLS if c not in fe.columns]
        if missing:
            results.append(_r("필수 컬럼", "block", f"필수 컬럼 없음: {missing}",
                             "그레인·조인·기간 계산이 불가능합니다"))
        else:
            results.append(_r("필수 컬럼", "ok", f"필수 컬럼 {REQUIRED_COLS} 전부 있음"))

    # 규칙 3 — 날짜 범위. 판정: 경고 (차단이 아니다). 근거: 이 도메인은 그레인이
    # 주문 1건이고 전체가 99,200건 규모라, config.PERIOD를 벗어난 소수 행이 있어도
    # 그 행만 제외하고 진행하면 분모가 크게 틀어지지 않는다 — "이 값을 쓰면 안 됨"이
    # 아니라 "사람이 확인하고 넘어갈 수 있는" 경우로 판단했다(2026-08-29).
    if fe is not None and "주문접수일" in fe.columns:
        start, end = pd.Timestamp(config.PERIOD[0]), pd.Timestamp(config.PERIOD[1])
        dates = pd.to_datetime(fe["주문접수일"], errors="coerce")
        out_of_range = ((dates < start) | (dates > end)).sum()
        if out_of_range > 0:
            results.append(_r("날짜 범위", "warn",
                             f"{out_of_range}건이 유효 기간({config.PERIOD[0]}~{config.PERIOD[1]}) 밖",
                             "그 행만 제외하고 진행 가능(경고). 근거: 전체 규모 대비 분모 왜곡이 작음"))
        else:
            results.append(_r("날짜 범위", "ok",
                             f"전부 {config.PERIOD[0]}~{config.PERIOD[1]} 안"))

    return results


def has_block(results: list) -> bool:
    return any(r["판정"] == "block" for r in results)
