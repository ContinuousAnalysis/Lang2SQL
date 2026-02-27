"""
v2 튜토리얼용 샘플 문서 생성 스크립트.

사용법
------
python scripts/setup_sample_docs.py
python scripts/setup_sample_docs.py --out-dir docs/business --force
"""

from __future__ import annotations

import argparse
from pathlib import Path


_SAMPLE_FILES: dict[str, str] = {
    "revenue.md": """
# 순매출 정의

순매출은 주문 금액(`orders.amount`)에서 취소 주문을 제외한 값으로 계산한다.
주문 상태가 `cancelled` 인 레코드는 집계에서 제외한다.

월간 매출 지표는 `orders.order_date` 기준으로 월 단위 그룹핑한다.
""".strip(),
    "order_status_policy.md": """
# 주문 상태 정책

주문 상태 컬럼은 `orders.status` 이다.

- pending: 결제 대기
- confirmed: 결제 완료
- shipped: 배송 완료
- cancelled: 취소

운영 리포트에서 "완료 주문"은 `confirmed`, `shipped`를 포함한다.
""".strip(),
    "rules.txt": """
고객 등급은 customers.grade 컬럼을 사용한다.
gold, silver, bronze 세 등급이 존재한다.
고객별 주문 빈도 분석은 orders.customer_id 와 customers.customer_id 를 조인해서 수행한다.
""".strip(),
}


def setup_sample_docs(out_dir: Path, force: bool = False) -> tuple[int, int]:
    out_dir.mkdir(parents=True, exist_ok=True)

    created_or_updated = 0
    skipped = 0

    for filename, content in _SAMPLE_FILES.items():
        path = out_dir / filename
        if path.exists() and not force:
            skipped += 1
            continue
        path.write_text(content + "\n", encoding="utf-8")
        created_or_updated += 1

    return created_or_updated, skipped


def main() -> None:
    parser = argparse.ArgumentParser(description="v2 튜토리얼 샘플 문서 생성")
    parser.add_argument(
        "--out-dir",
        default="docs/business",
        help="샘플 문서를 생성할 디렉터리 (기본값: docs/business)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="기존 파일이 있어도 덮어쓰기",
    )
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    created_or_updated, skipped = setup_sample_docs(out_dir=out_dir, force=args.force)

    print(f"문서 출력 경로: {out_dir}")
    print(f"생성/갱신: {created_or_updated}개")
    print(f"건너뜀:    {skipped}개")
    print()
    print("생성 파일:")
    for filename in sorted(_SAMPLE_FILES):
        print(f"  - {out_dir / filename}")


if __name__ == "__main__":
    main()
