# Lang2SQL — Discord-First 재설계 명세

> **작성일**: 2026-05-18
> **결정자**: ryan@brain-crew.com
> **상태**: 골격 승인. §10 잔여 결정 항목 보완 후 Week 1 착수.
> **범위**: 현 `lang2sql/` 트리를 비우고 본 문서대로 새로 채운다.

---

## 0. 제품 한 줄과 타이브레이커

> **"Discord에서 쓰는 read-only · audit-by-default SQL 에이전트.
> DB는 절대 변하지 않고, 모든 쿼리는 예산/시간/행 한도 안에서 돈다.
> 대화 맥락은 끊겨도 영속된다."**

설계 충돌 시 우선순위:

1. **Discord UX가 단순한가?**
2. **DB는 안 깨지는가?**
3. **맥락은 보존되는가?**

이 3가지에 부정으로 답하는 어떤 추상화도 도입하지 않는다.

---

## 1. 확정된 기술 결정

| # | 항목 | 선택 | 근거 |
|---|---|---|---|
| 1 | Discord lib | **`discord.py` 2.x** | 가장 성숙·안정. 문서/예제 풍부. 비동기 native. |
| 2 | DB 엔진 타깃 (V1) | **PostgreSQL** | EXPLAIN·statement_timeout·RO role·sslmode 등 모든 safety 기법이 정직하게 동작. MySQL/SQLite/BigQuery는 V2 이후. |
| 3 | 세션 영속화 | **Hermes-style write-through** | 매 메시지·매 도구 호출/결과·매 pause·매 audit 항목을 즉시 디스크에 flush. 봇 재시작/배포/네트워크 단절 후 다시 붙어도 동일 맥락 복구. |
| 4 | 세션 + 자격증명 스토어 | **AES-GCM 암호화된 SQLite 단일 파일** | 트라이얼 단계 무료·무의존. JSON1으로 conversation 저장. 외부 secret manager는 V2 옵션. |
| 5 | LLM 백엔드 | **OpenAI + NVIDIA NIM 듀얼 어댑터** | NIM endpoint가 OpenAI 호환(`/v1/chat/completions`) → 어댑터 거의 그대로 재사용. 슬래시 명령 `/model` 로 유저 전환. |
| 6 | Go TUI | **유지 (개발 도구)** | Discord 불가 환경 fallback. `serve.py` NDJSON 인터페이스 유지. |
| 7 | 차트 출력 | **PNG 첨부 + 자동 페이지네이션** | matplotlib + Pillow. Discord 첨부 한도(무료 8MB/메시지, 임베드 10개)에 맞춰 잘라 보냄. |
| 8 | 호스팅 (트라이얼) | **소형 VPS** | §1.1 참조. Cloudflare Workers 부적합. |

### 1.1 호스팅 — "Cloudflare 5천원" 건에 대한 솔직한 답

`discord.py` 는 Discord WebSocket gateway에 **계속 붙어 있어야 하는 장기 실행 Python 프로세스**입니다. Cloudflare Workers의 edge runtime은 짧은 HTTP 요청-응답 모델이라 봇 본체를 못 올립니다. (D1/KV/R2 같은 backing store로는 활용 가능하지만 V1 범위 밖.)

**저렴·트라이얼 권장 옵션**

| 옵션 | 비용 | 메모 |
|---|---|---|
| **Oracle Cloud Always Free** | $0 (무기한) | ARM Ampere 4코어/24GB. 가성비 최강. 가입 시 카드 검증. |
| **fly.io shared-cpu-1x** | $0 ~ $5/월 | 256MB로 시작 가능. 한국에서 가까운 region(NRT/SIN). |
| **Hetzner CX11** | €4.5/월 (~6,500원) | 안정·빠름. 유럽 region. |
| **본인 PC + 24h on** | $0 | 데모 단계 충분. 동적 IP면 이주 권장. |

**비추**: Cloudflare Workers(런타임 비호환), Heroku 무료(폐지), Render 무료(60s sleep으로 봇 끊김).

