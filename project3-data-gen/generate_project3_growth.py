# -*- coding: utf-8 -*-
"""7주차 project3_growth 합성 데이터 생성기.

강의에서 배포하는 parquet 9개(고객·세션·퍼널·이용량·실험배정·문의·광고비·캠페인·실험)를
받지 못해, 교안(Day1_교안.pdf)이 설명하는 구조적 특징을 그대로 갖도록 직접 생성한다.

일부러 심은 것 (교안이 다루는 학습 포인트와 그대로 대응):
- customers.visitor_id 대부분 결측(기존 고객은 2025년 퍼널을 거치지 않음) — Day1 조인 함정
- sessions.campaign_id 일부 결측(자연 유입) — Day1
- support_tickets.satisfaction_score 다수 결측(응답 안 한 사람) — Day1
- 퍼널 단계별 전환율이 서로 다름, 특히 "신청시작→신청완료" 구간이 병목 — Day2
- experiment_assignments 중 EXP-003 하나만 50:50이 아니게 배정(SRM) — Day4

시드 고정 — 재실행해도 같은 데이터가 나온다.
"""
import numpy as np
import pandas as pd

SEED = 42
rng = np.random.default_rng(SEED)

OUT = "../data"

FUNNEL_STAGES = ["랜딩방문", "요금제조회", "신청시작", "신청완료", "개통", "첫결제"]
# 단계별 전환율. 신청시작->신청완료가 의도적으로 낮다(병목).
STAGE_CONVERSION = [1.0, 0.50, 0.44, 0.20, 0.90, 0.93]

N_VISITORS = 180_000
N_CUSTOMERS = 50_000

# ---------------------------------------------------------------------------
# 1) 방문자 퍼널 시뮬레이션 -> funnel_events, 최종 전환자 집합
# ---------------------------------------------------------------------------
visitor_ids = np.array([f"V{i:07d}" for i in range(1, N_VISITORS + 1)])
base_dates = pd.Timestamp("2025-01-01") + pd.to_timedelta(
    rng.integers(0, 365, size=N_VISITORS), unit="D"
)

funnel_rows = []
reached = np.ones(N_VISITORS, dtype=bool)  # 전원 랜딩방문에서 시작
stage_reach_day_offset = np.zeros(N_VISITORS, dtype=int)

for stage, conv in zip(FUNNEL_STAGES, STAGE_CONVERSION):
    if stage != FUNNEL_STAGES[0]:
        advance = rng.random(N_VISITORS) < conv
        reached = reached & advance
    idx = np.where(reached)[0]
    stage_reach_day_offset[idx] += rng.integers(0, 3, size=len(idx))
    event_dates = base_dates[idx] + pd.to_timedelta(stage_reach_day_offset[idx], unit="D")
    for vid, d in zip(visitor_ids[idx], event_dates):
        funnel_rows.append((vid, stage, d))

funnel_events = pd.DataFrame(funnel_rows, columns=["visitor_id", "stage", "event_date"])
funnel_events["event_date"] = funnel_events["event_date"].clip(upper=pd.Timestamp("2025-12-31"))
funnel_events.insert(0, "event_id", [f"FE{i:08d}" for i in range(1, len(funnel_events) + 1)])
funnel_events = funnel_events.sort_values(["visitor_id", "event_date"]).reset_index(drop=True)

converted_visitors = set(
    funnel_events.loc[funnel_events["stage"] == "첫결제", "visitor_id"]
)
converted_visitors = np.array(sorted(converted_visitors))
n_converted = len(converted_visitors)

# ---------------------------------------------------------------------------
# 2) customers — 그레인: 고객 1명
#    기존 고객(2018~2024 가입, visitor_id 없음) + 신규 2025 전환 고객(visitor_id 있음)
# ---------------------------------------------------------------------------
n_existing = N_CUSTOMERS - n_converted
existing_signup = pd.Timestamp("2018-12-25") + pd.to_timedelta(
    rng.integers(0, (pd.Timestamp("2024-12-31") - pd.Timestamp("2018-12-25")).days, size=n_existing),
    unit="D",
)
first_payment = (
    funnel_events[funnel_events.stage == "첫결제"]
    .sort_values("event_date")
    .drop_duplicates("visitor_id", keep="first")
    .set_index("visitor_id")["event_date"]
)
new_signup = pd.to_datetime(first_payment.loc[converted_visitors].values)

customer_ids = np.array([f"C{i:06d}" for i in range(1, N_CUSTOMERS + 1)])
rng.shuffle(customer_ids)
existing_cids, new_cids = customer_ids[:n_existing], customer_ids[n_existing:]

plan_tiers = rng.choice(["basic", "standard", "premium"], size=N_CUSTOMERS, p=[0.5, 0.35, 0.15])

