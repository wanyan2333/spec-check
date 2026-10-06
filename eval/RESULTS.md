# Evaluation results

**Setup:** 8 cases, 19 acceptance criteria, labels verified by program
([LABEL_VERIFICATION.md](LABEL_VERIFICATION.md)). Each case was run **twice**, giving
38 judgments per configuration. Temperature 0, JSON mode, 4 s pause between calls.
Default model `gemini-3.5-flash-lite` (free tier). Raw outputs, including every
model reasoning and evidence snippet, are in [`results/`](results/).

Reproduce:

```bash
uv run python eval/run_eval.py --prompt v1
uv run python eval/run_eval.py --prompt v2
uv run python eval/run_eval.py --prompt v2 --model gemini-3.1-flash-lite --name v2-gemini-3.1-flash-lite
uv run python eval/run_eval.py --compare v1 v2 v2-gemini-3.1-flash-lite
```

## Summary: prompt v1 vs v2 (and one model comparison)

| Metric | v1 (3.5-flash-lite) | **v2 (3.5-flash-lite)** | v2 (3.1-flash-lite) |
|--------|------|------|------|
| Judgments (criteria x runs) | 38 | 38 | 38 |
| Implemented accuracy | 36/38 (95%) | 36/38 (95%) | 38/38 (100%) |
| Tested accuracy | 37/38 (97%) | **38/38 (100%)** | 36/38 (95%) |
| Both correct | 35/38 (92%) | **36/38 (95%)** | 36/38 (95%) |
| Missing-implementation detection (expected no/partial, predicted not yes) | 10/12 (83%) | 10/12 (83%) | **12/12 (100%)** |
| Missing-test detection (expected tested=no, predicted no) | 19/20 (95%) | **20/20 (100%)** | 20/20 (100%) |
| False positives on fully correct items (predicted a gap) | 0/16 (0%) | 0/16 (0%) | 0/16 (0%) |
| False positives incl. human-review flags | 0/16 (0%) | 0/16 (0%) | 0/16 (0%) |
| Unverified evidence snippets | 1/54 (2%) | 1/67 (1%) | 0/64 (0%) |
| Run-to-run consistency (same verdict in both runs) | 18/19 (95%) | **19/19 (100%)** | 19/19 (100%) |
| Schema repair retries needed | 2 | **0** | 0 |
| 429/5xx retries | 0 | 0 | 1 |
| Avg latency per check | 2.51 s | 2.40 s | 9.99 s |
| Total tokens (16 checks) | 23,898 | 26,203 | 25,460 |

How to read it:

- **v1 → v2** fixed the *tested* errors: tested accuracy went from 97% to 100%. It also made
  the model fully consistent between runs and removed the schema violations that needed a
  repair retry. It did **not** fix the remaining *implemented* error (case 08, below).
- **0 false positives** in every configuration: no fully correct criterion was ever reported
  as a gap or flagged for review. A release gate that cries wolf gets switched off, so this
  number matters as much as recall.
- **The evidence checker caught a fabricated quote in each Flash-Lite 3.5 configuration**
  (details below). Both would otherwise have appeared in the report as trustworthy evidence.
- **Small sample warning:** 19 criteria. One judgment is about 2.6 percentage points.
  v2 was written after looking at v1's failures *on the same cases*, so its improvement is
  an in-sample result. See "Threats to validity".

## Per case (v1 → v2, 3.5-flash-lite, run 1 / run 2)