### 1.2 "타깃 = 가짜연구소 디스코드?" 정리

질문하신 *"이 타깃이 가짜연구소 디스코드?"* 에 대해: 문서에서 쓴 "타깃"은 **지원할 DB 엔진 종류**(PG vs MySQL vs BQ)를 의미한 것이고, **봇이 초대될 디스코드 커뮤니티**와는 별개입니다.

- **DB 엔진 타깃**: PostgreSQL (확정)
- **배포 커뮤니티**: 가짜연구소 디스코드라면 그쪽 길드에 봇을 초대하는 별개 결정. V1 코드는 어떤 길드에든 동작하도록 작성.

### 1.3 "자격증명 저장 위치" 풀이

`/connect` 로 입력받는 **DB 사용자명·비밀번호를 어디에 저장하느냐**의 질문입니다.

| 옵션 | 비용 | 강도 | 추천 시점 |
|---|---|---|---|
| **로컬 AES-GCM SQLite** | $0 | 마스터키(env) + per-row IV | **V1 — 채택** |
| AWS Secrets Manager | ~$0.40/secret/월 | 강함 | 다중 인스턴스·SOC2 |
| GCP Secret Manager | ~$0.06/secret/월 | 강함 | GCP 환경일 때 |
| HashiCorp Vault | self-host | 강함 | 사내 운영 |

V1은 **로컬 암호화 SQLite**. 마스터키는 `LANG2SQL_MASTER_KEY` env로 주입. 키 분실 시 secrets만 무효화되고 conversation/audit은 그대로 (분리 저장).

---

## 2. 상위 아키텍처

```
                          ┌──────────────────────────────┐
                          │      DISCORD GATEWAY         │
                          │  - DM (private analytics)    │
                          │  - Guild channel / thread    │
                          │  - Slash commands / modals   │
                          └───────────────┬──────────────┘
                                          │ events
                                          ▼
┌──────────────────────────────────────────────────────────────────────┐
│                       DISCORD ADAPTER  (1급)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────────┐  │
│  │ Onboarding   │  │ SessionRouter│  │ Streaming Renderer        │  │
│  │  /connect    │  │  key 결정    │  │  토큰 → message edits      │  │
│  │  modal+test  │  │              │  │  rows  → PNG (페이지)      │  │
│  └──────────────┘  └──────────────┘  └───────────────────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────────┐  │
│  │ Interactive  │  │ Permissions  │  │ DiscordRateLimit          │  │
│  │  ask_user /  │  │ guild-admin/ │  │  message edit throttle    │  │
│  │  show_plan   │  │ owner/user   │  │  per-user / per-guild     │  │
│  │  → buttons   │  │              │  │                           │  │
│  └──────────────┘  └──────────────┘  └───────────────────────────┘  │
└───────────────────────────┬──────────────────────────────────────────┘
                            │ ctx = ContextConcierge.build(session_key, principal)
                            ▼
┌──────────────────────────────────────────────────────────────────────┐
│                        TENANCY LAYER                                  │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────────────┐ │
│  │TenantRegistry│ │ExplorerCache │ │ EncryptedStore (AES-GCM)     │ │
│  │key→DBSpec    │ │LRU engines   │ │ secrets + conversation +     │ │
│  │              │ │              │ │ audit (단일 SQLite)           │ │
│  └──────────────┘ └──────────────┘ └──────────────────────────────┘ │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  ContextConcierge — session_key + principal → HarnessContext │   │
│  └──────────────────────────────────────────────────────────────┘   │
└───────────────────────────┬──────────────────────────────────────────┘
                            ▼ ctx
┌──────────────────────────────────────────────────────────────────────┐
│                        HARNESS KERNEL                                 │
│   agent_loop · system_prompt(per turn) · ToolRegistry(ctx 주입)       │
│   Session(live layer + pending_call + write-through) · Hooks(pub/sub) │
└──────┬─────────────────────┬──────────────────┬──────────────────────┘
       │ ports               │                  │
       ▼                     ▼                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    SAFETY LAYER  (제품의 moat)                        │
│  L0 connect (RO role, TLS)  →  L1 stmt gate (sqlglot AST)             │
│  L2 cost gate (EXPLAIN)     →  L3 runtime (timeout/row/byte)          │
│  L4 audit (append-only)     →  L5 rate limit (token bucket)           │
└──────┬─────────────────────┬──────────────────┬──────────────────────┘
       ▼                     ▼                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     OUTBOUND ADAPTERS                                 │
│  LLM (openai / nvidia-nim)  ·  DB (sqlalchemy-postgres)               │
│  Secrets (encrypted-sqlite) ·  SessionStore (encrypted-sqlite)        │
│  AuditSink (sqlite, file)                                             │
└──────────────────────────────────────────────────────────────────────┘
```

