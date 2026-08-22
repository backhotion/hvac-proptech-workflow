# -*- coding: utf-8 -*-
"""
인증키가 필요 없는 범위만 우선 수집: 법정동코드 참조 테이블.
시군구 단위로 추려서 sac-service-analysis의 17개 시도(강원~충북, 세종 포함)와
조인 가능한 형태로 정리한다.
"""
import unicodedata

import pandas as pd
import PublicDataReader as pdr


def nfc(s):
    return unicodedata.normalize("NFC", s) if isinstance(s, str) else s


SIDO_MAP = {
    "서울특별시": "서울", "부산광역시": "부산", "대구광역시": "대구", "인천광역시": "인천",
    "광주광역시": "광주", "대전광역시": "대전", "울산광역시": "울산", "세종특별자치시": "세종",
    "경기도": "경기", "강원특별자치도": "강원", "강원도": "강원",
    "충청북도": "충북", "충청남도": "충남",
    "전북특별자치도": "전북", "전라북도": "전북", "전라남도": "전남",
    "경상북도": "경북", "경상남도": "경남", "제주특별자치도": "제주",
}

SIDO_MAP = {nfc(k): v for k, v in SIDO_MAP.items()}

code = pdr.code_bdong()
code["시도명"] = code["시도명"].map(nfc)

sigungu_level = code[
    (code["읍면동명"].fillna("") == "") & (code["시군구명"].fillna("") != "")
].copy()

# 폐지(말소)되지 않은 현재 유효한 시군구만 사용 (말소일자가 빈 문자열인 행)
sigungu_level = sigungu_level[sigungu_level["말소일자"].fillna("") == ""]

sigungu_level["sido_short"] = sigungu_level["시도명"].map(SIDO_MAP)

unmapped = sigungu_level[sigungu_level["sido_short"].isna()]["시도명"].unique()
if len(unmapped):
    print("매핑 안 된 시도명:", list(unmapped))

# 세종특별자치시는 시/군/구 하위 구분이 없어 시군구명이 항상 비어 있으므로
# 위 필터에서 통째로 빠짐 -> 시도 전체를 대표하는 "36000" 행을 별도로 추가
sejong = code[
    (code["시도명"] == "세종특별자치시")
    & (code["시군구코드"] == code["시도코드"] + "000")
    & (code["말소일자"].fillna("") == "")
].copy()
sejong["시군구명"] = "세종특별자치시"
sejong["sido_short"] = "세종"

result = pd.concat([sigungu_level, sejong], ignore_index=True)[
    ["sido_short", "시도명", "시도코드", "시군구명", "시군구코드", "법정동코드"]
].sort_values(["sido_short", "시군구코드"])

out_path = "data_region_codes.csv"
result.to_csv(out_path, index=False, encoding="utf-8-sig")
print(f"총 {len(result)}개 시군구 코드 저장 -> {out_path}")
print(f"시도 커버리지: {result['sido_short'].nunique()}개 시도")
