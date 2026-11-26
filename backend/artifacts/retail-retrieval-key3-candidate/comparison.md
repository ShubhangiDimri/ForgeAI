# Retail retrieval verification

Both replays used the same corrected frozen 20 cases, GPT-OSS 120B agent,
GPT-OSS 20B judge, embeddings, rubric and prompts. The before snapshot matches
the previous runner and retrieval source hashes. Only those two runtime files
differed. The earlier 11/20 used a different benchmark.

| Replay | Passed | Failed | Errors |
| --- | --- | --- | --- |
| Before | 16/20 | 4 | 0 |
| Exact identifier retrieval | 16/20 | 4 | 0 |

- E017 and E018 moved from fail to pass. The candidate retrieved the
  matching records with different values and asked for clarification
  instead of returning one row's value.
- E004 moved from pass to fail. The full record and citation were correct,
  but the user-requested CSV lookup tool was skipped.
- E016 moved from pass to fail. The old answer incorrectly said the ID was
  absent and got credit for refusing. The candidate gave the shared
  historical price as a current dollar price and did not clarify.
- E001 still lacks the required document citation in its arithmetic answer.
  E007 still hits the rounded-calculator-output scoring mismatch.

Retained the candidate for its demonstrated improvement on the two target
cases. The aggregate score tied. Provider interruptions were preserved in
the run metadata and checkpoint files. Each final scorecard has 20 semantic
results and zero infrastructure errors. Groq slots 3 and 2 were used across
retries with the same pinned models. Slot 1 was rejected with HTTP 401.
