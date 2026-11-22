1. **Ambiguous questions get one silent interpretation.** For "average attendance percentage
   in Operating Systems" (Q052), Gemini restricted the answer to the current year 2026-27, while
   our gold query uses all years. For "how many students has the 2026-27 fee been raised for"
   (Q017), it refused. The assumption is shown in the app, but staff may not read it.
   *Next:* when `confidence` is low or an assumption changes the scope, ask a short
   clarifying question before running the query.
2. **The accuracy metric is stricter than a human reader.** For "number of boys and girls in
   each programme" (Q036), Gemini returned one row per programme with two count columns. The
   answer is correct, but it does not match the gold layout (one row per programme and gender),
   so it is scored wrong. Q066 (second-highest fee) is a real error: the model left out
   `DISTINCT`. The gold SQL is also **not yet hand-verified** (`verified: false`), so every
   number here is provisional.
   *Next:* verify and freeze the benchmark, and record equivalent answer layouts for the M3 error analysis.
3. **Free API quotas limited the evaluation.** Gemini allows 500 requests per day and Groq
   allows 200k tokens per day. So gpt-oss-120b was run on all 100 questions only for V1–V3
   and on the 30-question subset for V4 onwards. Every configuration was run once, not 3 times,
   so consistency is not measured yet.
   *Next:* spread the 3-run consistency test over several days using the response cache.
4. **Long prompts hurt small models.** The local `llama3.2:3b` scored 66.7% with V3 but only
   43.3–50.0% with the longer V4/V5 prompts (about 12k characters). The final prompt suits
   capable API models, not small offline ones.
   *Next:* send only the value hints for the tables a question needs.
