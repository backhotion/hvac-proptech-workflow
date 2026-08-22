# -*- coding: utf-8 -*-
"""
구역(시군구)당 대표 읍면동 코드 1개를 뽑는다.
건축인허가/건축물대장 API는 bjdongCd(읍면동코드)가 필수라, 시군구 전체를
받으려면 그 안의 모든 동(평균 38개, 최대 207개)을 순회해야 해서 범위가
너무 커진다 — 대신 구역당 "대표 동 1개"에서 최대 500건 샘플을 받는 방식으로,
애초 합의한 "구역당 500건 샘플" 취지를 유지한다.
"""
import unicodedata

import pandas as pd
import PublicDataReader as pdr


def nfc(s):
    return unicodedata.normalize("NFC", s) if isinstance(s, str) else s


SIDO_MAP = {"서울특별시": "서울", "경기도": "경기"}

code = pdr.code_bdong()
code["시도명"] = code["시도명"].map(nfc)
code["sido_short"] = code["시도명"].map(SIDO_MAP)

dong_level = code[
    (code["읍면동명"].fillna("") != "")
    & (code["말소일자"].fillna("") == "")
    & (code["sido_short"].isin(["서울", "경기"]))
].copy()

# 시군구코드별로 법정동코드가 가장 작은(=대체로 구청 소재지에 가까운) 동을 대표로 선택
dong_level = dong_level.sort_values(["시군구코드", "법정동코드"])
representative = dong_level.groupby("시군구코드", as_index=False).first()

# 읍면동코드는 법정동코드 10자리 중 뒤 5자리
representative["bdong_code"] = representative["법정동코드"].str[5:]

out = representative[
    ["sido_short", "시도명", "시군구코드", "시군구명", "읍면동명", "법정동코드", "bdong_code"]
]
out.to_csv("data_representative_dong.csv", index=False, encoding="utf-8-sig")
print(f"{len(out)}개 구역의 대표 동 저장 완료 -> data_representative_dong.csv")
print(out.head(10).to_string())
