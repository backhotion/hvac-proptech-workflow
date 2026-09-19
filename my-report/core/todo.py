# -*- coding: utf-8 -*-
"""골격 전용. 아직 안 채운 자리를 안내 카드로 보여준다.
전부 채우고 나면(9주차 배포 전) 이 파일과 화면의 안내 카드 호출을 지운다."""


class NotBuiltYet(Exception):
    """metrics.py의 함수가 아직 구현되지 않았을 때 낸다. 화면이 이 신호를 받아
    에러 화면(빨간 글씨) 대신 안내 카드를 그린다."""
    def __init__(self, day: str, what: str):
        self.day = day
        self.what = what
        super().__init__(f"★ {day} 채웁니다 — {what}")
