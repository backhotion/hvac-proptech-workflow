# -*- coding: utf-8 -*-
"""리포트 절 조립. 자동 절(요약·방법·결과·한계)은 metrics.py 계산 결과만 문장으로
옮긴다 — 숫자 이상을 주장하지 않는다(phrasing.check_phrasing으로 검사).
사람 절(배경·해석·제안)은 분석가가 쓴 자유 텍스트를 그대로 받는다.

보고서 절 순서(8주차 Day4 확정): 요약(자동) → 배경(사람) → 방법(자동) →
결과(자동, 분해 비교 포함) → 해석(사람) → 한계(자동) → 제안(사람).
"실험"에 해당하는 절은 이 도메인엔 진짜 실험이 없어 분해(segment 비교)로
대신하고, 결과 절 안에 포함시켰다 — 판단기준.md에 근거를 남겼다.
"""
import json
import os

from core import config, metrics

AUTO_SECTIONS = ["요약", "방법", "결과", "한계"]
HUMAN_SECTIONS = ["배경", "해석", "제안"]
SECTION_ORDER = ["요약", "배경", "방법", "결과", "해석", "한계", "제안"]

DECOMP_STEP_FROM = "완료"
DECOMP_STEP_TO = "해피콜완료"


def build_summary(tables: dict) -> str:
    k = metrics.kpis(tables)
    lines = [f"- {name}: {info['값']}{info['단위']} (상태: {info['상태']})" for name, info in k.items()]
    r = metrics.retention_funnel(tables)
    lines.append(f"- 거래선 {r['거래선_수']}개 · 관측 {r['관측_개월']}개월 · 이탈(활성 거래선 감소) {r['월별_이탈_발생']}건")
    pct = round(r["대리신호_건수"] / r["대리신호_전체건수"] * 100, 1) if r["대리신호_전체건수"] else 0.0
    lines.append(f"- 이탈 위험 신호(대리 지표): {r['대리신호_건수']}건 / {r['대리신호_전체건수']}건 ({pct}%)")
    return "\n".join(lines)


def build_method(tables: dict) -> str:
    steps = " → ".join(config.FUNNEL_LABELS[s] for s in config.FUNNEL_STEPS)
    return (
        f"- 데이터: {config.DATASET_SOURCE}\n"
        f"- 기간: {config.PERIOD[0]} ~ {config.PERIOD[1]}\n"
        f"- 그레인: {config.GRAIN}\n"
        f"- 퍼널 단계: {steps}\n"
        f"- 분해 축: {', '.join(config.FUNNEL_DIMS)} "
        f"(판정 기준 ±{config.VERDICT_MARGIN}%p, 표본 최소 {config.MIN_SAMPLE}건)"
    )


def build_result(tables: dict) -> str:
    f = metrics.funnel(tables)
    lines = [f"- {row['단계']}: 도달 {row['도달']:,}건, 누적전환율 {row['누적전환율']}%" for _, row in f.iterrows()]
    lines.append("")
    lines.append(f"분해 결과 ({config.FUNNEL_LABELS[DECOMP_STEP_FROM]}→{config.FUNNEL_LABELS[DECOMP_STEP_TO]} 구간):")
    for axis in config.FUNNEL_DIMS:
        df = metrics.funnel_by(tables, axis, DECOMP_STEP_FROM, DECOMP_STEP_TO)
        counts = df["판정"].value_counts().to_dict()
        summary = ", ".join(f"{k} {v}개" for k, v in counts.items())
        lines.append(f"- {axis}: {summary}")
    return "\n".join(lines)


def build_limitations(tables: dict) -> str:
    lines = [
        "- 이 데이터는 합성데이터(generated_2year)로, 실제 라이브 기록이 아니라 업무 구조를 모사한 것이다.",
        "- 거래선 그레인에는 이탈이 없어(원본 생성기가 거래상태를 '활성'으로 고정) 유지 지표는 이탈률 대신 전월 대비 주문금액 급감 대리 지표를 쓴다.",
        "- 완료율·평균 리드타임·오주문율 임계값은 관측 범위 바로 바깥에 둔 값으로, 관측 기간"
        f"({config.PERIOD[0]}~{config.PERIOD[1]}) 밖 데이터에는 그대로 적용할 수 없다.",
        f"- 분해는 거래선구분·시도 두 축만 검토했고, 판정 기준(±{config.VERDICT_MARGIN}%p)보다 작은 차이는 감지하지 못한다.",
    ]
    invalid = []
    for axis in config.FUNNEL_DIMS:
        df = metrics.funnel_by(tables, axis, DECOMP_STEP_FROM, DECOMP_STEP_TO)
        for _, row in df[df["판정"] == "무효"].iterrows():
            invalid.append(f"{axis}={row[axis]}(표본 {row['표본수']}건)")
    if invalid:
        lines.append(f"- 표본 부족으로 판정 보류: {', '.join(invalid)}")
    return "\n".join(lines)


def build_auto_sections(tables: dict) -> dict:
    return {
        "요약": build_summary(tables),
        "방법": build_method(tables),
        "결과": build_result(tables),
        "한계": build_limitations(tables),
    }


def _draft_path(run_id: str) -> str:
    # runs/ 바로 아래가 아니라 하위 폴더에 둔다 — gates.list_runs()의 "*.json"
    # 글롭과 안 섞이게 하려는 목적(안 그러면 초안 파일이 실행 기록으로 오인된다).
    return os.path.join(config.RUNS_DIR, "drafts", f"{run_id}.json")


def load_draft(run_id: str) -> dict:
    path = _draft_path(run_id)
    if os.path.exists(path):
        return json.load(open(path, encoding="utf-8"))
    return {s: "" for s in HUMAN_SECTIONS}


def save_draft(run_id: str, human_sections: dict) -> None:
    path = _draft_path(run_id)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(human_sections, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
