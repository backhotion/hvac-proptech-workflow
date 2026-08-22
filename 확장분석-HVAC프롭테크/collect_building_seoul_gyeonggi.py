# -*- coding: utf-8 -*-
"""
서울·경기 69개 구역 x 대표 읍면동 1개당 최대 500건(5페이지) 샘플로
건축인허가·건축물대장을 수집한다.
(시군구 전체 완전 수집은 구역당 평균 38개~최대 207개 동을 다 순회해야 해서
범위가 너무 커짐 — data_representative_dong.csv 생성 시 남긴 설명 참고)
"""
import time

import pandas as pd

from fetch_data import fetch_building_ledger, fetch_building_license

districts = pd.read_csv("data_representative_dong.csv", dtype=str)
print(f"대상 구역: {len(districts)}개")


def collect(fetch_fn, label, out_path, **fetch_kwargs):
    all_rows = []
    errors = []
    for i, row in enumerate(districts.itertuples(), start=1):
        try:
            df = fetch_fn(row.시군구코드, row.bdong_code, max_pages=5, **fetch_kwargs)
            df["sido_short"] = row.sido_short
            df["시군구명"] = row.시군구명
            df["대표동"] = row.읍면동명
            all_rows.append(df)
            print(f"[{label} {i}/{len(districts)}] {row.sido_short} {row.시군구명}/{row.읍면동명} -> {len(df)}행")
        except Exception as e:
            print(f"[{label} {i}/{len(districts)}] {row.sido_short} {row.시군구명}/{row.읍면동명} -> 실패: {e}")
            errors.append((row.시군구코드, row.시군구명, str(e)))
        time.sleep(0.2)

    result = pd.concat(all_rows, ignore_index=True) if all_rows else pd.DataFrame()
    result.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"\n[{label}] 총 {len(result)}행 저장 완료 -> {out_path}")
    if errors:
        print(f"[{label}] 실패 {len(errors)}개:")
        for code, name, err in errors:
            print(f"  - {name}({code}): {err}")
    return result


collect(fetch_building_license, "건축인허가", "data_building_license_seoul_gyeonggi.csv")
collect(fetch_building_ledger, "건축물대장", "data_building_ledger_seoul_gyeonggi.csv")

print("\n전체 완료.")
