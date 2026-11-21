# QueryCraft architecture

All diagrams describe the code in this repository (file names in brackets).
GitHub renders the Mermaid blocks; `docs/build_report.py` renders them into the report PDF.

## 1. System architecture

```mermaid
flowchart LR
    U([Admin staff]) -->|question, model, prompt version| UI[Streamlit app<br/>app/streamlit_app.py]
    UI --> P[Pipeline<br/>querycraft/pipeline.py]
    P --> PB[Prompt builder<br/>prompt_builder.py]
    PB -.reads.-> T[(Prompt templates<br/>prompts/v1..v4, final/)]
    PB -.reads.-> FS[(Few-shot examples<br/>fewshot_examples.yaml)]
    PB -.reads.-> SD[(Schema + value hints<br/>schema.sql, schema_docs.yaml)]
    P --> L[LLM interface<br/>llm.py]
    L --> G[Gemini<br/>Google AI Studio]
    L --> LL[Llama<br/>Groq or local Ollama]
    L -.cache.-> C[(eval/cache)]
    P --> PA[JSON parser<br/>parsing.py]
    P --> V[SQL validator<br/>validator.py · sqlglot]
    V --> E[Read-only executor<br/>executor.py]
    E --> DB[(SQLite university.db<br/>mode=ro)]
    P -->|explanation, rows, SQL,<br/>assumptions, confidence, latency| UI
```

## 2. Prompt workflow (final configuration V5 + self-correction)

Two prompts: **P1** generates the answer, **P2** repairs SQL that fails. P2 is used only when needed.

```mermaid
flowchart TD
    Q[/Staff question/] --> B[Fill P1 template v5_value_hints.txt:<br/>schema + column descriptions + allowed values<br/>+ 6 examples + question]
    B --> M1[LLM call #1, temperature 0]
    M1 --> J{Parse JSON}
    J -->|invalid| PE[Parse error shown,<br/>counted as wrong]
    J -->|valid| S{status?}
    S -->|UNSAFE| R1[Polite refusal:<br/>read-only, no bulk personal data]
    S -->|CANNOT_ANSWER| R2[Explain the data is not stored]
    S -->|OK| V{Validator:<br/>one SELECT, known tables/columns}
    V -->|write attempt| BL[Blocked, never executed]
    V -->|pass| X[Execute read-only<br/>LIMIT 500, 5 s timeout]
    V -->|other failure| F
    X -->|error| F{retries < 2?}
    X -->|rows| OUT[Explanation + table + SQL<br/>+ assumptions + confidence]
    F -->|yes| P2[Fill P2 fix_error.txt:<br/>question + previous SQL + error]
    P2 --> M2[LLM call, temperature 0] --> V
    F -->|no| FAIL[Show error, no result]
```

## 3. Task decomposition

```mermaid
flowchart LR
    A[Answer a staff question<br/>from the university DB] --> B[Step 1: Decide if it is allowed<br/>and answerable]
    A --> C[Step 2: Plan the query]
    A --> D[Step 3: Write one SQLite SELECT]
    A --> E[Step 4: Check it is safe]
    A --> F[Step 5: Run it read-only]
    A --> G[Step 6: Explain the result]
    B --> B1[UNSAFE: writes, injection,<br/>bulk personal data]
    B --> B2[CANNOT_ANSWER:<br/>data not stored]
    C --> C1[tables + join keys]
    C --> C2[filters with exact allowed values]
    C --> C3[grouping / derived values<br/>dues, attendance %]
    C --> C4[ordering / top-N]
    E --> E1[sqlglot parse, single statement,<br/>SELECT only, known tables/columns]
    F --> F1[mode=ro, authorizer,<br/>timeout, row limit]
    F --> F2[on error: self-correct, max 2]
    G --> G1[1–2 plain sentences, assumptions,<br/>confidence]
    classDef llm fill:#dbe9fb,stroke:#2a78d6;
    classDef code fill:#fde3d7,stroke:#eb6834;
    class B,C,D,G llm;
    class E,F code;
```

Blue steps are done by the model (P1/P2); orange steps are enforced in code.

## 4. Input–output flow

```mermaid
flowchart LR
    IN["<b>Input</b><br/>• question in plain English<br/>  e.g. 'How many day<br/>  scholars in BCA?'<br/>• model: Gemini or Llama<br/>• prompt version: V1–V5, V5+SC"]
    SENT["<b>Sent to the model</b><br/>• schema: CREATE TABLE<br/>  statements<br/>• column descriptions +<br/>  allowed values (no rows)<br/>• 6 worked examples<br/>• the question"]
    MODEL["<b>Model output (JSON)</b><br/>• plan<br/>• status<br/>• sql<br/>• explanation<br/>• assumptions<br/>• confidence"]
    OUT["<b>Shown to staff</b><br/>• explanation, large text<br/>• result table<br/>• SQL, collapsed<br/>• assumptions, confidence,<br/>  latency<br/>• or: refusal message"]
    IN --> SENT --> MODEL -->|validated +<br/>run read-only| OUT
```

## 5. Self-correction loop (agent loop)

```mermaid
sequenceDiagram
    participant P as pipeline.py
    participant M as LLM
    participant V as validator.py
    participant E as executor.py
    P->>M: P1 (question + schema + hints + examples)
    M-->>P: JSON {status: OK, sql}
    loop at most 2 retries, only if SQL fails and was not a write
        P->>V: validate(sql)
        alt blocked (unknown column, parse error...)
            V-->>P: reason
        else valid
            P->>E: execute read-only
            E-->>P: rows or runtime error
        end
        P->>M: P2 fix_error (question + previous SQL + error)
        M-->>P: JSON {status, sql}
    end
    P-->>P: final record: rows / refusal / error
```

## 6. Evaluation flow

```mermaid
flowchart LR
    BQ[(benchmark/questions.yaml<br/>100 items, gold SQL)] --> EV[eval/evaluate.py<br/>configs × models × runs]
    EV --> PIPE[pipeline.answer]
    BQ --> GOLD[Run gold SQL<br/>read-only]
    PIPE --> SC[eval/metrics.py<br/>EX, refusal, safety,<br/>hallucination, latency]
    GOLD --> SC
    SC --> RAW[(raw.jsonl<br/>+ meta.json)]
    RAW --> CMP[eval/compare.py]
    CMP --> SUM[summary.md / .csv]
    CMP --> CH[charts/*.png]
    CMP --> FL[failures.md<br/>by error type]
```
