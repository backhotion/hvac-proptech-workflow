# -*- coding: utf-8 -*-
"""퍼널·지표 계산. 8주차 Day2~Day3에 funnel·retention_funnel·kpis·monthly·
funnel_by·trust_check·verdict를 채웠다. 9주차 Day3에 proposal_topics()·
topic_evidence()를 추가한다 — 제안서 주제 후보를 뽑고, 고른 주제의 근거를
모으기만 한다(문장은 report/proposal.py가 만든다).
"""
from datetime import date

import pandas as pd

from core import config


def funnel(tables: dict) -> pd.DataFrame:
    """그레인: 주문 1건(주문번호 고유값). config.FUNNEL_STEPS 순서를 따른다.
    반환: 단계 | 도달 | 단계전환율(전 단계 대비, %) | 누적전환율(첫 단계 대비, %)
    """
    fe = tables["funnel_events"]
    cols = config.FUNNEL_STEP_COLUMNS
    first = fe["주문번호"].nunique()

    reach = {}
    reach[config.FUNNEL_STEPS[0]] = first  # 주문접수 — 전체 모집단
    reach[config.FUNNEL_STEPS[1]] = fe[cols[config.FUNNEL_STEPS[1]]].notna().sum()
    reach[config.FUNNEL_STEPS[2]] = fe[cols[config.FUNNEL_STEPS[2]]].notna().sum()
    reach[config.FUNNEL_STEPS[3]] = fe[cols[config.FUNNEL_STEPS[3]]].isin(["완료", "오주문처리"]).sum()
    reach[config.FUNNEL_STEPS[4]] = fe[cols[config.FUNNEL_STEPS[4]]].notna().sum()

    rows = []
    prev = None
    for step in config.FUNNEL_STEPS:
        n = int(reach[step])
        step_rate = (n / prev * 100) if prev else 100.0
        cum_rate = n / first * 100
        rows.append({
            "단계": config.FUNNEL_LABELS.get(step, step),
            "도달": n,
            "단계전환율": round(step_rate, 2),
            "누적전환율": round(cum_rate, 2),
        })
        prev = n
    return pd.DataFrame(rows)


def funnel_grain_check(tables: dict) -> dict:
    """3-1. 진짜 퍼널인지 판정 — 앞 단계를 안 거치고 다음 단계에 온 대상이 몇 건인가.
    mydomain/notes/02_퍼널실측.md에서 이미 0건으로 확인됐고, 여기서도 실측으로
    재확인한다(코드가 우연이 아니라 실제로 이 데이터에 대해 계산한 값임을 보장)."""
    fe = tables["funnel_events"]
    skip1 = int((fe["배송시작일"].isna() & fe["도착일자"].notna()).sum())
    skip2 = int((fe["도착일자"].isna() & fe["해피콜완료일"].notna()).sum())
    return {"배송시작_생략": skip1, "배송완료_생략": skip2, "진짜_퍼널": (skip1 == 0 and skip2 == 0)}


def retention_funnel(tables: dict) -> dict:
    """유지 퍼널 — 이 도메인은 "단계"가 아니라 대리 지표다.

    거래선 그레인에서 이탈 0건임을 확인했다(mydomain/notes/04_유지이탈정의.md,
    이번 40거래선·24개월 데이터로도 재확인). 그래서 config.RETENTION_STEPS를
    억지로 채우지 않고, 전월 대비 주문금액 급감을 "이탈 위험 신호" 대리 지표로 쓴다.
    """
    cmo = tables["client_monthly_orders"].sort_values(["거래선코드", "연월"]).copy()
    n_active_months = cmo.groupby("연월")["거래선코드"].nunique()
    total_clients = cmo["거래선코드"].nunique()
    churn_count = int((n_active_months < total_clients).sum())  # 0이어야 정상

    cmo["전월금액"] = cmo.groupby("거래선코드")["total_amount"].shift(1)
    cmo["증감률"] = (cmo["total_amount"] - cmo["전월금액"]) / cmo["전월금액"] * 100
    valid = cmo.dropna(subset=["증감률"])
    cutoff = config.RETENTION_PROXY["컷오프"]
    flagged = valid[valid["증감률"] <= cutoff].sort_values("증감률")

    return {
        "거래선_수": total_clients,
        "관측_개월": len(n_active_months),
        "월별_이탈_발생": churn_count,  # 0이면 "확인 완료 — 이탈 없음"
        "대리신호_건수": len(flagged),
        "대리신호_전체건수": len(valid),
        "대리신호_상세": flagged[["거래선코드", "거래선명", "연월", "total_amount", "전월금액", "증감률"]],
    }


