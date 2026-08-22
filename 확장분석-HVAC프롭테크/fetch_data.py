# -*- coding: utf-8 -*-
"""
HVAC(공조자재) + 프롭테크 확장 분석용 공공데이터 조회 스크립트.

사용 전 준비:
  1. pip install -r requirements.txt
  2. .env.example을 .env로 복사하고 발급받은 서비스키를 채워 넣기
     - 공공데이터포털(data.go.kr) 서비스키: 실거래가·건축인허가·건축물대장에 공통 사용
     - KOSIS 인증키: KOSIS 통계자료 조회 전용(공공데이터포털과 별도 발급)

이 스크립트는 각 데이터소스별로 함수 하나씩 제공한다. 실행하면(`python fetch_data.py`)
.env에 실제 키가 채워져 있는 함수만 시범 조회하고, 나머지는 건너뛰며 이유를 출력한다.

[알려진 이슈] 건축인허가/건축물대장 API는 서버가 한 번에 최대 100건만 응답한다.
PublicDataReader 라이브러리 기본값(numOfRows=99999)을 그대로 쓰면 서버가 이를 비정상
처리(1건만 반환 등)해서 라이브러리의 페이지 수 계산이 어긋나고, 페이지당 기본 30초
대기가 곱해져 사실상 멈춘 것처럼 보인다. 그래서 이 두 데이터소스는 라이브러리를 쓰지
않고 requests로 직접 페이지네이션한다(numOfRows=100 고정, max_pages로 상한).
"""
import os

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

PUBLIC_DATA_SERVICE_KEY = os.getenv("PUBLIC_DATA_SERVICE_KEY", "")
KOSIS_SERVICE_KEY = os.getenv("KOSIS_SERVICE_KEY", "")
KRX_SERVICE_KEY = os.getenv("KRX_SERVICE_KEY", "")

PLACEHOLDER_MARKERS = ("여기에_", "")

BUILDING_LICENSE_URLS = {
    "기본개요": "http://apis.data.go.kr/1613000/ArchPmsHubService/getApBasisOulnInfo",
    "동별개요": "http://apis.data.go.kr/1613000/ArchPmsHubService/getApDongOulnInfo",
    "층별개요": "http://apis.data.go.kr/1613000/ArchPmsHubService/getApFlrOulnInfo",
    "호별개요": "http://apis.data.go.kr/1613000/ArchPmsHubService/getApHoOulnInfo",
}

BUILDING_LEDGER_URLS = {
    "기본개요": "http://apis.data.go.kr/1613000/BldRgstHubService/getBrBasisOulnInfo",
    "총괄표제부": "http://apis.data.go.kr/1613000/BldRgstHubService/getBrRecapTitleInfo",
    "표제부": "http://apis.data.go.kr/1613000/BldRgstHubService/getBrTitleInfo",
    "층별개요": "http://apis.data.go.kr/1613000/BldRgstHubService/getBrFlrOulnInfo",
}

SERVER_MAX_ROWS = 100  # 두 API 모두 서버가 이보다 큰 numOfRows를 무시/오처리함


def _has_key(key):
    return bool(key) and key not in PLACEHOLDER_MARKERS and "여기에_" not in key


def lookup_region_code(sigungu_name):
    """
    시군구명으로 법정동코드를 조회한다 (인증키 불필요).
    예: lookup_region_code("분당구")
    """
    import PublicDataReader as pdr

    code = pdr.code_bdong()
    return code.loc[
        (code["시군구명"].str.contains(sigungu_name, na=False))
        & (code["읍면동명"] == "")
    ]


