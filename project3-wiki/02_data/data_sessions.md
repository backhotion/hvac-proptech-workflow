---
date: 2026-08-29
category: 스키마
data: data_sessions
tags: [방문세션]
source: "data/sessions.parquet (합성)"
---

## 개요

323,791행.

## 그레인

**한 행 = 방문 세션 1회.** 방문자 180,000명이 세션 323,791건을 만든다 — 1인당 평균 1.80세션. 그레인이 "방문자"가 아니라 "세션"이라는 점이 중요하다. 한 사람이 여러 번 온다.

## 기간

`session_date`: 2025-01-01 ~ 2025-12-31.

## 컬럼

| 컬럼명 | 타입 | 설명 | 결측 |
| --- | --- | --- | --- |
| session_id | string | 세션 ID (PK) | 0 |
| visitor_id | string | 방문자 ID | 0 |
| session_date | date | 방문일 | 0 |
| device_type | string | mobile/desktop/tablet | 0 |
| campaign_id | string | 유입 캠페인. 자연 유입(검색·직접 방문)은 캠페인이 없어 결측 | 123,190 (38.0%) |

## 연결

- `visitor_id` → [[data_customers]] (N:1, 전환한 방문자만), [[data_funnel_events]] (같은 방문자 기준)
- `campaign_id` → [[data_campaigns]] (N:1, 38% 결측 — "캠페인별 성과" 계산 시 이 38%를 어떻게 다룰지 정해야 한다)
