# Lang2SQL — Discord-First 재설계 (v3, Walking Skeleton)

> **작성일**: 2026-05-18
> **결정자**: ryan@brain-crew.com
> **상태**: v2 → v3. 5명 리뷰어(Codex + Agent Teams 4명) 라운드 2 audit 결과 반영.
> **핵심 변경**: v2의 *"5.5주에 다 넣자"* → v3의 *"3주에 가장 작은 작동하는 제품 + 확장점"*.
> **선행 문서**: `discord_first_redesign.md` (v1), `discord_first_redesign_v2.md` (v2, 확장 청사진으로 보존).

---

## 0. 한 줄과 타이브레이커

> **"Discord DM에서 자연어로 PostgreSQL에 묻고, 안전하게 답을 받는다. DB는 변하지 않고, 결과는 audit에 남는다."**

설계 충돌 시 우선순위:

1. **데이터·DB 무결성 + 권한** — DB가 변하지 않는가, 사용자가 권한 있는 데이터만 보는가
2. **의미적 정확성** — 답이 의미적으로 맞는가 (V1엔 audit + golden query set, validation loop는 V1.5+)
3. **Discord UX 단순성** — 한 번의 입력으로 결과를 얻는가
4. **맥락 보존** — 끊겨도 이어지는가 (V1은 *in-memory*, 영속화는 V1.6)

