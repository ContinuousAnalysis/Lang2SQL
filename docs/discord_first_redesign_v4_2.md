# Lang2SQL v4.2 — 컨셉과 아키텍처

> **작성일**: 2026-05-18
> **결정자**: ryan@brain-crew.com
> **상태**: 컨셉 확정 단계.

---

# Chap 1. 정체성

## 1.1 기존 오픈소스의 공통 한계

Vanna AI(~20k), Wren AI(~12k), SQLCoder(~3.8k) 같은 Text-to-SQL 오픈소스들은 *질문→SQL 파이프라인 자체* 는 이미 완성도 높음. 그러면 우리는 *그 위에 무엇을 더 얹을* 것인가가 정체성 결정.

기존 오픈소스의 **공통 약점**:

| 약점 | 기존 처리 |
|---|---|
| **DB 정보 완성도 낮으면 성능 급락** | Vanna: 학습 데이터 품질 의존 |
| **이전 대화·정의 못 기억** | 대부분 stateless |
| **비즈니스 맥락은 사람이 직접 정의** | Wren: MDL 수동 작성 |
| **단일 진실 모델의 조직 충돌** | 팀별 정의 차이 → 혼선 |

이 네 가지가 *실무에서 매우 중요* 한데 *비즈니스마다 다르기 때문에 정량 평가가 어려운 영역*. 그래서 오픈소스가 잘 안 건드림. 우리는 **이 네 가지를 한 번에 다루는 방향** 으로 차별화.

## 1.2 우리의 한 줄 컨셉

> **"문서로 비즈니스 맥락을 학습하고, 팀별로 시멘틱이 분기되고, 불완전한 DB에서도 답하고, 모든 정의·대화를 기억하는 오픈소스 분석 에이전트."**

기존 SQL 봇이 *"질문하면 SQL 만들어 줄게"* 였다면, 우리는 *"우리 회사 문서 넣어줘 → 학습할게 → 팀별로 다른 정의도 같이 들고 있을게 → 너희가 묻고 답을 받자 → 다 기억하고 다음에도 적용할게"*.

**Discord 는 Phase 1 인터페이스**. Slack/Teams/Web 도 같은 코어 위에서 어댑터로 추가 가능.

## 1.3 4기둥 (Pillars)

| 기둥 | 정체성 | 차별점 |
|---|---|---|
| **① 비즈니스 맥락 학습** | 문서→시멘틱 자동 추출 + 사용자 confirm | Wren MDL 은 수동. 우리는 *문서가 곧 진실의 출처* |
| **② DB 강건성** | 불완전 메타데이터를 *자동 보강* (description 자동 생성, FK 추정, 샘플 profile 등) | Vanna 는 *학습 데이터 의존*. 우리는 *DB가 깨끗하지 않아도 동작* |
| **③ Hermes 기억** | conversation + facts + preferences 영속 | 대부분 stateless |
| **④ 멀티 인터페이스** | Phase 1: Discord, Phase 2: Slack, Phase 3: Teams, Phase 4: Web | Discord 는 *어댑터 하나*, lock-in 없음 |

기둥 ② 가 **진짜 차별점**. *Vanna 의 한 포인트 한계 보완* 이 정체성. 부수적으로 **시멘틱 강건성 (팀별 다른 정의 federation)** 이 같이 들어옴.

## 1.4 타이브레이커 (충돌 시 우선순위)

1. **무결성 + 권한**
2. **의미적 정확성**
3. **UX 단순성**
4. **맥락 보존**

---

# Chap 2. 아키텍처

## 2.1 전체 흐름

