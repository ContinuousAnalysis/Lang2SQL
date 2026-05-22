# Lang2SQL v4 — 컨셉과 아키텍처

> **작성일**: 2026-05-18
> **결정자**: ryan@brain-crew.com
> **상태**: 컨셉 확정 단계. v1/v2/v3는 보존 (역사 자료).
> **전제**: 기존 레포 wipe 후 백지에서 다시 작성.

---

# Chap 1. 만들려는 것의 정체성

## 1.1 기존 오픈소스의 공통 한계 — 어디를 비집고 들어갈까

Vanna AI(~20k), Wren AI(~12k), SQLCoder(~3.8k) 같은 Text-to-SQL 오픈소스들은 *질문→SQL 파이프라인 자체* 는 이미 충분히 완성도 높음. 그러면 우리는 *그 위에 무엇을 더 얹을* 것인가가 정체성 결정.

기존 오픈소스를 보면 공통적으로 **3가지 약점** 이 있음:

| 약점 | 누구의 문제 | 기존 처리 |
|---|---|---|
| **DB 정보 완성도가 낮으면 성능 급락** | 사용자가 description·sample query 없이 등록 | Vanna: 학습 데이터 품질에 전적 의존 |
| **이전 대화·정의를 기억 못함** | 매번 새 세션처럼 동작 | 대부분 stateless |
| **비즈니스 맥락은 사람이 직접 정의해야 함** | metric 정의·용어집을 사용자가 일일이 입력 | Wren: MDL 수동 작성 |

이 셋이 *실무에서는 매우 중요* 한데 *비즈니스마다 다르기 때문에 정량 평가가 어려운 영역*. 그래서 오픈소스가 잘 안 건드려옴. 우리는 **이 셋을 한 번에 다루는 방향** 으로 차별화.

## 1.2 우리의 한 줄 컨셉

> **"문서로 비즈니스 맥락을 학습하고, 당신의 DB에 대답하고, 모든 대화·정의를 기억하는 Discord 분석 에이전트."**

기존 SQL 봇이 *"질문하면 SQL 만들어 줄게"* 였다면, 우리는 *"우리 회사 문서 넣어줘 → 학습할게 → 너희 팀이 같이 묻고 답을 받자 → 다 기억하고 다음에도 적용할게"*.

## 1.3 4기둥 (Pillars)

| 기둥 | 정체성 | 차별점 |
|---|---|---|
| **① Discord multi-mode** | DM(개인 분석) + 채널 멘션→thread(팀 협업) 양면 | 대부분 오픈소스는 Slack 또는 웹 UI 일면. Discord native + thread 패턴 |
| **② Hermes-style 기억** | conversation + 학습된 facts + preferences 영속 | 대부분 stateless. *"우리 fiscal year는 7월 시작"* 한 번 가르치면 계속 적용 |
| **③ 문서 → 시멘틱 레이어** | 사용자가 문서 업로드 → LLM이 metric/dim/rule 추출 → 사용자 confirm → 등록 | Wren의 MDL은 수동 작성. 우리는 *문서가 곧 진실의 출처* |
| **④ DB 강건성 facade** | 사용자가 description 없이 등록해도 동작 | Vanna는 학습 데이터 품질 의존. 우리는 *불완전한 DB에서도 작동* 이 핵심 가치 |

기둥 ④가 *우리 연구·제품 정체성의 가장 중요한 한 포인트*. *"사용자가 입력하는 DB 정보의 완성도가 낮아도 성능 하락을 최소화"* 가 차별화. V1엔 껍데기만, V1.x에서 깊이 채움.

## 1.4 타이브레이커 (충돌 시 우선순위)

설계가 충돌하면 위에서 아래로:

1. **무결성 + 권한** — DB가 변하지 않고, 권한 있는 데이터만 본다
2. **의미적 정확성** — 답이 *진짜로* 맞는다 (자신 있게 틀린 답이 가장 위험)
3. **Discord UX** — 한 번에 결과 (멘션→thread)
4. **맥락 보존** — 끊겨도 이어진다 (Hermes 영속화)

