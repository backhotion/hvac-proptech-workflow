# -*- coding: utf-8 -*-
"""
설계_통합테이블.md의 fact_region_month_integrated를 기존 CSV들을 조인해 실제로 만든다.
"""
import pandas as pd
from google.cloud import bigquery

BASE = "."
SAC_BASE = "../영업지원-분석"
BQ_PROJECT = "crested-vortex-390400"
BQ_DATASET = "hvac_ops"

# ---- 1. 지역 마스터 (서울+경기, 실거래가 수집 때 쓴 것과 동일 76개) ----
regions = pd.read_csv(f"{BASE}/data_region_codes.csv", dtype=str)
regions = regions[regions["sido_short"].isin(["서울", "경기"])].copy()
regions = regions.rename(columns={"시군구코드": "region_key", "시군구명": "sigungu_name"})

# ---- 2. 실거래가: region_key x year_month 별 건수/평균가 ----
tp = pd.read_csv(f"{BASE}/data_transaction_price_seoul_gyeonggi.csv", dtype=str, encoding="utf-8-sig")
tp["region_key"] = tp["법정동시군구코드"]
tp["year_month"] = tp["계약년도"].str.zfill(4) + tp["계약월"].str.zfill(2)
tp["거래금액_num"] = pd.to_numeric(tp["거래금액"].str.replace(",", "", regex=False), errors="coerce")
tp_agg = tp.groupby(["region_key", "year_month"]).agg(
    n_transactions=("거래금액_num", "size"),
    avg_transaction_price_10k=("거래금액_num", "mean"),
).reset_index()

# ---- 3. 건축인허가: region_key x year_month(archPmsDay 앞 6자리) 별 건수 ----
bl = pd.read_csv(f"{BASE}/data_building_license_seoul_gyeonggi.csv", dtype=str, encoding="utf-8-sig")
bl["region_key"] = bl["sigunguCd"]
bl["year_month"] = bl["archPmsDay"].str[:6]
bl_agg = bl.dropna(subset=["year_month"]).groupby(["region_key", "year_month"]).size().reset_index(name="n_new_building_permits")

# ---- 4. 영업지원-서비스분석.csv: (sido,sigungu 이름) x data_ym 별 SAC/전체 연면적 합 ----
nb = pd.read_csv(f"{SAC_BASE}/영업지원-서비스분석.csv", dtype={"data_ym": str})
nb["is_sac"] = nb["is_sac"].astype(str).str.lower().isin(["true", "1"])
name_to_code = regions[["sido_short", "sigungu_name", "region_key"]].drop_duplicates()
nb = nb.merge(name_to_code, left_on=["sido", "sigungu"], right_on=["sido_short", "sigungu_name"], how="left")
nb_unmatched = nb["region_key"].isna().sum()
nb_agg = nb.dropna(subset=["region_key"]).groupby(["region_key", "data_ym"]).agg(
    sac_eligible_grfa_sqm=("grfa", lambda s: s[nb.loc[s.index, "is_sac"]].sum()),
    total_new_grfa_sqm=("grfa", "sum"),
).reset_index().rename(columns={"data_ym": "year_month"})

# ---- 5. 시도별 상업전기사용량(단일 스냅샷, 월 구분 없음 -> 그대로 broadcast) ----
elec = pd.read_csv(f"{SAC_BASE}/data/data_sac_sido_correlation.csv")
elec_map = dict(zip(elec["sido"], elec["elec_commercial"]))

# ---- 6. 기준 격자: region x year_month (두 시간범위의 합집합) ----
all_months = sorted(set(tp_agg["year_month"]) | set(nb_agg["year_month"]))
grid = regions[["region_key", "sido_short", "sigungu_name"]].assign(key=1).merge(
    pd.DataFrame({"year_month": all_months, "key": 1}), on="key"
).drop(columns="key")

# ---- 7. 조인 ----
fact = grid.merge(tp_agg, on=["region_key", "year_month"], how="left")
fact = fact.merge(bl_agg, on=["region_key", "year_month"], how="left")
fact = fact.merge(nb_agg, on=["region_key", "year_month"], how="left")
fact["elec_commercial_sido_approx"] = fact["sido_short"].map(elec_map)

