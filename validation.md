# Validation design

Reference for sessions implementing or iterating on the validation stage of the
clue generator pipeline. Covers the two-call architecture, prompt properties,
output shape, and open calibration questions.

---

## Architecture

Validation uses two independent API calls, each with a fresh context — no access
to the brainstorm conversation.

**Why two calls:** The solvability test must be blind — providing the answer
word defeats the test. Quality evaluation (factual accuracy, difficulty
calibration, craft assessment) requires knowing the answer. These constraints
are incompatible in a single call.

**Solvability call** — Blind: receives clue text and answer length only. The
model guesses the answer as a human solver would. Pass criterion: the target
answer appears in the top N guesses of the correct length (N requires empirical
calibration — see _Open questions_).

**Quality call** — Answer-aware: receives clue text, answer word, and target
difficulty day. Evaluates convention compliance and scores the clue on graded
rubric scales. Pass criterion: convention compliance plus a scale profile that
matches the expected profile for the target day.

The final verdict requires both calls to pass. A solvable but lazy clue fails; a
well-crafted clue that no one can solve also fails. The exact combination logic
is an open question — see _Open questions_.

---

## Solvability call

### Persona and context

The model plays an experienced NYT crossword solver. The system prompt
establishes this persona and briefly notes that NYT crossword clues often
exploit wordplay, double meanings, and deliberate misdirection — so the solver
should consider multiple interpretations before committing to guesses.

The target difficulty day is **not** named. Instead, the system prompt provides
a style hint describing how hard to think — e.g. "this clue may use wordplay or
misdirection; consider multiple interpretations before committing." This
calibrates the solver's persistence without triggering priors about what
day-appropriate answer words look like, which would inflate false-pass rates on
weak clues. See _Open questions_ for the full tradeoff analysis.

### Input

