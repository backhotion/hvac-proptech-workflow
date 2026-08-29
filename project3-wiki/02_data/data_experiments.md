---
date: 2026-08-29
category: 스키마
data: data_experiments
tags: [실험]
source: "data/experiments.parquet (합성)"
---

## 개요

5행.

## 그레인

**한 행 = 실험 1개**

## 기간

`start_date`~`end_date`: 2025-02-01 ~ 2025-10-01 (실험마다 다름). 실험 기간이므로 정상.

## 컬럼

| 컬럼명 | 타입 | 설명 | 결측 |
| --- | --- | --- | --- |
| experiment_id | string | 실험 ID (PK). EXP-001~005 | 0 |
| experiment_name | string | 실험명 | 0 |
| start_date | date | 시작일 | 0 |
| end_date | date | 종료일 | 0 |

## 연결

- `experiment_id` → [[data_experiment_assignments]] (1:N)