규칙: 화살표는 **안쪽으로만**. Kernel/Safety는 어댑터를 import하지 않는다. 새 frontend·새 LLM·새 DB·새 session store는 어댑터 한 장 추가로 끝.

---

## 3. 세션 전략 — Hermes-style 영속화

### 3.1 session_key 정책

| Discord 컨텍스트 | session_key | DB credential 출처 | 멤버 가시성 | 용도 |
|---|---|---|---|---|
| **봇과의 DM** | `dm:{user_id}` | 유저 본인의 비밀저장소 항목 | 본인만 | **개인 분석 (기본 경로)** |
| **길드 채널(메인)** | `chan:{guild_id}:{channel_id}` | 길드 어드민이 등록한 공용 DB | 채널 멤버 전원 | 팀 공용 대시보드 질의 |
| **길드 스레드** | `thr:{guild_id}:{channel_id}:{thread_id}` | 상위 채널과 동일 | 스레드 참여자 | 병렬 조사 (1조사 = 1스레드) |

**원칙**:
- 민감 DB 자격증명은 **DM에서만 받음**. 채널 메시지는 영구히 history에 남고 다른 멤버에게 보임.
- 위 3가지 외의 session_key는 사용 금지. 변형이 늘면 "누가 무엇을 보는지" 추적 불가.
- **principal** (= 누가 보낸 메시지인가) 은 session_key와 별개로 매 요청 기록. 공용 채널에서도 audit log에 *"이 쿼리는 누가 시켰는지"* 가 남음.

### 3.2 영속화 메커니즘 (write-through)

```
User msg ──▶ Discord adapter ──▶ session.append_message(msg)
                                      │
                                      ├─▶ in-memory state update
                                      └─▶ store.write(session_id, msg)   ← 동기, 즉시
                                              │
                                              ▼
                                  AES-GCM SQLite (append-only segment)

Tool call/result ──▶ same path, immediate flush
Pause(ask_user)   ──▶ pending_call snapshot, immediate flush
LLM stream delta ──▶ buffered in-mem, flush at chunk boundary
```

**보장**: 봇 프로세스가 임의 시점에 죽어도 *디스크에 마지막으로 flush된 상태까지는* 안전. 재시작 시:

1. `SessionStore.iter_active(since=now-30d)` 로 미완 세션 로드
2. `pending_call` 이 있는 세션은 *사용자 답을 기다리는 상태*로 복원
3. Discord 어댑터가 DM·채널·스레드별로 reattach
4. 사용자가 다음 메시지를 보내면 **끊김 없이 이어짐** — 이게 Hermes-style 핵심

**저장 모델** (SQLite 스키마):

