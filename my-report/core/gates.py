# -*- coding: utf-8 -*-
"""게이트 기록. 사람이 통과시킬 때 근거를 남기고, runs/에 영구 저장한다.

게이트 1(입구)·2(출구)는 되돌릴 수 있다. 게이트 3(발송)은 되돌릴 수 없다 — 8주차
Day4에서 그 무게를 화면에 드러낸다. 오늘(Day1)은 게이트 1만 쓴다.
"""
import glob
import json
import os
import uuid
from datetime import datetime

from core import config


def _run_path(run_id: str) -> str:
    return os.path.join(config.RUNS_DIR, f"{run_id}.json")


def record_gate(gate: int, reason: str, run_id: str | None = None, reversible: bool = True) -> str:
    """게이트 통과 기록을 남긴다. run_id를 안 주면 새로 만든다(게이트 1을 통과할 때).
    이미 있는 run_id를 주면 그 실행 기록에 게이트를 이어붙인다(게이트 2·3)."""
    os.makedirs(config.RUNS_DIR, exist_ok=True)
    if run_id is None:
        run_id = datetime.now().strftime("run_%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:6]
        record = {"run_id": run_id, "gates": []}
    else:
        path = _run_path(run_id)
        record = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {"run_id": run_id, "gates": []}
    record["gates"].append({
        "게이트": gate, "근거": reason, "시각": datetime.now().isoformat(timespec="seconds"),
        "되돌림가능": reversible,
    })
    json.dump(record, open(_run_path(run_id), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return run_id


def list_runs() -> list:
    """runs/ 바로 아래(하위 폴더 제외) 실행 기록만 최신순으로 돌려준다. 아카이브
    화면에서 쓴다. "run_id"·"gates" 키가 없는 파일(예: report/sections.py가
    같은 폴더에 남기는 초안 파일)은 실행 기록이 아니므로 건너뛴다 — 2026-09-12,
    초안 파일이 파일명 정렬에서 실행 기록보다 앞서 나와 게이트 판정이 거짓으로
    나오는 버그를 겪고 나서 방어적으로 걸러내게 고쳤다."""
    paths = sorted(glob.glob(os.path.join(config.RUNS_DIR, "*.json")), reverse=True)
    out = []
    for p in paths:
        try:
            record = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        if "run_id" in record and "gates" in record:
            out.append(record)
    return out


def latest_gate_passed(gate: int) -> bool:
    """가장 최근 실행에서 해당 게이트를 통과했는지."""
    runs = list_runs()
    if not runs:
        return False
    return any(g["게이트"] == gate for g in runs[0].get("gates", []))


def latest_run_id() -> str | None:
    """가장 최근 실행의 run_id. 새 세션에서 1_실행.py를 안 거치고 바로 다른
    화면으로 온 경우, session_state 대신 여기서 run_id를 이어받는다."""
    runs = list_runs()
    return runs[0]["run_id"] if runs else None