def fetch_transaction_price(
    sigungu_code,
    year_month=None,
    start_year_month=None,
    end_year_month=None,
    property_type="아파트",
    trade_type="매매",
):
    """
    국토교통부 부동산 실거래가 조회.
    property_type: "아파트" | "연립다세대" | "단독다가구" | "오피스텔" | "상업업무용" 등
    trade_type: "매매" | "전월세"
    year_month: 단일 년월(예: "202506") — start/end_year_month와 배타적으로 사용
    """
    if not _has_key(PUBLIC_DATA_SERVICE_KEY):
        raise RuntimeError(".env의 PUBLIC_DATA_SERVICE_KEY를 먼저 채워주세요.")

    from PublicDataReader import TransactionPrice

    api = TransactionPrice(PUBLIC_DATA_SERVICE_KEY)
    kwargs = {
        "property_type": property_type,
        "trade_type": trade_type,
        "sigungu_code": sigungu_code,
    }
    if year_month:
        kwargs["year_month"] = year_month
    else:
        kwargs["start_year_month"] = start_year_month
        kwargs["end_year_month"] = end_year_month
    return api.get_data(**kwargs)


def _fetch_arch_hub(url_map, service_type, params_base, max_pages, timeout):
    """건축인허가/건축물대장 공통 페이지네이션 헬퍼 (requests 직접 호출)."""
    if not _has_key(PUBLIC_DATA_SERVICE_KEY):
        raise RuntimeError(".env의 PUBLIC_DATA_SERVICE_KEY를 먼저 채워주세요.")
    if service_type not in url_map:
        raise ValueError(f"service_type은 {list(url_map)} 중 하나여야 합니다.")

    url = url_map[service_type]
    all_rows = []
    total_count = None
    page = 1
    while True:
        params = {
            **params_base,
            "serviceKey": requests.utils.unquote(PUBLIC_DATA_SERVICE_KEY),
            "numOfRows": SERVER_MAX_ROWS,
            "pageNo": page,
            "_type": "json",
        }
        res = requests.get(url, params=params, timeout=timeout, verify=False)
        res.raise_for_status()
        body = res.json().get("response", {}).get("body", {})
        total_count = int(body.get("totalCount", 0))
        items = body.get("items")
        rows = [] if not items else items.get("item", [])
        if isinstance(rows, dict):
            rows = [rows]
        all_rows.extend(rows)

        if not rows or len(all_rows) >= total_count or page >= max_pages:
            break
        page += 1

    df = pd.DataFrame(all_rows)
    fetched = len(df)
    if total_count is not None and fetched < total_count:
        print(
            f"  [안내] 전체 {total_count}건 중 {fetched}건만 수집함 "
            f"(max_pages={max_pages}, 페이지당 {SERVER_MAX_ROWS}건). "
            "전체가 필요하면 max_pages를 늘려서 다시 호출하세요."
        )
    return df


def fetch_building_license(sigungu_code, bdong_code, service_type="기본개요", max_pages=3, timeout=15):
    """
    국토교통부 건축HUB 건축인허가정보 조회.
    service_type: "기본개요" | "동별개요" | "층별개요" | "호별개요"
    max_pages: 페이지당 100건씩, 최대 이 페이지 수까지만 수집(전체 수집 시 시간이 오래 걸림)
    """
    params_base = {"sigunguCd": sigungu_code, "bjdongCd": bdong_code}
    return _fetch_arch_hub(BUILDING_LICENSE_URLS, service_type, params_base, max_pages, timeout)


def fetch_building_ledger(sigungu_code, bdong_code, bun=None, ji=None, ledger_type="기본개요", max_pages=3, timeout=15):
    """
    국토교통부 건축HUB 건축물대장정보 조회.
    ledger_type: "기본개요" | "총괄표제부" | "표제부" | "층별개요"
    bun/ji: 지번의 본번/부번 (예: 237번지 -> bun="237")
    max_pages: 페이지당 100건씩, 최대 이 페이지 수까지만 수집(전체 수집 시 시간이 오래 걸림)
    """
    params_base = {"sigunguCd": sigungu_code, "bjdongCd": bdong_code}
    if bun:
        params_base["bun"] = str(bun).zfill(4)
    if ji:
        params_base["ji"] = str(ji).zfill(4)
    return _fetch_arch_hub(BUILDING_LEDGER_URLS, ledger_type, params_base, max_pages, timeout)