```sql
-- 세션 메타
CREATE TABLE sessions (
  id            TEXT PRIMARY KEY,         -- session_key
  principal     TEXT NOT NULL,            -- 마지막 발화 유저
  kind          TEXT NOT NULL,            -- 'dm' | 'channel' | 'thread'
  db_spec_id    TEXT,                     -- secrets.id 참조
  created_at    TIMESTAMP NOT NULL,
  updated_at    TIMESTAMP NOT NULL,
  pending_call  TEXT,                     -- JSON | NULL
  closed_at     TIMESTAMP                 -- NULL = active
);

-- 메시지 append-only 로그
CREATE TABLE messages (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id  TEXT REFERENCES sessions(id),
  ts          TIMESTAMP NOT NULL,
  role        TEXT NOT NULL,              -- system|user|assistant|tool_result
  content     TEXT,                       -- JSON or text
  tool_calls  TEXT,                       -- JSON | NULL
  tool_call_id TEXT,
  principal   TEXT
);
CREATE INDEX ON messages(session_id, id);

-- 암호화 자격증명
CREATE TABLE secrets (
  id            TEXT PRIMARY KEY,         -- e.g. "user:123:default"
  owner         TEXT NOT NULL,            -- discord user id
  label         TEXT,                     -- "prod-pg" 같은 표시명
  ciphertext    BLOB NOT NULL,            -- AES-GCM
  iv            BLOB NOT NULL,
  tag           BLOB NOT NULL,
  created_at    TIMESTAMP NOT NULL,
  last_used_at  TIMESTAMP
);

-- 감사 로그 (append-only)
CREATE TABLE audit (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  ts          TIMESTAMP NOT NULL,
  session_id  TEXT,
  principal   TEXT,
  kind        TEXT,                       -- 'sql' | 'tool' | 'pause' | 'safety_block'
  payload     TEXT,                       -- JSON
  duration_ms INTEGER,
  status      TEXT                        -- 'ok' | 'error' | 'blocked'
);
```

### 3.3 동시성

```
전역 concurrency       = 무제한 (asyncio)
per-session            = FIFO 1 (같은 conversation에 동시 LLM 호출 금지)
per-user rate limit    = token bucket  (LLM 20/min,  DB 60/min)
per-guild rate limit   = token bucket  (DB 200/min)
LLM stream             = 세션마다 독립 (한 사용자가 폭주해도 다른 사용자 영향 X)
```

이 모델이면 **사용자 1000명도 단일 프로세스 처리 가능**. 한 유저가 폭주해도 다른 유저는 영향 없음.

---

## 4. DB 연결 온보딩 (Discord-native)

```
사용자                  Bot (DM)                  Tenancy Layer
  │                       │                             │
  │── /connect ──────────▶│                             │
  │                       │   Modal 출력:                │
  │                       │   ┌──────────────────┐      │
  │                       │   │ label: "prod-pg" │      │
  │                       │   │ host:            │      │
  │                       │   │ port: 5432       │      │
  │                       │   │ database:        │      │
  │                       │   │ user:            │      │
  │                       │   │ password: [hide] │      │
  │                       │   │ schema: (opt)    │      │
  │                       │   │ sslmode: require │      │
  │                       │   │ ☑ RO 계정인가요? │      │
  │                       │   └──────────────────┘      │
  │── submit ────────────▶│                             │
  │                       │── build url ────────────────│
  │                       │── encrypt (AES-GCM) ───────▶│ secrets.put
  │                       │── test SELECT 1 ───────────▶│ Explorer 임시
  │                       │── probe RO (BEGIN; CREATE TABLE __probe; ROLLBACK)
  │                       │   - 실패하면 ✅ RO 확정      │
  │                       │   - 성공하면 ⚠️ 경고 + 명시적 confirm
  │                       │── SHOW TABLES ──────────────│
  │                       │◀── ok, 17 tables ───────────│
  │◀── ephemeral embed ───│                             │
  │   ✅ Connected to     │                             │
  │   "prod-pg" (17 tbls) │                             │
  │   Try: "tables 보여줘"│                             │
  │                       │                             │
  │── "tables 보여줘" ───▶│                             │
  │                       │── agent_loop(ctx) ─────────▶│ kernel
```

