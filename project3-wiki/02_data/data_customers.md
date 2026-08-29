---
date: 2026-08-29
category: 스키마
data: data_customers
tags: [고객마스터]
source: "data/customers.parquet (합성 — [[../../project3-data-gen/README]] 참고)"
---

## 개요

50,000행. 헤더 제외 실제 데이터 50,000건.

## 그레인

**한 행 = 고객 1명**

## 기간

`signup_date`: 2018-12-25 ~ 2025-12-31. 2025년 이전 가입자(기존 고객)와 2025년 신규 가입자가 섞여 있다 — 정상(부록 C "기간이 다르다" 케이스, 가입일은 과거일 수밖에 없음).

## 컬럼

| 컬럼명 | 타입 | 설명 | 결측 |
| --- | --- | --- | --- |
| customer_id | string | 고객 ID (PK) | 0 |
| visitor_id | string | 2025년 퍼널을 거쳐 가입한 고객만 존재. 기존 고객은 2025년 퍼널 이력이 없어 결측 | 43,239 (86.5%) |
| signup_date | date | 가입일 | 0 |
| churn_date | date | 이탈일. 이탈하지 않았으면 결측 | 39,301 (78.6%) |
| plan_tier | string | 가입 요금제. 값: basic, standard, premium | 0 |

## 연결

- `customer_id` → [[data_usage_monthly]], [[data_support_tickets]] (1:N)
- `visitor_id` → [[data_sessions]], [[data_funnel_events]] (1:N, **43,239건 결측 — 조인 함정 주의**. INNER JOIN 시 43,239명이 소실된다. 원인: 기존 고객은 2025년 퍼널을 거치지 않았다. 정상)