- Clue text, exactly as it would appear to a human solver
- Answer length (number of letters)
- Style hint describing how hard to think (e.g. "this clue may use wordplay or
  misdirection; consider multiple interpretations before committing")
- Notably absent: the answer word, and the target difficulty day by name

### Multi-turn structure

The call is multi-turn. Turn 1 (scratchpad) asks the model to reason through the
clue: consider multiple interpretations, possible wordplay angles, and candidate
answers. Turn 2 asks the model to commit to a ranked list of guesses. Separating
reasoning from output is especially important for non-reasoning models; see
`prompting.md` — "Making non-reasoning models reason."

### Guess filtering

Turn 2 asks for significantly more guesses than N (e.g., 3–4× N). The answer
length is provided upfront, but models don't reliably self-filter, so
programmatic filtering to the correct length is applied after parsing.

### Pass criterion

The target answer appears within the top N length-filtered guesses. N requires
calibration against a golden set of known-good clues — see _Open questions_.

Record the target answer's rank among filtered guesses regardless of pass/fail.
The rank is a secondary difficulty signal: an answer landing at rank 1 on a
Thursday or Saturday clue suggests the clue may be too easy for the day even if
it passes the solvability threshold. This data is also needed for calibrating N.

### Known limitation

The blind validator is stricter than real crossword conditions: human solvers
have crossing letters, which substantially narrow the answer space. Expect more
false negatives for hard clues. Account for this when calibrating N.

---

## Quality call

### Persona and context

The model plays an experienced NYT crossword editor evaluating a submitted clue.
The system prompt describes the target difficulty day (Monday through Saturday,
with a concrete description of what each day means for clue style and
difficulty) and the relevant NYT crossword conventions.

**Sycophancy guard:** framing must be neutral. Do not imply a preferred verdict.
Use "evaluate whether this clue meets these criteria" — not "assess whether this
is a good clue."

### Input

- Clue text
- Answer word
- Target difficulty day

### Convention compliance

Checked first. These are binary pass/fail properties. A convention failure
rejects the clue immediately — the rubric scales are not evaluated.

- **Tense and number agreement:** the clue's grammatical form agrees with the
  answer (plural answer → plural clue surface; verb answer → matching tense)
- **Wordplay indicator:** a `?` suffix is required when the clue uses
  misdirection or wordplay; it must not appear on a straight definition clue
- **Abbreviation signaling:** any abbreviation in the answer must be signaled in
  the clue (e.g., "Abbr.", "briefly", or an abbreviated word in the clue)
- **Fill-in-the-blank format:** blanks rendered as `___`

TODO: consider a dedicated convention-rewrite stage that fixes violations
automatically, rather than failing clues outright, if violations turn out to be
frequent.

### Rubric scales

The six scales were chosen to capture the dimensions that make crossword clues
enjoyable — derived from reasoning and research into what solvers value:
misdirection and aha moments, wordplay mechanics, surface elegance,
accessibility of references, and the craft of choosing a deliberate angle.
Anti-patterns (lazy definitions, forced phrasing) are encoded as the low end of
these scales rather than enumerated separately; the same dimensions apply, just
at the unfavorable extreme.

Each scale is scored 1–5. The model should produce a score and a brief rationale
for each. Scores are not aggregated into a single number; they form a profile
compared against the target day's expected range — see _Difficulty calibration_.

**Angle craft** — Did the constructor choose a deliberate, specific angle, or is
this the first thing that comes to mind? Score 1: default dictionary entry or
trivial antonym ("Opposite of black" for WHITE). Score 5: unexpected, considered
angle that creates a moment of recognition even without wordplay.

**Misdirection** — Does the clue's surface reading lead elsewhere before the
answer clicks? Score 1: the clue points directly and unambiguously at the
answer. Score 5: strong deliberate misdirection — the solver is confidently led
the wrong direction before the answer lands.

**Wordplay complexity** — Does the clue employ a linguistic mechanism (pun,
double meaning, homophone, hidden word, etc.)? Score 1: none. Score 5:
multi-layer mechanism.

**Reference accessibility** — How broadly known is the knowledge required to
solve the clue? Score 1: niche or specialist. Score 5: universal.

**Surface coherence** — Does the clue read as natural, polished English in its
surface register? For misdirection clues, this is evaluated in the misdirected
register — the fake reading should flow naturally as a real sentence or phrase,
not just be grammatically valid. Score 1: tortured syntax or assembled phrasing.
Score 5: reads as a real, idiomatic sentence or phrase.

**Fairness of deception** — When misdirection is present, does the connection
resolve cleanly once the answer is known? Score 1: ambiguity that doesn't
resolve, or deception that feels like a trick. Score 5: the misdirection is
elegant and the connection is unambiguous once seen. For clues with no
misdirection, score 5 by default.

### Difficulty calibration

Craft and fairness are quality floors — high scores are expected regardless of
difficulty level. The difficulty axes are misdirection, wordplay complexity, and
reference accessibility.

Indicative day profiles (to be validated empirically against a golden set):

| Day | Craft | Misdirection | Wordplay | Accessibility |
| --- | ----- | ------------ | -------- | ------------- |
| Mon | high  | low          | low–mid  | high          |
| Tue | high  | low–mid      | low–mid  | high          |
| Wed | high  | mid          | mid      | mid–high      |
| Thu | high  | high         | high     | mid           |
| Fri | high  | high         | high     | mid           |
| Sat | high  | high         | high     | low–mid       |

Sunday clues profile roughly at Wednesday–Thursday; the added complexity comes
from the theme, not individual clue difficulty.

For implementation, map the labels to approximate score ranges: low = 1–2, mid =
3, high = 4–5. Treat these as starting points to be tightened once a golden set
is available.

A clue passes difficulty calibration when each scale's score falls within the
expected range for the target day. A Monday clue with low misdirection passes;
the same clue submitted for Thursday fails not because it is bad in isolation,
but because it is wrong for the day.

---

## Output format

Both calls use Ollama's `format` parameter with a JSON schema. Strip markdown
fences defensively regardless. Always have a retry loop. See `prompting.md` —
"JSON and structured output."

**Solvability call output:**

```json
{
  "guesses": ["WORD", "WORD", "..."]
}
```

`guesses` is an ordered list, most confident first, before length filtering. The
scratchpad turn's content is in the message history and captured in the debug
log; it is not repeated in the structured output.

**Quality call output:**

```json
{
  "conventions": {
    "tense_agreement": true,
    "wordplay_indicator": true,
    "abbreviation_signaled": true,
    "fill_format": true
  },
  "scales": {
    "angle_craft": { "score": 4, "rationale": "..." },
    "misdirection": { "score": 3, "rationale": "..." },
    "wordplay_complexity": { "score": 2, "rationale": "..." },
    "reference_accessibility": { "score": 5, "rationale": "..." },
    "surface_coherence": { "score": 4, "rationale": "..." },
    "fairness_of_deception": { "score": 5, "rationale": "..." }
  }
}
```

---

## Error handling and logging

- A validation failure (malformed JSON, network error, parse error after
  retries) must not abort the pipeline. Log the error, attach a failed
  validation result to the clue, and continue to the next word.
- On JSON parse failure: retry up to a fixed limit with the same prompt before
  recording failure. See `prompting.md` — "JSON and structured output."
- Log both calls' inputs and full outputs in human-readable form (e.g.
  pretty-printed JSON), not just raw API responses.