**핵심 결정**:
- **Modal로만** 자격증명 입력 (슬래시 명령 인자로 URL 받지 않음) → 비밀번호가 채널 로그에 안 남음.
- **자동 RO 검증**: `BEGIN; CREATE TABLE __probe(x int); ROLLBACK;` 시도 → 실패하면 RO 확정, 성공하면 경고.
- **`db_url`은 절대 평문 저장 안 함**. AES-GCM 암호화 후 SQLite secrets 테이블에 저장.
- **여러 DB 등록 가능**: `/connections` 로 목록, `/use <label>` 로 활성 DB 전환, `/disconnect <label>` 로 삭제.

**관련 슬래시 명령**:

| 명령 | 위치 | 동작 |
|---|---|---|
| `/connect` | DM | Modal로 새 DB 등록 + 검증 |
| `/connections` | DM/Channel | 등록된 DB 목록 (label만) |
| `/use <label>` | DM | 활성 DB 전환 |
| `/disconnect <label>` | DM | 자격증명 삭제 |
| `/test` | DM | 현재 활성 DB SELECT 1 |
| `/safety` | Any | 현재 활성 보호 레이어 embed |
| `/safety self-test` | Any | 7개 공격 자가 검증 + 결과 embed |
| `/audit me` | Any | 본인 최근 50건 쿼리 |
| `/audit export` | DM | CSV DM 첨부 |
| `/model` | Any | OpenAI / NIM 모델 전환 |
| `/reset` | DM/Channel | 현 세션 conversation 초기화 (audit는 보존) |

---

## 5. DB 강건성 — Safety Layer (제품의 moat)

```
요청 ─▶ ┌──────────────────────────────────────────────────────┐
        │ L0 Connection                                         │
        │  • RO role 권장/검증 (CREATE TABLE 시도 → 실패해야 함)│
        │  • sslmode=require 강제 옵션                            │
        │  • 헬스체크 + pool recycle 30분                         │
        │  • dialect=postgres (V1 고정)                          │
        └──────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌──────────────────────────────────────────────────────┐
        │ L1 Statement Gate (sqlglot AST)                       │
        │  • 화이트리스트: SELECT, WITH, EXPLAIN, SHOW           │
        │  • 서브쿼리/CTE 내부도 검사 (regex 아님)               │
        │  • 위반 시: ❌ embed "blocked: DROP not allowed"       │
        │  • audit.kind = 'safety_block'                         │
        └──────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌──────────────────────────────────────────────────────┐
        │ L2 Cost Gate                                          │
        │  • EXPLAIN 먼저 → 예상 rows 추출                      │
        │  • 임계 초과(default: 1M rows) → show_plan            │
        │  • 사용자가 ✅ 누르면 진행, ❌ 누르면 취소              │
        │  • 본 단계는 *cost*만 검사, 권한은 L1 통과 후         │
        └──────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌──────────────────────────────────────────────────────┐
        │ L3 Runtime Caps                                       │
        │  • statement_timeout = 30s (configurable)             │
        │  • row_limit = 1000 (truncate + 사용자 알림)          │
        │  • 위반 시: ⚠️ "timeout @ 30s, partial 0 rows"        │
        └──────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌──────────────────────────────────────────────────────┐
        │ L4 Audit (append-only)                                │
        │  • {ts, principal, session_id, sql, rows, ms,         │
        │     status, error?, safety_path}                      │
        │  • SQLite, 일 단위 로그 회전, /audit export CSV        │
        └──────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌──────────────────────────────────────────────────────┐
        │ L5 Rate Limit (token bucket)                          │
        │  • per-user:  LLM 20/min, DB 60/min                   │
        │  • per-guild: DB 200/min                              │
        │  • 위반 시: friendly "잠시 후 다시 시도, 남은 12s"      │
        └──────────────────────────────────────────────────────┘
                              │
                              ▼
                          실행 / 응답
```

### 5.1 어필 — 5가지 무기

