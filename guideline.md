lang2sql/
├── __init__.py                         # public re-exports (Flow, Component, flows, components)
├── _version.py
│
├── core/                               # ✅ 외부 의존성 0% (절대 import 금지)
│   ├── __init__.py
│   ├── base.py                         # BaseComponent, BaseFlow (define-by-run 핵심 뼈대)
│   ├── types.py                        # 최소 타입(dataclass/typing): Table/Column/Result 등(강제 X, 참고용)
│   ├── exceptions.py                   # Lang2SQLError, ComponentError, IntegrationMissingError...
│   ├── hooks.py                        # TraceHook, Event, NullHook (관측/로깅 인터페이스)
│   ├── context.py                      # (선택) RunContext: dict wrapper (권장일 뿐 강제 X)
│   ├── registry.py                     # (선택) PluginRegistry + entry_points 로더 (retriever 100개 대비)
│   └── utils.py                        # 순수 유틸
│
├── components/                         # ✅ Lang2SQL이 제공하는 “부품 상자”
│   ├── __init__.py
│   ├── retrieval/
│   │   ├── __init__.py
│   │   ├── keyword.py                  # vstore 없는 기본 retriever (즉시 사용 가능)
│   │   ├── vector.py                   # vector retriever (실제 store는 integrations를 통해 주입)
│   │   ├── catalog.py                  # schema/catalog 기반 retriever
│   │   └── normalize.py                # (선택) 후보 정규화 유틸 (표준 강제가 아니라 “편의”)
│   │
│   ├── context/
│   │   ├── __init__.py
│   │   ├── builder.py                  # build_context (토큰 예산/압축 정책 포함 가능)
│   │   └── budget.py                   # token budget helpers (의존성 없는 버전)
│   │
│   ├── generation/
│   │   ├── __init__.py
│   │   ├── sql.py                      # SQL 생성 컴포넌트(LLM은 integrations llm client를 주입)
│   │   └── prompts.py                  # 프롬프트 템플릿/formatters
│   │
│   ├── validation/
│   │   ├── __init__.py
│   │   ├── static.py                   # 문법/금지쿼리/스키마 참조 등 “실행 없는” 검증
│   │   └── execution.py                # (옵션) 실제 DB 실행 검증(연동은 integrations)
│   │
│   └── adapters.py                     # ⭐ 핵심: 외부 retriever/llm 객체를 callable로 감싸는 as_callable
│
├── flows/                              # ✅ “완제품/프리셋” (define-by-run 클래스/함수)
│   ├── __init__.py
│   ├── baseline.py                     # BaselineFlow: retrieve -> context -> generate -> validate
│   ├── agentic.py                      # AgenticFlow: while/for 루프 포함 (사용자 override 용이)
│   └── examples.py                     # weird flow 예시(문서/테스트 겸)
│
├── integrations/                       # ✅ 외부 의존성 구현 (extras)
│   ├── __init__.py
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── base.py                     # thin wrapper 인터페이스(여긴 외부 의존성 있을 수 있음)
│   │   ├── openai_.py                  # openai extra
│   │   ├── anthropic_.py               # anthropic extra
│   │   └── upstage_.py                 # upstage extra
│   │
│   ├── vector_store/
│   │   ├── __init__.py
│   │   ├── base.py                     # VectorStorePort (여긴 integrations 계층)
│   │   ├── faiss_.py                   # faiss extra
│   │   ├── pgvector_.py                # pgvector extra
│   │   └── pinecone_.py                # pinecone extra
│   │
│   ├── metadata/
│   │   ├── __init__.py
│   │   ├── base.py                     # SchemaProviderPort
│   │   ├── sqlalchemy_.py              # sqlalchemy extra
│   │   └── datahub_.py                 # datahub extra
│   │
│   └── langgraph/                      # (선택) "브릿지"만. 메인 설계는 아님.
│       ├── __init__.py
│       └── bridge.py                   # Flow를 langgraph node로 감싸거나, component를 노드로 변환하는 정도
│
├── presets/                            # ✅ 초보자 UX: “원클릭 생성기”
│   ├── __init__.py
│   ├── factory.py                      # AutoText2SQL(...) -> BaselineFlow/AgenticFlow + 기본 컴포넌트 조립
│   └── defaults.py                     # 기본 조합 정책(vstore 없이도 동작하는 기본값 포함)
│
├── cli/
│   ├── __init__.py
│   └── main.py                         # lang2sql query/run 등
│
├── app/
│   ├── __init__.py
│   └── streamlit/
│       ├── __init__.py
│       └── main.py
│
├── tests/
│   ├── test_baseline.py
│   ├── test_agentic.py
│   ├── test_adapters.py
│   └── test_registry.py
│
└── docs/
    ├── philosophy.md
    ├── quickstart.md
    ├── customizing.md
    ├── writing-your-own-flow.md
    └── plugins.md