- On parse failure: log the raw response to aid diagnosis.

---

## Implementation checklist

Properties to verify manually as the prompts are built out. Check each off once
it's confirmed to be in place.

### Solvability call

- [ ] System prompt establishes an experienced NYT solver persona
- [ ] System prompt notes that NYT clues exploit wordplay, double meanings, and
      misdirection
- [ ] Style hint calibrates solver persistence without naming the difficulty day
- [ ] Answer word absent from input
- [ ] Target difficulty day name absent from input
- [ ] Turn 1 asks the model to reason through interpretations and candidates
      (scratchpad)
- [ ] Turn 2 asks the model to commit to a ranked guess list
- [ ] Turn 2 requests significantly more guesses than N (target: 3–4× N)
- [ ] Programmatic length filtering applied after parsing
- [ ] Pass criterion: target answer appears in top N length-filtered guesses
- [ ] Target answer rank debug-logged regardless of pass/fail

### Quality call

- [ ] System prompt establishes an experienced NYT editor persona
- [ ] System prompt describes the target difficulty day concretely (style,
      solver expectations)
- [ ] System prompt covers the relevant NYT crossword conventions
- [ ] Prompt framing is neutral — no implied preferred verdict (sycophancy
      guard)
- [ ] Convention compliance evaluated before rubric scales
- [ ] Convention failure rejects the clue immediately; scales skipped
- [ ] Tense and number agreement checked
- [ ] Wordplay indicator (`?`) presence/absence checked
- [ ] Abbreviation signaling checked
- [ ] Fill-in-the-blank format (`___`) checked
- [ ] All six rubric scales scored 1–5 with rationale: angle craft,
      misdirection, wordplay complexity, reference accessibility, surface
      coherence, fairness of deception
- [ ] Fairness of deception defaults to 5 for clues with no misdirection
- [ ] Scale scores compared against day profile ranges for difficulty
      calibration

### Combined verdict

- [ ] Final pass requires both calls to pass
- [ ] Validation failure (network error, parse error after retries) does not
      abort the pipeline; error logged and attached to clue
- [ ] Both calls' inputs and outputs logged in human-readable form

---

## Open questions

**Difficulty context in the solvability call:** Three approaches, each with
different error profiles:

| Approach             | False positives | False negatives         | Notes                                                |
| -------------------- | --------------- | ----------------------- | ---------------------------------------------------- |
| No day context       | low             | elevated for hard clues | Clue must stand entirely alone                       |
| Day named            | elevated        | lower                   | Model's answer-type priors contaminate guesses       |
| Style hint (default) | low             | moderate                | Calibrates persistence without contaminating guesses |

The default (style hint) describes how hard to think — "this clue may use
wordplay or misdirection; consider multiple interpretations" — without naming
the day or implying anything about answer type. Revisit if N calibration reveals
systematic false negatives on hard clues.

**N calibration (solvability pass threshold):** N should be calibrated against a
golden set of known-good clues at each difficulty level. The crossing-letter
limitation means N may need to be more permissive than real solving conditions
would suggest.

**Pass/fail combination logic:** The final verdict integrates solvability rank
and the quality profile. Neither call alone is sufficient. The thresholds and
weighting are TBD; this requires empirical work against the golden set.

**Quality call multi-turn:** Whether the quality call benefits from its own
scratchpad turn before scoring is worth testing empirically.

**Golden set:** A set of known-good NYT clues with known answers, spanning all
difficulty levels, is needed to calibrate N, validate the day profiles, and
derive the pass/fail thresholds. Building this set is a follow-up task.
