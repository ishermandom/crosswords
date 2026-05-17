# Acrostic Clue Generator — Spec

*Scope: what the tool does, who it serves, and what requirements it must
meet. Does not prescribe how it is built — technology choices and
implementation details belong in `plan.md`.*

## Goal

Generate crossword-style clues for acrostic puzzle answer words. The tool
takes a list of answer words and produces one clue per word (or more, if
requested), saving puzzle constructors from writing clues by hand. It runs
entirely locally with no external API calls or per-use cost.

## Users

Small group: the constructor and a few collaborators with similar workflows.
Not intended for general public distribution; polish and error handling can
be practical rather than exhaustive.

## Clue quality

**Primary criterion**: enjoyable to solve while remaining solvable.

Style is an open mix — no single style dominates:
- Straight definitions ("Capital of France" → PARIS)
- Fill-in-the-blank ("___ of the opera" → PHANTOM)
- Wordplay and double meanings
- Light cryptic elements (not full British cryptic style)
- Trivia and pop-culture references (permitted but not the default)

The tool does **not** use the source quote or author as context. Clues are
generated from the answer word alone.

## Difficulty

Calibrated to NYT crossword difficulty scale:

| Flag value | Character |
|---|---|
| `Mon` | Immediately gettable; plain definitions |
| `Tue` | Slightly tricky; mild misdirection |
| `Wed` | Moderate; some wordplay required |
| `Thu` | Misdirections, wordplay, fair but requires thought ← **default** |
| `Fri` | Hard; creative constructions, indirect definitions |
| `Sat` | Maximum difficulty; devious, multi-layered |

Flag: `--difficulty {Mon,Tue,Wed,Thu,Fri,Sat}`, default `Thu`.

## Interface

CLI tool, written in Python.

## Input

A plain-text file with one answer word (or phrase) per line, passed via
`--words FILE`.

Example:
```
ALPHA
BRAVO
CHARLIE
```

## Output

JSON printed to stdout. Tentative structure (exact shape for `--candidates N
> 1` is an open question — see below):

```json
[
  {"word": "ALPHA", "clues": ["First in line, informally"]},
  {"word": "BRAVO", "clues": ["Cheer for a performer"]}
]
```

When `--candidates N` is used, `clues` contains N entries.

## Open questions

1. **Multi-candidate output format**: When `--candidates N > 1`, should
   `clues` be a flat list of strings, or annotated objects (e.g. with
   style/difficulty metadata per candidate)? Deferred to implementation.
