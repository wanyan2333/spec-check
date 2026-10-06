# AI development log

This project was built by an AI coding agent (Claude, in Claude Code), working from a written
brief by the human owner. This log records, honestly, what the AI produced, what was kept,
what was changed or thrown away, and why. It also records the places where an AI was wrong:
the agent itself, and Gemini during the evaluation.

## 1. Setup and model choice

| What the AI did | Outcome | Why |
|---|---|---|
| Probed four Flash-Lite model ids with a one-line JSON request before choosing | **Kept** `gemini-3.5-flash-lite` | `gemini-2.5-flash-lite` appears in `models.list()` but returns *404 "no longer available to new users"*, so a listed model is not necessarily a callable one. Google's rate-limit page says per-model free quotas are only shown in AI Studio, so "highest free quota" could not be read from an API. I picked the newest stable Flash-Lite and pinned it rather than the moving `gemini-flash-lite-latest` alias, so eval runs stay comparable. |
| First version of `.env` loading used `load_dotenv()` | **Changed** to `load_dotenv(find_dotenv(usecwd=True))` | A probe script outside the project raised `KeyError: 'GEMINI_API_KEY'`. `load_dotenv()` searches upward from the *calling file*, not the working directory. The CLI is run from the user's repo, so the cwd is the right place to look. |
| LLM client initially relied on the OpenAI SDK's built-in retries | **Changed**: SDK retries off (`max_retries=0`), own exponential backoff on 429/5xx | Retries must show up in logs and in the report (`Retries` column), and must be unit-testable with an injected `sleep`. |

## 2. Core design decisions (kept)

- **Evidence verification is programmatic, not another LLM call.** A second model judging the
  first would share its failure modes. A substring check against the diff cannot hallucinate.
- **Verification uses the post-change side of the diff only** (context + added lines). A
  snippet that only matches *removed* lines is marked UNVERIFIED: deleted code is not
  evidence that something is implemented now.
- **Stricter than the brief:** `tested=yes` needs a verified snippet *from a test file*, and
  `implemented=yes/partial` needs a verified snippet *from a non-test file*. Without this,
  a model could "prove" a test exists by quoting production code. Also flagged: the
  contradiction `tested=yes` with `implemented=no`, and confidence below 0.5.
- **Diff parsing counts hunk lines** from the `@@ -a,b +c,d @@` header instead of guessing
  from prefixes, so a removed line that starts with `--` is not taken for a file header
  (covered by a unit test).

## 3. Evaluation set: how the labels were made trustworthy

The brief asked for labels to be verified by program, not by eye. What the AI built:

- `eval/build_cases.py` generates every `change.diff` with real `git diff --cached`: it copies
  the sample app into a temporary repo, commits it, overlays the case's `after/` files, and
  diffs. No diff was written by hand.
- `eval/verify_labels.py` checks **both** labels. The brief only required mutation testing
  for `tested`. I added hidden behavioral *probes* (`probes.py`, never shown to the model) so
  that `implemented` (yes / partial / no) is also checked against running code, not just my
  reading of it. Each mutation must also make that criterion's probe fail. Otherwise
  "tests still pass after the mutation" could just mean the mutation did nothing.
- **Testing the tester:** all 19 labels passed on the first run. A checker that always says
  OK would look the same, so I temporarily flipped two labels (04/AC2 tested no→yes,
  08/AC2 implemented no→partial). The verifier rejected both with the right reason
  ("mutation testing says tested=no", "probes say implemented=no"). Then I restored them.

Mistakes the agent made here, and how they were caught:

- **Relative path bug in `verify_labels.py`**: `git apply cases/.../change.diff` ran with
  `cwd` set to the temp dir, so the relative path broke. Found while running the
  flipped-label test from a different working directory. Fixed with `.resolve()`.
- **Silent no-op edit:** the agent's first attempt to add `extend-exclude` to the ruff config
  did nothing, so the following `ruff format .` also ran over the `after/` fixtures. This
  was noticed because ruff still reported the *deliberate* unused variable in case 04's
  test. Before trusting the fixtures again, I regenerated every diff and compared it byte
  for byte with the previous version. They were identical (the formatter had changed
  nothing), and the config was then fixed and confirmed with `ruff check --show-settings`.
  The root cause turned up later (section 5).
- **Labeling convention made explicit:** for 06/AC2 (only the upper bound of a range is
  enforced), "tested" is ambiguous. I defined it operationally (if breaking the
  *implemented part* fails a test, then tested=yes) and documented it in
  `label_notes.md`, so the label is not a judgment call.

## 4. Where Gemini was wrong during the evaluation

All examples are from the saved raw outputs in `eval/results/*.json`. The "Failure cases"
and "Evidence that failed verification" sections of [`eval/RESULTS.md`](eval/RESULTS.md)
have the full analysis.

**Quotes of code that does not exist (caught by `verify.py`, not by a human):**

