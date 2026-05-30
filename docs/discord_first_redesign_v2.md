# Lang2SQL — Discord-First 재설계 명세 (v2)

> **작성일**: 2026-05-18
> **결정자**: ryan@brain-crew.com
> **상태**: v1 → v2. Codex 독립 리뷰 + Agent Teams 다각도 audit (devils-advocate / discord-fact-checker / pg-safety-expert / codebase-reality) 결과 반영.
> **선행 문서**: `docs/discord_first_redesign.md` (v1, 보존)
> **범위**: 현 `lang2sql/` 트리를 **evolve in place** 로 점진 재구성 (v1의 "wipe and rebuild" 어조는 폐기. §6 참조.)

---

## v1 → v2 변경 요약

| # | 영역 | v1 | v2 |
|---|---|---|---|
| 1 | **타이브레이커** | 3축 (UX·무결성·맥락) | **4축** — *의미적 정확성* 추가 |
| 2 | **§3 세션** | DM/채널/스레드 모두 V1 | **V1은 DM-only**, 채널/스레드는 V2 (allowlist 이후) |
| 3 | **§3.2 영속화** | 모든 토큰 delta 까지 flush | **6개 이벤트만 append-log**, stream chunk 복구 폐기 |
| 4 | **§3.2 스키마** | sessions/messages/secrets/audit | **+ `persistent_views`** 추가 (Discord 재시작 복구 필수) |
| 5 | **§4 `/connect`** | 7+필드 Modal + `password: [hide]` | **connection string 1필드 Modal** (Discord Modal은 5필드 한도·password style 미지원) |
| 6 | **§4 RO probe** | `CREATE TABLE __probe; ROLLBACK` | **catalog 쿼리** (`information_schema.role_table_grants` + `pg_has_role`) |
| 7 | **§4 writable 계정** | "경고 + confirm" | **거부 + 도우미 명령** `/grant-readonly` 가 role 생성 SQL 제공 |
| 8 | **§5 L0 Connection** | "RO role 권장" | **dedicated `lang2sql_readonly` role + 5개 GUC SET (`temp_file_limit='1GB'` 단위 필수)** |
| 9 | **§5 L1 Statement Gate** | sqlglot 화이트리스트만 | **catalog-driven function denylist (OID 매칭) + `EXPLAIN ANALYZE + DML` 거부 + `COPY` 전면 차단** |
| 10 | **§5 L2 Cost Gate** | EXPLAIN row → 차단 | **EXPLAIN 다중 metric → 경고+사용자 confirm**. 실제 차단은 L3 runtime cap에 위임 |
| 11 | **§5 L3 Runtime** | timeout/row만 명시 | **5개 GUC 모두 명시** (statement_timeout, lock_timeout, idle_in_transaction_session_timeout, temp_file_limit, search_path) + `row_security=on` |
| 12 | **§5 L4 Audit** | hash chain 암시 | hash chain은 V2 로 명시 이전. V1은 append-only SQLite + 일 회전 |
| 13 | **§7 일정** | 5주, Week 4 과적재 + cost_gate Week 5 모순 | **6 PR (PR-0 + 5주 + 0.5주 여유)**. Week 4 분할, cost_gate는 Week 2 (경고 모드)로 이동 |
| 14 | **§6 레이아웃** | 신규 트리 (wipe) | **evolve in place**. 보존/포팅/삭제 표로 명시 |
| 15 | **§9 NIM** | "OpenAI 호환 그대로 재사용" | **contract test 통과 후 experimental** 노출, OpenAI가 V1 디폴트 |
| 16 | **§1.4 (신규)** | — | **Discord 플랫폼 제약** 단독 절: Modal 5필드, Interaction token 15분, autocomplete 3s, persistent view 요건 |
| 17 | **§2 다이어그램** | sync 추정 | **async boundary 명시** — `create_async_engine(asyncpg)` |
| 18 | **§ToolResult 규약 (신규 §3.4)** | `data: Any` | **canonical shape** (`{kind, payload, meta}`) — write-through 영속화 호환 |
| 19 | **§11 (신규)** | — | Codex 지적 중 **거부한 항목**과 사유 (transparency) |
| 20 | **§10 (개편)** | open questions | **V1 명시적 제외 = V2+** 항목 정리 |

---

## 0. 제품 한 줄과 타이브레이커

> **"Discord에서 쓰는 read-only · audit-by-default SQL 에이전트.
> DB는 절대 변하지 않고, 답은 의미적으로 검증 가능하며, 모든 쿼리는 예산/시간/행 한도 안에서 돈다.
> 대화 맥락은 끊겨도 영속된다."**

설계 충돌 시 우선순위 (위에서 아래 = 강함):

1. **DB 무결성** — 쓰기·부작용·자원 hog가 발생하지 않는가
2. **의미적 정확성** — 답이 문법적으로만이 아니라 *의미적으로* 맞는가
3. **Discord UX 단순성** — 한 번의 입력으로 가능한 결과를 얻는가
4. **맥락 보존** — 끊겨도 이어지는가

`v1`은 "DB는 안 깨지는가?"만 다뤘다. NL→SQL 제품의 진짜 위험은 *"안전하게 실행되어 자신 있게 틀린 결론을 답하는 것"* — 정확성 축이 v2의 핵심 추가.

타이브레이커는 **3축에서 4축으로**. (Codex의 5축 권고는 솔로 트라이얼에 과한 product framing이라 거부 — 4축이 적정 균형.)

---

## 1. 확정된 기술 결정

| # | 항목 | 선택 | 근거 |
|---|---|---|---|
| 1 | Discord lib | **`discord.py` 2.x** | 가장 성숙. 단, Modal 5필드 한도·Interaction token 15분 만료 등 §1.4 제약 인지. |
| 2 | DB 엔진 타깃 (V1) | **PostgreSQL** | EXPLAIN·`SET TRANSACTION READ ONLY`·dedicated role·`statement_timeout` 등 모든 safety 기법이 정직하게 동작. V2: MySQL/SQLite/BigQuery. |
| 3 | 세션 영속화 | **Hermes-style write-through, 6 event types** | 매 발화·도구·일시정지를 즉시 flush. **스트림 청크 복구는 폐기** (idempotency 폭탄 위험). |
| 4 | 세션 + 자격증명 스토어 | **AES-GCM 암호화 SQLite (per-row, secrets 테이블만)** | secrets만 행 단위 암호. sessions/messages/audit는 평문(검색 가능). 키 분실 시 secrets만 무효. |
| 5 | LLM 백엔드 | **OpenAI 디폴트, NVIDIA NIM은 contract-test 통과 후 experimental** | NIM 어댑터는 `base_url` 차이만이라 30 LOC. 단, tool-calling/streaming/JSON schema 동치성은 contract test로 검증 후 `/model` 노출. |
| 6 | DB 드라이버 | **`asyncpg` via `sqlalchemy.ext.asyncio.create_async_engine`** | discord.py는 100% asyncio. sync SQLAlchemy를 그대로 호출하면 event loop를 블록하여 gateway disconnect 위험. |
| 7 | Go TUI | **freeze 유지 (개발 도구)** | NDJSON 인터페이스(`cli/commands/serve.py`) 호환 그대로. V1에선 신규 기능 0. |
| 8 | Python TUI (`src/lang2sql/tui/`) | **삭제** | 스펙에 없고 Discord가 1급 frontend. 약 1,400 LOC 정리. |
| 9 | 차트 출력 | **PNG 첨부 + Discord 한도 인지 페이지네이션** | 메시지 2000자 / embed description 4096자 / embed 총 6000자 / 첨부 8MB 한도. §8 참조. |
| 10 | 호스팅 (트라이얼) | **소형 VPS** | §1.1 참조. Cloudflare Workers는 부적합. |