(Codex가 v2 4축에 *"권한/data exposure를 최상위 축으로 올리지 않았다"* 고 STILL-INVALID 판정 → 축 #1을 *"무결성 + 권한"* 통합으로 명확화. devils-advocate의 "5축은 product framing overkill" 우려는 4축 유지로 절충.)

---

## 1. v3-minimal 범위

### 1.1 V1에 *들어가는* 것

| 영역 | V1 |
|---|---|
| 인터페이스 | Discord DM only. 슬래시 명령 3개: `/connect`, `/ask <질문>`, `/disconnect` |
| LLM | OpenAI `gpt-4.1-mini` 단일 |
| DB | PostgreSQL only (dedicated readonly role 강제) |
| 응답 형식 | 텍스트 (≤50행) 또는 CSV 첨부 (>50행) — PNG·차트·페이지 버튼 V1 미포함 |
| Safety | L0 (GUC pack) + L1 (statement gate) + L4 (audit) **3개만** |
| 세션 | in-memory dict — 봇 재시작 시 손실. 사용자가 다시 `/ask` 호출 |
| 영속화 | audit + secrets만 SQLite. conversation은 휘발 |
| 도구 | `run_sql`, `explore_schema`, `ask_user` **3개만** |
| 호스팅 | 본인 PC 또는 fly.io free / Oracle Cloud Always Free |

### 1.2 V1에 *안* 들어가는 것 (V1.x로 미룸)

| 항목 | 미루는 곳 | 이유 |
|---|---|---|
| `run_code` / `write_code` 도구 | **삭제** (V2도 보류) | Codex 최우선 지적: read-only 제품에서 Python subprocess는 모든 safety layer를 무력화 (token·secret·FS·network 노출). 부활 시 sandbox 필수. |
| Cost gate (EXPLAIN-based) | V1.5 | L1 + L0 timeout으로 1차 충분. confirm UX는 persistent View 의존이라 V1.7에 자연스럽게 들어옴. |
| Rate limit | V1.5 | 트라이얼은 1~2명. |
| Self-test 7개 자동화 | V1.5 | V1엔 수동 회귀. CI YAML은 V1.5와 동반. |
| Persistent View / streaming / PNG paginate | V1.7 | Discord SDK 깊은 영역. V1엔 ephemeral 한 번 응답으로 충분. |
| Hermes write-through (영속 conversation) | V1.6 | in-memory로 시작. 사용자가 끊김 불편을 호소하면 SessionStore 어댑터 교체. |
| `define_metric/dimension/relationship` 등 semantic CRUD 도구 | V1.5 | `write_sql` 컴포저는 비어 있는 layer로도 작동. semantic 구축은 trial 사용자가 명시 요청할 때. |
| NVIDIA NIM | V1.5 (contract test 통과 후) | OpenAI 하나로 시작. |
| Anthropic 노출 (`/model` 명령) | V2 | 코드는 보존, V1엔 미노출. |
| 길드 채널 / 스레드 세션 | V2 | Codex가 "DM-only도 DM 덤프 위험"으로 추가 지적 — V2에 schema/table allowlist + per-user audit 완성 후. |
| `/grant-readonly` 도우미 명령 | V1.5 | V1은 README의 SQL 가이드로 충분. |
| Audit hash chain / 외부 sink | V2 | V1엔 append-only SQLite + `/audit me`. |
| `visualize` 도구 | V1.7 | PNG render 함께. |
| `load_skill` | V1.5 | skills/ 디렉토리는 보존, 도구만 미노출. |
| Python Textual TUI | **삭제** | |
| Go TUI | freeze (유지하되 V1에서 신규 작업 0) | |
| RAG / 벡터스토어 / embedding | V2+ | V1은 schema-grounded NL→SQL. |

### 1.3 기술 결정 (최소)

| 항목 | 선택 |
|---|---|
| Discord lib | `discord.py` 2.x |
| DB 드라이버 | `asyncpg` + `sqlalchemy.ext.asyncio.create_async_engine` (**AUTOCOMMIT isolation**) |
| LLM | OpenAI `gpt-4.1-mini` |
| Secret 저장 | AES-GCM per-row in SQLite (`secrets` 테이블만 암호화) |
| 호스팅 | Oracle Cloud Always Free 또는 fly.io free (Cloudflare Workers 불가 — discord.py는 장기 실행) |

---

## 2. 상위 아키텍처 (V1)

```
                    ┌──────────────────────────┐
                    │   DISCORD GATEWAY (DM)   │
                    └──────────────┬───────────┘
                                   │ asyncio
                                   ▼
┌──────────────────────────────────────────────────────────────┐
│            DISCORD ADAPTER (단순)                              │
│   /connect Modal · /ask handler · /disconnect                  │
│   ephemeral response · CSV attach (>50 rows)                   │
└──────────────┬───────────────────────────────────────────────┘
               │ ctx = await Concierge.build(dm:user_id, principal)
               ▼
┌──────────────────────────────────────────────────────────────┐
│            TENANCY (최소)                                      │
│   ContextConcierge · EncryptedSecrets (AES-GCM SQLite)         │
└──────────────┬───────────────────────────────────────────────┘
               ▼ ctx
┌──────────────────────────────────────────────────────────────┐
│            HARNESS KERNEL                                      │
│   agent_loop · Session(in-memory) · ToolRegistry(ctx)          │
│   system_prompt(per-turn)                                      │
└──────┬───────────────────────┬───────────────────────────────┘
       │                       │
       ▼                       ▼
┌──────────────────────────────────────────────────────────────┐
│            SAFETY (3 레이어)                                   │
│   L0 connect (readonly role + GUC pack)                        │
│   L1 statement gate (sqlglot AST + hardcoded fn denylist)      │
│   L4 audit (SQLite append-only)                                │
└──────┬───────────────────────┬───────────────────────────────┘
       ▼                       ▼
┌──────────────────────────────────────────────────────────────┐
│            ADAPTERS                                            │
│   LLM: openai_                                                 │
│   DB:  postgres_explorer (asyncpg)                             │
│   Secrets/Audit: encrypted_sqlite                              │
└──────────────────────────────────────────────────────────────┘
```

규칙:
- 포트는 5개만 정의 (`LLMPort`, `ExplorerPort`, `ToolPort`, `SecretsPort`, `AuditPort`). 나머지(`SessionStorePort`, `PersistentViewStorePort`, `HookPort`)는 V1.x에 추가.
- 모든 어댑터는 async. event loop 블로킹 금지.
- safety는 `run_sql` 한 곳에서만 통과. 다른 도구는 SQL을 실행 안 함.

---

## 3. DB 연결 — `/connect` (Modal 2필드)

```
사용자                       Bot DM                        Tenancy
  │                            │                               │
  │── /connect ───────────────▶│                               │
  │                            │   Modal 출력:                  │
  │                            │   ┌────────────────────────┐ │
  │                            │   │ label    (Short)        │ │
  │                            │   │ url      (Short)        │ │
  │                            │   │  postgresql://USER:PASS │ │
  │                            │   │   @HOST:5432/DB         │ │
  │                            │   │   ?sslmode=require       │ │
  │                            │   └────────────────────────┘ │
  │── submit ─────────────────▶│                               │
  │                            │                               │
  │                            │   defer (ephemeral)            │
  │                            │   ─ RO probe (catalog) ──────▶│
  │                            │   ← OK/FAIL                   │
  │                            │   if OK:                       │
  │                            │     encrypt → secrets.put      │
  │                            │   if FAIL:                     │
  │                            │     embed: "read-only role 필요│
  │                            │              README의 SQL 참조"│
  │                            │                               │
  │                            │   button view 동의:            │
  │                            │   ┌────────────────────────┐ │
  │                            │   │ READ-ONLY 정책 동의     │ │
  │                            │   │  [✅ Agree] [❌ Cancel]│ │
  │                            │   └────────────────────────┘ │
  │── ✅ Agree ───────────────▶│                               │
  │                            │   secrets 활성화 + ephemeral  │
  │                            │   "✅ Connected to 'prod-pg'" │
```

**핵심 결정** (v2 → v3):
- v2의 7필드 Modal → **2필드** (label + url). `acknowledgment="READ-ONLY"` 평문 입력 강제 폐기 → **별도 button view**로 동의 분리 (discord-fact-checker 권고).
- `connection_url`은 **Short** 필드 (Paragraph는 줄바꿈 사고 유발). PG connection string은 ~200자라 Short 4000자 한도 안에 충분.
- Modal 제출 후 **3초 안에 `interaction.response.defer(ephemeral=True)`** 필수 (Discord 한도). RO probe + secrets put은 defer 후 followup.
- **RO probe가 먼저, secrets put은 후** (probe 실패 시 orphan 자격증명 방지).
- writable 계정 등록은 **거부** (Codex/pg-safety-expert 합의 fail-closed). README에 readonly role 생성 SQL 가이드.

### 3.1 RO probe (개선된 catalog 쿼리)

```sql
SELECT
  current_setting('transaction_read_only')::bool                  AS tx_ro,
  -- pg_write_all_data role 직접/간접 멤버십
  pg_has_role(current_user, 'pg_write_all_data', 'USAGE')         AS has_write_role,
  -- non-system table 쓰기 권한 (PUBLIC + role-chain + inherited 모두 포함)
  EXISTS (
    SELECT 1 FROM information_schema.tables t
    WHERE t.table_schema NOT IN ('pg_catalog','information_schema')
      AND (
           has_table_privilege(current_user, t.table_schema||'.'||t.table_name, 'INSERT')
        OR has_table_privilege(current_user, t.table_schema||'.'||t.table_name, 'UPDATE')
        OR has_table_privilege(current_user, t.table_schema||'.'||t.table_name, 'DELETE')
        OR has_table_privilege(current_user, t.table_schema||'.'||t.table_name, 'TRUNCATE')
      )
    LIMIT 1
  )                                                                AS has_write_grant,
  -- schema CREATE 권한
  EXISTS (
    SELECT 1 FROM information_schema.schemata s
    WHERE s.schema_name NOT IN ('pg_catalog','information_schema')
      AND has_schema_privilege(current_user, s.schema_name, 'CREATE')
    LIMIT 1
  )                                                                AS has_create;
```

**합격 조건**: `tx_ro = true AND has_write_role = false AND has_write_grant = false AND has_create = false`. 셋 중 하나라도 진실이면 거부.

(pg-safety-expert + Codex가 v2의 `role_table_grants WHERE grantee=current_user` 가 PUBLIC·role-chain·inherited grant를 못 잡는다고 지적 → `has_table_privilege()` 기반으로 재작성.)

---

## 4. Safety Layer (3개)

### 4.1 L0 Connection — readonly role + GUC pack

```sql
-- 매 connection 시작 (postgres_explorer.on_connect)
SET ROLE lang2sql_readonly;             -- ← 반드시 dedicated role
SET default_transaction_read_only = on;
SET transaction_read_only = on;
SET statement_timeout = '30s';
SET lock_timeout = '5s';
SET idle_in_transaction_session_timeout = '60s';
SET temp_file_limit = '1GB';           -- 단위 명시 필수 (없으면 kB 해석)
SET work_mem = '64MB';                  -- sort/hash spill을 temp_file_limit로 가두기
SET jit = off;                          -- JIT 컴파일 비용 폭주 방지
SET bytea_output = 'hex';
SET client_min_messages = 'warning';
SET application_name = 'lang2sql/v1';
SET search_path = pg_catalog, public;
SET row_security = on;
```

**Engine**: `create_async_engine(..., isolation_level='AUTOCOMMIT', pool_size=2, pool_recycle=1800, pool_pre_ping=True)`.
**ExplorerCache**: LRU 30 (per db_url). 사용자당 등록 가능 DB는 V1에서 1개로 고정 (V1.5에 다중 지원).

**제약**: V1 트라이얼 두 자릿수 사용자에서 PG `max_connections=100` 안에 머무름. 사용자 N × pool_size 2 = 2N connection.

(`SET TRANSACTION READ ONLY`는 *"high-level, does not prevent all writes"* — dedicated role + GUC + L1이 3중 방어. pg-safety-expert 출처: https://www.postgresql.org/docs/current/sql-set-transaction.html)

### 4.2 L1 Statement Gate — sqlglot AST

```python
# safety/statement_gate.py
ALLOWED_TOP = {Select, With, Explain, Describe}
BLOCKED_NODES = (Insert, Update, Delete, Merge, Create, Drop, Alter,
                 Truncate, Grant, Revoke, Copy, Set)
DENY_FUNCTIONS = {            # V1 hardcoded names (V1.5에 OID 매핑으로 승격)
    'pg_sleep', 'pg_sleep_for', 'pg_sleep_until',
    'pg_advisory_lock', 'pg_advisory_lock_shared',
    'pg_advisory_xact_lock', 'pg_advisory_xact_lock_shared',
    'pg_try_advisory_lock', 'pg_try_advisory_xact_lock',
    'pg_terminate_backend', 'pg_cancel_backend',
    'pg_read_file', 'pg_read_binary_file', 'pg_ls_dir',
    'lo_import', 'lo_export', 'lo_create', 'lo_unlink',
    'lo_truncate', 'lo_open', 'lo_from_bytea', 'lo_put', 'lowrite',
    'dblink', 'dblink_exec', 'dblink_connect',
    'pg_reload_conf', 'pg_rotate_logfile',
    'pg_create_restore_point', 'pg_switch_wal',
    'pg_logical_emit_message',
    'pg_promote', 'pg_wal_replay_pause', 'pg_wal_replay_resume',
    'pg_backup_start', 'pg_backup_stop',
}

def classify(sql: str) -> Verdict:
    # 1. parse — 실패하면 fail-closed
    try:
        ast = sqlglot.parse(sql, dialect='postgres')
    except ParseError:
        return Verdict.block(reason='parse_error')
    if len(ast) > 1:
        return Verdict.block(reason='multi_statement')
    root = ast[0]
    # 2. 최상위 노드 화이트리스트
    if type(root) not in ALLOWED_TOP:
        return Verdict.block(reason='not_a_read_statement')
    # 3. EXPLAIN ANALYZE + DML 거부
    if isinstance(root, Explain) and root.args.get('analyze'):
        if root.find(*BLOCKED_NODES[:4]):  # Insert/Update/Delete/Merge
            return Verdict.block(reason='explain_analyze_dml')
    # 4. 모든 서브트리에서 차단 노드 검사 (CTE 내부 INSERT 등)
    for node in root.find_all(*BLOCKED_NODES):
        return Verdict.block(reason=f'forbidden_{type(node).__name__.lower()}')
    # 5. 함수 호출 검사 — schema-qualified bypass 포함
    for func in root.find_all(exp.Func):
        name = (func.name or '').lower()
        # public.pg_sleep 같은 schema 접두사도 처리
        if name in DENY_FUNCTIONS:
            return Verdict.block(reason=f'forbidden_function_{name}')
    return Verdict.allow()
```

V1.5 보강:
- OID-based 매핑 (extension 동적 등록 대응).
- TTL refresh (mid-session 새 함수 감지).
- `DO $$ ... $$` 블록 차단 (PG 동적 SQL).

### 4.3 L4 Audit — SQLite append-only

```sql
CREATE TABLE audit (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  ts          TIMESTAMP NOT NULL,
  principal   TEXT NOT NULL,                 -- discord user_id
  session_id  TEXT NOT NULL,                 -- 'dm:USER_ID'
  kind        TEXT NOT NULL,                 -- 'sql' | 'safety_block' | 'connect' | 'disconnect'
  sql         TEXT,                          -- 차단된 SQL 포함
  row_count   INTEGER,
  duration_ms INTEGER,
  status      TEXT,                          -- 'ok' | 'error' | 'blocked'
  error       TEXT                           -- 차단 사유 또는 PG error
);
CREATE INDEX audit_by_principal ON audit(principal, id);
```

V1 명령: `/audit me` → 최근 20건 ephemeral embed. CSV export·hash chain·외부 sink는 V2.

---

## 5. 영속화 스토어 (V1: secrets + audit만)

```sql
-- secrets: AES-GCM per-row
CREATE TABLE secrets (
  id           TEXT PRIMARY KEY,           -- f"user:{user_id}:default"
  owner        TEXT NOT NULL,              -- discord user_id
  label        TEXT NOT NULL,
  ciphertext   BLOB NOT NULL,              -- AES-GCM(url, key, iv)
  iv           BLOB NOT NULL,
  tag          BLOB NOT NULL,
  created_at   TIMESTAMP NOT NULL,
  last_used_at TIMESTAMP
);

-- audit (위 §4.3)
```

**V1엔 `sessions`, `messages`, `events`, `persistent_views` 테이블 없음.** conversation은 `dict[user_id, list[Message]]` in-memory. 봇 재시작 시 conversation 손실 (사용자가 다시 `/ask`).

마스터 키: `LANG2SQL_MASTER_KEY` env (32 bytes urlsafe base64). 분실 시 secrets만 무효.

---

## 6. 레포 레이아웃 (V1)

```
lang2sql/
├── README.md                    # 30초 setup + readonly role SQL
├── pyproject.toml
├── .env.example                 # LANG2SQL_MASTER_KEY, DISCORD_TOKEN, OPENAI_API_KEY
│
├── src/lang2sql/
│   ├── core/
│   │   ├── types.py             # Message, ToolCall, ToolResult, Event
│   │   ├── identity.py          # Principal (discord user_id)
│   │   └── ports/
│   │       ├── llm.py
│   │       ├── explorer.py
│   │       ├── tool.py
│   │       ├── secrets.py
│   │       └── audit.py
│   │
│   ├── harness/
│   │   ├── context.py           # HarnessContext
│   │   ├── session.py           # in-memory dict
│   │   ├── loop.py              # agent_loop (기존 70% 보존)
│   │   ├── system_prompt.py     # per-turn
│   │   └── tool_registry.py
│   │
│   ├── semantic/                # ★ 기존 코드 그대로 (dialect="postgres")
│   │
│   ├── safety/
│   │   ├── statement_gate.py    # sqlglot + hardcoded denylist
│   │   ├── runtime.py           # L0 GUC SET (connect hook)
│   │   └── audit.py             # append-only writer
│   │
│   ├── tools/                   # 3개만
│   │   ├── run_sql.py           # statement_gate 통과 후 실행
│   │   ├── explore_schema.py    # information_schema 기반
│   │   └── ask_user.py
│   │
│   ├── tenancy/
│   │   ├── concierge.py         # ContextConcierge
│   │   └── encrypted_secrets.py # AES-GCM SQLite
│   │
│   ├── discord/
│   │   ├── bot.py
│   │   └── commands/
│   │       ├── connect.py       # Modal 2필드 + button view 동의
│   │       ├── ask.py           # 자연어 질문 → agent_loop → 응답
│   │       ├── disconnect.py
│   │       └── audit.py         # /audit me
│   │
│   └── adapters/
│       ├── llm/openai_.py       # 기존 그대로
│       └── db/postgres_explorer.py  # 기존 explorer를 async로 진화
│
├── tests/
│   ├── test_semantic_layer.py   # 기존 보존
│   ├── test_harness_core.py     # 기존 보존 (ctx 시그니처만 조정 ~50 LOC)
│   ├── test_skills_registry.py  # 기존 보존
│   └── safety/
│       ├── test_statement_gate.py  # 회귀 12개 (V1 hard gate)
│       └── test_ro_probe.py
│
└── docs/
    ├── discord_first_redesign.md       # v1 보존
    ├── discord_first_redesign_v2.md    # v2 보존 (확장 청사진)
    ├── discord_first_redesign_v3_minimal.md  # ← 본 문서
    ├── README_DEPLOY.md
    └── README_READONLY_ROLE.md         # /connect 실패 시 가이드
```

**삭제** (PR-0):
- `src/lang2sql/tui/` (Python Textual, ~1,400 LOC)
- `src/lang2sql/components/`, `flows/`, `viz/`, `interface/`, `utils/`
- `src/lang2sql/integrations/{embedding,vectorstore,loaders,chunking,catalog}/`
- `src/lang2sql/integrations/llm/{gemma_, bedrock_, azure_, huggingface_, ollama_, gemini_}.py`
- `src/lang2sql/tools/{run_code,write_code,define_*,search_semantic,write_sql,visualize,explain_query,profile_table,show_plan,load_skill}.py` (V1 미사용 — V1.5/V1.7에 복원)
- `src/lang2sql/integrations/llm/anthropic_.py` 는 보존 (V2 노출용)
- `cli/commands/{tui,init,quary,run_streamlit}.py`
- `infra/observability/`, `infra/monitoring/`, `docker/pgvector/`, `pgvector.sh`
- `interface/`, `prompt/`, `dev/e2e_traces/`, `test/`, `bench/` 일부, 옛 테스트 파일들

**보존**:
- `src/lang2sql/semantic/*` (~670 LOC, `dialect="postgres"` 기본값만 변경)
- `src/lang2sql/harness/types.py` → `core/types.py`로 이동
- `src/lang2sql/skills/registry.py` (V1.5 `load_skill` 도구 부활 시 사용)
- `src/lang2sql/integrations/llm/{openai_, anthropic_}.py`
- `src/lang2sql/integrations/db/sqlalchemy_explorer.py` → `adapters/db/postgres_explorer.py`로 async 진화
- `cli/commands/{agent, serve}.py` → `frontends_dev/`로 이동 (V1엔 미노출, 디버그 보존)
- `tui-go/` freeze
- `bench/` (V1.5 마케팅 자료로 활용)
- `docker/postgres/init/` (CI 시드)
- 테스트 3개 (semantic, harness_core, skills_registry)

---

## 7. 마이그레이션 — 3주 walking skeleton

```
Week 0 (PR-0a + PR-0b, 합 1주)              [-7,700 LOC, +50 LOC]
   PR-0a 안전 삭제 (3일):
     • src/lang2sql/tui/, components/, flows/, viz/, 옛 cli
     • 미사용 LLM 어댑터 (gemma 등)
     • V1.x에서 부활할 tools/* 6개 (run_code/write_code 포함 — V2도 보류)
     • python -c "import lang2sql" + 보존 tests 3개 통과 확인
   PR-0b 의존 검증 후 삭제 (2일):
     • grep -r "from lang2sql\." 로 cross-module import 그래프
     • interface/, utils/, integrations/{embedding,vectorstore,...}
     • harness/builder.py 의 build_explorer_from_url 사용처 확인 — utils/ 에 있다면 adapters/db/로 이동
     • .github/workflows/v1_ci.yml 추가 (pytest 보존 3개)

Week 1 (PR-1, kernel + ctx)                  [+450 LOC]
   • core/ports/* 5개 (LLM, Explorer, Tool, Secrets, Audit)
   • HarnessContext + Session(in-memory dict)
   • Tool.execute(ctx, **args) 시그니처
   • test_harness_core.py ctx 마이그레이션 (~50 LOC, 1시간)
   • frontends_dev/cli.py로 kernel 검증 (PG sample db 로컬)

Week 2 (PR-2, safety + 도구 3개)             [+550 LOC]
   • safety/statement_gate.py (sqlglot + hardcoded denylist)
   • safety/runtime.py (L0 GUC SET on connect)
   • safety/audit.py + SQLite schema
   • tools/run_sql.py — statement_gate 호출 후 execute
   • tools/explore_schema.py — information_schema 기반
   • adapters/db/postgres_explorer.py — async (asyncpg, AUTOCOMMIT)
   • adapters/secrets/encrypted_sqlite.py (AES-GCM)
   • tests/safety/ 회귀 12개 (CI gate)

Week 3 (PR-3, discord + 출하)                [+700 LOC]
   • discord/bot.py + setup_hook
   • discord/commands/{connect, ask, disconnect, audit}
   • Modal 2필드 + 동의 button view
   • RO probe (§3.1 catalog 쿼리)
   • tenancy/concierge.py
   • ephemeral 응답 + CSV attach
   • README_DEPLOY.md + README_READONLY_ROLE.md

총: ~1,750 LOC 신규, ~7,700 LOC 삭제, 3주 솔로.
```

**회귀 12개** (V1 CI gate, Week 2에 완성):

| # | 입력 | 기대 |
|---|---|---|
| 1 | `DROP TABLE users` | L1 block (Drop 노드) |
| 2 | `; DELETE FROM t; --` | L1 block (multi_statement) |
| 3 | `WITH x AS (INSERT INTO t VALUES (1) RETURNING *) SELECT * FROM x` | L1 block (CTE 내 Insert) |
| 4 | `SELECT pg_sleep(60)` | L1 block (함수 denylist) |
| 5 | `SELECT public.pg_sleep(60)` | L1 block (schema-qualified) |
| 6 | `COPY foo TO PROGRAM 'curl ...'` | L1 block (Copy 노드) |
| 7 | `EXPLAIN ANALYZE DELETE FROM t` | L1 block (analyze + DML) |
| 8 | `DO $$ BEGIN INSERT INTO t VALUES(1); END $$` | L1 block (parse_error 또는 미허용 노드 — fail-closed) |
| 9 | `SELECT * FROM big_table` (50,001 rows) | L0 timeout 30s 또는 row 한도 1000 truncate |
| 10 | `SELECT pg_advisory_lock(1)` | L1 block |
| 11 | `RESET ROLE; SELECT 1` | L1 block (multi_statement) |
| 12 | `SELECT lo_export(1, '/tmp/x')` | L1 block (함수 denylist) |

(pg-safety-expert가 라운드 1·2에서 권고한 회귀를 V1 CI로 승격. V2 backlog에 두는 게 아니라 V1 fail-closed의 정당성 자체이므로.)

---

## 8. 확장 로드맵 — 같은 포트에 어댑터 추가

각 V1.x 는 **이전 V를 부수지 않고 어댑터/모듈만 추가**.

```
V1.5  (1주)  — Safety + 운영 보강
   + safety/cost_gate.py (EXPLAIN warn+confirm — 단 V1.7 persistent View 전엔 텍스트 confirm만)
   + safety/rate_limit.py (token bucket)
   + safety/self_test.py (CI 자동 회귀, +5개 공격)
   + tools/{define_metric, define_dimension, define_relationship, search_semantic, write_sql, load_skill}
   + adapters/llm/nvidia_nim.py + contract test (통과 시 /model 노출)
   + `/grant-readonly` 명령
   + per-user 다중 DB (`/connections`, `/use`)

V1.6  (1주)  — Hermes-lite 영속화
   + adapters/session_store/encrypted_sqlite.py
   + 11 event types: user_msg, tool_started, tool_finished,
                    assistant_final, pending_prompt, run_interrupted,
                    user_action, session_updated, safety_decision,
                    cost_confirm, audit_marker
     (Codex 권고로 6 → 11 확장)
   + Session 어댑터를 in-memory → SQLite로 교체
   + 부팅 시 active 세션 reattach + run_interrupted 표시

V1.7  (1.5주)  — Discord 풍부함
   + discord/streaming.py (throttled message edit)
   + discord/interactive.py (persistent View)
   + discord/render.py (PNG paginate, 25MB cap)
   + tools/visualize.py 부활
   + persistent_views 테이블 + recovery (setup_hook)
   + cost_gate를 persistent View confirm으로 승격
   + max_pages 200 + CSV 25MB 분할 정책

V2  (별도 분기)  — 확장
   + 길드 채널 / 스레드 세션 (schema/table allowlist + admin 승인)
   + Anthropic provider family 노출 (family 전환 시 confirm)
   + cost_gate hard-block tier (3-tier)
   + audit hash chain + 외부 sink (S3/GCS)
   + 의미적 정확성 implementation: golden query set, answer citation, validation loop
   + MySQL / SQLite / BigQuery 어댑터
   + 외부 secret manager (AWS SM / GCP SM)
```

**확장 시 절대 깨지지 않는 약속**:
- 포트 5개의 시그니처 변경 금지 (확장은 *추가* 메서드만)
- secrets / audit SQLite 스키마 변경은 마이그레이션 스크립트 동반
- L0 + L1 + L4 는 모든 V에서 fail-closed

---

## 9. 핵심 거부·수용 사항 (transparency)

5명 리뷰어 audit에서 **수용한 것**:
- `run_code` / `write_code` 도구 V1 즉시 삭제 (Codex 최우선 지적)
- Modal `acknowledgment` 평문 강제 폐기 → 별도 button view (discord-fact-checker)
- RO probe를 `has_table_privilege()` 기반으로 (pg-safety-expert + Codex)
- L0 GUC에 `work_mem`, `jit=off`, `bytea_output`, `application_name`, AUTOCOMMIT 추가 (pg-safety-expert)
- `pool_size=5 → 2`, per-user db 1개 (max_connections 보호)
- `connection_url`을 Paragraph → Short
- 첨부 한도 8MB → **25MB** (현재 값, 2022 변경)
- self-test 회귀를 V2 backlog → **V1 CI gate**로 승격 (12개)
- 5.5주 → 3주 (walking skeleton + V1.x 단계로 분할)
- 6 event types → V1엔 없음 (in-memory), V1.6에 11 event types로 확장 (Codex가 6→`user_action/session_updated/safety_decision` 추가 권고)

**거부한 것** (사유 명시):
- `write_sql` 코드 파일명 개명 — 코드 본문은 SQL 생성만, 실행은 `run_sql`. 파일명 유지. **단 LLM에 노출되는 tool name은 `compose_sql`로 변경** (codex의 PARTIALLY-JUSTIFIED 절충).
- 5축 타이브레이커 — 4축 유지하되 축 #1을 "무결성 + 권한 + data exposure" 통합으로 명확화.
- DM 데이터 유출 방지를 위한 V1 allowlist — V1엔 README 가이드로만, table allowlist는 V2 (사용자 trial 부담 최소화).
- Hermes write-through full — V1엔 in-memory, V1.6에 영속화 단계 도입.

---

## 10. 잔여 결정 (V1 착수 전)

1. **`compose_sql` vs `write_sql` LLM tool name** — 위 §9 절충안 적용? 그대로 `write_sql`?
2. **첫 배포 길드 / 봇 application 생성** — Discord developer portal 어디 계정?
3. **OpenAI 키 / NIM 키** — V1엔 OpenAI 하나면 충분.
4. **`/audit me` 응답 — 최근 N건의 N 기본값** — 권고: 20건.

---

## 11. 한 줄

> **V1은 "DM에서 `/connect` → `/ask` → 안전한 답"이 작동하는 walking skeleton. 3주에 출하. 확장은 모두 어댑터·모듈 추가로 V1.x 단위. V2 청사진은 `v2.md`에 보존.**

— end —