# 이탈: 오래된 고객일수록 이탈 확률이 높다
existing_age_days = (pd.Timestamp("2025-12-31") - existing_signup).days.to_numpy()
churn_prob_existing = np.clip(existing_age_days / 365 * 0.06, 0, 0.6)
churned_existing = rng.random(n_existing) < churn_prob_existing
churn_date_existing = pd.Series(pd.NaT, index=range(n_existing), dtype="datetime64[ns]")
idx_churn = np.where(churned_existing)[0]
churn_date_existing.iloc[idx_churn] = existing_signup[idx_churn] + pd.to_timedelta(
    rng.integers(180, existing_age_days[idx_churn].clip(min=181)), unit="D"
)
churn_date_existing = churn_date_existing.clip(upper=pd.Timestamp("2025-12-31"))

new_age_days = (pd.Timestamp("2025-12-31") - new_signup).days.to_numpy()
churn_prob_new = np.clip(new_age_days / 365 * 0.04, 0, 0.3)
churned_new = rng.random(n_converted) < churn_prob_new
churn_date_new = pd.Series(pd.NaT, index=range(n_converted), dtype="datetime64[ns]")
idx_churn_new = np.where(churned_new)[0]
safe_span = new_age_days[idx_churn_new].clip(min=31)
churn_date_new.iloc[idx_churn_new] = new_signup[idx_churn_new] + pd.to_timedelta(
    rng.integers(30, safe_span), unit="D"
)
churn_date_new = churn_date_new.clip(upper=pd.Timestamp("2025-12-31"))

customers = pd.concat([
    pd.DataFrame({
        "customer_id": existing_cids,
        "visitor_id": pd.array([None] * n_existing, dtype="string"),
        "signup_date": existing_signup,
        "churn_date": churn_date_existing.values,
        "plan_tier": plan_tiers[:n_existing],
    }),
    pd.DataFrame({
        "customer_id": new_cids,
        "visitor_id": converted_visitors,
        "signup_date": new_signup,
        "churn_date": churn_date_new.values,
        "plan_tier": plan_tiers[n_existing:],
    }),
]).sample(frac=1, random_state=SEED).reset_index(drop=True)

# ---------------------------------------------------------------------------
# 3) sessions — 그레인: 방문 세션 1회. 방문자당 세션 여러 개(1인당 평균 ~1.6세션)
# ---------------------------------------------------------------------------
n_sessions_target = 292_866
sessions_per_visitor = rng.poisson(1.63, size=N_VISITORS).clip(min=1)
scale = n_sessions_target / sessions_per_visitor.sum()
sessions_per_visitor = np.round(sessions_per_visitor * scale).astype(int).clip(min=1)

sess_visitor = np.repeat(visitor_ids, sessions_per_visitor)
n_sessions = len(sess_visitor)
sess_dates = pd.Timestamp("2025-01-01") + pd.to_timedelta(rng.integers(0, 365, size=n_sessions), unit="D")
device = rng.choice(["mobile", "desktop", "tablet"], size=n_sessions, p=[0.62, 0.33, 0.05])

campaign_ids_pool = np.array([f"CMP{i:04d}" for i in range(1, 121)])
has_campaign = rng.random(n_sessions) >= 0.38  # 38% 결측(자연유입)
sess_campaign = np.where(has_campaign, rng.choice(campaign_ids_pool, size=n_sessions), None)

sessions = pd.DataFrame({
    "session_id": [f"S{i:08d}" for i in range(1, n_sessions + 1)],
    "visitor_id": sess_visitor,
    "session_date": sess_dates,
    "device_type": device,
    "campaign_id": pd.array(sess_campaign, dtype="string"),
})

# ---------------------------------------------------------------------------
# 4) usage_monthly — 그레인: 고객 x 월
# ---------------------------------------------------------------------------
usage_rows = []
signup_map = dict(zip(customers.customer_id, customers.signup_date))
churn_map = dict(zip(customers.customer_id, customers.churn_date))
for cid, signup, churn in zip(customers.customer_id, customers.signup_date, customers.churn_date):
    start = max(signup, pd.Timestamp("2025-01-01"))
    end = churn if pd.notna(churn) else pd.Timestamp("2025-12-31")
    end = min(end, pd.Timestamp("2025-12-31"))
    if end < start:
        continue
    months = pd.period_range(start, end, freq="M")
    for m in months:
        usage_rows.append((cid, str(m)))

usage_monthly = pd.DataFrame(usage_rows, columns=["customer_id", "month"])
n_u = len(usage_monthly)
usage_monthly["usage_minutes"] = rng.gamma(shape=4.0, scale=120, size=n_u).round(1)
usage_monthly["billing_amount"] = rng.choice([9900, 19900, 29900], size=n_u, p=[0.5, 0.35, 0.15]) \
    + rng.normal(0, 500, size=n_u).round(0)
usage_monthly["billing_amount"] = usage_monthly["billing_amount"].clip(lower=0).round(0)

