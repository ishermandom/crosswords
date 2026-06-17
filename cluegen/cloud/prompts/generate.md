# GENERATION TASK

You are a crossword setter building a clue bank. The full clue-writing
specification (CLUE_SPEC.md) is your system prompt; a list of answer words
follows below.

For EACH word in the list:

- Produce one JSON object on a single line, exactly following Part C of the spec
  (the Output Schema).
- Clue counts for this run: {{CLUE_MIX}}. Use the per-style skip mechanism
  honestly when a word resists fair treatment in a style.
- Multiple clues for the same word must take genuinely different angles —
  different senses, mechanisms, or misdirection domains. Never paraphrases.
- The clue text must never contain the answer word, its plural/inflection, or a
  trivially close cognate.
- If a CATEGORY NOTE is provided below, it names the failure mode that weak clue
  banks exhibit for these words and suggests promising angles. Avoid that
  failure mode explicitly.

Output rules (strict — your output is machine-parsed):

- One JSON object per word, one per line (JSONL).
- No prose, no markdown fences, no commentary before, between, or after the JSON
  lines.
- Output the words in the order given.

CATEGORY NOTE (may be empty): {{CATEGORY_NOTE}}

WORDS: {{WORDS}}
