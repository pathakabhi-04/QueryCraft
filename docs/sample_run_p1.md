From `eval/results/20261122-170552-gemini-full100/raw.jsonl` (benchmark item Q060, config V5+SC,
`gemini-3.5-flash-lite`, temperature 0).

**Input (`{question}`):** List students who have pending dues in more than one academic year.

**Actual model output (raw, unedited):**

```json
{
  "plan": "fees joined to students on student_id. Filter where amount_due > amount_paid (pending dues). Group by student_id, student name. Having count(academic_year) > 1. Select student name and email.",
  "status": "OK",
  "sql": "SELECT s.name, s.email FROM students s JOIN fees f ON s.student_id = f.student_id WHERE f.amount_due > f.amount_paid GROUP BY s.student_id HAVING COUNT(DISTINCT f.academic_year) > 1;",
  "explanation": "These students have unpaid dues recorded across more than one academic year.",
  "assumptions": [
    "Pending dues mean amount_due is strictly greater than amount_paid."
  ],
  "confidence": "high"
}
```

**After validation and execution:** the validator accepted the query and added `LIMIT 500`. It
returned 8 rows (first: *Ayush Khosla, ayush.khosla69@students.univ.example*, synthetic data),
and the result matched the gold SQL. No self-correction was needed.