def fetch_kosis_search(search_term):
    """KOSIS 통합검색 — 통계표를 키워드로 찾을 때 사용 (예: "미분양 현황")."""
    if not _has_key(KOSIS_SERVICE_KEY):
        raise RuntimeError(".env의 KOSIS_SERVICE_KEY를 먼저 채워주세요.")

    from PublicDataReader import Kosis

    api = Kosis(KOSIS_SERVICE_KEY)
    return api.get_data("KOSIS통합검색", searchNm=search_term)


def fetch_kosis_data(org_id, tbl_id, start_period, end_period, period_type="Y"):
    """
    KOSIS 통계자료 조회.
    org_id/tbl_id: fetch_kosis_search로 먼저 찾은 통계표의 기관코드/통계표ID
    period_type: "Y"(연) | "Q"(분기) | "M"(월)
    """
    if not _has_key(KOSIS_SERVICE_KEY):
        raise RuntimeError(".env의 KOSIS_SERVICE_KEY를 먼저 채워주세요.")

    from PublicDataReader import Kosis

    api = Kosis(KOSIS_SERVICE_KEY)
    return api.get_data(
        "통계자료",
        orgId=org_id,
        tblId=tbl_id,
        itmId="ALL",
        objL1="ALL",
        objL2="ALL",
        prdSe=period_type,
        startPrdDe=start_period,
        endPrdDe=end_period,
    )


def fetch_reits_price(*args, **kwargs):
    """
    [준비 중] KRX Open API(openapi.krx.co.kr)로 상장리츠 23종목 시세·배당 조회 예정.

    아직 실제 엔드포인트/요청 파라미터를 확인하지 못해 미구현 상태다(추측으로 잘못된
    엔드포인트를 넣지 않기 위해 비워둠). KRX_SERVICE_KEY 발급 후 포털의 API 문서에서
    아래 정보를 확인해 이 함수를 채울 것:
      - 정확한 엔드포인트 URL (예: /svc/apis/sto/stk_bydd_trd 형태로 추정되나 미확인)
      - 요청 파라미터명(인증키 헤더/쿼리 위치, 종목코드, 조회일자 등)
      - 리츠 23종목의 종목코드 목록(KRX 정보데이터시스템 "상장리츠 현황"에서 확인 가능)
    """
    if not _has_key(KRX_SERVICE_KEY):
        raise RuntimeError(".env의 KRX_SERVICE_KEY를 먼저 채워주세요.")
    raise NotImplementedError(
        "KRX Open API 엔드포인트 사양이 아직 확인되지 않았습니다. "
        "포털에서 API 문서를 확인한 뒤 이 함수를 구현해야 합니다."
    )


if __name__ == "__main__":
    print("=== 법정동코드 조회 (인증키 불필요) ===")
    print(lookup_region_code("분당구"))

    demo_calls = [
        ("실거래가(분당구, 아파트, 2025-06)", lambda: fetch_transaction_price("41135", year_month="202506")),
        ("건축인허가(분당구 기본개요, 최대 3페이지)", lambda: fetch_building_license("41135", "11000", max_pages=3)),
        ("건축물대장(분당구 기본개요, 최대 3페이지)", lambda: fetch_building_ledger("41135", "11000", max_pages=3)),
        ("KOSIS 통합검색('미분양 현황')", lambda: fetch_kosis_search("미분양 현황")),
    ]

    for label, call in demo_calls:
        print(f"\n=== {label} ===")
        try:
            df = call()
            print(f"rows={len(df)}")
            print(df.head() if isinstance(df, pd.DataFrame) else df)
        except RuntimeError as e:
            print(f"건너뜀: {e}")