# ---- 7-2. 거래선-지역 매핑: dim_client에 이미 시군구코드가 채워져 있어(설계 당시 착각했던
# "매핑 없음"이 지금은 사실이 아님) misorder_rate_regional·client_service_score_avg를
# 실제로 계산할 수 있다. hvac2025h2_오주문율 정의(분자=fact_misorder COUNT, 분모=
# fact_sales_order_line의 COUNT DISTINCT 주문번호)를 지역 단위로 그대로 적용한다.
bq = bigquery.Client(project=BQ_PROJECT)

orders_sql = f"""
SELECT CAST(c.`시군구코드` AS STRING) AS region_key, o.`연월` AS ym_str,
       COUNT(DISTINCT o.`주문번호`) AS `주문건수`
FROM `{BQ_PROJECT}.{BQ_DATASET}.fact_sales_order_line` o
JOIN `{BQ_PROJECT}.{BQ_DATASET}.dim_client` c ON o.`거래선코드` = c.`거래선코드`
GROUP BY region_key, ym_str
"""
misorder_sql = f"""
SELECT CAST(c.`시군구코드` AS STRING) AS region_key, m.`연월` AS ym_str,
       COUNT(*) AS `오주문건수`
FROM `{BQ_PROJECT}.{BQ_DATASET}.fact_misorder` m
JOIN `{BQ_PROJECT}.{BQ_DATASET}.dim_client` c ON m.`거래선코드` = c.`거래선코드`
GROUP BY region_key, ym_str
"""
happycall_sql = f"""
SELECT CAST(c.`시군구코드` AS STRING) AS region_key, h.`연월` AS ym_str,
       AVG(h.`만족도점수`) AS client_service_score_avg
FROM `{BQ_PROJECT}.{BQ_DATASET}.fact_happycall` h
JOIN `{BQ_PROJECT}.{BQ_DATASET}.dim_client` c ON h.`거래선코드` = c.`거래선코드`
GROUP BY region_key, ym_str
"""

def _run(sql):
    return pd.DataFrame([dict(r.items()) for r in bq.query(sql).result()])

orders_df = _run(orders_sql)
misorder_df = _run(misorder_sql)
happycall_df = _run(happycall_sql)

rate_df = orders_df.merge(misorder_df, on=["region_key", "ym_str"], how="left")
rate_df["오주문건수"] = rate_df["오주문건수"].fillna(0)
rate_df["misorder_rate_regional"] = rate_df["오주문건수"] / rate_df["주문건수"] * 100
rate_df["year_month"] = rate_df["ym_str"].str.replace("-", "", regex=False)
happycall_df["year_month"] = happycall_df["ym_str"].str.replace("-", "", regex=False)

fact = fact.merge(rate_df[["region_key", "year_month", "misorder_rate_regional"]],
                   on=["region_key", "year_month"], how="left")
fact = fact.merge(happycall_df[["region_key", "year_month", "client_service_score_avg"]],
                   on=["region_key", "year_month"], how="left")

filled_regions = sorted(set(rate_df["region_key"]) | set(happycall_df["region_key"]))
print(f"거래선-지역 매핑으로 값이 채워진 지역: {len(filled_regions)}개 — {filled_regions}")
print(f"misorder_rate_regional 채워진 행: {fact['misorder_rate_regional'].notna().sum()} / {len(fact)}")
print(f"client_service_score_avg 채워진 행: {fact['client_service_score_avg'].notna().sum()} / {len(fact)}")

fact["ym_date"] = pd.to_datetime(fact["year_month"], format="%Y%m").dt.strftime("%Y-%m-01")

cols = [
    "region_key", "sido_short", "sigungu_name", "year_month", "ym_date",
    "n_transactions", "avg_transaction_price_10k", "n_new_building_permits",
    "sac_eligible_grfa_sqm", "total_new_grfa_sqm", "elec_commercial_sido_approx",
    "client_service_score_avg", "misorder_rate_regional",
]
fact = fact[cols].sort_values(["region_key", "year_month"])
fact.to_csv(f"{BASE}/fact_region_month_integrated.csv", index=False, encoding="utf-8-sig")

print(f"완성: {len(fact)}행, {fact['region_key'].nunique()}개 지역, {fact['year_month'].nunique()}개 월")
print(f"영업지원-서비스분석.csv 중 지역명 매칭 실패: {nb_unmatched}행")
print(f"연월 범위: {min(all_months)} ~ {max(all_months)}")
