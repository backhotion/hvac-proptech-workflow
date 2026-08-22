# -*- coding: utf-8 -*-
"""서울·경기 전체 시군구 x 최근 6개월(2026-02~2026-07) 아파트 매매 실거래가 수집."""
import time

import pandas as pd

from fetch_data import fetch_transaction_price

regions = pd.read_csv("data_region_codes.csv", dtype=str)
regions = regions[regions["sido_short"].isin(["서울", "경기"])].sort_values(
    ["sido_short", "시군구코드"]
)
print(f"대상 구역: {len(regions)}개 ({regions['sido_short'].value_counts().to_dict()})")

all_rows = []
errors = []
for i, row in enumerate(regions.itertuples(), start=1):
    try:
        df = fetch_transaction_price(
            row.시군구코드, start_year_month="202602", end_year_month="202607"
        )
        df["sido_short"] = row.sido_short
        df["시군구명"] = row.시군구명
        all_rows.append(df)
        print(f"[{i}/{len(regions)}] {row.sido_short} {row.시군구명}({row.시군구코드}) -> {len(df)}행")
    except Exception as e:
        print(f"[{i}/{len(regions)}] {row.sido_short} {row.시군구명}({row.시군구코드}) -> 실패: {e}")
        errors.append((row.시군구코드, row.시군구명, str(e)))
    time.sleep(0.2)

result = pd.concat(all_rows, ignore_index=True) if all_rows else pd.DataFrame()
result.to_csv("data_transaction_price_seoul_gyeonggi.csv", index=False, encoding="utf-8-sig")
print(f"\n총 {len(result)}행 저장 완료 -> data_transaction_price_seoul_gyeonggi.csv")
if errors:
    print(f"실패한 구역 {len(errors)}개:")
    for code, name, err in errors:
        print(f"  - {name}({code}): {err}")
