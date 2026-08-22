# -*- coding: utf-8 -*-
"""
분당구(41135)를 표본으로 4개 데이터소스를 실제로 수집해 CSV로 저장한다.
전체 지역 확장은 이 결과를 확인한 뒤 진행한다.
"""
from fetch_data import (
    fetch_building_ledger,
    fetch_building_license,
    fetch_kosis_search,
    fetch_transaction_price,
)

SIGUNGU_CODE = "41135"  # 성남시 분당구
BDONG_CODE = "11000"

jobs = [
    (
        "data_transaction_price_bundang.csv",
        lambda: fetch_transaction_price(SIGUNGU_CODE, year_month="202506"),
    ),
    (
        "data_building_license_bundang.csv",
        lambda: fetch_building_license(SIGUNGU_CODE, BDONG_CODE, max_pages=5),
    ),
    (
        "data_building_ledger_bundang.csv",
        lambda: fetch_building_ledger(SIGUNGU_CODE, BDONG_CODE, max_pages=5),
    ),
    (
        "data_kosis_search_misale.csv",
        lambda: fetch_kosis_search("미분양 현황"),
    ),
]

for filename, call in jobs:
    print(f"수집 중: {filename}")
    df = call()
    df.to_csv(filename, index=False, encoding="utf-8-sig")
    print(f"  -> {len(df)}행 저장 완료\n")

print("전체 수집 완료.")
