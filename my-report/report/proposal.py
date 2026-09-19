# -*- coding: utf-8 -*-
"""제안서(결재 문서) 조립. 9주차 Day3에 처음부터 다시 짰다 — 어제(Day2)의
build()/절 구조는 리포트(임시) 탭 안의 것이었고, 오늘은 독립 메뉴
(pages/5_제안서.py)의 것이다. 남이 만든 템플릿을 쓰지 않는다.

이 문서는 분석 문서가 아니라 결재 문서다 — 계산 과정·함수 이름·컬럼 이름을
넣지 않는다. 궁금하면 앱(대시보드·리포트)을 열면 된다.

절 구조(내 데이터가 채울 수 있는 것만, 최대 7개, CLAUDE.md에 근거 표 있음):
  현황(auto)   → metrics.funnel()
  원인(auto)   → metrics.funnel_by() (주제에 축이 있을 때만)
  규모(auto)   → 격차 × 연간환산 모집단
  제안(auto)   → my-report/제안카드.md
  위험·철회 기준(human) — 사람이 쓴다. 데이터가 "언제 접을지"는 못 정한다
  요청(human)  — 사람이 쓴다. 무엇을 결정해 달라고 할지는 판단이다
"실험 결과"·"경쟁사 비교" 절은 이 도메인에는 없음(무작위 배정·경쟁사 데이터가
없다) — 만들지 않는다.

문장 검사(check_phrasing)는 자동 절에만 건다. 사람 절(위험·철회, 요청)에는
안 건다 — 원인 설명·요청은 원래 판단이 들어가는 자리라서다.
"""
import json
import os
import re

import pandas as pd

from core import config
from viz import proposal_charts as charts

SECTION_KEYS = ["현황", "원인", "규모", "제안", "위험철회", "요청"]
HUMAN_SECTIONS = ["위험철회", "요청"]
DECISION_VERBS = ("승인", "결정", "판단")


# ── 제안카드.md 파싱 (8주차 Day2에서 그대로 가져옴 — 카드 읽는 방식은 안 바뀌었다) ──

def _cell(line: str):
    m = re.match(r"^\|\s*(.+?)\s*\|\s*(.+?)\s*\|$", line.strip())
    if not m or m.group(1) in ("항목", "---"):
        return None
    return m.group(1), m.group(2)


def parse_cards(path: str) -> list:
    text = open(path, encoding="utf-8").read()
    blocks = re.split(r"^## ", text, flags=re.MULTILINE)[1:]
    cards = []
    for b in blocks:
        lines = b.strip().splitlines()
        header = lines[0]
        m = re.match(r"카드\s*\d+\s*[—-]\s*\[분류:\s*(.+?)\]\s*(.+)", header)
        분류, 제목 = (m.group(1).strip(), m.group(2).strip()) if m else ("미정", header)
        row = {"분류": 분류, "제목": 제목}
        for line in lines[1:]:
            cell = _cell(line)
            if cell:
                row[cell[0]] = cell[1]
        cards.append(row)
    return cards


def load_cards(app_dir: str = None) -> list:
    path = os.path.join(app_dir or config.APP_DIR, "제안카드.md")
    if not os.path.exists(path):
        return []
    return parse_cards(path)


def check_gate(cards: list) -> dict:
    """8주차 Day2에서 정한 규칙을 그대로 지킨다 — 근거 없는 카드나 "하지 말 것"이
    하나도 없는 카드 구성은 화면에 붙이지 않는다(부록 B)."""
    if not cards:
        return {"통과": False, "사유": "제안카드.md가 없거나 카드가 비어 있다"}
    no_evidence = [c["제목"] for c in cards if not c.get("근거", "").strip()]
    if no_evidence:
        return {"통과": False, "사유": f"근거 없는 후보: {', '.join(no_evidence)}"}
    if not any(c.get("분류") == "하지 말 것" for c in cards):
        return {"통과": False, "사유": '"하지 말 것"이 하나도 없다 — 지금 하는 게 다 옳을 리 없다'}
    return {"통과": True, "사유": "근거 있음, 하지 말 것 포함"}


# ── 문서의 말: config.PROPOSAL_WORDS에서만 가져온다 ──

def _word(category: str, key: str) -> str:
    table = config.PROPOSAL_WORDS.get(category, {})
    return table.get(key, key)  # 라벨에 없는 키는 에러 내지 않고 그대로 쓴다