def judge(name: str, value: float) -> str:
    """config.THRESHOLDS 기준으로 ok/warn/block 중 하나를 정한다.
    THRESHOLDS에 없는 지표(예: 월 주문건수 — 계절성 때문에 임계값을 안 둠)는 "none"."""
    rule = config.THRESHOLDS.get(name)
    if rule is None:
        return "none"
    worse_is_high = rule["방향"] == "높을수록 나쁨"
    if worse_is_high:
        if value >= rule["위험"]:
            return "block"
        if value >= rule["경고"]:
            return "warn"
    else:
        if value <= rule["위험"]:
            return "block"
        if value <= rule["경고"]:
            return "warn"
    return "ok"


def kpis(tables: dict) -> dict:
    """지표 카드 넷 — 규모·전환·속도·품질 네 축에서 하나씩.
    월 주문건수(규모)는 계절성이 너무 커서 임계값을 안 둔다(config.THRESHOLDS 참고).
    전월 대비 델타와 임계값 판정(ok/warn/block/none)을 함께 담는다.
    """
    m = monthly(tables)
    last = m.iloc[-1]
    prev = m.iloc[-2] if len(m) >= 2 else None

    out = {}
    for name, unit in [("월 주문건수", "건"), ("완료율", "%"), ("평균 리드타임", "일"), ("오주문율", "%")]:
        val = last[name]
        val = int(val) if name == "월 주문건수" else round(float(val), 2)
        delta = None
        if prev is not None:
            d = last[name] - prev[name]
            delta = int(d) if name == "월 주문건수" else round(float(d), 2)
        out[name] = {"값": val, "단위": unit, "델타": delta, "상태": judge(name, last[name])}
    return out


def monthly(tables: dict) -> pd.DataFrame:
    """월별 추이. 열 이름은 kpis()의 지표 이름과 같게 맞춘다(스파크라인·delta 계산용)."""
    fe = tables["funnel_events"].copy()
    fe["연월"] = fe["주문접수일"].str.slice(0, 7)
    fe["리드타임"] = (pd.to_datetime(fe["도착일자"]) - pd.to_datetime(fe["주문접수일"])).dt.days

    g = fe.groupby("연월").agg(
        주문건수=("주문번호", "nunique"),
        완료건수=("주문상태", lambda s: s.isin(["완료", "오주문처리"]).sum()),
        평균리드타임=("리드타임", "mean"),
        오주문건수=("오주문건여부", lambda s: (s == "Y").sum()),
    ).reset_index()
    g["완료율"] = (g["완료건수"] / g["주문건수"] * 100).round(2)
    g["오주문율"] = (g["오주문건수"] / g["주문건수"] * 100).round(2)
    g["평균 리드타임"] = g["평균리드타임"].round(2)
    g["월 주문건수"] = g["주문건수"]
    return g[["연월", "월 주문건수", "완료율", "평균 리드타임", "오주문율"]]


def _reached(df: pd.DataFrame, step: str) -> pd.Series:
    col = config.FUNNEL_STEP_COLUMNS[step]
    if step == "완료":
        return df[col].isin(["완료", "오주문처리"])
    return df[col].notna()


