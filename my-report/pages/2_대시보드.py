# -*- coding: utf-8 -*-
"""2. 대시보드 — 퍼널·지표. Day2에 획득 퍼널·유지 대리지표·KPI 카드를 채운다.
Day3에서 분해 축(funnel_by)·못 믿을 조건(trust_check)을 여기 더한다.
"""
import streamlit as st

from core import config, gates, load, metrics
from core.todo import NotBuiltYet
from viz import ui

st.set_page_config(page_title="2. 대시보드", layout="wide")
ui.css()
ui.sidebar_nav()
st.title("2. 대시보드")
ui.context_bar()

if not gates.latest_gate_passed(1):
    st.warning("게이트 1을 먼저 통과하십시오. [1. 실행] 화면으로 가십시오.")
    st.page_link("pages/1_실행.py", label="1. 실행으로 이동", icon="▶")
    st.stop()

tables = load.load_tables()

tab_acq, tab_ret, tab_decomp = st.tabs(
    ["획득 퍼널 (주문→해피콜)", "유지 (거래선 이탈 대리지표)", "분해 (세그먼트 비교)"]
)


@st.fragment
def _render_acquisition():
    k = metrics.kpis(tables)
    delta_color_map = {"완료율": "normal", "평균 리드타임": "inverse", "오주문율": "inverse", "월 주문건수": "off"}
    cols = st.columns(4)
    for col, (name, info) in zip(cols, k.items()):
        with col:
            delta = f'{info["델타"]:+}{info["단위"]}' if info["델타"] is not None else None
            ui.kpi_card(
                name, f'{info["값"]}{info["단위"]}', delta,
                level=info["상태"], delta_color=delta_color_map.get(name, "normal"),
            )

    st.divider()

    gc = metrics.funnel_grain_check(tables)
    if gc["진짜_퍼널"]:
        ui.callout("ok", "앞 단계를 건너뛴 주문 0건 — 진짜 퍼널로 확인됨 (배송 생략 0건, 완료 생략 0건)")
    else:
        ui.callout("warn", f'앞 단계를 건너뛴 주문 있음 — 배송시작 생략 {gc["배송시작_생략"]}건, 배송완료 생략 {gc["배송완료_생략"]}건')

    f = metrics.funnel(tables)
    st.dataframe(
        f,
        hide_index=True,
        use_container_width=True,
        column_config={
            "단계": st.column_config.TextColumn("단계", width="medium"),
            "도달": st.column_config.NumberColumn("도달(건)", format="%d"),
            "단계전환율": st.column_config.NumberColumn("단계 전환율(%)", format="%.2f%%"),
            "누적전환율": st.column_config.ProgressColumn(
                "누적 전환율", format="%.2f%%", min_value=0, max_value=100,
            ),
        },
    )

    with st.expander("월별 추이"):
        m = metrics.monthly(tables)
        st.dataframe(m, hide_index=True, use_container_width=True)


@st.fragment
def _render_retention():
    try:
        r = metrics.retention_funnel(tables)
    except NotBuiltYet as e:
        ui.todo_card(e.day, e.what)
        return

    st.caption(
        f'{config.RETENTION_PROXY["이름"]} · 컷오프 {config.RETENTION_PROXY["컷오프"]}%'
    )
    with st.expander("이 대리 지표를 쓰는 이유"):
        st.write(config.RETENTION_PROXY["근거"])

    if r["월별_이탈_발생"] == 0:
        ui.callout("ok", f'거래선 {r["거래선_수"]}개 · 관측 {r["관측_개월"]}개월 — 이탈(활성 거래선 감소) 0건 확인됨')
    else:
        ui.callout("warn", f'{r["월별_이탈_발생"]}개월에서 활성 거래선 수 감소 발생')

    pct = round(r["대리신호_건수"] / r["대리신호_전체건수"] * 100, 1) if r["대리신호_전체건수"] else 0.0
    with st.container(border=True):
        st.metric("이탈 위험 신호", f'{r["대리신호_건수"]}건')
        st.caption(f'{pct}% (전체 {r["대리신호_전체건수"]}건 중) — 추세가 아니라 현재 시점 비율이다')

    st.dataframe(
        r["대리신호_상세"],
        hide_index=True,
        use_container_width=True,
        column_config={
            "증감률": st.column_config.NumberColumn("전월 대비 증감률(%)", format="%.1f%%"),
            "total_amount": st.column_config.NumberColumn("당월 금액", format="%d"),
            "전월금액": st.column_config.NumberColumn("전월 금액", format="%d"),
        },
    )


