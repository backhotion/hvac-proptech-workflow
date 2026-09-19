# -*- coding: utf-8 -*-
"""5. 제안서 — 독립 메뉴(9주차 Day3). 주제를 고르면 그 주제로 결재 문서
(현황→원인→규모→제안→위험·철회 기준→요청)를 조립한다. 계산 과정·함수 이름·
컬럼 이름은 여기 안 보인다 — 궁금하면 [2. 대시보드]·[3. 리포트]를 연다."""
import streamlit as st

from core import gates, load, metrics
from report import phrasing, proposal
from viz import ui

st.set_page_config(page_title="5. 제안서", layout="wide")
ui.css()
ui.sidebar_nav()
st.title("5. 제안서")
ui.context_bar()

if not gates.latest_gate_passed(1):
    st.warning("게이트 1을 먼저 통과하십시오. [1. 실행] 화면으로 가십시오.")
    st.page_link("pages/1_실행.py", label="1. 실행으로 이동", icon="▶")
    st.stop()

run_id = st.session_state.get("run_id") or gates.latest_run_id()
tables = load.load_tables()
cards = proposal.load_cards()

card_gate = proposal.check_gate(cards)
if not card_gate["통과"]:
    ui.callout("block", f"제안 카드를 쓸 수 없습니다 — {card_gate['사유']}")
    st.caption("my-report/제안카드.md를 확인하십시오.")
    st.stop()

topics = metrics.proposal_topics(tables)

if not topics:
    ui.callout("block", "주제 후보가 없습니다 — core/metrics.py의 proposal_topics()를 확인하십시오.")
    st.stop()


def _label(t: dict) -> str:
    title = proposal.display_title(t)
    if t["기각사유"]:
        return f"{title} (차이 없음)"
    return f"{title} (연 {t['규모_연간건수']:,}건)"


options = ["전체"] + [_label(t) for t in topics]
picked = st.selectbox("주제", options, index=0)

if picked == "전체":
    st.info("주제를 하나 고르면 그 주제로 제안서가 조립됩니다. 후보는 규모(연간 건수)가 큰 순서로, "
            "차이가 작아 기각된 것은 뒤에 \"(차이 없음)\"으로 표시됩니다.")
    with st.expander(f"주제 후보 전체 보기 ({len(topics)}개)"):
        for t in topics:
            st.markdown(f"- **{proposal.display_title(t)}** — {proposal.display_line(t)}"
                        + (f" *(기각: {t['기각사유']})*" if t["기각사유"] else ""))
    st.stop()

topic = topics[options.index(picked) - 1]
evidence = metrics.topic_evidence(tables, topic)

st.caption(f"근거 요약: {proposal.display_line(topic)}")
if topic["기각사유"]:
    ui.callout("warn", f"이 주제는 기각된 후보입니다 — {topic['기각사유']}")

human = proposal.load_draft(run_id)
secs = proposal.build(topic, evidence, cards, human)

with st.expander("절별 미리보기", expanded=True):
    for s in secs:
        badge = "🧑 사람" if s["kind"] == "human" else "⚙ 자동"
        st.markdown(f"**{s['제목']}** <span style='color:#6b7280;font-size:0.85em'>({s['질문']} · {badge})</span>",
                     unsafe_allow_html=True)
        if s["kind"] == "human":
            key = "위험철회" if s["질문"] == "위험·철회 기준" else "요청"
            human[key] = st.text_area(s["제목"], value=human.get(key, ""), label_visibility="collapsed",
                                       key=f"proposal5_{key}")
        else:
            st.markdown((s["문장"] or "(비어 있음)").replace("\n", "  \n"))
            hit = phrasing.check_phrasing(s["문장"] or "")
            if hit:
                ui.callout("block", f"이 절에서 금지 표현 {len(hit)}건 발견")
                st.dataframe(hit, hide_index=True, use_container_width=True)

if st.button("저장"):
    proposal.save_draft(run_id, {k: human.get(k, "") for k in proposal.HUMAN_SECTIONS})
    st.toast("저장했습니다.")

secs = proposal.build(topic, evidence, cards, human)  # 방금 저장한 사람 절 반영

요청_문장 = next((s["문장"] for s in secs if s["질문"] == "요청"), "")
if not proposal.check_decision_verb(요청_문장):
    ui.callout("warn", '"요청" 절 문장에 결정을 요구하는 동사(승인·결정·판단)가 없습니다. 저장은 막지 않습니다.')

st.divider()
html = proposal.to_html(secs, title=proposal.display_title(topic))
st.download_button("제안서.html 다운로드", html.encode("utf-8"), file_name="제안서.html", mime="text/html")