1. *v1, case 08, run 1.* Gemini quoted the test `test_stats` as one block but **dropped the
   line** `assert body["total"] == 2` from the middle. Each line is real; the block is not.
   How it was found: `check_evidence` normalizes whitespace and searches for the
   *contiguous* block in the post-change side of `test_app.py`. It returned
   `snippet not found in this file's diff`, and the report showed the criterion as
   "needs human review".
2. *v2, case 06, run 2.* Gemini quoted
   `response = client.post(", json={"title": "Pay rent", "priority": 6})`. The real line is
   `client.post("/todos", json=...)`, so the `/todos"` part was lost and the string literal
   is broken. This was the only test-file evidence for a `tested=yes` claim, so the tool
   also raised "claims tested=yes without verified evidence from a test file". The verdict
   was correct, but its evidence was not, and the tool flagged it instead of passing it on.

**Confident wrong verdicts (caught by comparing against the verified labels):**

3. *Case 08 / AC2, all 4 runs of v1 and v2.* `done = sum(1 for t in todos.values() if t.done is not None)`
   counts every todo, because a `bool` is never `None`. Gemini said "implemented" every time,
   with confidence 0.8 to 1.0. The prompt fix aimed at this (v2: "trace computed values")
   did not help. The same v2 prompt on `gemini-3.1-flash-lite` caught it. Conclusion: a
   capability limit of this model on semantic bugs, and confidence scores cannot be used
   to find these errors.
4. *Case 04 / AC2, v1 run 1.* Gemini wrote in its own reasoning that "the test body uses an
   empty string payload", which is the bug, and still answered `tested=yes` because "the
   implementation correctly enforces max_length=100". The reasoning text contained the right
   answer and the verdict field did not. Fixed in v2 by defining "tested" as a mental
   mutation test and asking for reasoning *before* the verdict fields.
5. *Case 08, v1, both runs.* Gemini returned `tested: "partial"`, a value the schema does not
   allow. Pydantic rejected it, the tool sent the validation error back, and the single
   repair retry returned valid JSON. v2 states the allowed values explicitly; 0 repairs needed.

**Infrastructure:** `gemini-3.5-flash` returned `503 "This model is currently experiencing
high demand"` (and some 429s) on every retry across two attempts, so the planned
larger-model comparison was replaced by the 3.1-flash-lite comparison.

## 5. Mistakes by the agent itself, and how they were caught

| Mistake | How it was caught | Fix |
|---|---|---|
| **Edits that silently did nothing.** Several file patches were run as `python - <<EOF ... EOF` in Git Bash. On this Windows machine, `python` on PATH is the Microsoft Store *alias stub*, which exits without running anything and without an error. Only `uv run python` is a real interpreter. | Three separate symptoms: the ruff exclude was missing (section 3), a CLI error handler was missing (next row), and a helper refactor was missing. An audit with `grep` showed that all three patches had been no-ops. | Re-applied with the editor tool, then checked each file. Every patch made the same way was audited. |
| **CLI crashed with a traceback on API failure.** The handler for `openai.APIError` was "added" by one of the no-op patches above. | A real run against `gemini-3.5-flash` hit 503 on every retry and printed a Python traceback instead of `spec-check: error: ...` with exit code 2. | Added the handler and a regression test (`test_api_failure_after_retries_is_a_clean_error`). |
| A Bash heredoc batch with nested heredocs failed to parse, and *no* files were written. | `ls tests/` after the command showed the files were missing. | Wrote those files with the editor tool instead. |
| Windows `Path.write_text` wrote CRLF line endings in generated reports. | Git warnings on `git add`. | `.gitattributes` (`eol=lf`) and `newline="\n"` in the eval scripts. `change.diff` was always written with LF, so the diffs were never affected. |
| HTTP client INFO logs mixed into the CLI's per-call log lines. | Noticed while generating the README example. | Only the `spec_check` logger is set to INFO. |

## 6. Decisions: accepted, modified, rejected

- **Rejected: a second LLM to judge the evidence.** It would share the first model's
  failure modes and add cost. Plain string matching cannot hallucinate.
- **Rejected: fuzzy matching of snippets** (e.g. 90% similarity). Both hallucinations
  above are "almost right" (one dropped line, a few dropped characters). Fuzzy matching would
  have accepted both. The match is exact after whitespace normalization only.
- **Modified: the brief's rule "claims without verified evidence need review"** was
  tightened to *kind-aware* evidence (test file for `tested`, non-test file for
  `implemented`). Hallucination #2 above was only caught as a *claim* problem because of
  this.
- **Accepted, with a caveat: prompt v2 was tuned on the same 8 cases it is evaluated on.**
  Documented as a threat to validity in RESULTS.md rather than hidden. The v2 rules are
  general definitions, not case-specific hints, but only a held-out set can prove that.
- **Kept `gemini-3.5-flash-lite` as the default** even though 3.1-flash-lite scored better
  on missing implementations. The brief asked for the Flash-Lite model with the best free
  quota, 3.5 is the current stable one and is 4x faster, and 8 cases are not enough to
  justify overriding that. The trade-off is documented so a user can switch with one
  environment variable.