with tab_acq:
    _render_acquisition()

with tab_ret:
    _render_retention()

with tab_decomp:
    st.subheader("분해 — 세그먼트별로 쪼개 보면 다른가")

    qp = st.query_params
    axis_options = config.FUNNEL_DIMS
    step_options = config.FUNNEL_STEPS

    default_axis = qp.get("axis", axis_options[0])
    default_from = qp.get("from", "완료")
    default_to = qp.get("to", "해피콜완료")
    if default_axis not in axis_options:
        default_axis = axis_options[0]
    if default_from not in step_options:
        default_from = step_options[0]
    if default_to not in step_options:
        default_to = step_options[-1]

    c1, c2, c3 = st.columns(3)
    axis = c1.selectbox("분해 축", axis_options, index=axis_options.index(default_axis))
    step_from = c2.selectbox("시작 단계", step_options, index=step_options.index(default_from))
    step_to = c3.selectbox("도착 단계", step_options, index=step_options.index(default_to))
    st.query_params["axis"] = axis
    st.query_params["from"] = step_from
    st.query_params["to"] = step_to

    if step_options.index(step_from) >= step_options.index(step_to):
        st.error("시작 단계는 도착 단계보다 앞 단계여야 합니다.")
    else:
        with st.status(f"{axis} 기준 {config.FUNNEL_LABELS[step_from]}→{config.FUNNEL_LABELS[step_to]} 구간 분해 중") as status:
            st.write("funnel_events를 clients와 거래선코드로 조인합니다.")
            df = metrics.funnel_by(tables, axis, step_from, step_to)
            st.write(f"세그먼트 {len(df)}개 집계 완료 — 표본 {config.MIN_SAMPLE}건 미만이면 무효로 판정합니다.")
            status.update(label="분해 완료", state="complete")

        rows = df.to_dict("records")
        for i in range(0, len(rows), 4):
            cols = st.columns(4)
            for col, row in zip(cols, rows[i:i + 4]):
                with col:
                    ui.verdict_card(
                        row[axis], row["판정"], row["전환율"], row["전체평균"],
                        row["표본수"], row["판정근거"],
                    )

st.divider()
st.subheader("게이트 2 — 이 분석을 리포트로 넘겨도 되는가")

_run_id = st.session_state.get("run_id") or gates.latest_run_id()


@st.dialog("게이트 2 확인")
def _gate2_dialog(run_id: str):
    st.write("퍼널·유지·분해 결과를 리포트 작성 단계로 넘깁니다. 되돌릴 수 있는 게이트입니다.")
    reason = st.text_area(
        "판단 근거",
        placeholder="예: 분해 결과 세그먼트 간 유의미한 차이 없음(±1.0%p 기준 미달) — 전체 지표 기준으로 리포트 작성",
    )
    if st.button("확정", type="primary", disabled=not reason.strip()):
        gates.record_gate(2, reason.strip(), run_id=run_id, reversible=True)
        st.session_state["run_id"] = run_id
        st.rerun()


if gates.latest_gate_passed(2):
    st.success("게이트 2 통과됨 — 리포트로 이동할 수 있습니다.")
    st.page_link("pages/3_리포트.py", label="3. 리포트로 이동", icon="📄")
else:
    if st.button("분석 확정 — 리포트로 넘기기", type="primary"):
        _gate2_dialog(_run_id)