def trust_check(n_sample: int) -> dict:
    """못 믿을 조건 — 표본이 config.MIN_SAMPLE 미만이면 이 세그먼트의 판정을
    믿지 않는다. 판정 자체를 안 하는 것이지, 계산해서 감추는 게 아니다(호출
    쪽에서 이 결과를 보고 계산을 아예 건너뛴다)."""
    ok = n_sample >= config.MIN_SAMPLE
    if ok:
        reason = f"표본 {n_sample}건 확보 (최소 {config.MIN_SAMPLE} 이상)"
    else:
        reason = f"표본 {n_sample}건 (최소 {config.MIN_SAMPLE} 미만) — 판정을 하지 않는다"
    return {"신뢰": ok, "사유": reason}


def verdict(rate: float, baseline_rate: float, n_sample: int) -> dict:
    """세그먼트 전환율을 전체 평균과 비교해 성공/주의필요/효과없음/무효 중 하나로 정한다.
    기준은 config.VERDICT_MARGIN(사용자 결정) — 이 값 이상 벌어져야 '차이가 있다'고 본다."""
    trust = trust_check(n_sample)
    if not trust["신뢰"]:
        return {"판정": "무효", "사유": trust["사유"]}

    diff = round(rate - baseline_rate, 2)
    margin = config.VERDICT_MARGIN
    if diff >= margin:
        return {"판정": "성공", "사유": f"전체 평균 대비 {diff:+.2f}%p (기준 ±{margin}%p 이상 벌어짐)"}
    if diff <= -margin:
        return {"판정": "주의필요", "사유": f"전체 평균 대비 {diff:+.2f}%p (기준 ±{margin}%p 이상 벌어짐)"}
    return {"판정": "효과없음", "사유": f"전체 평균 대비 {diff:+.2f}%p — 기준(±{margin}%p) 안이라 차이로 보지 않는다"}


def funnel_by(tables: dict, axis: str, step_from: str, step_to: str) -> pd.DataFrame:
    """분해 축(거래선구분·시도)으로 퍼널 한 구간(step_from→step_to)을 쪼갠다.
    각 세그먼트를 전체 평균과 비교해 판정까지 붙여 돌려준다.

    도달 판정은 metrics.funnel()과 같은 방식으로 각 단계 컬럼을 독립적으로
    본다(이전 단계 도달 여부로 AND하지 않는다) — 그래야 전체 평균이 funnel()의
    누적전환율과 정확히 같아진다. 완료→해피콜완료 구간에는 "취소" 처리된 주문
    440건에 해피콜완료일이 남아있는 경우가 있는데, 이것도 funnel()처럼 그대로
    센다 — 이 구간만 다르게 세면 두 화면의 숫자가 어긋난다.
    """
    fe = tables["funnel_events"]
    clients = tables["clients"]
    if axis == "거래선코드":
        # 조인 키 자체를 축으로 쓰는 경우(예: 거래선 단위 편차 확인, 9주차 Day1
        # 발견 2·3) — clients 쪽에서 또 가져오면 같은 이름 컬럼이 겹쳐 merge가
        # 깨진다. funnel_events에 이미 있으니 그대로 쓴다.
        merged = fe
    else:
        merged = fe.merge(clients[["거래선코드", axis]], on="거래선코드", how="left")

    baseline_from = int(_reached(merged, step_from).sum())
    baseline_to = int(_reached(merged, step_to).sum())
    baseline_rate = round(baseline_to / baseline_from * 100, 2) if baseline_from else 0.0

    rows = []
    for seg, g in merged.groupby(axis):
        n_from = int(_reached(g, step_from).sum())
        n_to = int(_reached(g, step_to).sum())
        rate = round(n_to / n_from * 100, 2) if n_from else 0.0
        v = verdict(rate, baseline_rate, n_from)
        rows.append({
            axis: seg, "표본수": n_from, "도달": n_to, "전환율": rate,
            "전체평균": baseline_rate, "판정": v["판정"], "판정근거": v["사유"],
        })
    return pd.DataFrame(rows).sort_values("전환율", ascending=False).reset_index(drop=True)


