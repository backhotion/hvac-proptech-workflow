---
date: 2026-08-29
category: 스키마
data: data_experiment_assignments
tags: [실험]
source: "data/experiment_assignments.parquet (합성)"
---

## 개요

257,688행.

## 그레인

**한 행 = 실험 1개 × 방문자 1명 (복합 그레인)**

## 기간

날짜 컬럼 없음 — [[data_experiments]]의 실험 기간을 따른다.

## 컬럼

| 컬럼명 | 타입 | 설명 | 결측 |
| --- | --- | --- | --- |
| experiment_id | string | 실험 ID | 0 |
| visitor_id | string | 방문자 ID | 0 |
| variant | string | A 또는 B | 0 |

## 배정 균형 (SRM 사전 점검)

| 실험 | A | B | 비율 |
| --- | --- | --- | --- |
| EXP-001~002, 004~005 | ~50% | ~50% | 정상 |
| **EXP-003** | 52.4% | 47.6% | **50:50 아님 — Day4에서 SRM 검정 필요** |

## 연결

- `experiment_id` → [[data_experiments]] (N:1)
- `visitor_id` → [[data_customers]], [[data_sessions]]