```
   USER  (Phase 1: Discord)
       │
       ▼
┌─────────────────────────────────────────────────────────┐
│  Frontend 어댑터  (Phase 분리)                            │
│   discord/  slack/  teams/  web/  cli/                    │
└──────────────────┬──────────────────────────────────────┘
                   ▼
┌─────────────────────────────────────────────────────────┐
│  MEMORY + CONCIERGE                                      │
│                                                           │
│   기억 (★②) — 어디 저장 / 무엇을 가져올지 / 어떻게 만들지   │
│   문서 흡수 (★③) — 출처 × 해석                            │
│   시멘틱 federation (★④) — scope 분기                     │
│   DB 강건성 (★①) — 메타데이터 자동 보강                    │
│                                                           │
│   ContextConcierge — 위 넷을 묶어 ctx 조립                 │
└──────────────────┬──────────────────────────────────────┘
                   ▼ ctx
┌─────────────────────────────────────────────────────────┐
│  HARNESS  (조립된 단위, 하나의 덩어리)                     │
│   • LLM 클라이언트                                         │
│   • 도구들 (run_sql, ingest_doc, ...)                      │
│   • semantic (scope-aware + 보강된 상태)                    │
│   • session (영속 conversation + facts)                    │
│   • DB explorer                                            │
│   • audit logger                                           │
│                                                           │
│   agent_loop:                                              │
│     prompt = system_prompt(ctx)                            │
│       (effective semantic + facts + 보강된 schema 주입)     │
│     LLM 호출 → 도구 호출 → 다음 턴 또는 종료                 │
└──────────────────┬──────────────────────────────────────┘
                   ▼
┌─────────────────────────────────────────────────────────┐
│  OUTBOUND ADAPTERS                                       │
│   LLM · DB (asyncpg) · Storage (encrypted SQLite)         │
└─────────────────────────────────────────────────────────┘
```

★ 4개가 **확장 핵심** — Chap 3 에서.

## 2.2 디렉토리 구조

```
lang2sql/src/lang2sql/
├── core/                  ports (추상)
├── harness/               agent_loop, ctx
├── semantic/              types, scoped_layer, sql_composer
├── robustness/            ★① pipeline + enrichers/
├── memory/                ★② service + stores/recall/extractors/
├── ingestion/             ★③ pipeline + sources/extractors/
├── tools/                 ctx-aware (run_sql, ingest_doc, ...)
├── tenancy/               concierge, encrypted_secrets
├── frontends/             ★ Phase 분리 (discord/slack/teams/web/cli)
└── adapters/              llm, db, storage
```

---

# Chap 3. 확장성 — 4개의 ★ 패턴

V1엔 *가장 단순한 1개씩만* 구현, V1.5/V2 에서 *어댑터를 추가* 하는 방식. 비유 — *콘센트와 가전제품*. V1엔 LED 전구만 꽂혀 있어도, 콘센트 규격이 표준이라 V1.5에 선풍기·스마트조명 그냥 꽂으면 됨.

★ 4 패턴 모두 **우리 차별점**:

| ★ | 이름 | 역할 |
|---|---|---|
| ① | **Robustness 파이프라인** | DB 강건성 — 불완전 메타데이터 자동 보강 |
| ② | Memory service | Hermes 기억 — 3축 분리 |
| ③ | Ingestion pipeline | 문서 흡수 — 출처 × 해석 |
| ④ | Semantic federation | 시멘틱 강건성 — git-like 팀별 분기 |

## 3.1 ★ ① Robustness 파이프라인 — *우리의 진짜 차별점*

사용자가 자기 DB 를 봇에 등록할 때, *현실은 메타데이터가 항상 불완전* — description 빈 컬럼, FK 누락, 의미 모호한 컬럼명, 샘플 데이터 부재.

기존 오픈소스는 *이걸 사용자 숙제* 로 떠넘김 (Vanna: *"학습 데이터 잘 만드세요"*, Wren: *"MDL 잘 쓰세요"*).

**우리의 접근 — 봇이 *능동적으로 보강***. DB 정보가 비어 있으면 봇이 채워 넣음. 비유로 *번역가가 누락된 원문을 문맥으로 추정해 채워 가는* 작업.