def _uncertain(what: list) -> str:
    """"미확인"을 낱말 하나로 안 둔다 — [무엇을 모르는가]-[누가·어떻게 확인]-
    [모르는 채로 할 수 있는 결정]을 함께 적는다(판단 기준⑥)."""
    who = config.PROPOSAL_WORDS.get("확인필요", "확인 필요")
    return f"{'·'.join(what)}: {who}. 이 값이 없어도 조치 착수 여부는 지금 결정할 수 있습니다."


# ── 절 문장 조립 ──

def _situation(evidence: dict) -> str:
    f = evidence["현황"]["표"]
    step_label = evidence["현황"]["병목단계"]
    row = f[f["단계"] == step_label]
    if row.empty:
        return "이 주제에 대응하는 퍼널 단계를 찾을 수 없습니다."
    r = row.iloc[0]
    prev_row = f.iloc[row.index[0] - 1] if row.index[0] > 0 else None
    prev_rate = prev_row["단계전환율"] if prev_row is not None else 100.0
    prev_label = prev_row["단계"] if prev_row is not None else "주문 접수"
    # 분모(직전 단계 도달 건수)를 함께 적는다 — 한 장 요약만 보고도 분모를
    # 알 수 있어야 한다(동료 질문에서 실제로 나온 지적, 9주차 Day4).
    denom = int(prev_row["도달"]) if prev_row is not None else r["도달"]
    s1 = f"{step_label} 단계 전환율이 {r['단계전환율']}%({r['도달']:,}/{denom:,}건)로 나타났습니다."
    s2 = f"직전 단계인 {prev_label}({prev_rate}%) 대비 {round(prev_rate - r['단계전환율'], 2)}%p 낮습니다."
    return s1 + " " + s2


# 분해 축 컬럼 이름 → 문서에 쓰는 자연어. config.FUNNEL_DIMS의 원본 컬럼명을
# 그대로 문장에 넣으면 "컬럼 이름을 문서에 넣지 마라"는 규칙을 어긴다.
AXIS_LABELS = {"거래선구분": "거래선 구분", "시도": "지역(시도)", "거래선코드": "거래선"}


def _axis_label(axis: str) -> str:
    return AXIS_LABELS.get(axis, axis)


def display_title(topic: dict) -> str:
    """metrics.proposal_topics()의 "제목"은 내부 축 컬럼명을 그대로 쓸 수
    있다(예: "거래선코드별..."). 화면·문서에 보이기 전에 자연어로 바꾼다."""
    title = topic.get("제목", "")
    axis = topic.get("근거축")
    return title.replace(axis, _axis_label(axis)) if axis and axis in title else title


def display_line(topic: dict) -> str:
    line = topic.get("한줄", "")
    axis = topic.get("근거축")
    return line.replace(axis, _axis_label(axis)) if axis and axis in line else line


def _cause(evidence: dict) -> str:
    ev = evidence["원인"]
    if ev.get("표") is None:
        return ev.get("사유", "이 주제는 축이 없습니다.")
    df, axis = ev["표"], ev["축"]
    axis_label = _axis_label(axis)
    best = df.loc[df["전환율"].idxmax()]
    worst = df.loc[df["전환율"].idxmin()]
    gap = round(best["전환율"] - worst["전환율"], 2)
    s = (
        f"{axis_label} 기준으로 나누면 {best[axis]} {best['전환율']}%, {worst[axis]} {worst['전환율']}%로 "
        f"{gap}%p 차이가 있습니다."
    )
    if len(df) > 10:
        s += f" (전체 {len(df)}개 중 상위·하위 5개만 그림에 표시했습니다.)"
    return s


def _scale(evidence: dict) -> str:
    s = evidence["규모"]
    if not s.get("연간건수"):
        return "이 주제는 연간 규모를 계산하지 않았습니다(임계값·추세 확인용 주제)."
    s1 = f"이 격차가 유지된다고 보면 연 {s['연간건수']:,}건 규모입니다."
    s2 = "(" + "; ".join(s["가정"]) + ")"
    trend = evidence.get("추세", {})
    s3 = ""
    if trend.get("표") is not None:
        col = trend["지표"]
        vals = trend["표"][col]
        s3 = f" 최근 {len(vals)}개월 동안 {vals.min()}~{vals.max()}% 범위에서 유지돼, 최근에 갑자기 나빠진 것은 아닙니다."
    return s1 + " " + s2 + s3


