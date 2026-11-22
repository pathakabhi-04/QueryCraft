# Reel script (target ≈ 120 s; allowed 90–150 s)

Presenter: **Ishita**. Format: screen recording of the **deployed** app with voice-over (optional
webcam in a corner). The demo must be a **real run**, so ask the question live.
About 330 spoken words, roughly 2 min 10 s at a normal pace. If it runs over 150 s, cut the sentence about the models in part 3.

---

### 1. Introduction (0–15 s)
**On screen:** the QueryCraft app home page (or webcam full screen for the first line).

> "Hello everyone, I am Ishita, and today I am presenting our project, **QueryCraft**,
> a natural language to SQL assistant for university administration."

### 2. What it is (15–40 s)
**On screen:** the app with the sidebar showing the database tables.

> "In a university, the fee, exam, hostel and admissions offices need reports every day:
> how many students have pending dues, who is below seventy-five percent attendance, and so on.
> But office staff cannot write SQL, so every report waits for the IT team.
> QueryCraft solves this. Staff simply type a question in plain English, and QueryCraft
> writes a safe, **read-only** SQL query, runs it, and explains the answer in simple words.
> If a question is unsafe, or the data does not exist, it politely refuses."

### 3. Specifications (40–80 s)
**On screen:** slowly scroll the GitHub repo (`prompts/` folders), then the chart
`eval/results/M2-cumulative/charts/accuracy_by_version.png`.

> "Here is how it is built.
> The main work is **prompt engineering**. We improved our prompt across **six versions**:
> rules with JSON output, few-shot examples, a plan-first step, column value hints, and
> finally a **self-correction** prompt that fixes a query when the database reports an error.
> We use **Gemini 3.5 Flash-Lite** and the open-weight **gpt-oss-120b**, with identical
> prompts at temperature zero.
> For safety, we do not rely on the prompt alone: in code, a SQL validator allows only a single
> SELECT query, and the database is opened read-only.
> We tested everything on a **hundred-question benchmark**. Accuracy went from **sixty-seven
> percent** with our first prompt to **ninety-six percent** with the final one, and every
> harmful request was blocked."

### 4. Demo: one example (80–115 s)
**On screen:** the app. Model: **Gemini**, prompt version: **V5 + self-correction**.
Type the question, click **Ask**, then open **Show SQL**.

**Example command to type:**
```
How many CSE students are day scholars?
```

> "Let me show you a live example. I'll ask: *How many CSE students are day scholars?*
> Notice that I wrote just 'CSE', and 'day scholar' is an office term; neither appears in
> the database. QueryCraft understood that CSE means B.Tech CSE, and that a day scholar is a
> student with no hostel. It answers **forty-four**, explains the result in one line, lists
> its assumption, and shows the SQL so anyone can check it."

**Expected result (verified in our test table, test 8):** `44`, with the assumption
"day scholars are students whose hostel ID is not assigned".

### 5. Closing (115–125 s)
**On screen:** the app or the GitHub repo page.

> "So, QueryCraft lets office staff get answers from their data in seconds: safely, with
> an explanation, and without writing SQL. Thank you!"

---

**Checklist before recording**
- Ask the demo question once in the deployed app to check that it answers 44.
- Close `.env` and any window showing API keys.
- Zoom the browser to about 125% so the text is readable.
- After recording, note the exact length in seconds for the form (Q14).
