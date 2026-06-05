#!/usr/bin/env bash
# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT
#
# Probe the model's wordplay-indicator reasoning in isolation.
# Tweak CLUE, ANSWER, DAY, or the system prompt text to iterate.

MODEL="${MODEL:-gemma4:26b}"
CLUE="${CLUE:-Starts a fire?}"
ANSWER="${ANSWER:-MATCH}"
DAY="${DAY:-Wednesday — mid-week difficulty. Deliberate misdirection or wordplay is expected. References may be moderately niche. A practiced solver should need to consider multiple interpretations before the answer clicks.}"

# -s: suppress curl progress output
# jq -r: raw string output — strips outer JSON quotes from the reply text
curl -s http://localhost:11434/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d @- <<EOF | jq -r '.choices[0].message.content'
{
  "model": "$MODEL",
  "options": {"num_ctx": 8192},
  "reasoning_effort": "none",
  "messages": [
    {
      "role": "system",
      "content": "You are an experienced NYT crossword editor evaluating a submitted clue.\n\nTarget day: $DAY\n\nFocus only on the wordplay indicator convention:\n\nWordplay indicator: a ? suffix is required when no reasonable surface reading leads to the answer — the solver can only arrive via wordplay, a pun, or a non-obvious secondary meaning. It is forbidden when any reasonable surface reading already gives the answer, even if extra meanings exist. A ? that only hints at secondary meanings not needed to reach the answer is unearned. What counts as \"reasonable\" scales with difficulty: harder days expect more lateral readings, so ? appears less often on Friday/Saturday."
    },
    {
      "role": "user",
      "content": "Clue: $CLUE\nAnswer: $ANSWER\n\nEvaluate: is the ? use correct for this clue? Reason step by step, then give a verdict: PASS or FAIL."
    }
  ],
  "stream": false
}
EOF
