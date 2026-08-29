---
date: 2026-08-29
category: 스키마
data: data_usage_monthly
tags: [이용량, 청구]
source: "data/usage_monthly.parquet (합성)"
---

## 개요

455,706행. (customer_id, month) 조합 중복 0건.

## 그레인

**한 행 = 고객 1명 × 월 1개 (복합 그레인)**

customers(50,000행)와 customer_id로 조인하면 최대 12배까지 팬아웃될 수 있다 — 조인 후 `AVG` 계산 시 부록 B 참고(예: AVG(age)를 조인 후에 하면 오래 남은 고객 쪽으로 평균이 기운다).

## 기간

`month`: 2025-01 ~ 2025-12.

## 컬럼

| 컬럼명 | 타입 | 설명 | 결측 |
| --- | --- | --- | --- |
| customer_id | string | 고객 ID | 0 |
| month | string (YYYY-MM) | 집계 월 | 0 |
| usage_minutes | float | 월 이용 시간(분) | 0 |
| billing_amount | float | 월 청구액(원) | 0 |

## 연결

- `customer_id` → [[data_customers]] (N:1)