def _observed_months() -> int:
    """config.PERIOD의 개월 수. datetime.now()를 쓰지 않는다 — 재현성 때문에
    "지금"이 아니라 config에 정의된 관측 기간만 본다."""
    start = date.fromisoformat(config.PERIOD[0])
    end = date.fromisoformat(config.PERIOD[1])
    return (end.year - start.year) * 12 + (end.month - start.month) + 1


def _annualize(count: int, months: int) -> float:
    return count / months * 12 if months else 0.0


def _funnel_bottleneck(tables: dict) -> dict:
    """퍼널 4개 전환 구간 중 단계전환율이 가장 낮은 구간과, 그다음으로 낮은
    구간의 격차를 찾는다. 원래 100%로 시작하는 첫 단계(모집단 자체)는
    "전환"이 아니라 정의상 100%라 비교 대상에서 뺀다."""
    f = funnel(tables)
    raw_keys = config.FUNNEL_STEPS
    rows = list(zip(raw_keys, f.to_dict("records")))[1:]  # 첫 단계 제외
    rows_sorted = sorted(rows, key=lambda r: r[1]["단계전환율"])
    (worst_key, worst), (runner_key, runner) = rows_sorted[0], rows_sorted[1]
    worst_pos = raw_keys.index(worst_key)
    prev_key = raw_keys[worst_pos - 1]
    population = int(f.iloc[worst_pos - 1]["도달"])
    return {
        "구간": (prev_key, worst_key), "구간_전환율": worst["단계전환율"],
        "차저구간": runner_key, "차저_전환율": runner["단계전환율"],
        "격차": round(runner["단계전환율"] - worst["단계전환율"], 2),
        "모집단": population,
    }


def proposal_topics(tables: dict) -> list:
    """제안서 주제 후보를 뽑는다. 후보를 만드는 곳 넷 — 퍼널 구간·분해 축·
    임계값(config.THRESHOLDS)·추세(최근 3개월 vs 직전 3개월). 격차가 작아
    기각된 것도 지우지 않고 "기각사유"만 채워 남긴다(부록 참고). 표본 부족으로
    비교 자체가 안 되는 칸(무효)은 애초에 후보로 만들지 않는다 — 기각과 다르다.

    규모_연간건수 = 격차(비율) × 관련 모집단의 연간 환산 건수. "비중"은 그
    모집단을 고르는 단계에서 이미 반영된다(예: 축 후보는 두 극단 칸이 아니라
    이 구간 전체 모집단 기준으로 규모를 잰다 — 실제로 격차를 없앴을 때 움직일
    수 있는 전체 크기이기 때문이다).
    """
    months = _observed_months()
    out = []
    out += _topics_from_funnel(tables, months)
    out += _topics_from_axes(tables, months)
    out += _topics_from_thresholds(tables)
    out += _topics_from_trend(tables)

    accepted = sorted((c for c in out if not c["기각사유"]), key=lambda c: c["규모_연간건수"], reverse=True)
    rejected = sorted((c for c in out if c["기각사유"]), key=lambda c: c["규모_연간건수"], reverse=True)
    return accepted + rejected


def _topics_from_funnel(tables: dict, months: int) -> list:
    b = _funnel_bottleneck(tables)
    step_from, step_to = b["구간"]
    annual_pop = _annualize(b["모집단"], months)
    size = round(b["격차"] / 100 * annual_pop)
    label_from, label_to = config.FUNNEL_LABELS[step_from], config.FUNNEL_LABELS[step_to]
    return [{
        "키": f"funnel_{step_to}",
        "제목": f"{label_from}→{label_to} 전환 병목",
        "한줄": f"{label_to} 단계 전환율이 {b['구간_전환율']}%로 가장 낮고, "
               f"다음으로 낮은 {config.FUNNEL_LABELS[b['차저구간']]} 단계({b['차저_전환율']}%)보다 {b['격차']}%p 낮습니다.",
        "규모_연간건수": size,
        "근거축": None,
        "구간": (step_from, step_to),
        "기각사유": None,
    }]


