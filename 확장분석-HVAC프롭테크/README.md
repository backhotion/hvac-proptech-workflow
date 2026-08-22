# 확장분석 — HVAC(공조자재) + 프롭테크

`영업지원-분석`(SAC 설치자재) 프로젝트를 HVAC 종합공조자재 + 프롭테크(부동산+AI) 영역으로 확장하기 위한
데이터 조회 준비 폴더. 아직 실제 분석은 시작하지 않았고, **데이터를 가져올 수 있는 상태까지만** 준비되어 있다.

## 준비된 것

- `PublicDataReader`, `python-dotenv` 설치 완료(로컬 환경)
- `fetch_data.py` — 데이터소스별 조회 함수:
  - `lookup_region_code(시군구명)` — 법정동코드 조회, **인증키 불필요, 바로 실행 가능**
  - `fetch_transaction_price(...)` — 국토부 실거래가(아파트/오피스텔/상가 등)
  - `fetch_building_license(...)` — 건축HUB 건축인허가정보
  - `fetch_building_ledger(...)` — 건축HUB 건축물대장정보
  - `fetch_kosis_search(...)` / `fetch_kosis_data(...)` — KOSIS 통계 검색·조회

## 사용 방법

1. `pip install -r requirements.txt` (이미 로컬엔 설치됨)
2. `.env.example`을 `.env`로 복사
3. [공공데이터포털](https://www.data.go.kr)에서 회원가입 → 아래 API들에 활용신청(보통 2~3일 내 승인) → 발급된 서비스키를 `.env`의 `PUBLIC_DATA_SERVICE_KEY`에 붙여넣기
   - 국토교통부 실거래가 정보
   - 국토교통부_건축HUB_건축인허가정보 서비스
   - 국토교통부_건축HUB_건축물대장정보 서비스
4. KOSIS 통계자료를 쓰려면 [KOSIS 공유서비스](https://kosis.kr/openapi/)에서 **별도로** 인증키 발급 후 `.env`의 `KOSIS_SERVICE_KEY`에 붙여넣기
5. `python fetch_data.py` 실행 — 키가 채워진 함수만 실제로 조회하고, 나머지는 이유를 출력하며 건너뜀
6. `python run_pipeline.py` — `build_fact_region_month.py`(csv들과 BigQuery `dim_client` 조인으로
   `fact_region_month_integrated.csv` 재생성) → `validate_fact_region_month.py`(설계서 규칙 검증)를
   순서대로 실행한다. 검증에서 FAIL이 하나라도 나오면 종료코드 1로 알린다.

## 아직 안 된 것 (필요시 후속 작업)

- 조달청(자재 단가) API — `PublicDataReader` 미지원, 별도 `requests` 호출 코드 필요
- 부동산 빅데이터 플랫폼(REBPP), 한국에너지공단 통계 — API가 아니라 마켓플레이스/파일배포 형태라 별도 접근 방식 필요
- 실제 데이터 수집 범위(지역, 기간), 전처리 규칙, BigQuery 적재는 **API 키 발급 후 사용자 결정에 따라** 진행