(v2까지의 *"DB가 안 변하는가"* 한 축에서 *"+ 권한"* 까지 통합. Codex 외부 리뷰의 *"권한/data exposure를 별도 축으로"* 우려를 축 #1 안에 흡수.)

---

# Chap 2. 아키텍처 — ASCII로 보는 큰 그림

## 2.1 전체 흐름

```
┌─────────────────────────────────────────────────────────────────────┐
│                          USER (Discord)                              │
│                                                                       │
│   DM message     |     Channel @mention      |     Thread reply       │
│   ─────────     |     ─────────────────     |     ─────────────       │
│   (개인 분석)    |    (봇이 thread 생성)     |   (같은 thread 계속)    │
└──────┬────────────────────┬────────────────────────┬─────────────────┘
       │                    │                        │
       └────────────────────┼────────────────────────┘
                            ▼
       ┌────────────────────────────────────────────────┐
       │  DISCORD ADAPTER                                │
       │   • 입력 분류 → session_key 결정                  │
       │     - dm:USER_ID                                │
       │     - thr:GUILD:CHANNEL:THREAD_ID                │
       │   • 멘션 없는 채널 메시지 → 무시                  │
       │   • 응답 렌더링 (텍스트 / CSV / PNG)              │
       └────────────────────┬───────────────────────────┘
                            ▼
       ┌────────────────────────────────────────────────┐
       │  MEMORY + CONCIERGE                             │
       │                                                  │
       │   MemoryService {                                │
       │     FactStore        ◄─ "어디 저장하나"           │
       │     RecallStrategy   ◄─ "무엇을 가져올지"          │
       │     FactExtractor    ◄─ "어떻게 만들지"           │
       │   }                                              │
       │                                                  │
       │   IngestionPipeline {                            │
       │     DocumentSource[] ◄─ "어디서 가져올지"          │
       │     DocumentExtractor[] ◄─ "어떻게 해석할지"       │
       │   }                                              │
       │                                                  │
       │   ContextConcierge.build(session_key, principal) │
       │     → ctx 조립                                    │
       └────────────────────┬───────────────────────────┘
                            ▼ ctx
       ┌────────────────────────────────────────────────┐
       │  ★ HARNESS (조립된 단위, 하나의 덩어리)            │
       │                                                  │
       │   HarnessContext {                               │
       │     llm           — OpenAI port                  │
       │     tools         — run_sql, ingest_doc, ...     │
       │     semantic      — SemanticLayer (live ref)     │
       │     session       — 영속 conversation + facts    │
       │     safety        — SafetyPipeline               │
       │     explorer      — DB (asyncpg)                 │
       │     audit         — append-only                  │
       │   }                                              │
       │                                                  │
       │   agent_loop(ctx, question):                     │
       │     while turn < max:                            │
       │        prompt = system_prompt(ctx)               │
       │            ├─ semantic 주입                       │
       │            ├─ recalled facts 주입                 │
       │            └─ schema 주입                         │
       │        resp = llm.invoke(prompt, tools)          │
       │        if resp.tool_calls:                       │
       │          for tc in resp.tool_calls:              │
       │            result = tools.execute(ctx, tc)       │
       │            session.append('tool_finished', ...)  │
       │        else:                                     │
       │          yield resp.content                      │
       │          break                                   │
       │                                                  │
       │   run_sql tool 내부:                              │
       │     ★ ctx.safety.evaluate(sql, ctx)              │
       │        Layer 1 → 2 → 3 → ...                     │
       └────────────────────┬───────────────────────────┘
                            ▼
       ┌────────────────────────────────────────────────┐
       │  OUTBOUND ADAPTERS                              │
       │   LLM:     openai_                              │
       │   DB:      postgres_explorer (asyncpg)          │
       │   Store:   encrypted_sqlite                     │
       └────────────────────────────────────────────────┘
                            ▼
              사용자 PostgreSQL · OpenAI · 로컬 SQLite
```

핵심 정정:
- **하네스는 tools·semantic·session·safety 를 *분리된 레이어로 위아래* 두지 않음.** 모두 `HarnessContext` 안에 *주입된 의존성* 으로 들어감. 하네스 = 조립된 한 덩어리.
- DM/Channel 양분은 *session_key 결정 단계에서만 다름*. 그 아래로는 동일 흐름.
- 도구 안에서 SafetyPipeline 호출 → 각 layer가 차례로 검증.

## 2.2 디렉토리 구조

```
lang2sql/
├── README.md
├── pyproject.toml
├── .env.example
│
├── src/lang2sql/
│   ├── core/                      # 순수 타입 + 포트
│   │   ├── types.py               # Message, ToolCall, ToolResult, Event
│   │   ├── identity.py            # Principal
│   │   └── ports/
│   │       ├── llm.py
│   │       ├── explorer.py
│   │       ├── tool.py
│   │       ├── secrets.py
│   │       ├── audit.py
│   │       ├── session_store.py
│   │       ├── safety.py          ── SafetyLayer Protocol
│   │       ├── memory.py          ── FactStorePort, RecallStrategy, FactExtractor
│   │       └── ingestion.py       ── DocumentSource, DocumentExtractor
│   │
│   ├── harness/                   # 조립된 단위
│   │   ├── context.py             # HarnessContext
│   │   ├── session.py             # conversation + facts
│   │   ├── loop.py                # agent_loop (async generator)
│   │   ├── system_prompt.py       # per-turn rebuild
│   │   └── tool_registry.py
│   │
│   ├── semantic/                  # 도메인 모델
│   │   ├── types.py
│   │   ├── layer.py
│   │   ├── sql_composer.py
│   │   └── store.py
│   │
│   ├── safety/                    # ★ SafetyPipeline chain
│   │   ├── pipeline.py
│   │   └── layers/
│   │       ├── whitelist_gate.py
│   │       └── timeout_setter.py
│   │
│   ├── memory/                    # ★ 3축 분리
│   │   ├── service.py
│   │   ├── stores/
│   │   │   └── inmemory.py
│   │   ├── recall/
│   │   │   └── all_facts.py
│   │   └── extractors/
│   │       └── manual.py
│   │
│   ├── ingestion/                 # ★ Source × Extractor
│   │   ├── pipeline.py
│   │   ├── sources/
│   │   │   └── file.py
│   │   └── extractors/
│   │       └── llm_extractor.py
│   │
│   ├── tools/                     # ctx-aware
│   │   ├── run_sql.py
│   │   ├── explore_schema.py
│   │   ├── define_metric.py
│   │   ├── ingest_doc.py
│   │   ├── remember.py
│   │   └── ask_user.py
│   │
│   ├── tenancy/                   # 멀티유저
│   │   ├── concierge.py
│   │   └── encrypted_secrets.py
│   │
│   ├── discord/                   # ★ 1급 frontend
│   │   ├── bot.py
│   │   ├── commands/
│   │   │   ├── connect.py
│   │   │   ├── ingest.py
│   │   │   ├── remember.py
│   │   │   └── audit.py
│   │   ├── session_router.py      # DM / thread 분기
│   │   └── render.py
│   │
│   └── adapters/                  # outbound
│       ├── llm/openai_.py
│       ├── db/postgres_explorer.py
│       └── storage/encrypted_sqlite.py
│
├── tests/
│   ├── unit/
│   ├── safety/                    # 회귀 12개 (CI gate)
│   └── e2e/
└── docs/
```

`★` 3개가 **확장 핵심** — 다음 Chap 3에서 자세히.

---

# Chap 3. 확장성 — 3개의 chain/strategy 패턴

## 3.1 왜 chain/strategy 패턴인가

V1엔 *가장 단순한 1개씩* 만 구현, V1.5/V2에서 *어댑터를 추가* 하는 방식으로 확장.

이게 *진짜* "확장 가능"의 의미. 단순히 *"미루는 것"* 이 아니라, *V1엔 단순 구현으로 동작하지만 추상은 박혀 있어서 V1.5에 새 구현을 끼울 때 기존 코드를 안 건드리는* 것.

비유: 콘센트(포트)와 가전(어댑터)의 관계. V1엔 LED 전구 하나, V1.5엔 선풍기 추가, V2엔 스마트 조명 추가 — 콘센트는 그대로.

## 3.2 ★ ① SafetyPipeline — DB 강건성의 모이는 곳

### 패턴

```python
class SafetyLayer(Protocol):
    name: str
    async def check(self, sql: str, ctx: HarnessContext) -> Verdict: ...
    # Verdict: allow | block(reason) | confirm(plan) | transform(sql')

class SafetyPipeline:
    def __init__(self, layers: list[SafetyLayer]):
        self.layers = layers
    
    async def evaluate(self, sql, ctx) -> SafetyResult:
        current = sql
        for layer in self.layers:
            v = await layer.check(current, ctx)
            if v.kind == 'block':     return SafetyResult.blocked(...)
            if v.kind == 'confirm':   await ctx.request_confirm(v.plan)
            if v.kind == 'transform': current = v.transformed_sql
        return SafetyResult.allowed(current)
```

### V1 → V2 진화

| 버전 | layers (순서대로) | 비용 |
|---|---|---|
| **V1** (껍데기) | `WhitelistGate` (SELECT/WITH로 시작) + `TimeoutSetter` (statement_timeout) | ~200 LOC |
| **V1.5** | + `SqlglotASTGate` (AST 기반 정밀 검증) + `FunctionDenylist` (pg_sleep 등 차단) + `LimitInjector` (SELECT에 LIMIT 자동 부착) + `GUCPackSetter` (5 GUC pack) + `RateLimit` (token bucket) | +500 LOC |
| **V2** | + `CostGate` (EXPLAIN multi-metric) + per-engine pipeline (PG vs BQ) + `AuditHashChain` | +400 LOC |

### 의미 — *DB 정보 완성도가 낮아도 동작*

V1.5에 *"description 없는 컬럼은 자동 description 생성"* 같은 layer 추가 가능:

```python
class AutoDescribeLayer:
    """description이 없는 컬럼을 LLM으로 생성해 시멘틱에 주입"""
    async def check(self, sql, ctx):
        missing = [c for c in ctx.referenced_columns(sql) if not c.description]
        for col in missing:
            desc = await self.llm.describe_column(col)
            ctx.semantic.upsert_dimension(col.name, description=desc)
        return Verdict.allow()
```

기존 컴포넌트 변경 0. 그냥 layer 1개 추가.

V1.5엔 *"DB 강건성"* 차별화의 핵심 layer들이 들어옴 — *불완전한 메타데이터를 자동 보강* 하는 layer들. 그게 우리 제품의 한 포인트.

---

## 3.3 ★ ② MemoryService — Hermes 기억의 3축 분리

### 패턴

```python
# 3축이 독립적으로 진화
class FactStorePort(Protocol):
    async def put(self, fact: Fact) -> str: ...
    async def query(self, scope: Scope, filter: dict) -> list[Fact]: ...

class RecallStrategy(Protocol):
    async def recall(self, store, ctx, question: str) -> list[Fact]: ...

class FactExtractor(Protocol):
    async def extract(self, recent_events: list[Event]) -> list[Fact]: ...

class MemoryService:
    def __init__(self, store, recall, extractor): ...
```

### V1 → V2 진화

| 버전 | Store | Recall | Extractor |
|---|---|---|---|
| **V1** | `InMemoryFactStore` | `AllFactsRecall` (전부 주입) | `ManualOnly` (`/remember` 명령만) |
| **V1.5** | `SqliteFactStore` (영속) | `KeywordRecall` (질문 키워드 매칭) | `LLMExtractor` (대화에서 반복 패턴 추출) |
| **V2** | `SqliteFactStore` | `EmbeddingRecall` (벡터 유사도) | + `ConflictResolver` (사용자가 X 했다가 not-X 했을 때) |
| **V2.5** | `PostgresFactStore` (멀티 인스턴스) | `HybridRecall` (keyword + embedding + recency) | + 신뢰도 점수 |

### 의미 — *진짜* Hermes-style

V1엔 *"`/remember "우리 fiscal year는 7월 시작"` 명령으로만 fact 등록 + 모든 facts를 매번 전부 주입"* — 단순. 그러나 *facts가 영속화되고 모든 세션에서 적용* 됨.

V1.5에 LLMExtractor 추가하면 *"사용자가 매번 'KST 기준'을 강조하니 자동으로 facts에 시간대=KST 저장"* 같은 자동 학습. V2에 EmbeddingRecall 추가하면 *"질문과 관련된 facts만 가져와 토큰 절약 + 신호 강화"*.

핵심: V1.5/V2 변경 시 `harness/` 코드는 한 줄도 안 건드림. `memory/` 안에 새 클래스 추가.

---

## 3.4 ★ ③ IngestionPipeline — 문서 → 시멘틱 레이어

### 패턴

```python
class DocumentSource(Protocol):
    name: str
    async def fetch(self, ref: str) -> Document: ...

class DocumentExtractor(Protocol):
    name: str
    target_kinds: set[str]   # {'metric', 'dimension', 'business_rule'}
    async def extract(self, doc, schema_summary) -> list[Candidate]: ...

class IngestionPipeline:
    def __init__(self, sources, extractors): ...
    
    async def ingest(self, source_kind, ref, ctx) -> list[Candidate]:
        doc = await self.sources[source_kind].fetch(ref)
        candidates = []
        for ext in self.extractors:
            candidates += await ext.extract(doc, ctx.schema_summary)
        return candidates   # → 사용자 confirm UI로
```

### V1 → V2 진화

| 버전 | Sources | Extractors |
|---|---|---|
| **V1** | `FileUpload` (MD/PDF/TXT) | `LLMExtractor` (단일 prompt) |
| **V1.5** | + `URLFetch` (HTML/PDF) | + `DDLExtractor` (DB schema 파일 직접 파싱) |
| **V2** | + `NotionMCP`, `ConfluenceMCP` | + `HybridExtractor` (LLM + rule-based) |
| **V2.5** | + `GitHubMarkdown`, `GoogleDriveMCP` | + `ChunkedRAGExtractor` (긴 문서) |

### 흐름 — V1 walking skeleton

```
사용자: /ingest <파일 첨부> metric_definitions.md
   │
   ▼
FileUpload.fetch()
   │ doc.text = "매출은 SUM(orders.amount) WHERE status != 'cancelled'..."
   ▼
LLMExtractor.extract(doc, current_schema)
   │ LLM prompt:
   │  "다음 문서에서 metric/dimension/business_rule을 찾아 JSON으로 반환:
   │   - 현재 DB 스키마: {orders, order_items, products, customers}
   │   - 문서: {doc.text}
   │  ..."
   │ → candidates = [
   │     {kind: 'metric', name: 'total_revenue', 
   │      expr: 'SUM(orders.amount)', source_doc: 'metric_definitions.md#L12'},
   │     {kind: 'business_rule', name: 'exclude_cancelled',
   │      sql: "status != 'cancelled'", applies_to: ['total_revenue']},
   │   ]
   ▼
Discord embed (button view):
   "이 문서에서 다음을 찾았어요:
    📊 METRIC: total_revenue
       SUM(orders.amount)
       출처: metric_definitions.md L12
    
    📋 RULE: exclude_cancelled (적용: total_revenue)
       status != 'cancelled'
    
    [✅ 모두 등록] [개별 선택] [❌ 취소]"
   ▼
사용자 ✅
   ▼
SemanticLayer.add(...) + source_doc reference 보존
   ▼
이후 /ask "이번 달 매출" 
   ▼ LLM이 SemanticLayer에서 total_revenue 자동 매칭
   ▼ SQLComposer가 exclude_cancelled rule을 WHERE에 자동 주입
```

V1.5에서 같은 문서 재업로드 시 *diff* 표시 → 사용자가 update/keep/remove 선택. 즉 *"문서가 곧 단일 진실 소스"* 패턴.

### 의미 — *비즈니스 맥락을 잘 이해*

기둥 ③의 진짜 의미. 사용자가 사내 정의를 *문서로* 가지고 있다면 그대로 업로드 → 자동 추출 → confirm → 적용. *Wren AI의 MDL 수동 작성* 대비 비교 우위.

---

## 3.5 V1엔 무엇을 박아두고 무엇을 미루는가

```
V1에 반드시 있어야 할 추상 (포트·인터페이스만, ~300 LOC 추가 비용):
  core/ports/safety.py        — SafetyLayer Protocol
  core/ports/memory.py        — FactStorePort, RecallStrategy, FactExtractor
  core/ports/ingestion.py     — DocumentSource, DocumentExtractor
  
  safety/pipeline.py          — SafetyPipeline 클래스
  memory/service.py           — MemoryService 클래스
  ingestion/pipeline.py       — IngestionPipeline 클래스

V1엔 각 추상의 단순 구현 1~2개씩만 (~700 LOC):
  safety/layers/{whitelist_gate, timeout_setter}.py
  memory/stores/inmemory.py + recall/all_facts.py + extractors/manual.py
  ingestion/sources/file.py + extractors/llm_extractor.py
```

추상 비용: ~300 LOC.
V1.5에서 절감하는 비용: ~500 LOC (chain 패턴이 없었다면 매번 코어 수정).
V2에서 절감하는 비용: ~1,000 LOC.
**초기 투자가 빠르게 회수**.

---

# Chap 4. V1 walking skeleton

## 4.1 V1에 들어가는 것

| 영역 | V1 |
|---|---|
| Discord 진입 | DM 메시지 / 채널 `@bot` 멘션 → 자동 thread / thread reply |
| 명령 | `/connect`, `/ingest <파일>`, `/remember "..."`, `/audit me`, `/forget <id>` |
| 자연어 | DM 또는 thread 안에서 그냥 묻기 |
| LLM | OpenAI `gpt-4.1-mini` 단일 |
| DB | PostgreSQL only |
| 응답 | 텍스트 (≤50행) 또는 CSV 첨부 (>50행) |
| Safety | SafetyPipeline + V1 layer 2개 (WhitelistGate + TimeoutSetter) |
| Memory | MemoryService + V1 구현 (InMemory + AllFacts + Manual) |
| Ingestion | IngestionPipeline + V1 (FileUpload + LLMExtractor) |
| 영속화 | secrets/audit/sessions/facts → SQLite. conversation → 영속 |
| 도구 | run_sql · explore_schema · ingest_doc · define_metric · remember · ask_user |
| 호스팅 | Oracle Cloud Always Free 또는 fly.io free |

## 4.2 V1에 *안* 들어가는 것

| 항목 | 미루는 곳 | 이유 |
|---|---|---|
| `run_code` / `write_code` (Python 실행) | **영구 삭제** | read-only 약속을 무력화. 부활 시 sandbox 필수 |
| Cost gate (EXPLAIN 기반) | V1.5 | L1 + L0 timeout으로 1차 충분 |
| Function denylist | V1.5 | WhitelistGate가 1차 방어 |
| Rate limit | V1.5 | 트라이얼 두 자릿수 |
| Auto fact extraction | V1.5 (LLMExtractor 추가) | Manual `/remember` 로 시작 |
| URL/Notion 문서 입력 | V1.5 / V2 | FileUpload 1개로 시작 |
| Embedding recall | V2 | 토큰 절약 효과는 facts가 많아질 때 |
| Persistent View / streaming / PNG paginate | V1.7 | Discord SDK 깊은 영역 |
| Anthropic / NIM | V1.5 (contract test 후) | OpenAI 하나로 시작 |
| 길드 channel 활성화 admin 게이트 | (멘션 패턴이 대체) | thread는 채널 권한 상속 |
| Audit hash chain | V2 | 트라이얼은 SQLite append-only로 충분 |
| `visualize` (PNG 차트) | V1.7 | V1엔 CSV 첨부로 충분 |

## 4.3 V1 LOC 추정

```
core/                ~600 LOC  (ports + types + identity)
harness/             ~700 LOC  (context, session, loop, system_prompt, tool_registry)
semantic/            ~600 LOC  (types, layer, sql_composer, store)
safety/              ~250 LOC  (pipeline + 2 layers)
memory/              ~350 LOC  (service + 3 simple impls)
ingestion/           ~300 LOC  (pipeline + 2 adapters)
tools/               ~700 LOC  (6 tools × 평균 ~120 LOC)
tenancy/             ~400 LOC  (concierge, encrypted_secrets, factstore)
discord/             ~800 LOC  (bot, commands 5개, session_router, render)
adapters/            ~500 LOC  (openai, postgres_async, encrypted_sqlite)
tests/               ~900 LOC  (unit + safety 회귀 + e2e mock)

총 V1: ~6,100 LOC 신규
```

## 4.4 일정 — 4.5~5주 솔로

```
Week 1 — core + harness
   • core/ports/ (5 + safety/memory/ingestion 추상 3)
   • HarnessContext, Session (in-memory + 영속 facts), agent_loop
   • frontends_dev/cli.py 로 단위 검증

Week 2 — semantic + safety + 첫 도구들
   • semantic/* 도메인 모델 + SQLComposer
   • safety/pipeline.py + layers/(whitelist, timeout)
   • tools/{run_sql, explore_schema}
   • adapters/{openai, postgres_async, encrypted_sqlite}
   • tests/safety/ 회귀 12개 (CI gate)

Week 3 — memory + ingestion + 나머지 도구
   • memory/service + 3 impl
   • ingestion/pipeline + 2 adapter
   • tools/{ingest_doc, define_metric, remember, ask_user}
   • tenancy/{concierge, encrypted_secrets, factstore}

Week 4 — Discord
   • bot.py + setup_hook
   • commands/{connect, ingest, remember, audit, forget}
   • session_router (DM / channel @mention → thread / thread reply)
   • render (텍스트 / CSV 첨부)
   • Modal + 동의 button view

Week 5 — polish + e2e + 출하
   • README + DEPLOY 가이드
   • bench/ 데모 시나리오 1개
   • CI YAML
   • 첫 길드 배포

총: 4.5~5주 솔로 풀타임.
```

3주는 *기존 코드 70% 활용* 가정이었음. wipe 기준엔 4.5~5주가 정직.

## 4.5 회귀 12개 (V1 CI gate)

| # | 입력 | 기대 |
|---|---|---|
| 1 | `DROP TABLE users` | WhitelistGate block (DDL) |
| 2 | `; DELETE FROM t; --` | WhitelistGate block (multi-statement) |
| 3 | `INSERT INTO t VALUES (1)` | WhitelistGate block |
| 4 | `UPDATE t SET x=1` | WhitelistGate block |
| 5 | `WITH x AS (INSERT INTO t VALUES (1)) SELECT * FROM x` | WhitelistGate block (CTE 안 INSERT — V1.5 SqlglotASTGate 이전엔 *최상위 노드만* 보지만, WITH+INSERT는 첫 키워드가 WITH라 통과될 수 있음 → V1엔 *INSERT 키워드 검색* 으로 fail-closed) |
| 6 | `SELECT * FROM nonexistent` | PG error (gate 통과, 실행 단계 실패) |
| 7 | `SELECT pg_sleep(60)` | (V1엔 timeout 30s에서 cut. V1.5 FunctionDenylist 추가 시 명시 block.) |
| 8 | `SELECT * FROM huge_table` (50k rows) | row_limit 1000 truncate |
| 9 | `SELECT 1` (정상) | allow |
| 10 | `WITH a AS (SELECT 1) SELECT * FROM a` (정상 CTE) | allow |
| 11 | `EXPLAIN SELECT 1` | allow |
| 12 | `` (빈 문자열) | block (parse_error) |

V1엔 단순한 회귀. V1.5에서 ASTGate 추가 시 회귀가 *훨씬 정밀해짐*. 그때 추가:
- `SELECT public.pg_sleep(60)` (schema-qualified) → FunctionDenylist
- `COPY foo TO PROGRAM 'curl ...'` → ASTGate
- `EXPLAIN ANALYZE DELETE FROM t` → ASTGate

---

# Chap 5. 의견 정리

## 5.1 왜 이 설계가 작동할 거라 보는가

**(1) "오픈소스의 정체성"이 차별점에 부합**

Vanna/Wren/SQLCoder가 *질문→SQL 파이프라인 자체* 는 완성도 높음. 우리가 또 *"GPT-4보다 더 좋은 SQL을 만든다"* 로 경쟁하면 *오픈소스 정체성* 이 약함 — 모델 fine-tuning은 데이터·GPU 싸움.

대신 우리는 *"불완전한 DB에서도 잘 동작" + "문서로 비즈니스 맥락 학습" + "Discord에서 팀이 같이 묻고 답을 받음" + "모든 정의·대화를 기억"* — 이 4가지 조합은 기존 오픈소스에 *없음*. 그게 정체성.

**(2) chain/strategy 패턴이 *체계화된 강건성 연구* 의 코드 토대**

DB 강건성 차별화는 *"description 없으면 자동 생성"* 같은 *상황별 커스텀 전략* 의 모음. V1.5의 SafetyPipeline layer들이 그 전략을 *추가 가능한 형태* 로 받아들임. 새 전략 = 새 layer 1개.

연구자 입장에선 *Hint Vector* 같은 *DB 구조에 대한 근본적 강건성* 도 한 layer로 들어올 수 있음. 즉 *연구→제품* 흐름이 자연스러움.

**(3) 멘션+thread 패턴이 Discord native**

DM vs Channel 양분이 사라지고, *thread* 가 *분석 노트* 가 됨. Discord 사용자 멘탈 모델과 일치. 가짜연구소 같은 use case도 자연스럽게 들어옴.

**(4) Hermes 기억이 *실무 가치* 와 직결**

*"우리 회사 매출 정의는 이거"* 한 번 가르치면 *모든 세션에서 적용*. 매번 prompt에 풀어 넣는 LLM과 차별. facts가 쌓일수록 *제품 가치가 누적* 됨 — 사용자 lock-in.

## 5.2 한계와 trade-off (정직하게)

| 한계 | 영향 | 대응 |
|---|---|---|
| 의미적 정확성의 정량 평가 부재 | "안전하게 틀린 답"이 가장 위험한데 V1엔 validation loop 없음 | V1.5에 golden query set + answer citation. 그러나 본질은 *비즈니스마다 다름* — 우리 측 한계 |
| LLM 비용 노출 | 토큰 폭주 시 사용자 비용 증가 | V1.5에 rate limit + per-user 토큰 cap |
| 첫 출하까지 4.5~5주 | 빠른 검증 어려움 | walking skeleton이지만 wipe라 4주 미만은 무리 |
| chain/strategy 추상 비용 | V1 LOC +300 | V1.5/V2에서 절감되는 비용으로 회수 (계산상 흑자) |
| Discord 플랫폼 락-인 | Discord 외 사용 시 어댑터 추가 필요 | 4기둥 중 Discord는 *frontend 어댑터* 일 뿐, 핵심은 변하지 않음. Slack 어댑터 추가 시 ~500 LOC |
| 의미 추출 LLM 환각 | 문서에서 잘못된 metric 추출 가능 | 사용자 confirm 단계가 1차 방어. V1.5에 validator layer |
| in-memory recall (V1) | facts 많아지면 토큰 폭증 | V1.5에 KeywordRecall, V2에 EmbeddingRecall |

## 5.3 비교 — 기존 오픈소스 대비 위치

| 영역 | Vanna AI | Wren AI | SQLCoder | **Lang2SQL (우리)** |
|---|---|---|---|---|
| 자연어 → SQL | ✅ RAG | ✅ MDL 기반 | ✅ fine-tuned LLM | ✅ RAG + 시멘틱 + harness |
| DB 직접 연결 | ✅ | ✅ | ✅ | ✅ |
| Semantic layer | ❌ | ✅ (수동 MDL) | ❌ | ✅ (**문서 자동 추출**) |
| 대화 기억 | ❌ | ❌ | ❌ | ✅ (**Hermes**) |
| 멀티유저 협업 | 2.0에서 추가 | enterprise BI | ❌ | ✅ (**Discord thread**) |
| 불완전 DB 보강 | ❌ (학습 데이터 의존) | ❌ | ❌ | ✅ (**V1.5+ 자동 보강 layer**) |
| 사용 UI | Web UI | Web UI | CLI | **Discord** |
| 확장 모델 | 단일 architecture | enterprise platform | 단일 LLM | **chain/strategy 3개** |

**위치 요약**: *Vanna의 자연어→SQL + Wren의 시멘틱 + 우리만의 (문서 자동 추출 + Discord 협업 + Hermes 기억 + DB 강건성 layer)*.

## 5.4 한 줄

> **"Discord 멘션으로 thread를 띄우고, 문서를 넣어 비즈니스 맥락을 학습시키고, DB가 불완전해도 견디고, 모든 대화·정의를 기억하는 오픈소스 분석 에이전트."**

---

# 결정 필요 사항

V1 착수 전 답이 있으면 좋은 항목:

1. **첫 배포 Discord 길드** — 본인 테스트 길드 / 가짜연구소 / 기타?
2. **OpenAI API 키** — 본인 키 / 팀 키 / 무료 한도?
3. **레포 새 이름 vs `lang2sql/` 유지** — 권고: 유지 + 새 브랜치 (`feature/v4-rebuild`)
4. **첫 데모 시나리오 1개** — bench/ 에 들어갈 *완성된 use case*. 예: "이커머스 매출 분석 — 4 테이블, 3 metric, 1 문서, 5개 질문"
5. **NIM 도입 시점** — V1.5에 contract test 후 / V2까지 보류?

답해 주시면 v4-final 로 마무리하고 Week 1 PR-1 (core + harness) 부터 시작.

— end —