def _topics_from_axes(tables: dict, months: int) -> list:
    # 지금 이 앱에서 가장 뚜렷한 구간(완료→해피콜완료, 9주차 Day1 발견 1)을
    # 기준으로 축마다 비교한다 — Day1이 이미 이 구간에서 축별 편차를 확인했다.
    step_from, step_to = "완료", "해피콜완료"
    population = int(_reached(tables["funnel_events"], step_from).sum())
    annual_pop = _annualize(population, months)
    out = []
    for axis in config.FUNNEL_DIMS:
        df = funnel_by(tables, axis, step_from, step_to)
        best = df.loc[df["전환율"].idxmax()]
        worst = df.loc[df["전환율"].idxmin()]
        gap = round(best["전환율"] - worst["전환율"], 2)
        significant = bool((df["판정"] != "효과없음").any())
        size = round(gap / 100 * annual_pop) if significant else 0
        rejected = None
        if not significant:
            rejected = f"칸 간 최대 격차 {gap}%p — 판정 기준(±{config.VERDICT_MARGIN}%p) 미달, 이 축으로는 결론을 낼 수 없다"
        out.append({
            "키": f"axis_{axis}",
            "제목": f"{axis}별 전환율 격차",
            "한줄": f"{axis} 기준으로 나누면 최고 {best[axis]} {best['전환율']}%, "
                   f"최저 {worst[axis]} {worst['전환율']}%로 {gap}%p 벌어집니다.",
            "규모_연간건수": size,
            "근거축": axis,
            "구간": (step_from, step_to),
            "기각사유": rejected,
        })
    return out


def _topics_from_thresholds(tables: dict) -> list:
    k = kpis(tables)
    out = []
    for name, rule in config.THRESHOLDS.items():
        info = k.get(name)
        if not info:
            continue
        breached = info["상태"] != "ok"
        if breached:
            headline = f"{name}이(가) 임계값(경고 {rule['경고']})을 벗어났습니다. 현재 {info['값']}{info['단위']}."
            rejected = None
        else:
            headline = f"{name}은(는) {info['값']}{info['단위']}로 임계값(경고 {rule['경고']}) 안에 있습니다."
            rejected = f"{info['값']}{info['단위']} — 임계값(경고 {rule['경고']}) 안(config.THRESHOLDS 참고)"
        out.append({
            "키": f"threshold_{name}", "제목": f"{name} 임계값 확인", "한줄": headline,
            "규모_연간건수": 0, "근거축": None, "구간": None, "기각사유": rejected,
        })
    return out


def _topics_from_trend(tables: dict, window: int = 3) -> list:
    m = monthly(tables)
    out = []
    if len(m) < window * 2:
        return out
    for name in ["완료율", "평균 리드타임", "오주문율"]:
        recent = round(m[name].tail(window).mean(), 2)
        prior = round(m[name].iloc[-(window * 2):-window].mean(), 2)
        diff = round(recent - prior, 2)
        worse_is_high = config.THRESHOLDS.get(name, {}).get("방향") == "높을수록 나쁨"
        worsened = diff > 0 if worse_is_high else diff < 0
        # 이 도메인은 월별 물량이 최대 3.6배 차 나는 계절 패턴이 있다(config.py
        # 월 주문건수 주석 참고) — 작은 변동은 계절 잡음과 구분이 안 되므로
        # 0.5(리드타임 0.5일 / 비율 0.5%p) 미만은 추세로 인정하지 않는다.
        significant = worsened and abs(diff) >= 0.5
        rejected = None if significant else f"차이 {diff:+} — 계절 변동 범위 안(월별 물량 최대 3.6배차)"
        out.append({
            "키": f"trend_{name}", "제목": f"{name} 최근 추세",
            "한줄": f"최근 {window}개월 {name} 평균이 {recent}, 직전 {window}개월 평균은 {prior}입니다(차이 {diff:+}).",
            "규모_연간건수": 0, "근거축": None, "구간": None, "기각사유": rejected,
        })
    return out


