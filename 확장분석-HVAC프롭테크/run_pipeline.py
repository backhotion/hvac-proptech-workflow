# -*- coding: utf-8 -*-
"""build_fact_region_month.py -> validate_fact_region_month.py를 순서대로 실행한다.
검증 결과에 FAIL이 하나라도 있으면 종료코드 1로 알린다(사람이 놓치기 쉬운 걸 자동으로
잡아내는 것뿐, 실패해도 이 스크립트가 뭔가를 자동으로 고치지는 않는다).

사용법: python run_pipeline.py
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def run(script_name):
    print(f"\n{'=' * 60}\n실행: {script_name}\n{'=' * 60}")
    result = subprocess.run(
        [sys.executable, str(HERE / script_name)],
        cwd=HERE, capture_output=True, text=True, encoding="utf-8",
    )
    print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if result.returncode != 0:
        print(f"\n중단: {script_name} 실행이 실패했습니다(종료코드 {result.returncode}).")
        sys.exit(result.returncode)
    return result.stdout


def main():
    run("build_fact_region_month.py")
    validate_output = run("validate_fact_region_month.py")

    fail_lines = [line for line in validate_output.splitlines() if "FAIL" in line]
    print(f"\n{'=' * 60}")
    if fail_lines:
        print(f"검증 실패 {len(fail_lines)}건 발견:")
        for line in fail_lines:
            print(f"  {line.strip()}")
        print("=" * 60)
        sys.exit(1)
    else:
        print("검증 전부 PASS — fact_region_month_integrated.csv 갱신 완료")
        print("=" * 60)
        sys.exit(0)


if __name__ == "__main__":
    main()