| Case | AC | Expected | v1 | v2 |
|------|----|----------|----|----|
| 01-complete-with-tests | AC1 | yes/yes | yes/yes, yes/yes | yes/yes, yes/yes |
| 01-complete-with-tests | AC2 | yes/yes | yes/yes, yes/yes | yes/yes, yes/yes |
| 01-complete-with-tests | AC3 | yes/yes | yes/yes, yes/yes | yes/yes, yes/yes |
| 02-missing-edge-case | AC1 | yes/yes | yes/yes, yes/yes | yes/yes, yes/yes |
| 02-missing-edge-case | AC2 | no/no | no/no, no/no | no/no, no/no |
| 03-no-tests | AC1 | yes/no | yes/no, yes/no | yes/no, yes/no |
| 03-no-tests | AC2 | yes/no | yes/no, yes/no | yes/no, yes/no |
| 04-misleading-test | AC1 | yes/yes | yes/yes, yes/yes | yes/yes, yes/yes |
| 04-misleading-test | AC2 | yes/no | **yes/yes ❌**, yes/no | yes/no, yes/no |
| 04-misleading-test | AC3 | yes/no | yes/no, yes/no | yes/no, yes/no |
| 05-unrelated-change | AC1 | no/no | no/no, no/no | no/no, no/no |
| 05-unrelated-change | AC2 | no/no | no/no, no/no | no/no, no/no |
| 06-partial-validation | AC1 | yes/yes | yes/yes, yes/yes | yes/yes, yes/yes |
| 06-partial-validation | AC2 | partial/yes | partial/yes, partial/yes | partial/yes, partial/yes ⚠️ |
| 07-mixed | AC1 | yes/yes | yes/yes, yes/yes | yes/yes, yes/yes |
| 07-mixed | AC2 | yes/no | yes/no, yes/no | yes/no, yes/no |
| 07-mixed | AC3 | no/no | no/no, no/no | no/no, no/no |
| 08-weak-assertion | AC1 | yes/yes | yes/yes, yes/yes | yes/yes, yes/yes |
| 08-weak-assertion | AC2 | no/no | **yes/no ❌ ⚠️**, **yes/no ❌** | **yes/no ❌**, **yes/no ❌** |

❌ wrong label · ⚠️ flagged "needs human review" by the evidence checks.
Full per-run tables: [v1](results/v1.md), [v2](results/v2.md),
[v2 on 3.1-flash-lite](results/v2-gemini-3.1-flash-lite.md).

## Failure cases

### F1. 08-weak-assertion / AC2: wrong value accepted as "implemented" (v1 x2, v2 x2)

- Expected `no/no`, got `yes/no` in all four runs (v2 confidence **1.0**).
- Code: `done = sum(1 for t in todos.values() if t.done is not None)`. `done` is a `bool`
  and never `None`, so this counts *every* todo.
- Model (v1): *"The 'done' field is implemented and returned by the endpoint, but the test
  does not assert the exact value of done."*
- Model (v2): *"The code implements the done count, but the test only checks that the key
  "done" exists in the body..."*
- **Analysis:** the model did get the *test* half right: it saw that `assert "done" in body`
  proves nothing. But it pattern-matched `sum(1 for t in todos.values() if t.done ...)` as
  "counts done todos" and never evaluated `is not None` against the field's type. v2's
  explicit instruction to "trace computed values... a field that exists but produces a wrong
  value is NOT a full implementation" did not help. The confidence even went up. That
  points to a **capability limit, not a prompt problem**. Supporting evidence: with the
  *same* v2 prompt, `gemini-3.1-flash-lite` got it right in both runs:
  *"checks if 'done' is not None, which is incorrect for a boolean field (it should check if
  it is True)."*
- **Lesson:** high confidence is not correctness. This error class (plausible-looking but
  semantically wrong code) is exactly what a release gate must catch. Run-time evidence
  (executing the code, like the label verifier's probes) would catch it; text review by a
  small model does not, reliably.

### F2. 04-misleading-test / AC2: copy-paste test counted as a test (v1 run 1)

- Expected `yes/no`, got `yes/yes`.
- Test: `long_title = "x" * 101` then `client.post("/todos", json={"title": ""})`.
  The long title is never sent.
- Model: *"...a test checks for too long titles (though the test body uses an empty string
  payload, the implementation correctly enforces max_length=100)."*
- **Analysis:** the model *noticed* the bug in its own reasoning and then decided `tested=yes`
  anyway, because the implementation was correct. It conflated "the code is right" with
  "a test proves it". Run 2 of the same prompt answered correctly, so v1 was borderline
  here (the one inconsistent criterion in v1).