# ---------------------------------------------------------------------------
# 5) experiments, experiment_assignments
# ---------------------------------------------------------------------------
experiments = pd.DataFrame({
    "experiment_id": ["EXP-001", "EXP-002", "EXP-003", "EXP-004", "EXP-005"],
    "experiment_name": ["요금제페이지_UI", "신청폼_단계축소", "첫결제_할인배너", "온보딩_이메일", "환불정책_문구"],
    "start_date": pd.to_datetime(["2025-02-01", "2025-03-15", "2025-04-01", "2025-06-01", "2025-08-01"]),
    "end_date": pd.to_datetime(["2025-03-01", "2025-04-15", "2025-05-01", "2025-07-01", "2025-10-01"]),
})

assign_rows = []
exp_visitor_pools = {
    "EXP-001": rng.choice(visitor_ids, size=60000, replace=False),
    "EXP-002": rng.choice(visitor_ids, size=55000, replace=False),
    "EXP-003": rng.choice(visitor_ids, size=50000, replace=False),
    "EXP-004": rng.choice(visitor_ids, size=45000, replace=False),
    "EXP-005": rng.choice(visitor_ids, size=47688, replace=False),
}
for exp_id, pool in exp_visitor_pools.items():
    if exp_id == "EXP-003":
        # 일부러 SRM: 50:50이 아니라 52.9:47.1
        variant = rng.choice(["A", "B"], size=len(pool), p=[0.529, 0.471])
    else:
        variant = rng.choice(["A", "B"], size=len(pool), p=[0.5, 0.5])
    for vid, var in zip(pool, variant):
        assign_rows.append((exp_id, vid, var))

experiment_assignments = pd.DataFrame(assign_rows, columns=["experiment_id", "visitor_id", "variant"])

# ---------------------------------------------------------------------------
# 6) support_tickets
# ---------------------------------------------------------------------------
n_tickets = 32_724
ticket_cust = rng.choice(customers.customer_id, size=n_tickets)
ticket_dates = pd.Timestamp("2025-01-01") + pd.to_timedelta(rng.integers(0, 365, size=n_tickets), unit="D")
issue_types = rng.choice(
    ["요금문의", "서비스오류", "해지요청", "환불요청", "기타"], size=n_tickets, p=[0.35, 0.25, 0.15, 0.1, 0.15]
)
has_score = rng.random(n_tickets) >= 0.70  # 70% 결측
raw_score = rng.choice([1, 2, 3, 4, 5], size=n_tickets, p=[0.12, 0.1, 0.18, 0.3, 0.3])
satisfaction = np.where(has_score, raw_score, None)

support_tickets = pd.DataFrame({
    "ticket_id": [f"T{i:07d}" for i in range(1, n_tickets + 1)],
    "customer_id": ticket_cust,
    "ticket_date": ticket_dates,
    "issue_type": issue_types,
    "satisfaction_score": pd.array(satisfaction, dtype="Int64"),
})

# ---------------------------------------------------------------------------
# 7) campaigns, ad_spend
# ---------------------------------------------------------------------------
n_campaigns = 120
camp_channel = rng.choice(["search", "social", "display", "referral"], size=n_campaigns, p=[0.4, 0.35, 0.15, 0.1])
camp_start = pd.Timestamp("2025-01-01") + pd.to_timedelta(rng.integers(0, 335, size=n_campaigns), unit="D")
camp_end = camp_start + pd.to_timedelta(rng.integers(10, 30, size=n_campaigns), unit="D")
campaigns = pd.DataFrame({
    "campaign_id": campaign_ids_pool,
    "campaign_name": [f"캠페인_{i:03d}" for i in range(1, n_campaigns + 1)],
    "channel": camp_channel,
    "start_date": camp_start,
    "end_date": camp_end,
})

ad_rows = []
for cid, s, e in zip(campaigns.campaign_id, campaigns.start_date, campaigns.end_date):
    for d in pd.date_range(s, e, freq="D"):
        ad_rows.append((cid, d))
ad_spend = pd.DataFrame(ad_rows, columns=["campaign_id", "date"])
n_a = len(ad_spend)
ad_spend["spend_amount"] = rng.gamma(3.0, 50000, size=n_a).round(0)
ad_spend["impressions"] = (ad_spend["spend_amount"] / rng.uniform(50, 150, size=n_a)).round(0).astype(int)
ad_spend["clicks"] = (ad_spend["impressions"] * rng.uniform(0.01, 0.05, size=n_a)).round(0).astype(int)

# ---------------------------------------------------------------------------
# 저장
# ---------------------------------------------------------------------------
tables = {
    "customers": customers,
    "sessions": sessions,
    "funnel_events": funnel_events,
    "usage_monthly": usage_monthly,
    "experiment_assignments": experiment_assignments,
    "support_tickets": support_tickets,
    "ad_spend": ad_spend,
    "campaigns": campaigns,
    "experiments": experiments,
}

import os
os.makedirs(OUT, exist_ok=True)
total = 0
for name, df in tables.items():
    path = f"{OUT}/{name}.parquet"
    df.to_parquet(path, index=False)
    total += len(df)
    print(f"{name:<25} {len(df):>10,}행  {df.shape[1]}컬럼")
print(f"{'합계':<25} {total:>10,}행")