def _proposal(cards: list) -> str:
    """현황·원인 절이 이미 근거 숫자를 보였으므로, 여기서는 반복하지 않고
    조치·비용·효과·되돌림만 추가로 적는다."""
    if not cards:
        return "카드가 없습니다."
    lines = []
    for c in cards:
        label = _word("분류어", c.get("분류", ""))
        비용, 효과, 되돌림 = c.get("비용", ""), c.get("효과", ""), c.get("되돌림", "")
        unknown = [n for n, v in [("비용", 비용), ("효과", 효과)] if "미확인" in v]
        parts = []
        if unknown:
            parts.append(_uncertain(unknown))
        if "비용" not in unknown and 비용 and "해당없음" not in 비용:
            parts.append(f"비용 {비용}")
        if "효과" not in unknown and 효과 and "해당없음" not in 효과:
            parts.append(f"효과 {효과}")
        if 되돌림:
            parts.append(f"되돌림: {되돌림}")
        lines.append(f"[{label}] {c['제목']}. " + " ".join(parts))
    return "\n".join(lines)


def _situation_chart(evidence: dict) -> str:
    f = evidence["현황"]["표"]
    steps = [{"label": r["단계"], "값": int(r["도달"])} for r in f.to_dict("records")]
    return charts.funnel_svg(steps, evidence["현황"]["병목단계"], grain=config.GRAIN)


def _cause_chart(evidence: dict) -> str:
    ev = evidence["원인"]
    if ev.get("표") is None:
        return None
    df, axis = ev["표"], ev["축"]
    rows = df.sort_values("전환율", ascending=False)
    if len(rows) > 10:
        # 결재 문서에 40칸짜리 막대는 장식이 된다 — 최고/최저 5개씩만 보여주고
        # 나머지는 문장에서 "그 사이 N개는 완만하게 이어진다"로 요약한다.
        rows = pd.concat([rows.head(5), rows.tail(5)])
    cats = [{"label": r[axis], "값": r["전환율"]} for r in rows.to_dict("records")]
    return charts.gap_svg(cats, unit="%", grain=f"{_axis_label(axis)} 1개")


def _scale_chart(evidence: dict) -> str:
    ev = evidence["추세"]
    if ev.get("표") is None:
        return None
    m, metric = ev["표"], ev["지표"]
    pts = [{"label": r["연월"], "값": r[metric]} for r in m.to_dict("records")]
    threshold = config.THRESHOLDS.get(metric, {}).get("경고")
    unit = "%" if "율" in metric else "일"
    return charts.trend_svg(pts, unit=unit, grain="월", threshold=threshold)


def _request(topic: dict, human_text: str) -> str:
    size = topic.get("규모_연간건수", 0)
    lines = []
    if size:
        lines.append(f"이 주제의 규모는 연 {size:,}건입니다.")
        lines.append(f"결정을 다음 분기까지 미루면 약 {round(size / 4):,}건이 그대로 누적됩니다.")
    lines.append("결정 선택지: 승인(즉시 착수) / 조건부 승인(범위·기간을 좁혀 착수) / 보류(다음 분기 재검토).")
    lines.append((human_text or "").strip())
    return "\n".join(l for l in lines if l)


def check_decision_verb(human_text: str) -> bool:
    return any(v in (human_text or "") for v in DECISION_VERBS)


# ── 조립기 ──

# 절 제목(조직 언어, 질문형)은 config.PROPOSAL_WORDS에서 가져오지만, 그 절이
# "원래 어느 질문에 답하는 자리인지"는 CLAUDE.md 설계표에 쓴 일반 범주로 고정
# 해 둔다 — 절 제목을 나중에 다른 말로 바꿔도(config만 수정) 이 범주는 안 변한다.
SECTION_LABELS = {
    "현황": "현황", "원인": "원인", "규모": "규모", "제안": "제안",
    "위험철회": "위험·철회 기준", "요청": "요청",
}


