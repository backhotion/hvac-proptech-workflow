---
date: 2026-08-29
category: 스키마
data: data_campaigns
tags: [캠페인]
source: "data/campaigns.parquet (합성)"
---

## 개요

120행.

## 그레인

**한 행 = 캠페인 1개**

## 기간

`start_date`~`end_date`: 2025-01-01 ~ 2025-12-26 (캠페인마다 10~30일 구간).

## 컬럼

| 컬럼명 | 타입 | 설명 | 결측 |
| --- | --- | --- | --- |
| campaign_id | string | 캠페인 ID (PK) | 0 |
| campaign_name | string | 캠페인명 | 0 |
| channel | string | search/social/display/referral | 0 |
| start_date | date | 시작일 | 0 |
| end_date | date | 종료일 | 0 |

## 연결

- `campaign_id` → [[data_sessions]], [[data_ad_spend]] (1:N)
