---
date: 2026-08-29
category: 스키마
data: data_funnel_events
tags: [퍼널]
source: "data/funnel_events.parquet (합성)"
---

## 개요

331,923행. (visitor_id, stage) 조합 중복 0건 — 그레인이 유일하다.

## 그레인

**한 행 = 방문자 1명이 퍼널 단계 1개에 도달한 사건 1건**

## 기간

`event_date`: 2025-01-01 ~ 2025-12-31.

## 컬럼

| 컬럼명 | 타입 | 설명 | 결측 |
| --- | --- | --- | --- |
| event_id | string | 이벤트 ID (PK) | 0 |
| visitor_id | string | 방문자 ID | 0 |
| stage | string | 랜딩방문/요금제조회/신청시작/신청완료/개통/첫결제 중 하나 | 0 |
| event_date | date | 도달일 | 0 |

## 단계별 도달자 수 (전환율)

| 단계 | 도달자 | 직전 대비 전환율 |
| --- | --- | --- |
| 랜딩방문 | 180,000 | — |
| 요금제조회 | 90,122 | 50.1% |
| 신청시작 | 39,684 | 44.0% |
| 신청완료 | 8,084 | **20.4% (병목)** |
| 개통 | 7,272 | 90.0% |
| 첫결제 | 6,761 | 93.0% |

**신청시작 → 신청완료 구간이 가장 낮다.** Day2에서 원인을 다룬다.

## 연결

- `visitor_id` → [[data_customers]] (첫결제 도달자만 customers.visitor_id로 연결됨), [[data_sessions]]