확장 단위는 *enricher*. *description 자동 생성*, *FK 관계 추정*, *샘플 profile*, *컬럼명 패턴 → 쿼리 예시 우선순위*, *도메인 힌트 주입* 등을 *각각 enricher 한 종류* 로 추가.

V1엔 추상만 박힘 (enricher 0 개). V1.5 부터 *DescriptionGenerator* 같은 첫 enricher 가 들어오며 실 가치 발생. 새 enricher 추가는 *클래스 1개 + 줄에 끼우기* 로 끝.

**의미** — *Hint Vector* 같은 *DB 구조 강건성* 연구 결과를 그대로 enricher 로 plugin 가능. **연구실 코드가 곧 제품 layer**. *연구 친화* 아키텍처의 핵심.

## 3.2 ★ ② Memory service — Hermes 기억의 3축 분리

기억은 *하나의 큰 상자* 가 아니라 **세 가지 독립 기능의 조합**:

| 축 | 역할 |
|---|---|
| **Store** | facts 를 어디에 보관 (메모리/SQLite/PostgreSQL/Redis ...) |
| **Recall** | 현재 질문에 어떤 facts 를 가져올지 (전부/키워드/벡터/하이브리드) |
| **Extractor** | 새 facts 를 어떻게 만들지 (사용자 명령만 / LLM 자동 추출) |

각 축이 독립 진화. 예: V1.5 에 Store 만 SQLite 로 교체하는 게 *어댑터 1개 추가* 로 끝.

진화:

| 버전 | Store | Recall | Extractor |
|---|---|---|---|
| **V1** | 메모리 dict | 전부 주입 | `/remember` 명령만 |
| **V1.5** | SQLite | 키워드 매칭 | LLM 자동 추출 |
| **V2** | (같음) | 벡터 유사도 | + 충돌 해결 |
| **V2.5** | PostgreSQL | 하이브리드 | + 신뢰도 점수 |

## 3.3 ★ ③ Ingestion pipeline — 문서 → 시멘틱 레이어

문서가 들어오면 두 단계:

| 단계 | 역할 |
|---|---|
| **Source** | 어디서 문서를 가져오나 (파일/URL/Notion/Confluence/Google Drive) |
| **Extractor** | 문서에서 metric/dimension/rule 후보를 어떻게 뽑는가 (LLM/DDL 파싱/하이브리드) |

Source 와 Extractor 가 *매트릭스* 라서 *Source 1개 추가 = N 개 Extractor 와 자동 결합*.

사용자 흐름 (V1):
1. `/ingest` + 파일 첨부
2. 봇이 LLM 에 *"metric/dimension/rule 찾아줘"* 요청
3. Discord embed 로 후보 보여줌 + [✅ 모두 등록] [개별 선택] [❌ 취소]
4. ✅ → 시멘틱 레이어에 등록 (출처 문서 ID 보존)
5. 이후 *"이번 달 매출"* 질문 시 자동 적용

진화:

| 버전 | Sources | Extractors |
|---|---|---|
| **V1** | 파일 업로드 | LLM 추출 |
| **V1.5** | + URL | + DDL 파일 직접 파싱 |
| **V2** | + Notion / Confluence MCP | + 하이브리드 |
| **V2.5** | + GitHub / Google Drive MCP | + 청크 RAG |

## 3.4 ★ ④ Semantic federation — Git-like 시멘틱 분기

같은 회사라도 팀별로 *같은 용어, 다른 의미*:

| 용어 | 마케팅 | 프로덕트 | 파이낸스 |
|---|---|---|---|
| 활성 사용자 | 30일 내 로그인 | 7일 내 핵심 액션 | 유료 구독자 |
| 매출 | 광고 매출 | (관심 없음) | net (환불 차감) |

기존 *single truth* 모델은 *조직 현실과 충돌* — Wren 의 *"한 회사 한 MDL"* 은 팀별 합의 안 되면 깨짐.

