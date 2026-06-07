# Lang2SQL — Claude Code 작업 가이드

## 프로젝트 정체성

"더 좋은 SQL 생성기"가 아니라 **현실의 messy DB에서도 답하는 분석 에이전트**.
Vanna/Wren이 못 푸는 4가지 현실 문제(DB 강건성, 기억, 문서 ingestion, 팀별 시멘틱 분기)를 다룬다.

## 4기둥 현황

| ★ | 기둥 | V1 상태 | V1.5 목표 |
|---|---|---|---|
| ① | **Safety pipeline + DB 강건성** | whitelist/timeout layer만 존재. 메타데이터 자동 보강 **미구현** | 자동 보강이 핵심 차별점 |
| ② | Memory 3축 | in-memory store, inject-all recall, manual extractor | SQLite/keyword/auto |
| ③ | Ingestion matrix | file source + LLM extractor | URL/Notion/DDL |
| ④ | Semantic federation | 3-scope merge 동작 | diff/promote 커맨드 |

## 아키텍처 한 줄 요약

```
frontends → tenancy(조립점) → harness(agent_loop) → 4기둥 → core ports ← adapters
```

- `core/ports/` — Protocol 정의만, 외부 의존 0. **건드리지 말 것**
- `adapters/` — 외부 시스템 구체 구현 (DB, LLM, storage)
- `tenancy/concierge.py` — 유일한 조립점 (구체 클래스 import 허용)

## 현재 작업 포커스: DB 강건성 (★①) 고도화

### 문제
`Column.description`이 비어 있는 실무 DB에서 LLM이 컬럼 의미를 모름 → 잘못된 SQL 생성.

### 관련 파일
- [src/lang2sql/core/ports/explorer.py](src/lang2sql/core/ports/explorer.py) — `Column.description` 필드 (v1.5 자동 보강 예정 주석 있음)
- [src/lang2sql/adapters/db/sqlalchemy_explorer.py](src/lang2sql/adapters/db/sqlalchemy_explorer.py) — `_describe_table_sync`: `c.get("comment") or ""`로 DB comment만 읽음
- [src/lang2sql/tools/explore_schema.py](src/lang2sql/tools/explore_schema.py) — description 있을 때만 프롬프트에 노출
- [src/lang2sql/harness/system_prompt.py](src/lang2sql/harness/system_prompt.py) — 스키마 주입 위치
- [src/lang2sql/safety/](src/lang2sql/safety/) — pipeline.py + layers/ (새 layer 추가 시 여기)

### 확장 패턴 (기존 코드 안 건드리고 추가)
- 새 safety layer → `safety/layers/<name>.py`에 `SafetyLayerPort` 구현 후 `pipeline.py` 목록에 끼우기
- 새 DB 어댑터 → `adapters/db/<name>_explorer.py`에 `ExplorerPort` 구현 후 `factory.py`에 scheme 분기
- 메타데이터 보강 → `ExplorerPort`에 `enrich_metadata()` 메서드 추가 또는 별도 enricher 포트로 추상화

## 개발 환경

```bash
cd /home/sewon/project/Lang2SQL
uv sync
.venv/bin/pytest -q                      # 110개 테스트 (safety 12개 회귀 포함)
.venv/bin/python bench/ecommerce_demo.py # federation + safety 데모
```

## Git 브랜치 전략

- 내 포크: `git@github.com:thrcle/Lang2SQL.git` (origin)
- 업스트림: `https://github.com/CausalInferenceLab/Lang2SQL.git` (upstream)
- 작업 브랜치 생성 후 origin에 push → upstream으로 PR
- 브랜치 가이드: `docs/branch_guidelines.md`, PR 가이드: `docs/pull_request_guidelines.md`

## 테스트 원칙

- safety 회귀 12케이스는 **머지 게이트** — 새 layer 추가 시 반드시 케이스 추가
- `adapters/llm/fake.py`로 오프라인 LLM 테스트 가능
