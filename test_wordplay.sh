#!/usr/bin/env bash
# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT
#
# Probe the model's wordplay-indicator reasoning in isolation.
# Tweak CLUE, ANSWER, DAY, or MODEL to iterate.
# Compare against test_conventions.sh to see whether multi-convention context
# affects reasoning quality on convention 2.

MODEL="${MODEL:-gemma4:26b}"
CLUE="${CLUE:-Starts a fire?}"
ANSWER="${ANSWER:-MATCH}"
DAY="${DAY:-Wednesday — mid-week difficulty. Deliberate misdirection or wordplay is expected. References may be moderately niche. A practiced solver should need to consider multiple interpretations before the answer clicks.}"

echo "=== $(date) MODEL=$MODEL CLUE=$CLUE ANSWER=$ANSWER ==="

SYSTEM_PROMPT="You are an experienced NYT crossword editor reviewing clues for
publication. Your role is quality gatekeeping: catch errors before they reach
solvers. The submission comes from a well-intentioned but inexperienced
constructor — expect mistakes, and apply each standard rigorously. A clue passes
only when it genuinely satisfies the requirement, not when a justification can
be found for it.

Target day: ${DAY}"

# Mirrors the wordplay convention from _CONVENTIONS_SCRATCHPAD_PROMPT in
# clue_gen/quality.py, evaluated in isolation.
WORDPLAY_PROMPT=$(cat <<'EOF'
Evaluate the wordplay indicator convention for this clue. Reason step by step,
then give a verdict: PASS or FAIL.

Wordplay indicator: reason from the clue to the answer, not the other way
around. Imagine a solver seeing this clue for the first time, with no knowledge
of the answer. Ask: does the clue's surface reading hand them the answer
directly, or must they make a lateral leap to get there? A ? suffix is required
when no reasonable surface reading leads to the answer — the solver can only
arrive via wordplay, a pun, or a non-obvious secondary meaning. It is forbidden
when any reasonable surface reading already gives the answer. The answer having
multiple meanings is irrelevant; the only question is whether the clue's surface
requires lateral thinking to reach it. A ? that only hints at secondary meanings
not needed to reach the answer is unearned. What counts as "reasonable" scales
with difficulty: harder days expect more lateral readings, so ? appears less
often on Friday/Saturday.

Examples:

Earned (? required):
- "Semi professional?" → TEAMSTER: The surface ("partly professional") gives
  no path to TEAMSTER. Only once you pivot — "semi" = semi-truck, TEAMSTER =
  professional truck driver — does the answer emerge. ? is required.
- "Perpetual homebody?" → SNAIL: The surface ("someone who never goes out")
  gives no path to SNAIL. The pivot: take "homebody" literally — a snail
  carries its home on its body. ? is required.

Unearned (? forbidden):
- "Keeps time?" → CLOCK: Keeping time is a clock's primary function. The
  surface delivers directly. ? is unearned even though CLOCK has other meanings;
  those meanings aren't needed to reach the answer.
- "Points the way?" → COMPASS: Pointing a direction is what a compass does.
  The surface leads straight to the answer. ? is unearned.
- "Draws blood?" → NEEDLE: Drawing blood is what a needle does in its most
  common use. The surface delivers directly. ? is unearned.
EOF
)

USER_CONTENT="Clue: ${CLUE}
Answer: ${ANSWER}

${WORDPLAY_PROMPT}"

# jq -n: build JSON from scratch rather than reading from stdin
# jq --arg: inject shell variables as properly escaped JSON strings
request=$(jq -n \
  --arg model "$MODEL" \
  --arg system "$SYSTEM_PROMPT" \
  --arg user "$USER_CONTENT" \
  '{
    model: $model,
    options: {num_ctx: 8192},
    messages: [
      {role: "system", content: $system},
      {role: "user", content: $user}
    ],
    stream: false
  }')

start=$(date +%s)

# -s: suppress curl progress output
response=$(curl -s http://localhost:11434/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d "$request")

elapsed=$(( $(date +%s) - start ))

reasoning=$(echo "$response" | jq -r '.choices[0].message.reasoning // empty')
content=$(echo "$response" | jq -r '.choices[0].message.content')

if [ -n "$reasoning" ]; then
  echo "--- reasoning ---"
  echo "$reasoning"
  echo ""
fi
echo "--- response ---"
echo "$content"
echo "(${elapsed}s)"
