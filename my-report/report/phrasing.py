# -*- coding: utf-8 -*-
"""자동 생성 절(요약·방법·결과·한계)이 사실·변동만 서술하는지 검사한다.

인과·제안·가치판단은 여기서 만들지 않는다 — 그건 사람이 쓰는 배경·해석·제안
절의 몫이다. 패턴은 영업지원-분석/app_hvac2026q3/pipeline/phrasing.py의
FORBIDDEN_PATTERNS/check_forbidden 구조를 이 도메인 절 구성에 맞게 재사용했다.
"""

FORBIDDEN_PATTERNS = {
    "인과": ["때문", "탓", "원인은", "따라서", "덕분"],
    "제안": ["해야", "필요하다", "권장", "제안한다"],
    "가치판단": ["개선", "악화", "우려", "심각", "양호", "우수", "부진"],
}


def check_phrasing(text: str) -> list:
    """금지 표현이 있으면 목록으로 돌려준다. 빈 목록이면 통과."""
    hits = []
    for i, line in enumerate(text.splitlines()):
        stripped = line.strip()
        if not stripped:
            continue
        for category, words in FORBIDDEN_PATTERNS.items():
            for w in words:
                if w in line:
                    hits.append({"카테고리": category, "표현": w, "줄번호": i + 1, "내용": stripped})
    return hits