- **Fix in v2:** "tested" is defined as a *mental mutation test* ("if the implementation
  were broken, would a test in the diff fail?"), plus the explicit rule "code being correct
  does not make it tested". This is the same operational definition the label verifier
  uses. v2 got this criterion right in both runs.

### F3. Schema violation: `tested: "partial"` (v1, 08-weak-assertion, both runs)

- Pydantic rejected `criteria.1.tested: Input should be 'yes' or 'no' [input_value='partial']`.
  The tool sent the validation error back and the repair retry returned valid JSON both times.
- **Analysis:** the model wanted to express "the key is tested but the value is not", and
  the binary field had no room for that.
- **Fix in v2:** "tested: exactly yes or no (never partial)" with the mutation-test
  definition. v2 needed 0 repair retries.

### F4. 06-partial-validation / AC2 on gemini-3.1-flash-lite: label convention disagreement

- Expected `partial/yes`, got `partial/no` (both runs). Model: *"The test only checks values
  above 5, so the lower bound is not correctly implemented or tested."*
- **Analysis:** this is arguably not a model error. My labeling convention (documented in
  the case's `label_notes.md`) says `tested` refers to the implemented part. The upper bound
  is tested, and the mutation removing `le=5` fails a test. 3.1-flash-lite reads "tested" as
  "the whole criterion is tested". Both readings flag the criterion as a gap (`partial`), so
  the release decision is the same. It shows that a binary `tested` field is ambiguous for
  partially implemented criteria. Possible fix: report tested per sub-behavior.

## Evidence that failed verification (caught hallucinations)

Both were caught automatically by `verify.py`; neither appears in the report as verified.

1. **v1, 08-weak-assertion AC2, run 1: a quote with a line silently removed.** The model
   quoted `test_stats` as one block, but dropped `assert body["total"] == 2` from the middle.
   Every individual line exists in the diff, but the quoted block as a whole does not.
   → `snippet not found in this file's diff`.
2. **v2, 06-partial-validation AC2, run 2: a corrupted string literal.** The model quoted
   `response = client.post(", json={"title": "Pay rent", "priority": 6})`. The path
   `/todos"` is missing, which leaves a broken string. The real line is
   `client.post("/todos", json={...})`. This was the *only* test evidence for `tested=yes`,
   so the criterion was additionally flagged *"claims tested=yes without verified evidence
   from a test file"* → **needs human review**. The verdict happened to be right, but the
   proof was not, and the tool said so.

Rate: 1/54 and 1/67 snippets on 3.5-flash-lite, 0/64 on 3.1-flash-lite. Low, but not zero.
A human reading the report has no way to tell a corrupted quote from a real one without
opening the diff. That is why the check exists.

## Prompt v1 vs v2: what changed

Both prompts are kept in [`src/spec_check/prompts.py`](../src/spec_check/prompts.py)
(`--prompt v1` still works).

| v1 | v2 | Motivated by |
|----|----|--------------|
| "tested is yes only if a test actually executes the behavior and asserts it" | Step-by-step procedure, ending in a **mental mutation test**. "Code being correct does not make it tested." | F2 |
| no guidance on correctness | "Trace what the code actually returns... a field that exists but produces a wrong value is NOT a full implementation" | F1 (did not help 3.5-flash-lite) |
| `tested: yes/no` | "exactly yes or no (never partial)"; if implemented is no, tested must be no | F3 |
| "copied verbatim" | "1 to 4 contiguous lines... never skip, merge, shorten or paraphrase" | spliced quote (#1 above) |
| verdict fields first, reasoning last | `evidence` → `reasoning` → verdict, so the model reasons before it decides | general practice |

Effect: tested accuracy 97% → 100%, consistency 95% → 100%, repair retries 2 → 0.
Implemented accuracy is unchanged (F1). Snippets per check went up (54 → 67) because v2
asks for both code and test evidence. A corrupted quote still occurred once (1/67), so
shorter quotes reduce the problem but do not remove it. Programmatic verification is
still needed.

## Model choice

`gemini-3.5-flash-lite` stays the default. It is the current stable Flash-Lite (the brief:
use Flash-Lite for the free quota), and it is fast (about 2.4 s per check). On this set,
`gemini-3.1-flash-lite` had perfect recall on missing implementations, at about 4x the
latency. For a pre-release gate, where a missed bug costs more than a slow check, I would
run it with `SPEC_CHECK_MODEL=gemini-3.1-flash-lite`, or with a larger model. A planned
comparison with `gemini-3.5-flash` on case 08 could not run: it returned
`503 "high demand"` on every retry during the evaluation window.

## Threats to validity

- **Tiny set:** 8 cases and 19 criteria, all on a toy API that I (the AI) wrote. Real
  diffs are longer and messier.
- **In-sample prompt tuning:** v2 was designed after reading v1's failures on the same
  cases. I tried to keep the v2 rules general (definitions and procedure, no case-specific
  hints). The honest test of v2 is new cases it has never seen.
- **Two runs per configuration.** At temperature 0 the model was mostly deterministic, but
  v1 still disagreed with itself once (F2).
- **The labels follow my conventions** (F4). They are verified by execution, but the
  definition of "tested" for partially implemented criteria is a choice.
