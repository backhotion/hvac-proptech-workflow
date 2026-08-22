# -*- coding: utf-8 -*-
"""설계_통합테이블.md의 fact_region_month_integrated 설계 대비 실제 산출물 검증."""
import re

import pandas as pd

fact = pd.read_csv("fact_region_month_integrated.csv", dtype={"year_month": str, "region_key": str})
regions = pd.read_csv("data_region_codes.csv", dtype=str)
valid_region_keys = set(regions["시군구코드"])

print("=" * 60)
print("1. 컬럼 목록이 설계서와 일치하는가")
print("=" * 60)
designed_cols = [
    "region_key", "sido_short", "sigungu_name", "year_month", "ym_date",
    "n_transactions", "avg_transaction_price_10k", "n_new_building_permits",
    "sac_eligible_grfa_sqm", "total_new_grfa_sqm", "elec_commercial_sido_approx",
    "client_service_score_avg", "misorder_rate_regional",
]
actual_cols = list(fact.columns)
missing = [c for c in designed_cols if c not in actual_cols]
extra = [c for c in actual_cols if c not in designed_cols]
print(f"설계서 컬럼 수: {len(designed_cols)}, 실제 컬럼 수: {len(actual_cols)}")
print(f"누락된 컬럼: {missing or '없음'}")
print(f"설계서에 없는 추가 컬럼: {extra or '없음'}")
print(f"순서까지 동일: {designed_cols == actual_cols}")

print()
print("=" * 60)
print('2. 그레인("한 행 = 시군구 1개 x 연월 1개")이 설계서와 일치하는가')
print("=" * 60)
dup = fact.duplicated(subset=["region_key", "year_month"]).sum()
total = len(fact)
unique_combo = fact[["region_key", "year_month"]].drop_duplicates().shape[0]
print(f"전체 행수: {total}, (region_key,year_month) 유니크 조합 수: {unique_combo}")
print(f"중복 행: {dup}건 -> {'PASS: 그레인 일치(1행=1조합)' if dup == 0 else 'FAIL: 그레인 위반, 중복 존재'}")

print()
print("=" * 60)
print("3. 키·날짜 컬럼의 값 범위가 설계서 규칙 안에 있는가")
print("=" * 60)

# 3-1. region_key 참조무결성 (규칙 #5)
invalid_region = set(fact["region_key"]) - valid_region_keys
print(f"[규칙#5] region_key가 data_region_codes.csv에 없는 값: {len(invalid_region)}개 "
      f"-> {'PASS' if not invalid_region else 'FAIL: ' + str(invalid_region)}")

# 3-2. year_month 포맷 (규칙 #6)
bad_format = fact[~fact["year_month"].str.match(r"^\d{6}$")]
month_part = fact["year_month"].str[4:6].astype(int)
bad_month = fact[(month_part < 1) | (month_part > 12)]
print(f"[규칙#6] year_month가 YYYYMM 6자리 숫자가 아닌 행: {len(bad_format)}건 -> {'PASS' if len(bad_format)==0 else 'FAIL'}")
print(f"[규칙#6] 월 부분이 01~12 범위 밖인 행: {len(bad_month)}건 -> {'PASS' if len(bad_month)==0 else 'FAIL'}")

# 3-3. (참고) 규칙 #2 n_transactions=0 -> avg_transaction_price_10k는 NULL
rule2_violation = fact[(fact["n_transactions"].fillna(0) == 0) & fact["avg_transaction_price_10k"].notna()]
print(f"[참고, 규칙#2] n_transactions=0인데 평균가가 있는 행: {len(rule2_violation)}건 -> {'PASS' if len(rule2_violation)==0 else 'FAIL'}")

# 3-4. (참고) 규칙 #3 sac_eligible_grfa_sqm <= total_new_grfa_sqm
both = fact.dropna(subset=["sac_eligible_grfa_sqm", "total_new_grfa_sqm"])
rule3_violation = both[both["sac_eligible_grfa_sqm"] > both["total_new_grfa_sqm"] + 1e-6]
print(f"[참고, 규칙#3] sac_eligible_grfa_sqm > total_new_grfa_sqm인 행: {len(rule3_violation)}건 -> {'PASS' if len(rule3_violation)==0 else 'FAIL'}")

# 3-5. 규칙 #7 (2026-08-22 수정) — dim_client(BigQuery)에 시군구코드가 이미 채워져
# 있음을 확인해 misorder_rate_regional/client_service_score_avg를 실제로 계산했다.
# "항상 NULL"은 더 이상 규칙이 아니고, "거래선이 있는 지역·그 거래선의 데이터가 있는
# 월에서만 값이 있어야 한다"로 바뀐다. client_service_score_avg는 원래 설계서의
# market_거래선_서비스점수(0~100, 월 구분 없음) 대신 fact_happycall 만족도점수(1~5, 월별
# 실측)를 원천으로 채택했다 — 값 범위가 0~100이 아니라 1~5임에 주의.
CLIENT_REGION_KEYS = {  # dim_client 15개 거래선의 시군구코드(2026-08-22 확인)
    "11170", "11350", "11590", "11650", "41135", "41171", "41173",
    "41192", "41196", "41250", "41281", "41310", "41360", "41463", "41670",
}
filled = fact[fact["misorder_rate_regional"].notna() | fact["client_service_score_avg"].notna()]
outside_client_region = filled[~filled["region_key"].isin(CLIENT_REGION_KEYS)]
print(f"[규칙#7-수정] 거래선이 없는 지역인데 값이 채워진 행: {len(outside_client_region)}건 "
      f"-> {'PASS' if len(outside_client_region)==0 else 'FAIL'}")

rate_bad = fact[(fact["misorder_rate_regional"] < 0) | (fact["misorder_rate_regional"] > 100)]
print(f"[규칙#7-수정] misorder_rate_regional이 0~100% 범위 밖인 행: {len(rate_bad)}건 "
      f"-> {'PASS' if len(rate_bad)==0 else 'FAIL'}")

score_bad = fact[(fact["client_service_score_avg"] < 1) | (fact["client_service_score_avg"] > 5)]
print(f"[규칙#7-수정] client_service_score_avg가 1~5점 범위 밖인 행: {len(score_bad)}건 "
      f"-> {'PASS' if len(score_bad)==0 else 'FAIL'}")
print(f"[참고] 값이 채워진 (지역,월) 조합: {len(filled)}건 (거래선 지역 {len(CLIENT_REGION_KEYS)}개 기준)")

print()
print("=" * 60)
print("데이터 커버리지 요약 (진단용)")
print("=" * 60)
print(f"실거래가 값 있는 행: {fact['n_transactions'].notna().sum()} / {total}")
print(f"건축인허가 값 있는 행: {fact['n_new_building_permits'].notna().sum()} / {total}")
print(f"SAC신축연면적 값 있는 행: {fact['sac_eligible_grfa_sqm'].notna().sum()} / {total}")
print(f"세 값 다 있는 행(완전 관측): {fact[['n_transactions','n_new_building_permits','sac_eligible_grfa_sqm']].notna().all(axis=1).sum()} / {total}")