1. **`/safety` 슬래시 명령** — 현재 활성 보호 레이어를 embed로 보여줌. 마케팅 페이지가 봇 안에 있는 셈.
2. **레드팀 자체 시연 GIF** — `DROP TABLE`, `; DELETE`, `pg_sleep(10000)`, `SELECT * FROM huge_table` 4가지를 시도하면 4가지 방식으로 막히는 30초 영상. README 첫 화면.
3. **공개 audit log 샘플** — "이 쿼리는 이렇게 기록됩니다" JSON. SOC2/ISO27001 친화 메시지.
4. **`/safety self-test`** — 봇이 자기 자신에게 7개 공격을 시도하고 결과를 embed로 출력. 운영자가 정기 실행 → "녹색 7/7" 스크린샷을 README에 박음.
5. **벤치마크 페이지** — `lang2sql` vs *"그냥 LLM에 connection 던지기"*. 동일 적대적 10개 프롬프트 대결: 우리 10/10 차단, 비교군 N개 실행. 정량 비교가 가장 강한 어필.

### 5.2 self-test 7개 공격 (Week 2 tests/safety/ 에 위치)

| # | 입력 | 기대 결과 |
|---|---|---|
| 1 | `DROP TABLE users` | L1 block |
| 2 | `; DELETE FROM users; --` (SQL injection in arg) | L1 block |
| 3 | CTE 안에 INSERT (`WITH x AS (INSERT ...) SELECT...`) | L1 block |
| 4 | `SELECT pg_sleep(10000)` | L3 timeout 30s |
| 5 | `SELECT * FROM huge_table` (수십억 rows) | L2 cost gate confirm |
| 6 | row 50,000개 반환 | L3 row_limit truncate |
| 7 | 분당 100회 호출 | L5 rate limit |

---

## 6. 새 레포 레이아웃

```
lang2sql/
├── README.md                      # Discord-first pitch + safety GIF
├── pyproject.toml
├── .env.example                   # LANG2SQL_MASTER_KEY, DISCORD_TOKEN, ...
│
├── src/lang2sql/
│   │
│   ├── core/                      # 순수 타입 + 포트
│   │   ├── types.py               # Message/ToolCall/ToolResult/Event
│   │   ├── identity.py            # Principal, GuildRole
│   │   ├── safety_types.py        # SafetyVerdict, Budget, RateBucket
│   │   └── ports/
│   │       ├── llm.py
│   │       ├── explorer.py        # capabilities() 추가
│   │       ├── tool.py
│   │       ├── secrets.py
│   │       ├── session_store.py
│   │       ├── audit.py
│   │       └── hook.py
│   │
│   ├── harness/                   # kernel
│   │   ├── context.py             # HarnessContext
│   │   ├── session.py             # Session + pending_call + write-through
│   │   ├── loop.py                # agent_loop (async gen)
│   │   ├── system_prompt.py       # per-turn rebuild
│   │   ├── tool_registry.py       # ctx 주입
│   │   └── prompts/
│   │
│   ├── semantic/                  # 기존 자산 이식 (그대로)
│   │
│   ├── safety/                    # ★ moat
│   │   ├── statement_gate.py      # sqlglot AST
│   │   ├── cost_gate.py           # EXPLAIN → budget
│   │   ├── runtime.py             # timeout / row / bytes
│   │   ├── audit.py               # append-only logger
│   │   ├── rate_limit.py          # token bucket
│   │   ├── ro_probe.py            # RO 검증
│   │   └── self_test.py           # /safety self-test 7개
│   │
│   ├── tools/                     # ctx-aware
│   │   ├── explore_schema.py
│   │   ├── run_sql.py             # → safety 통과 후 실행
│   │   ├── write_sql.py
│   │   ├── define_metric.py
│   │   ├── define_dimension.py
│   │   ├── define_relationship.py
│   │   ├── search_semantic.py
│   │   ├── ask_user.py
│   │   ├── show_plan.py
│   │   ├── visualize.py           # rows → PNG (페이지네이션 메타)
│   │   ├── explain_query.py
│   │   └── load_skill.py
│   │
│   ├── skills/                    # SkillRegistry (현재 자산 이식)
│   │
│   ├── tenancy/                   # 멀티유저
│   │   ├── concierge.py           # ContextConcierge.build()
│   │   ├── tenant_registry.py     # key → DBSpec
│   │   ├── explorer_cache.py      # LRU SQLAlchemy engines
│   │   ├── session_queue.py       # per-session FIFO
│   │   └── encrypted_store.py     # AES-GCM SQLite
│   │
│   ├── discord/                   # ★ 1급 frontend
│   │   ├── bot.py                 # discord.py 진입점
│   │   ├── commands/
│   │   │   ├── connect.py         # /connect Modal
│   │   │   ├── connections.py     # /connections /use /disconnect
│   │   │   ├── safety.py          # /safety, /safety self-test
│   │   │   ├── audit.py           # /audit me /audit export
│   │   │   ├── model.py           # /model (openai/nim)
│   │   │   ├── reset.py           # /reset
│   │   │   └── help.py
│   │   ├── session_router.py      # msg → session_key
│   │   ├── streaming.py           # 토큰 → message edit (throttle 1s)
│   │   ├── interactive.py         # ask_user → Button view
│   │   ├── render.py              # rows → PNG (페이지 분할)
│   │   ├── permissions.py         # guild admin 검사
│   │   └── recovery.py            # 부팅 시 active session reattach
│   │
│   ├── adapters/
│   │   ├── llm/
│   │   │   ├── openai_.py
│   │   │   └── nvidia_nim.py      # OpenAI-호환 엔드포인트
│   │   ├── db/
│   │   │   └── postgres_explorer.py
│   │   ├── secrets/
│   │   │   └── encrypted_sqlite.py
│   │   ├── session_store/
│   │   │   └── encrypted_sqlite.py
│   │   └── audit_sink/
│   │       └── sqlite.py
│   │
│   └── frontends_dev/             # 부수 (개발 도구)
│       ├── cli.py                 # 단발 질의 디버그
│       └── serve.py               # NDJSON (tui-go 유지용)
│
├── tui-go/                        # 유지 — Discord 불가 시 fallback
├── tests/
│   ├── safety/                    # 7개 공격 회귀 (CI 차단 기준)
│   ├── harness/
│   ├── discord/                   # discord mock
│   └── tenancy/
└── docs/
    ├── discord_first_redesign.md  # ← 본 문서
    ├── DB_ROBUSTNESS.md           # ★ trust page
    ├── DISCORD_ONBOARDING.md      # 사용자 가이드
    └── DEPLOY.md
```

