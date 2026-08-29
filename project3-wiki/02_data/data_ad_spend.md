---
date: 2026-08-29
category: 스키마
data: data_ad_spend
tags: [광고]
source: "data/ad_spend.parquet (합성)"
---

## 개요

2,422행.

## 그레인

**한 행 = 캠페인 1개 × 집행일 1일 (복합 그레인)**

## 기간

`date`: 2025-01-01 ~ 2025-12-26.

## 컬럼

| 컬럼명 | 타입 | 설명 | 결측 |
| --- | --- | --- | --- |
| campaign_id | string | 캠페인 ID | 0 |
| date | date | 집행일 | 0 |
| spend_amount | float | 집행 금액(원) | 0 |
| impressions | int | 노출수 | 0 |
| clicks | int | 클릭수 | 0 |

## 연결

- `campaign_id` → [[data_campaigns]] (N:1)