def _funnel_step_monthly(tables: dict, step_from: str, step_to: str) -> pd.DataFrame:
    """구간(step_from→step_to) 전환율의 월별 추이. "이 격차가 최근에만 생긴
    것인가, 계속 그래왔는가"를 확인하려고 만들었다(9주차 Day4, 동료 질문에서
    나온 실제 확인 필요 사항)."""
    fe = tables["funnel_events"].copy()
    fe["연월"] = fe["주문접수일"].str.slice(0, 7)
    label = f"{config.FUNNEL_LABELS[step_to]} 전환율"
    rows = []
    for ym, g in fe.groupby("연월"):
        n_from = int(_reached(g, step_from).sum())
        n_to = int(_reached(g, step_to).sum())
        rows.append({"연월": ym, label: round(n_to / n_from * 100, 2) if n_from else 0.0})
    return pd.DataFrame(rows).sort_values("연월"), label


def topic_evidence(tables: dict, topic: dict) -> dict:
    """주제 하나에 대해 제안서가 쓸 근거를 한 번에 모아 돌려준다. 조회만
    한다 — 문장은 report/proposal.py가 만든다. 없는 것은 None + 사유."""
    months = _observed_months()
    evidence = {}

    f = funnel(tables)
    bottleneck_key = topic["구간"][1] if topic.get("구간") else None
    evidence["현황"] = {
        "표": f, "병목단계": config.FUNNEL_LABELS.get(bottleneck_key, bottleneck_key),
    }

    axis = topic.get("근거축")
    if axis and topic.get("구간"):
        step_from, step_to = topic["구간"]
        evidence["원인"] = {"표": funnel_by(tables, axis, step_from, step_to), "축": axis, "사유": None}
    else:
        evidence["원인"] = {"표": None, "축": None, "사유": "이 주제는 분해 축이 없다(퍼널 구간 전체의 문제)"}

    evidence["규모"] = {
        "연간건수": topic.get("규모_연간건수", 0),
        "가정": [
            f"관측 {months}개월({config.PERIOD[0]}~{config.PERIOD[1]})을 12개월 기준으로 환산했다",
            "최근 시점의 격차가 앞으로도 유지된다고 보았다",
        ],
    }

    metric_name = None
    if topic["키"].startswith(("threshold_", "trend_")):
        metric_name = topic["제목"].split(" ")[0]
    m = monthly(tables)
    if metric_name and metric_name in m.columns:
        evidence["추세"] = {"표": m[["연월", metric_name]].tail(12), "지표": metric_name, "사유": None}
    elif topic.get("구간") and not axis:
        # 임계값·추세 주제가 아니어도, 퍼널 구간 주제는 "이 격차가 최근에만
        # 생겼는가"를 확인할 수 있다 — 조회 가능하면 확인 계획으로 남기지 않고
        # 조회해서 채운다(9주차 Day4 판단 기준: 앱에서 조회되면 채운다).
        step_from, step_to = topic["구간"]
        m2, label = _funnel_step_monthly(tables, step_from, step_to)
        evidence["추세"] = {"표": m2.tail(12), "지표": label, "사유": None}
    else:
        evidence["추세"] = {
            "표": None, "지표": None,
            "사유": "이 주제에 대응하는 월별 지표가 없다(분해 축 주제는 현황·원인으로 설명한다)",
        }

    return evidence