---

## 7. 마이그레이션 — 5주 plan

```
Week 1 ─ Foundation                                         [PR-1]
   • core/ports/* 정의
   • HarnessContext + Session(pending_call) + Tool(ctx, **args)
   • agent_loop + per-turn system prompt
   • semantic/* 그대로 이식
   • frontends_dev/cli.py 로 kernel 검증

Week 2 ─ Safety Layer                                       [PR-2]
   • statement_gate (sqlglot)
   • runtime (timeout/row)
   • audit (sqlite sink)
   • ro_probe
   • self_test 7개 + tests/safety/ (CI gate)

Week 3 ─ Tenancy + Persistence (Hermes-style)               [PR-3]
   • encrypted_sqlite (AES-GCM)  — secrets + sessions 통합
   • SessionStore.write_through() + iter_active()
   • tenant_registry + explorer_cache
   • session_queue
   • ContextConcierge

Week 4 ─ Discord (product 본체)                              [PR-4]
   • bot 진입 + /connect Modal + onboarding 전 플로우
   • session_router (DM/channel/thread)
   • recovery.py (부팅 reattach)
   • streaming + interactive (Button view)
   • render (PNG 페이지네이션)
   • /safety, /audit, /connections, /use, /model

Week 5 ─ Polish + Appeal                                    [PR-5]
   • /safety self-test 자동 데모
   • README GIF + benchmark
   • DB_ROBUSTNESS.md trust page
   • cost_gate (EXPLAIN) — 마지막
   • DEPLOY.md (Oracle Cloud / fly.io)
```

각 PR은 별 브랜치(`feature/week{N}-*`)로 끊고, 직전 PR이 master에 머지된 후 다음 시작.