def build(topic: dict, evidence: dict, cards: list, human: dict = None) -> list:
    """절 하나 = {"제목","질문","kind","문장","차트","표"}. "제목"은 조직 언어
    (질문형, config.PROPOSAL_WORDS), "질문"은 이 절이 원래 답하는 일반 범주
    (SECTION_LABELS) — 화면에 작은 회색 글씨로 함께 보여준다.
    evidence에 없는 값으로 문장을 만들지 않는다 — 없으면 그 절을 아예 만들지 않는다."""
    human = human or {}
    W = config.PROPOSAL_WORDS["절_제목"]
    secs = []

    secs.append({
        "제목": W["현황"], "질문": SECTION_LABELS["현황"], "kind": "auto",
        "문장": _situation(evidence), "차트": _situation_chart(evidence), "표": evidence["현황"]["표"],
    })

    if evidence["원인"].get("표") is not None or evidence["원인"].get("사유"):
        secs.append({
            "제목": W["원인"], "질문": SECTION_LABELS["원인"], "kind": "auto",
            "문장": _cause(evidence), "차트": _cause_chart(evidence),
            "표": evidence["원인"].get("표"),
        })

    secs.append({
        "제목": W["규모"], "질문": SECTION_LABELS["규모"], "kind": "auto",
        "문장": _scale(evidence), "차트": _scale_chart(evidence), "표": None,
    })

    secs.append({
        "제목": W["제안"], "질문": SECTION_LABELS["제안"], "kind": "auto",
        "문장": _proposal(cards), "차트": None, "표": None,
    })

    secs.append({
        "제목": W["위험철회"], "질문": SECTION_LABELS["위험철회"], "kind": "human",
        "문장": human.get("위험철회", ""), "차트": None, "표": None,
    })

    secs.append({
        "제목": W["요청"], "질문": SECTION_LABELS["요청"], "kind": "human",
        "문장": _request(topic, human.get("요청", "")), "차트": None, "표": None,
    })

    return secs


# ── 사람 절 초안 저장/로드 ──

def _draft_path(run_id: str) -> str:
    return os.path.join(config.RUNS_DIR, "drafts", f"{run_id}_proposal_v2.json")


def load_draft(run_id: str) -> dict:
    path = _draft_path(run_id)
    if os.path.exists(path):
        return json.load(open(path, encoding="utf-8"))
    return {s: "" for s in HUMAN_SECTIONS}


def save_draft(run_id: str, human_sections: dict) -> None:
    path = _draft_path(run_id)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(human_sections, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


# ── HTML (A4 인쇄, 단일 파일) ──

def to_html(secs: list, title: str) -> str:
    def esc(s: str) -> str:
        return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def numify(text: str) -> str:
        return re.sub(r"[\d][\d,\.]*%?p?건?일?", lambda m: f'<span class="num">{m.group()}</span>', esc(text))

    parts = []
    for s in secs:
        body = (s.get("문장") or "").strip()
        if not body:
            continue  # 빈 절은 그리지 않는다
        chart_html = s.get("차트") or ""
        parts.append(
            f'<section>'
            f'<h2>{esc(s["제목"])}</h2>'
            f'<p class="q">{esc(s["질문"])}</p>'
            f'<div class="body">{numify(body).replace(chr(10), "<br>")}</div>'
            f'{chart_html}'
            f'</section>'
        )

    summary = secs[0]["문장"] if secs else ""
    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><title>{esc(title)}</title>
<style>
@page {{ size: A4; margin: 18mm 16mm; }}
body {{ font-family: -apple-system, "Malgun Gothic", sans-serif; font-size: 10.5pt;
       color: #1c1c1c; line-height: 1.55; max-width: 720px; margin: 0 auto; }}
h1 {{ font-size: 15pt; margin-bottom: 4pt; }}
h2 {{ font-size: 12pt; margin: 0 0 2pt 0; page-break-after: avoid; }}
.q {{ color: #6b7280; font-size: 9pt; margin: 0 0 6pt 0; }}
section {{ margin-bottom: 16pt; page-break-inside: avoid; }}
.summary {{ border: 1px solid #d1d5db; border-radius: 6px; padding: 10pt 12pt; margin-bottom: 18pt; background: #f9fafb; }}
.body {{ white-space: pre-line; }}
.num {{ font-variant-numeric: tabular-nums; font-weight: 700; }}
table {{ border-collapse: collapse; width: 100%; margin-top: 6pt; font-size: 9.5pt; }}
th, td {{ border: none; border-bottom: 1px solid #e5e7eb; padding: 3pt 6pt; text-align: left; }}
th {{ background: #f3f4f6; }}
svg {{ max-width: 100%; margin-top: 6pt; }}
</style></head>
<body>
<h1>{esc(title)}</h1>
<div class="summary"><b>한 장 요약</b><br>{numify(summary)}</div>
{''.join(parts)}
</body></html>"""
