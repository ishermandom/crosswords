# Prompting guide

Reference for sessions designing or iterating on the LLM prompts in the clue
generator pipeline. Captures the empirical picture — what works, what doesn't,
and why — so each session can build on it without re-researching.

---

## The central frame

The key distinction isn't local vs. hosted — it's **reasoning vs. non-reasoning
models**. Reasoning models (o3, Claude extended thinking, Gemini 2.5 thinking)
run a hidden scratchpad before producing output: they decompose the problem,
identify assumptions, generate and evaluate candidates, and self-correct.
Non-reasoning models — including the gemma4 models we use — do a single forward
pass against the prompt as written.

Every technique in this guide is an attempt to externalize that scratchpad
explicitly into the prompt or conversation structure.

---

## Prompting fundamentals

**Specificity over inference.** Non-reasoning models take prompts literally and
won't bridge gaps. Define success criteria explicitly: not "write a good clue,"
but specify what good means — difficulty, style, what to avoid.

**Output format as scaffolding.** Specifying output structure isn't just about
parsability — it constrains the generation path. Asking for a numbered list of
options before a verdict forces the model to generate options before committing.
A JSON schema with required fields acts as a checklist. This is especially
high-leverage for non-reasoning models because it performs some of the planning
work a reasoning model does internally. See the table in the next section for
how this maps to specific reasoning steps.

**Persona/role.** Assigning a domain role steers tone and content selection,
likely by narrowing the model's conditional distribution. More important for
non-reasoning models than reasoning models. Put the persona in the system
prompt; reinforce it in the first user turn. Whether a persona persists reliably
across 4–5 turns in a multi-turn brainstorm is an open question — local models
may drift out of frame in ways hosted models don't. Treat this as something to
validate empirically during brainstorm prompt development.

**System prompt authority is weaker than expected.** Local models weight user
turns more heavily than system prompts. Put stable context (persona, task
framing, output format rules) in the system prompt, but reinforce the specific
constraint that matters immediately before the turn that must comply with it.

**Few-shot examples.** 2–5 input/output examples formatted as real conversation
turns improve format compliance and style alignment. Counterintuitively,
few-shot _hurts_ reasoning models (o3, o1) by over-constraining their internal
reasoning path — but for gemma4, it's a useful tool.

---

## Making non-reasoning models reason

Many current non-reasoning models self-initiate CoT-like reasoning without
explicit instruction. Whether gemma4 does this — and to what degree — is worth
checking empirically before adding scaffolding that may be redundant.

When scaffolding is needed, the prompt has to provide the structure a reasoning
model would generate internally:

| Reasoning model does internally   | Non-reasoning model needs in the prompt   |
| --------------------------------- | ----------------------------------------- |
| Problem decomposition             | Explicit numbered steps or sub-questions  |
| Assumption identification         | "Before answering, list your assumptions" |
| Candidate generation + evaluation | "Generate N options, then evaluate each"  |
| Self-correction                   | A separate critique turn with new info    |
| Output planning                   | A format template with labeled sections   |

**Plan-and-solve pattern.** "First understand the problem and devise a plan,
then execute step by step" outperforms vanilla "think step by step" by
separating decomposition from execution.

**Explicit scratchpad turn.** For complex generation tasks, dedicate a turn to
working through the reasoning before committing to output: "In this turn, think
through the angles. Don't write the final answer yet." This forces the model to
commit to a reasoning path before the output turn.

---

## Multi-turn conversation design

**One turn per cognitive mode.** Don't mix brainstorming with committing to an
answer in the same turn. Separation of concerns improves output quality.

**State dilution.** By turn 5+, the model attends more to recent context than to
original instructions. Mitigate by restating key constraints at each turn rather
than relying on the system prompt to persist.

**Context budget.** Token history grows with each turn. Models attend poorly to
the middle of long contexts (lost-in-the-middle effect) — put the most important
instructions at the very beginning and very end. Set `num_ctx` explicitly in API
options; Ollama defaults to 2048 and silently truncates without warning.
8192–16384 is a reasonable default for our tasks.

---

## Validation design

**LLMs cannot reliably self-correct their own reasoning without new
information.** Prompting the same model to "check its work" is largely noise and
sometimes degrades performance (ICLR 2024). Our architecture avoids this: the
validation call uses a fresh context with no access to the brainstorm
conversation. Within that fresh context it may itself be multi-turn — e.g. a
scratchpad turn before the verdict turn — in which case the multi-turn design
considerations (state dilution, one cognitive mode per turn) apply here too.

**What works for validation:**

- **Cross-model critique.** A separate API call with a neutral, independent
  system prompt. The validator should receive the clue, the answer word, and the
  evaluation criteria — nothing else.
- **Structured property checking.** Enumerate specific, concrete properties to
  verify rather than asking open-ended "is this good?" questions. Checking
  concrete properties works; open-ended quality judgments do not.

**Sycophancy.** Models suppress their own judgment when the prompt implies a
preferred answer. Evaluation criteria in the validation prompt should be neutral
— no hints about what the "correct" verdict is.

---

## JSON and structured output

Failure modes in order of frequency:

1. Conversational text wrapping the JSON ("Sure! Here's the output: `{…}`")
2. Markdown fence wrapping (` ```json … ``` `)
3. Type drift (`"true"` as a string instead of boolean `true`)
4. Structural entropy in nested output near context limits

**Reliability gradient:**

| Approach                                            | Parse rate |
| --------------------------------------------------- | ---------- |
| Plain prompting ("respond with JSON")               | ~60–70%    |
| Explicit instruction + fence-stripping + retry loop | ~90–95%    |
| Ollama `format` with JSON schema + retry            | ~99%+      |

Use Ollama's `format` parameter with a schema for all structured output calls.
Strip fences defensively regardless. Always have a retry loop. Schema
enforcement guarantees syntactic validity, not semantic correctness — the model
can produce structurally valid output with wrong values.

---

## Local model parameters

**Verbosity.** Local models fill available tokens if not constrained. "Be
concise" doesn't work. Specify counts ("exactly 3 bullet points, no preamble")
and add explicit negatives ("do not explain your reasoning, do not restate the
question"). A complementary technique: append a partial assistant message to the
`messages` list — e.g. an assistant turn containing just `"1."` — which primes
the model to continue from that point and skips warm-up prose.

**Temperature.** ~0.7 for creative generation (brainstorm); 0.1–0.2 for
deterministic scoring (validation).

**Sampler.** `min_p` (0.05–0.1) outperforms `top_p` for local models, especially
at higher temperatures. It's a local-only advantage not available in hosted
APIs. Set it explicitly alongside temperature.

---

## Applying this to our pipeline

The pipeline has two distinct LLM interactions; different parts of this guide
are most relevant to each.

**Brainstorm call** (multi-turn): focus on _Prompting fundamentals_, _Making
non-reasoning models reason_, and _Multi-turn conversation design_. Key
concerns: persona persistence, state dilution, explicit scratchpad turns,
verbosity control.

**Validation call** (fresh context, possibly multi-turn): focus on _Validation
design_ and _JSON and structured output_, plus _Multi-turn conversation design_
if the validation interaction has more than one turn. Key concerns: structured
property checking, sycophancy, schema enforcement, retry loop.

Both calls share the same parameter considerations.
