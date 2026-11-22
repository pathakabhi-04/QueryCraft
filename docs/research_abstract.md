### Research abstract

**QueryCraft: Measuring Prompt Techniques for Safe Natural-Language-to-SQL in University Administration**

University office staff need answers from student databases but cannot write SQL. We study
how far prompt design alone can make a large language model a safe, read-only query assistant
for them. On a synthetic university database (8 tables, 500 students), we built six prompt
versions that each add one technique: rules with JSON output, few-shot examples, a plan-first
step, column value hints, and an execution-feedback self-correction loop. A code-level safety
layer (sqlglot validation and a read-only SQLite connection) blocks any write regardless of what
the model says. We evaluated every version on a 100-question benchmark of easy, medium, hard,
unanswerable and adversarial questions, at temperature 0, using execution accuracy and refusal
accuracy. On `gemini-3.5-flash-lite`, overall accuracy rose from 67% (baseline) to 93% with
rules and JSON, and to 96% with value hints and self-correction. Safety on adversarial inputs
rose from 60% to 100%, and false refusals fell to 1.3%. The open-weight `gpt-oss-120b` followed
the same trend on a 30-question subset (53.3% to 96.7%). A small local model (`llama3.2:3b`) gained most from
few-shot examples (13.3% to 66.7%) but lost accuracy with longer prompts. We conclude that
structured output with refusal rules gives the largest gain, value hints remove wrong-literal
errors, and safety must be enforced in code as well as in the prompt. The gold queries are
still being verified by hand, so these results are provisional.