### 우리의 해결 — git 처럼 브랜치를 가져감

```
                       ┌──────────────┐
                       │  main 브랜치  │ ← 회사 공통 (admin 정의)
                       └──────┬───────┘
                              │ 상속
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
       ┌──────────┐    ┌──────────┐    ┌──────────┐
       │#marketing│    │ #product │    │ #finance │
       │active_   │    │active_   │    │revenue=  │
       │user=30d  │    │user=7d   │    │net       │
       └──────────┘    └──────────┘    └──────────┘
              │
              │ 상속
              ▼
       ┌──────────────────┐
       │ thread 브랜치     │ ← 일시적 정의
       └──────────────────┘
```

**동작**: 가장 구체적인 scope 가 이김. `#marketing` 에서 *"활성 사용자 수"* → 채널 정의(30일) 적용. `#product` 에서 같은 질문 → 채널 정의(7일) 적용. **충돌 없음** — 각자 자기 scope 에서 산다.

사용자 흐름:

```
@user in #marketing:
   /define_metric active_user "30일 내 로그인"   → 채널 scope

admin:
   /define_metric --guild revenue "gross + tax"  → main 브랜치
   → finance 채널엔 자체 override 우선

@user in #marketing:
   /semantic show
   → "이 채널: active_user (override) 30일, revenue (main) gross+tax"
```

진화:

| 버전 | 기능 |
|---|---|
| **V1** | 3-scope (guild/channel/thread) 자동 resolution |
| **V1.5** | `/semantic diff`, `/semantic promote` (admin 승인), 충돌 알림 |
| **V2** | 외부 git 저장소 동기화 (semantic-as-code) |
| **V2.5** | branch fork & merge UI |

### 의미 — *시멘틱 강건성*

기둥 ② DB 강건성 과 *짝* 인 개념:
- **DB 강건성** (★①) — *불완전한 메타데이터* 에 견딤
- **시멘틱 강건성** (★④) — *조직별 다른 정의* 에 견딤

둘 다 *"현실의 messy함에 강건"*. **둘 다 Vanna/Wren 이 못 하는 영역**.

---

# Chap 4. 의견 정리

## 4.1 비교 — 기존 오픈소스 대비 위치

| 영역 | Vanna AI | Wren AI | SQLCoder | **Lang2SQL** |
|---|---|---|---|---|
| 자연어 → SQL | ✅ RAG | ✅ MDL | ✅ fine-tuned | ✅ RAG + 시멘틱 + harness |
| DB 직접 연결 | ✅ | ✅ | ✅ | ✅ |
| Semantic layer | ❌ | ✅ (수동 MDL) | ❌ | ✅ (**문서 자동 추출**) |
| **시멘틱 federation** | ❌ | ❌ | ❌ | ✅ (**git-like 3-scope**) |
| **DB 메타데이터 자동 보강** | ❌ | ❌ | ❌ | ✅ (**Robustness pipeline**) |
| 대화 기억 | ❌ | ❌ | ❌ | ✅ (Hermes) |
| Frontend 종류 | Web UI | Web UI | CLI | **Discord → Slack → Teams → Web** |
| 확장 모델 | 단일 아키텍처 | enterprise platform | 단일 LLM | **★ 4 패턴** |

**위치 요약**: *Vanna 의 자연어→SQL + Wren 의 시멘틱 + 우리만의 (문서 자동 추출 + git-like 팀 federation + DB 메타데이터 자동 보강 + Hermes 기억 + 멀티 인터페이스)*.

## 4.2 한 줄

> **"문서를 넣어 비즈니스 맥락을 학습시키고, 팀별로 시멘틱이 분기되고, *DB 메타데이터가 불완전해도 자동 보강* 하고, 모든 정의·대화를 기억하는 오픈소스 분석 에이전트."**

— end —