---

## 8. 차트 페이지네이션 (질문 #4 상세)

요구: 행이 많을 때 한 메시지에 다 넣으면 Discord 한도(첨부 8MB, 이미지 1장 권장)에 걸림.

```
DataEvent (rows=N) ──▶ discord/render.py
                          │
                          ├─▶ row 수에 따라 분할:
                          │     ≤ 50 rows   → 텍스트 embed 1개
                          │     ≤ 500 rows  → PNG table 1장
                          │     > 500 rows  → 50행씩 PNG 페이지 K장
                          │
                          ├─▶ K장이 ≤ 10이면: 한 메시지에 attachments=[png1..pngK]
                          │
                          └─▶ K > 10이면: View(buttons=[◀ Prev, Next ▶, ⇩ CSV])
                                            └─ 누를 때마다 message.edit(file=...)
                                            └─ CSV 버튼 = 전체 CSV를 DM 첨부

차트(시각화) 도 동일 패턴:
  - 단일 line/bar → 1장
  - facet (예: 카테고리별 시계열) → 카테고리당 1장, 페이지 버튼
```

`tools/visualize.py` 가 `VizSpec` 을 반환하고, Discord 어댑터의 `render.py` 가 spec → PNG 변환·페이지 분할 책임을 짐. **렌더링은 discord 레이어에만 존재** → 다른 frontend(TUI 등)는 spec을 받아 자기 방식으로 렌더링.

---

## 9. LLM 멀티 백엔드 — OpenAI + NVIDIA NIM

```
adapters/llm/openai_.py        — 기존 자산 그대로
adapters/llm/nvidia_nim.py     — base_url 만 https://integrate.api.nvidia.com/v1
                                  api_key 만 NVIDIA_API_KEY
                                  나머지는 OpenAI 클라이언트 그대로 재사용
```

**`/model` 명령** — Modal/Select로 모델 선택:

| Provider | 노출 후보 (디폴트는 V1에서 1개씩 고정) |
|---|---|
| OpenAI | `gpt-4.1`, `gpt-4.1-mini`, `o4-mini` |
| NVIDIA NIM | `meta/llama-3.1-70b-instruct`, `mistralai/mixtral-8x22b-instruct-v0.1`, `nvidia/llama-3.1-nemotron-70b-instruct` |

선택은 **세션 스코프** (DM 세션마다 다른 모델 가능). audit log에 `model_id` 기록.

비용 관점:
- OpenAI: per-token, 디폴트는 `gpt-4.1-mini` (저렴) 추천
- NIM: NVIDIA 계정 무료 크레딧 사용 → 떨어지면 자비. `/model` 로 OpenAI 폴백 유도.
- 향후 글로벌 per-user 토큰 캡 추가 가능 (Week 5+).

---

## 10. 잔여 결정 (Week 1 착수 전 답이 있으면 좋음)

1. **NIM 모델 디폴트** — 70B Llama vs Mixtral 8x22B? (Mixtral이 tool-calling 안정성↑)
2. **첫 배포 길드** — 가짜연구소 디스코드인가, 본인 테스트 길드인가? 부팅 시 길드 화이트리스트 적용 여부.
3. **세션 retention** — 비활성 세션을 며칠까지 보존? (현재 §3.2 가정: 30일 후 archive로 이동, 90일 후 삭제)
4. **audit retention** — 동일 질문, 별도 정책 필요? (compliance 관점)
5. **`/reset` 시 audit 보존 여부** — 기본 보존 권장(이미 기록된 건 지우면 안 됨), 사용자에게 명시.

위 5개는 Week 1 코드에 직접 영향 없으므로 그동안 답변 받으면 됩니다.

---

## 11. 한 줄 요약

> **kernel/safety 레이어를 hexagonal로 굳히고, Discord adapter와 SafetyLayer를 1급 영역으로 격상하고, Hermes-style write-through로 세션을 영속화한다. 그 외 모든 것은 어댑터 한 장.**

— end —
