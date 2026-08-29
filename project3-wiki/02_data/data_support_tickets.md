---
date: 2026-08-29
category: 스키마
data: data_support_tickets
tags: [문의, 만족도]
source: "data/support_tickets.parquet (합성)"
---

## 개요

32,724행.

## 그레인

**한 행 = 문의 티켓 1건**

## 기간

`ticket_date`: 2025-01-01 ~ 2025-12-31.

## 컬럼

| 컬럼명 | 타입 | 설명 | 결측 |
| --- | --- | --- | --- |
| ticket_id | string | 티켓 ID (PK) | 0 |
| customer_id | string | 고객 ID | 0 |
| ticket_date | date | 접수일 | 0 |
| issue_type | string | 요금문의/서비스오류/해지요청/환불요청/기타 | 0 |
| satisfaction_score | Int64 | 1~5점. 만족도 설문에 응답하지 않은 문의는 결측 | 22,954 (70.1%) |

**결측을 평균으로 채우지 않는다.** 응답한 사람만의 평균은 전체 만족도가 아니고, 매우 만족/매우 불만인 사람이 더 많이 응답하는 경향이 있다. 결측 자체가 정보다.

## 연결

- `customer_id` → [[data_customers]] (N:1)