### 1.1 호스팅 — Cloudflare Workers는 부적합

`discord.py` 는 Discord WebSocket gateway에 **계속 붙어 있어야 하는 장기 실행 Python 프로세스**입니다. Cloudflare Workers의 edge runtime은 short-request 모델이라 불가.

| 옵션 | 비용 | 메모 |
|---|---|---|
| **Oracle Cloud Always Free** | $0 무기한 | ARM Ampere 4코어/24GB. 카드 검증 필요. |
| **fly.io shared-cpu-1x** | $0 ~ $5/월 | 256MB 시작. 한국 가까운 region. |
| **Hetzner CX11** | €4.5/월 (~6,500원) | 안정·빠름. 유럽 region. |
| **본인 PC 24h** | $0 | 데모 단계 충분. |

### 1.2 "타깃 = 가짜연구소 디스코드?" 정리

질문하신 *"이 타깃이 가짜연구소 디스코드?"* 에 대해: 문서의 "타깃"은 **지원할 DB 엔진**(PG vs MySQL vs BQ)을 의미. **배포 커뮤니티**(어느 길드에 봇을 초대하는가)와는 별개. V1 코드는 어떤 길드에든 동작.

### 1.3 자격증명 저장 (모순 명확화)

- 단일 SQLite 파일 `lang2sql.db` 안에 4개 테이블 (`secrets`, `sessions`, `messages`, `audit`, `persistent_views`).
- **`secrets` 테이블만** AES-GCM per-row 암호화 (컬럼: `ciphertext`, `iv`, `tag`).
- `sessions`/`messages`/`audit`/`persistent_views`는 평문. 검색 가능. (대화 텍스트 자체가 민감하다 판단되면 V2에서 전체 컬럼 암호로 확장.)
- 마스터키: `LANG2SQL_MASTER_KEY` env. 분실 시 **secrets만 무효** — 사용자가 `/connect` 재등록. 대화/감사는 보존.
- (v1 §1.3 vs §1#4의 "모순"은 Codex 오독. SQLCipher 형 파일 단위 암호가 아니라 per-row 컬럼 암호로 명확화.)

### 1.4 Discord 플랫폼 제약 (신규)

이 제약들이 §4 설계와 §3 영속화 스키마를 직접 좌우.

| 제약 | 값 | 영향 |
|---|---|---|
| **Modal 최대 컴포넌트** | 5개 TextInput (각 ActionRow 1개) | §4 `/connect`는 single-field connection string 강제. |
| **Modal password style** | **없음** (Short / Paragraph 2종만) | 비밀번호 평문 입력. 완화책: dedicated `lang2sql_readonly` role + 1회용 약한 비밀번호. |
| **Interaction token** | 발급 후 **15분 만료** | 장기 쿼리 결과는 `interaction.edit_original_response()` 대신 `bot.message.edit(channel_id, message_id)` (bot token) 로. |
| **Slash command 자동완성** | **3초 응답 데드라인** | DB 카탈로그 자동완성은 in-memory 캐시 필수 (실시간 조회 불가). |
| **메시지 길이** | content 2000자 / embed description 4096자 / embed 총 6000자 | 결과는 PNG 또는 첨부파일로 강제. |
| **메시지 첨부** | 8MB / 메시지 (무료 길드) | 차트 PNG 페이지 분할 필요. §8. |
| **persistent View** | `View(timeout=None)` + 모든 항목에 `custom_id` ≤ 100자 + `setup_hook()`에서 `add_view()` 재등록 | §3.2 `persistent_views` 테이블 필수. |
| **`custom_id`** | 100자 한도 | `query:{user_id}:{hash16}` 형태로 압축. |

출처: https://docs.discord.com/developers/components/reference , https://discordpy.readthedocs.io/en/latest/

---

## 2. 상위 아키텍처 (async 경계 명시)

```
                          ┌──────────────────────────────┐
                          │      DISCORD GATEWAY         │
                          │  (WebSocket, asyncio)        │
                          └───────────────┬──────────────┘
                                          │
                                          ▼
┌──────────────────────────────────────────────────────────────────────┐
│                       DISCORD ADAPTER  (1급, asyncio)                 │
│  /connect Modal · SessionRouter · Streaming(throttled edit)           │
│  Interactive(persistent View) · Render(PNG paginate) · Permissions    │
│  Recovery(reattach via persistent_views table)                        │
└───────────────────────────┬──────────────────────────────────────────┘
                            │ async ctx = await Concierge.build(key, principal)
                            ▼
┌──────────────────────────────────────────────────────────────────────┐
│                       TENANCY LAYER  (asyncio)                        │
│  TenantRegistry · ExplorerCache(LRU async engines)                    │
│  EncryptedStore · ContextConcierge · SessionQueue(per-session FIFO)   │
└───────────────────────────┬──────────────────────────────────────────┘
                            ▼ ctx
┌──────────────────────────────────────────────────────────────────────┐
│                       HARNESS KERNEL  (asyncio)                       │
│  agent_loop · system_prompt(per turn) · ToolRegistry(ctx 주입)        │
│  Session(write-through, 6 events) · Hooks(pub/sub)                    │
└──────┬─────────────────────┬──────────────────┬──────────────────────┘
       │ ports               │                  │
       ▼                     ▼                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│                   SAFETY LAYER  (제품의 moat)                         │
│  L0 connect (dedicated readonly role + 5 GUC SET)                     │
│  L1 stmt gate (sqlglot AST + catalog-driven function denylist by OID) │
│  L2 cost gate (EXPLAIN multi-metric → user confirm)                   │
│  L3 runtime caps (statement_timeout, lock_timeout, ...)               │
│  L4 audit (append-only SQLite, 일 회전)                                │
│  L5 rate limit (token bucket)                                         │
└──────┬─────────────────────┬──────────────────┬──────────────────────┘
       ▼                     ▼                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     OUTBOUND ADAPTERS                                 │
│  LLM (openai / nvidia-nim contract-tested)                            │
│  DB (sqlalchemy.ext.asyncio + asyncpg)                                │
│  Secrets·SessionStore·AuditSink·PersistentViewStore (encrypted-sqlite)│
└──────────────────────────────────────────────────────────────────────┘
```

규칙은 v1과 동일 — 화살표는 안쪽으로만. 변경점은 **모든 레이어 asyncio 명시**.

---

## 3. 세션 전략

### 3.1 V1 = DM-only

| Discord 컨텍스트 | session_key | V1 상태 |
|---|---|---|
| **봇과의 DM** | `dm:{user_id}` | ✅ **V1 디폴트 (유일한 진입로)** |
| 길드 채널 | `chan:{guild_id}:{channel_id}` | ⏸ V2 (table/schema allowlist + admin 승인 절차 이후) |
| 길드 스레드 | `thr:{guild_id}:{channel_id}:{thread_id}` | ⏸ V2 |

**근거**:
- 길드 채널은 *"채널 멤버 전원 가시"* — read-only여도 PII/민감 row가 노출되는 순간 **데이터 유출 제품**이 됨.
- V1 트라이얼은 개인 분석이 핵심 use case. 채널/스레드는 V2에서 권한 모델(allowlist + per-user audit) 완성 후 개방.
- (Codex + devils-advocate 합의: V1 공용 채널 활성화는 제품 정체성 ("read-only · audit-by-default")의 자기부정.)

**Cross-session 격리**: 같은 user가 DM과 (V2의) 채널을 동시 사용해도 ExplorerCache·rate-limit·schema_cache 키는 **(session_key, principal)** 페어로 격리. 같은 principal이라도 다른 session_key면 메타데이터 누설 금지.

### 3.2 영속화 — Hermes-style, 6 event types only

스트림 청크 단위 복구는 폐기. **6개 이벤트만** append-log:

```
user_msg          — 사용자 발화 (1회/메시지)
tool_started      — 도구 호출 시작
tool_finished     — 도구 결과 (성공/실패)
assistant_final   — 어시스턴트 최종 응답 (스트림 종료 시 1회)
pending_prompt    — ask_user / show_plan으로 일시정지 진입
run_interrupted   — 프로세스 종료/타임아웃으로 중단 (재시작 시 표시용)
```

```
User msg ──▶ Discord adapter ──▶ session.append('user_msg', payload)
                                        │
                                        ├─▶ in-memory state update
                                        └─▶ store.write_tx(...)   ← 동기 트랜잭션
                                                │
                                                ▼
                                       SQLite (WAL, append-only)

Tool start/end   ──▶ append('tool_started' / 'tool_finished')
Pause(ask_user)  ──▶ append('pending_prompt') + flush
LLM stream delta ──▶ buffered in-memory, NO persistence
Crash mid-turn   ──▶ 다음 부팅 시 turn에 'run_interrupted' 표시
                     사용자가 다음 메시지 보내면 새 turn으로 시작
                     (자동 재시도 안 함 — idempotency 폭탄 방지)
```

**보장**: 마지막으로 flush된 event까지 안전. 재시작 시:
1. `SessionStore.iter_active(since=now-30d)` 로 미완 세션 로드.
2. 마지막 event가 `pending_prompt` 면 그대로 대기 상태 복원.
3. 마지막 event가 `tool_started` 인데 `tool_finished` 없으면 `run_interrupted` 추가 + 사용자에게 "중단됨, `/retry` 로 재시도하세요" 표시.
4. Discord adapter가 DM별로 reattach.
5. **Persistent View** (cost confirm 버튼, paginate 버튼)는 `persistent_views` 테이블에서 message_id·channel_id 복원 후 `setup_hook()`에서 `add_view()`.

(v1의 "끊김 없이 이어짐" 어조는 과장이었음 — v2는 *"중단 표시 후 명시 재시도"* 로 축소.)

### 3.3 저장 스키마

```sql
-- 세션 메타
CREATE TABLE sessions (
  id            TEXT PRIMARY KEY,         -- session_key (V1: dm:USER_ID)
  principal     TEXT NOT NULL,            -- 마지막 발화 user id
  kind          TEXT NOT NULL,            -- V1: 'dm'
  db_spec_id    TEXT REFERENCES secrets(id),
  active_model  TEXT,                     -- 'openai:gpt-4.1-mini' 등
  created_at    TIMESTAMP NOT NULL,
  updated_at    TIMESTAMP NOT NULL,
  closed_at     TIMESTAMP
);

-- 이벤트 append-only (6 종)
CREATE TABLE events (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id  TEXT REFERENCES sessions(id),
  ts          TIMESTAMP NOT NULL,
  kind        TEXT NOT NULL,              -- user_msg|tool_started|...|run_interrupted
  payload     TEXT NOT NULL,              -- canonical JSON (§3.4)
  principal   TEXT
);
CREATE INDEX events_by_session ON events(session_id, id);

-- 암호화 자격증명
CREATE TABLE secrets (
  id            TEXT PRIMARY KEY,         -- e.g. "user:123:prod-pg"
  owner         TEXT NOT NULL,
  label         TEXT NOT NULL,
  ciphertext    BLOB NOT NULL,            -- AES-GCM
  iv            BLOB NOT NULL,
  tag           BLOB NOT NULL,
  created_at    TIMESTAMP NOT NULL,
  last_used_at  TIMESTAMP
);

-- 감사 로그
CREATE TABLE audit (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  ts          TIMESTAMP NOT NULL,
  session_id  TEXT,
  principal   TEXT,
  kind        TEXT,                       -- 'sql'|'tool'|'safety_block'|'rate_block'
  payload     TEXT,                       -- JSON
  duration_ms INTEGER,
  status      TEXT                        -- 'ok'|'error'|'blocked'
);

-- ★ Discord persistent view 복구용 (신규)
CREATE TABLE persistent_views (
  message_id   TEXT PRIMARY KEY,
  channel_id   TEXT NOT NULL,
  guild_id     TEXT,                      -- DM이면 NULL
  view_kind    TEXT NOT NULL,             -- 'cost_confirm'|'paginate'|'ask_user'|'plan_approval'
  state_json   TEXT NOT NULL,             -- view 생성자에게 넘길 인자
  session_id   TEXT REFERENCES sessions(id),
  expires_at   TIMESTAMP,                 -- NULL = persistent
  created_at   TIMESTAMP NOT NULL
);
CREATE INDEX views_active ON persistent_views(expires_at) WHERE expires_at IS NULL;
```

### 3.4 ToolResult canonical shape (신규)

`ToolResult.data` 가 `Any` 면 SQLite write-through 시 직렬화 불일치로 복구 불가능. canonical:

```python
{
  "kind": "rows" | "ddl" | "list" | "viz_spec" | "scalar" | "none",
  "payload": ...,           # kind에 따라:
                            #   rows  → [{...}, ...]
                            #   ddl   → "CREATE TABLE ..."
                            #   list  → ["t1", "t2", ...]
                            #   viz_spec → {chart_type, data, ...}
                            #   scalar → number | string
                            #   none  → null
  "meta": {                 # 공통 메타
    "truncated": bool,
    "row_count": int,
    "elapsed_ms": int,
    "warnings": [str, ...]
  }
}
```

도구 12개 전부 이 shape에 맞춤 (대부분 이미 dict 반환 — 키 표준화만).

**Provider-coupling 처리**: conversation은 internal canonical 형식 (`role` ∈ {system|user|assistant|tool_result}, `tool_calls`는 OpenAI-like)으로 저장. OpenAI 어댑터는 통과, Anthropic 어댑터는 양방향 변환. 모델을 *같은 provider family 내에서* 전환할 땐 conversation 유지. **provider family를 넘는 전환 (OpenAI↔Anthropic)** 시 사용자에게 "대화 초기화" 명시 confirm.

### 3.5 동시성

```
전역 concurrency    = 무제한 (asyncio)
per-session         = FIFO 1 (같은 conversation에 동시 LLM 호출 금지)
per-user rate       = token bucket (LLM 20/min,  DB 60/min)
per-guild rate      = token bucket (DB 200/min)        ← V2 채널 활성화 시
LLM stream          = 세션마다 독립
DB engines          = ExplorerCache LRU 50 (per db_url)
```

SQLite는 WAL 모드 + `busy_timeout=200ms`. V1 두 자릿수 동시 사용자에 충분. V2 본격 트래픽 시 Postgres 백엔드로 교체 (어댑터만 갈아끼움).

---

## 4. DB 연결 온보딩 (Discord-native, 재설계)

**v1 → v2 결정적 변경**: Modal 5필드 한도 + password style 미지원에 맞춰 **connection string 단일 필드 모델**로 전환.

### 4.1 `/connect` Modal (5필드)

```
┌─────────────────────────────────────────────────────────┐
│  /connect                                                │
├─────────────────────────────────────────────────────────┤
│  label              (Short, required)                   │
│  └ 예: "prod-pg"                                         │
│                                                          │
│  connection_url     (Paragraph, required)               │
│  └ postgresql://USER:PASS@HOST:5432/DB?sslmode=require  │
│  └ ⚠️ 가급적 dedicated readonly role 사용                │
│  └ /grant-readonly 로 role 생성 SQL 확인                 │
│                                                          │
│  default_schema     (Short, optional)                   │
│  └ 비우면 'public'                                       │
│                                                          │
│  notes              (Paragraph, optional)               │
│  └ 본인 메모                                              │
│                                                          │
│  acknowledgment     (Short, required)                   │
│  └ "READ-ONLY" 라고 정확히 입력해야 제출 가능             │
└─────────────────────────────────────────────────────────┘
```

5필드 정확히 사용. password masking은 Discord가 지원 안 함 — 평문이지만 Modal 자체가 interaction-scoped (메시지 history에 안 남음). 사용자에게 *"본인만 보이며 채팅 로그에 남지 않습니다. 그러나 화면 입력 중에는 노출되므로 dedicated readonly role + 1회용 비밀번호 사용을 강력 권장"* 안내.

### 4.2 제출 직후 처리 (`on_modal_submit`)

```
1. Parse connection_url → host/port/user/pass/db/options 분해. parse 실패 시 ephemeral error.
2. AES-GCM 즉시 암호화 → secrets 테이블 put. 메모리 평문 즉시 zeroize.
3. Async engine 임시 생성 (asyncpg). pool_size=1, pool_recycle=30s.
4. ★ RO Probe (catalog 쿼리, fail-closed):
     SELECT
       current_setting('transaction_read_only')::bool                 AS tx_ro,
       (SELECT bool_or(pg_has_role(current_user, r, 'USAGE'))
        FROM unnest(ARRAY['pg_write_all_data']) r)                    AS has_write_role,
       EXISTS (
         SELECT 1 FROM information_schema.role_table_grants
         WHERE grantee = current_user
           AND privilege_type IN ('INSERT','UPDATE','DELETE','TRUNCATE')
           AND table_schema NOT IN ('pg_catalog','information_schema')
       )                                                              AS has_write_grant;
5. has_write_role = TRUE 또는 has_write_grant = TRUE 면:
   ❌ REJECT. 사용자에게 안내:
     "이 계정은 쓰기 권한을 가지고 있어 등록할 수 없습니다.
      `/grant-readonly` 명령을 실행하면 read-only role 생성 SQL을 보내드립니다."
   secrets 행 즉시 삭제.
6. SELECT 1 검증 + `SELECT count(*) FROM information_schema.tables WHERE table_schema=...`
7. 성공 ephemeral embed:
   "✅ Connected to 'prod-pg'. N tables visible. Try: \"tables 보여줘\""
```

(v1의 `BEGIN; CREATE TABLE __probe; ROLLBACK` 은 fail-open이라 폐기. CREATE 권한 없음 ≠ UPDATE 권한 없음.)

### 4.3 `/grant-readonly` 도우미 명령

```
사용자: /grant-readonly database=prod_db schema=public

봇 DM:
  다음 SQL을 PG superuser로 실행하세요. 비밀번호 부분만 교체:

  CREATE ROLE lang2sql_ro_USER123 LOGIN PASSWORD '<DISPOSABLE>';
  GRANT CONNECT ON DATABASE prod_db TO lang2sql_ro_USER123;
  GRANT USAGE ON SCHEMA public TO lang2sql_ro_USER123;
  GRANT SELECT ON ALL TABLES IN SCHEMA public TO lang2sql_ro_USER123;
  ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT ON TABLES TO lang2sql_ro_USER123;
  ALTER ROLE lang2sql_ro_USER123 SET default_transaction_read_only = on;

  완료되면 /connect 로 이 계정을 등록하세요.
```

writable confirm 옵션 폐기 — read-only가 제품 정체성인데 우회를 열어두는 건 약속 깨짐. 대신 사용자가 RO role을 만들기 쉽게 도와줌.

### 4.4 슬래시 명령 (V1)

| 명령 | 위치 | 동작 |
|---|---|---|
| `/connect` | DM | §4.1 Modal |
| `/grant-readonly` | DM | §4.3 SQL 생성기 |
| `/connections` | DM | 등록 DB 목록 (label만, 비밀번호 안 보임) |
| `/use <label>` | DM | 활성 DB 전환 |
| `/disconnect <label>` | DM | 자격증명 삭제 |
| `/test` | DM | 현재 활성 DB `SELECT 1` + RO probe 재실행 |
| `/safety` | DM | 현재 활성 보호 레이어 embed |
| `/safety self-test` | DM | 7개 공격 자가 검증 |
| `/audit me` | DM | 본인 최근 50건 쿼리 |
| `/audit export` | DM | CSV 첨부 |
| `/model` | DM | provider 내 model 전환 (provider 변경 시 confirm) |
| `/reset` | DM | 현 세션 conversation 초기화 (audit 보존) |
| `/retry` | DM | 마지막 `run_interrupted` 턴 재시도 |
| `/help` | DM | 명령 목록 |

---

## 5. DB 강건성 — Safety Layer (v2 강화)

```
요청 ─▶ ┌──────────────────────────────────────────────────────┐
        │ L0 Connection                                         │
        │  • dedicated `lang2sql_readonly` role 강제 (§4.3)     │
        │  • sslmode=require / verify-full 옵션                  │
        │  • create_async_engine + asyncpg (event loop 비차단)  │
        │  • pool_size=5, pool_recycle=30min, pool_pre_ping=on  │
        │  • 매 connection 시작 시 GUC 일괄 SET:                  │
        │      SET ROLE <readonly_role>;                        │
        │      SET default_transaction_read_only = on;          │
        │      SET transaction_read_only = on;                  │
        │      SET statement_timeout = '30s';                   │
        │      SET lock_timeout = '5s';                         │
        │      SET idle_in_transaction_session_timeout = '60s'; │
        │      SET temp_file_limit = '1GB';     ← 단위 필수!     │
        │      SET search_path = pg_catalog, <user_schema>;     │
        │      SET row_security = on;                           │
        │  ※ SET TRANSACTION READ ONLY 단독은 부족함을 인지       │
        │     (PG: "high-level, does not prevent all writes")   │
        └──────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌──────────────────────────────────────────────────────┐
        │ L1 Statement Gate (sqlglot AST + catalog denylist)    │
        │                                                        │
        │  (a) sqlglot AST 파싱, 화이트리스트:                    │
        │      SELECT, WITH, EXPLAIN(*), DESCRIBE                │
        │      *EXPLAIN ANALYZE + (Insert|Update|Delete|Merge)*  │
        │       조합은 명시적 거부 (실제 실행됨)                   │
        │  (b) 모든 CTE 내부도 walk:                              │
        │      find_all(exp.Insert, exp.Update, exp.Delete,     │
        │               exp.Merge) → 발견 시 차단                 │
        │  (c) `COPY` 전면 차단 (FROM/TO PROGRAM/file 전부)       │
        │  (d) parse error → fail-closed (block)                │
        │  (e) multi-statement (";" 분할) → 첫 번째만 허용,       │
        │       나머지가 있으면 거부                              │
        │  (f) ★ Function denylist (catalog-driven, OID 매칭):    │
        │       부팅 시 pg_proc에서 위험 함수 OID 수집,           │
        │       AST의 모든 function call을 OID 매칭으로 차단     │
        │       → schema-qualified bypass 방어                   │
        │       (이름 매칭만 하면 public.pg_sleep 같은 alias에   │
        │        취약)                                            │
        │  • 위반 시: audit.kind='safety_block' + ❌ embed       │
        └──────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌──────────────────────────────────────────────────────┐
        │ L2 Cost Gate — *경고+confirm* 모드 (차단 아님)         │
        │                                                        │
        │  • EXPLAIN (FORMAT JSON) → JSON plan tree 재귀 walk    │
        │  • 임계 (V1 디폴트):                                     │
        │      Total Cost > 1,000,000                            │
        │    OR Plan Rows × Plan Width > 100 MB (bytes)          │
        │    OR Sort/Hash 노드 + 입력 > 1M rows                   │
        │  • 임계 초과 시:                                         │
        │      show_plan(plan=..., cost=..., est_rows=...,       │
        │                est_bytes=...) → Discord button view   │
        │      사용자 ✅ 누르면 진행, ❌ 누르면 취소               │
        │  • EXPLAIN 추정은 stale stats 시 빗나감 → 차단 아님      │
        │  • 실제 차단은 L3 runtime cap에 위임                    │
        └──────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌──────────────────────────────────────────────────────┐
        │ L3 Runtime Caps — GUC 기반                            │
        │  • statement_timeout = 30s     (L0에서 SET)            │
        │  • lock_timeout = 5s                                   │
        │  • idle_in_transaction_session_timeout = 60s           │
        │  • temp_file_limit = '1GB'                             │
        │  • app-level row_limit = 1000 (truncate + 알림)        │
        │  • 위반 시: ⚠️ "timeout/limit 적중, partial result"    │
        └──────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌──────────────────────────────────────────────────────┐
        │ L4 Audit (append-only SQLite)                         │
        │  • events 외에 audit 테이블 별도 (§3.3)                 │
        │  • 일 회전 + retention 90일                             │
        │  • /audit me  → 본인 최근 50건                          │
        │  • /audit export → CSV DM                              │
        │  • hash chain / 외부 sink → V2 백로그                   │
        └──────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌──────────────────────────────────────────────────────┐
        │ L5 Rate Limit (token bucket)                          │
        │  • per-user:  LLM 20/min, DB 60/min                   │
        │  • per-guild: V2 (V1은 DM-only)                        │
        │  • Discord API rate limit도 별도 어댑터 책임           │
        └──────────────────────────────────────────────────────┘
                              │
                              ▼
                          실행 / 응답
```

### 5.1 함수 denylist (V1, catalog 부팅 시 OID 수집)

| 카테고리 | 항목 | 사유 |
|---|---|---|
| **DoS / sleep** | `pg_sleep`, `pg_sleep_for`, `pg_sleep_until` | RO 통과, lock hold |
| **Advisory lock** | `pg_advisory_lock(_shared)?`, `pg_advisory_xact_lock(_shared)?`, `pg_try_advisory_*` | 자원 hog |
| **Backend control** | `pg_terminate_backend`, `pg_cancel_backend` | operational |
| **Logging / signal** | `pg_log_backend_memory_contexts`, `pg_reload_conf`, `pg_rotate_logfile` | 운영 부수효과 |
| **WAL / replication** | `pg_create_*_replication_slot`, `pg_drop_replication_slot`, `pg_logical_emit_message`, `pg_switch_wal`, `pg_backup_start/stop`, `pg_create_restore_point`, `pg_promote`, `pg_wal_replay_pause/resume` | 상태 변경 |
| **Server file / LO** | `pg_read_file`, `pg_read_binary_file`, `pg_ls_*`, `lo_import`, `lo_export`, `lo_create`, `lo_unlink`, `lo_truncate`, `lo_open`, `lo_from_bytea`, `lo_put`, `lowrite` | FS / large object bypass |
| **Egress / FDW** | `dblink_exec`, `dblink`, `dblink_connect`, `postgres_fdw_disconnect*` | 외부 egress |
| **Stats / maintenance** | `pg_restore_relation_stats`, `pg_clear_*_stats`, `brin_summarize_*`, `gin_clean_pending_list` | optimizer 조작 |
| **Configuration** | `set_config('...', ..., false)` (session-wide), `pg_reload_conf` | session 설정 우회 |
| **Misc** | `pg_export_snapshot`, `pg_log_standby_snapshot` | 자원 보유 |

Extension 함수 (`PostGIS`, `pgcrypto`, `http`, `plpython`, `plperlu`) 는 환경별 inventory 후 추가.

### 5.2 self-test 7개 공격 (회귀 — CI 차단 기준)

| # | 입력 | 기대 결과 |
|---|---|---|
| 1 | `DROP TABLE users` | L1 block (DDL) |
| 2 | `; DELETE FROM users; --` (multi-stmt) | L1 block (multi-statement) |
| 3 | `WITH x AS (INSERT INTO t VALUES (1) RETURNING *) SELECT * FROM x` | L1 block (DML in CTE, sqlglot walk) |
| 4 | `SELECT pg_sleep(10000)` | L1 block (function denylist, OID match) |
| 5 | `EXPLAIN (FORMAT JSON) SELECT * FROM huge_table` → estimated >100M rows | L2 cost gate → user confirm |
| 6 | `SELECT * FROM table_50k` (50,000 rows) | L3 row_limit 1000 → truncate |
| 7 | 분당 100 호출 | L5 rate limit |

추가 (V2 backlog):
- `SELECT public.pg_sleep(60)` (schema-qualified bypass) → catalog-driven OID match으로 V1에서도 차단 가능. 회귀 추가 권장.
- `COPY foo TO PROGRAM 'curl ...'` → L1 block (COPY 전면 차단)
- writable role probe: `/connect` 로 writable account 등록 시도 → RO probe 거부.

### 5.3 어필 — 5가지 무기 (v1과 동일, GIF 콘텐츠 업데이트)

1. `/safety` 슬래시 명령 — 현재 보호 레이어 embed.
2. 레드팀 GIF 30초 — 7개 공격 시도가 각각 다른 레이어에 막히는 영상.
3. 공개 audit log JSON 샘플 — "이렇게 기록됩니다".
4. `/safety self-test` — 본인이 본인에게 7개 공격 → "녹색 7/7" 스크린샷.
5. 벤치마크 — `lang2sql` vs *"그냥 LLM에 connection 던지기"* 정량 비교.

---

## 6. 새 레포 레이아웃 — Evolve in place

v1의 "wipe and rebuild" 어조는 폐기. 실제 작업은 **PR-0(정리) + 5개 PR(점진 추가)** 로 진행. (codebase-reality 결론.)

### 6.1 보존 / 포팅 / 삭제

| 분류 | 대상 | LOC | 메모 |
|---|---|---|---|
| **KEEP-AS-IS** | `src/lang2sql/semantic/*` | ~670 | 순수 in-memory. `dialect="postgres"` 기본값만 변경 (`sql_composer.py:19`). |
| | `src/lang2sql/harness/types.py` | ~155 | `core/types.py` 로 이동(rename)만. |
| | `src/lang2sql/skills/registry.py` | ~101 | 그대로. |
| | `src/lang2sql/tools/{ask_user,show_plan}.py` | ~93 | harness intercept라 본문 더미. |
| | `tests/test_semantic_layer.py`, `test_harness_core.py`, `test_skills_registry.py` | ~1,054 | 회귀 안전망. |
| | `src/lang2sql/integrations/llm/openai_.py`, `anthropic_.py` | ~362 | 그대로. NIM은 wrapper. |
| | `tui-go/*` | — | freeze. |
| **PORT-WITH-MINOR-CHANGES** | `src/lang2sql/harness/{tool,loop,system_prompt}.py` | ~575 | ctx 인자 추가. 본체 70% 그대로. |
| | `src/lang2sql/tools/{run_sql,explore_schema,profile_table,define_*,search_semantic,write_sql,visualize,load_skill}.py` | ~1,200 | ctx 사용 + run_sql만 safety 호출 추가. |
| | `src/lang2sql/integrations/db/sqlalchemy_explorer.py` | ~128 | async 전환 (asyncpg) + GUC SET. |
| | `src/lang2sql/core/ports.py` | ~101 | port 5개 추가 (secrets/session_store/audit/hook/persistent_view_store). |
| | `cli/commands/serve.py` | ~393 | `frontends_dev/serve.py` 로 이동. NDJSON 그대로 (Go TUI 호환). |
| | `cli/commands/agent.py` | ~111 | `frontends_dev/cli.py` 로 이동. |
| **REWRITE** | `src/lang2sql/harness/session.py` | ~215 → ~250 | 6-event write-through로 교체. |
| | `src/lang2sql/harness/builder.py` | ~88 → ~100 | `ContextConcierge` 로 승격. |
| **NEW** | `src/lang2sql/safety/*` (statement_gate, cost_gate, runtime, audit, rate_limit, ro_probe, self_test) | ~900 | |
| | `src/lang2sql/tenancy/*` (concierge, tenant_registry, explorer_cache, session_queue, encrypted_store, persistent_view_store) | ~700 | |
| | `src/lang2sql/discord/*` (bot, commands/*, session_router, streaming, interactive, render, permissions, recovery) | ~1,500 | |
| | `src/lang2sql/adapters/llm/nvidia_nim.py`, `adapters/db/postgres_explorer.py`, `adapters/secrets/encrypted_sqlite.py`, ... | ~600 | |
| | `tests/{safety,discord,tenancy}/*` | ~1,200 | |
| **DELETE** | `src/lang2sql/tui/*` (Python Textual + widgets) | ~1,400 | Discord가 1급. |
| | `src/lang2sql/{components,flows,viz,interface,utils}/*`, `integrations/{embedding,vectorstore,loaders,chunking,catalog}/*` | ~5,000 | V1에 RAG/구 파이프라인 없음. |
| | `src/lang2sql/integrations/llm/{gemma_,gemini_,bedrock_,azure_,huggingface_,ollama_}.py` | ~1,000 | gemma 등 백버너로 보관 또는 삭제. |
| | `cli/commands/{tui,init,quary,run_streamlit}.py` | ~350 | |
| | `tests/test_{components,flows,integrations}_*`, `test_tools_code_agent.py` | ~1,500 | 동반 삭제. |

### 6.2 최종 트리 (PR-5 끝난 시점)

```
lang2sql/
├── README.md
├── pyproject.toml
├── .env.example
│
├── src/lang2sql/
│   │
│   ├── core/                      # 순수 타입 + 포트
│   │   ├── types.py               # 기존 harness/types.py 이동
│   │   ├── identity.py            # Principal, GuildRole (신규)
│   │   ├── safety_types.py        # SafetyVerdict, Budget, RateBucket (신규)
│   │   └── ports/
│   │       ├── llm.py             # 기존 일부
│   │       ├── explorer.py        # async 전환
│   │       ├── tool.py            # ctx
│   │       ├── secrets.py         # 신규
│   │       ├── session_store.py   # 신규
│   │       ├── audit.py           # 신규
│   │       ├── persistent_view_store.py  # 신규
│   │       └── hook.py            # 기존
│   │
│   ├── harness/                   # kernel
│   │   ├── context.py             # HarnessContext (신규)
│   │   ├── session.py             # 6-event write-through (재작성)
│   │   ├── loop.py                # 기존 70% 보존
│   │   ├── system_prompt.py       # 기존, per-turn 유지
│   │   ├── tool_registry.py       # ctx 주입 (개명)
│   │   └── prompts/
│   │
│   ├── semantic/                  # 그대로 (dialect 기본값 변경)
│   │
│   ├── safety/                    # ★ 신규
│   │   ├── statement_gate.py
│   │   ├── cost_gate.py
│   │   ├── runtime.py
│   │   ├── audit.py
│   │   ├── rate_limit.py
│   │   ├── ro_probe.py
│   │   └── self_test.py
│   │
│   ├── tools/                     # ctx-aware
│   │   ├── explore_schema.py
│   │   ├── run_sql.py             # safety 호출 추가
│   │   ├── write_sql.py           # (compose만, 이름 유지 — devils-advocate 검증)
│   │   ├── define_metric.py
│   │   ├── define_dimension.py
│   │   ├── define_relationship.py
│   │   ├── search_semantic.py
│   │   ├── profile_table.py
│   │   ├── ask_user.py
│   │   ├── show_plan.py
│   │   ├── visualize.py
│   │   ├── explain_query.py       # 보존, V1 메뉴에 노출
│   │   └── load_skill.py
│   │
│   ├── skills/                    # 기존
│   │
│   ├── tenancy/                   # ★ 신규
│   │   ├── concierge.py
│   │   ├── tenant_registry.py
│   │   ├── explorer_cache.py
│   │   ├── session_queue.py
│   │   ├── encrypted_store.py
│   │   └── persistent_view_store.py
│   │
│   ├── discord/                   # ★ 1급 frontend (신규)
│   │   ├── bot.py
│   │   ├── commands/
│   │   │   ├── connect.py
│   │   │   ├── grant_readonly.py
│   │   │   ├── connections.py
│   │   │   ├── safety.py
│   │   │   ├── audit.py
│   │   │   ├── model.py
│   │   │   ├── reset.py
│   │   │   ├── retry.py
│   │   │   └── help.py
│   │   ├── session_router.py      # V1: DM-only
│   │   ├── streaming.py           # throttled message edit
│   │   ├── interactive.py         # persistent View
│   │   ├── render.py              # PNG 페이지네이션
│   │   ├── permissions.py
│   │   └── recovery.py            # 부팅 시 persistent_views reattach
│   │
│   ├── adapters/                  # outbound
│   │   ├── llm/
│   │   │   ├── openai_.py         # 기존
│   │   │   └── nvidia_nim.py      # 신규
│   │   ├── db/
│   │   │   └── postgres_explorer.py  # 기존 sqlalchemy_explorer 진화
│   │   ├── secrets/
│   │   │   └── encrypted_sqlite.py
│   │   ├── session_store/
│   │   │   └── encrypted_sqlite.py
│   │   └── audit_sink/
│   │       └── sqlite.py
│   │
│   └── frontends_dev/             # 부수
│       ├── cli.py                 # 기존 agent.py 이동
│       └── serve.py               # 기존 serve.py 이동 (Go TUI 호환)
│
├── tui-go/                        # freeze
├── tests/
│   ├── (보존) test_semantic_layer.py, test_harness_core.py, test_skills_registry.py
│   ├── safety/                    # 7개 self-test + 회귀
│   ├── discord/                   # mock 기반
│   └── tenancy/
└── docs/
    ├── discord_first_redesign.md       # v1 보존
    ├── discord_first_redesign_v2.md    # ← 본 문서
    ├── DB_ROBUSTNESS.md                # ★ trust page
    ├── DISCORD_ONBOARDING.md           # 사용자 가이드
    └── DEPLOY.md
```

---

## 7. 마이그레이션 — PR-0 + 5주 plan

```
PR-0 ─ 정리 (0.5주)                                       [-7,700 LOC]
   • src/lang2sql/tui/*, components/, flows/, viz/,
     interface/, utils/, 미사용 integrations/, 옛 cli/
     명령들, 동반 tests/ 삭제
   • python -c "import lang2sql" + pytest 통과 확인
   • 잔존: semantic/, harness/, skills/, openai+anthropic 어댑터,
           기존 sqlalchemy_explorer, tui-go/, 보존 tests 3종

PR-1 ─ Kernel (Week 1)                                    [~400 LOC]
   • core/ports/* 정의 (5개 신규 포트 시그니처)
   • HarnessContext, ctx-aware Tool 시그니처
   • harness/{tool_registry,loop,system_prompt} 시그니처 갈이
   • Session 임시 in-memory (PR-3에서 영속화)
   • ToolResult canonical shape 합의
   • frontends_dev/cli.py 로 검증

PR-2 ─ Safety (Week 2, 모두 *경고 모드* 포함)              [~900 LOC]
   • statement_gate (sqlglot AST + function denylist OID)
   • runtime (5개 GUC SET, temp_file_limit '1GB' 단위)
   • cost_gate (EXPLAIN multi-metric, 경고+confirm 모드)
   • audit (sqlite sink)
   • ro_probe (catalog 쿼리)
   • self_test 7개 + tests/safety/ (CI gate)
   • run_sql 도구가 safety 통과시키도록 ~20 LOC 추가

PR-3 ─ Async + Tenancy + Persistence (Week 3)             [~1,400 LOC]
   • DBExplorerPort async 전환 + asyncpg 어댑터
   • 모든 도구 async 호환 (대부분 자동, 일부 to_thread)
   • encrypted_sqlite (AES-GCM secrets)
   • SessionStore 6-event write-through + iter_active
   • PersistentViewStore (신규)
   • tenant_registry + explorer_cache(async LRU)
   • session_queue (per-session FIFO)
   • ContextConcierge

PR-4a ─ Discord onboarding (Week 4 전반)                  [~700 LOC]
   • bot 진입 + setup_hook (persistent View 재등록)
   • /connect Modal (5필드 connection string) + 제출 처리
   • /grant-readonly, /test, /connections, /use, /disconnect
   • Principal/Policy 기본
   • DM-only session_router
   • recovery.py (events 마지막=tool_started → run_interrupted,
                  persistent_views reattach)

PR-4b ─ Discord product (Week 4 후반)                     [~800 LOC]
   • streaming (토큰 → throttled message.edit 1s)
   • interactive (ask_user/show_plan → persistent View buttons)
   • render (PNG 페이지네이션, Discord 한도 인지)
   • /safety, /audit, /model, /reset, /retry, /help
   • cost_gate를 *차단 모드*로 승격 옵션 추가

PR-5 ─ Polish + Appeal (Week 5)                           [~300 LOC]
   • /safety self-test 자동 데모 GIF
   • README 갱신
   • DB_ROBUSTNESS.md (trust page)
   • DEPLOY.md (Oracle Cloud / fly.io)
   • benchmark (vs "naive LLM SQL")
   • NIM contract test 통과 후 /model에 노출
```

총 ~4,500 LOC 신규 + ~600 LOC 수정, ~7,700 LOC 삭제. 5.5주 1인 풀타임. Week 4 분할로 v1의 과적재 해소.

각 PR은 별 브랜치 (`feature/pr-{N}-*`), 직전 PR 머지 후 다음 시작.

---

## 8. 차트 페이지네이션 (Discord 한도 인지)

```
Result rows → discord/render.py
                │
                ├─ 50 rows 이하  → embed 텍스트 1개 (4096자 한도 체크)
                ├─ 500 rows 이하 → matplotlib + Pillow → PNG 1장
                ├─ > 500 rows    → 50 rows/페이지 PNG K장
                │
                ├─ K ≤ 5         → 단일 메시지에 첨부 K장 (8MB 한도 체크)
                ├─ K > 5         → persistent View (◀ Prev / Next ▶ / ⇩ CSV)
                │                   첫 페이지만 즉시 전송
                │                   메시지 ID + 페이지 상태 →
                │                     persistent_views 테이블 저장
                │                   봇 재시작 후에도 버튼 작동
                │
                └─ CSV 버튼      → 전체 CSV를 DM 첨부 (8MB 초과 시 분할)
```

차트(visualize) 도 동일 패턴 — facet 차트는 카테고리당 1장.

**한도 표** (v1엔 빠졌던 항목):
- content 2000자 / embed description 4096자 / embed 총 6000자
- 단일 메시지 첨부 8MB (무료 길드), 25MB (Nitro)
- 메시지당 임베드 최대 10개, 컴포넌트 최대 5 ActionRow

---

## 9. LLM 멀티 백엔드 — OpenAI (V1) + NVIDIA NIM (contract-tested)

```
adapters/llm/openai_.py        — 그대로
adapters/llm/nvidia_nim.py     — OpenAI(base_url=NIM_ENDPOINT, api_key=NIM_KEY)
                                  ~30 LOC wrapper
```

**V1 디폴트**: OpenAI `gpt-4.1-mini`. `/model` 슬래시 명령으로 전환 가능.

**NIM contract test (PR-2 또는 PR-5)**:
```
tests/llm_contract/test_nim_openai_parity.py
  • tool_calling: 동일 schema → 동일 호출 시그니처
  • streaming: text_delta chunk shape 호환
  • finish_reason: 'stop'|'tool_calls'|'length' 매핑
  • JSON mode: schema adherence
  통과 시 /model 노출, 실패 시 마스크
```

선택 가능한 모델 (V1 후보):

| Provider | 후보 |
|---|---|
| OpenAI | `gpt-4.1-mini` (디폴트), `gpt-4.1`, `o4-mini` |
| NVIDIA NIM (contract-test 통과 후) | `meta/llama-3.1-70b-instruct`, `mistralai/mixtral-8x22b-instruct-v0.1` |

비용 안내:
- OpenAI: per-token. `/model` 에서 mini 디폴트.
- NIM: NVIDIA 무료 크레딧 → 떨어지면 자비. `/model` 로 OpenAI 폴백 안내.
- per-user 토큰 캡은 V2 백로그 (`/audit` 에 누적 비용 표시는 V1.5).

**Provider family 전환** (OpenAI ↔ Anthropic): conversation 직렬화가 호환되지 않음. 사용자에게 *"대화 초기화 필요"* confirm 후 진행.

---

## 10. V1 명시적 제외 — V2+ 백로그

| 항목 | 사유 |
|---|---|
| 길드 채널·스레드 세션 | 데이터 노출 위험. allowlist + admin 승인 모델이 V2. |
| audit log hash chain / 외부 sink | V1 SOC2 친화 어조만 유지. 실제 hash chain은 V2. |
| 외부 secret manager (AWS SM / GCP SM / Vault) | V1은 로컬 암호 SQLite로 충분. |
| MySQL / SQLite / BigQuery 어댑터 | V1은 PostgreSQL 전용. |
| RAG / 벡터스토어 / 임베딩 | 본 제품은 schema-grounded NL→SQL. RAG는 V2 옵션. |
| Anthropic 어댑터 사용자 노출 | V1 디폴트는 OpenAI. 어댑터 코드는 보존만. |
| 다중 인스턴스 / Redis 세션 스토어 | 트라이얼은 단일 프로세스. V2 스케일링 시. |
| BQ cost gate (bytes_processed × $) | PG cost_gate가 먼저, BQ 어댑터 들어올 때 함께. |
| Components V2 (Discord 2025) | 모달은 변경 없음. message 컴포넌트 V2 migration은 V1 이후. |

---

## 11. Codex 리뷰에서 거부한 항목 (transparency)

본 v2는 Codex가 제기한 25개 지적 중 ~12개를 수용. 다음 항목은 **검증 후 거부**:

| Codex 지적 | 거부 사유 |
|---|---|
| **§1#4 vs §1.3 "AES-GCM 모순"** | doc은 per-row 컬럼 암호 (secrets만), Codex는 SQLCipher 형 파일 단위 암호로 오독. v2 §1.3에서 추가 명확화. |
| **`write_sql.py` → `draft_sql.py` 개명** | `write_sql.py` 본문은 SQLComposer로 *생성*만 함. 실행은 `run_sql.py`. Codex는 파일을 안 읽고 이름으로 추론. 이름 유지. |
| **§0 5단 타이브레이커** (권한→정확성→무결성→UX→맥락) | 솔로 트라이얼에 과한 product framing. 4축 (DB 무결성·의미적 정확성·Discord UX·맥락)으로 절충. |
| **Hermes-style write-through 통째 부정** | 사용자 명시 요구사항. 단, *"스트림 청크 복구"* 부분만 거부 — 6 event types로 단순화. |
| **EXPLAIN cost gate가 row estimate만으론 부족 → 차단** | trial V1에 stale stats까지 잡으라는 건 과함. *차단이 아니라 경고+사용자 confirm* 으로 절충, 실제 차단은 L3 runtime cap에 위임. |
| **NIM "OpenAI 호환" 검증 안 됨 → 사용 금지** | contract test 통과 후 experimental 노출로 절충. 전면 금지는 아님. |
| **SQLite single-writer "1000 유저" 비현실적** | trial 트래픽은 두 자릿수. V2 스케일 시점 항목으로 명시. |
| **wipe vs "semantic 이식" 모순** | "이식"은 트리 비우고 자산 복사라는 자연 해석. 그러나 v2에선 *evolve in place* 로 어조 자체를 변경 → 모순 자체 소멸. |

---

## 12. 잔여 결정 사항

(Week 1 착수 전 답이 있으면 좋은 항목)

1. **첫 배포 길드** — V1은 DM-only라 길드 선택은 봇 초대받을 수 있는 길드만 필요. 가짜연구소 디스코드 또는 본인 테스트 길드?
2. **세션 retention** — 비활성 세션 보존 기간. v2 §3.2 가정: **30일 active, 30~90일 archive, 90일 후 삭제**. 변경 필요 시 알려주세요.
3. **audit retention** — 90일 동일. compliance 관점에서 더 길게? 별도 보존?
4. **NIM 디폴트 후보** — `llama-3.1-70b-instruct` vs `mixtral-8x22b-instruct-v0.1`. (Mixtral이 tool-calling 안정성 우위로 알려져 있음 — contract test로 결정.)
5. **Cost gate 차단 모드 승격 시점** — V1은 경고만. PR-5에서 차단 옵션 추가? V2로?
6. **`/audit export` 형식** — CSV만? JSON 옵션도?
7. **`/reset` 시 audit 보존** — 기본 보존 권장. 사용자에게 명시.

위 7개는 Week 1 코드에 직접 영향 없음.

---

## 13. 한 줄 요약

> **Evolve in place. 4축 타이브레이커로 의미적 정확성을 1급화한다. Discord plataforma 한도(Modal 5필드, password style 없음, Interaction 15분, autocomplete 3s, persistent view)를 §1.4에 박는다. PostgreSQL safety는 `SET TRANSACTION READ ONLY` 단독을 신뢰하지 않고, dedicated readonly role + 5 GUC + catalog-driven function denylist(OID) 3중으로 막는다. 세션은 6 event types만 write-through, 스트림 청크 복구는 폐기. V1은 DM-only — 채널/스레드는 권한 모델 완성 후 V2.**

— end —
