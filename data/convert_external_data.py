#!/usr/bin/env python3
"""
Convert External_Data into our standard format.
─────────────────────────────────────────────────
Reads the 4 External_Data JSON files and produces one unified JSON list
matching the format used in data/generated/ and data/curated/:

{
    "topic":         "...",
    "question_type": "...",
    "question":      "Full question text (with directions context)",
    "choices":       ["A) ...", "B) ...", "C) ...", "D) ..."],
    "answer":        "A"|"B"|"C"|"D",
    "explanation":   "..."
}

Questions with answer = "E" are dropped (our pipeline only supports A-D).

Usage:
    python convert_external_data.py                          # default paths
    python convert_external_data.py --output external.json   # custom output
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path


# ═══════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════

LETTERS = ["A", "B", "C", "D"]

# Topic strings matching our generated data exactly
TOPIC_SERIES     = "Series and Patterns/Mixed Series (Alphanumeric)"
TOPIC_BLOOD      = "Blood Relations and Family Tree/Family tree logic"
TOPIC_SEATING    = "Puzzles/Seating Arrangements (Linear, Circular)"
TOPIC_SYLLOGISMS = "Logical Reasoning/Syllogisms"


# ═══════════════════════════════════════════════════════════════
# OPTION CLEANING
# ═══════════════════════════════════════════════════════════════

_LETTER_PREFIX_RE = re.compile(r"^[A-E][.):\s]+\s*")


def strip_letter_prefix(text: str) -> str:
    """Remove leading letter prefix like 'A. ', 'B) ', 'C: ' etc."""
    return _LETTER_PREFIX_RE.sub("", text).strip()


def format_choices(raw_options, take=4):
    """
    Normalise options to ['A) text', 'B) text', 'C) text', 'D) text'].
    Handles: list of plain strings, list with letter prefixes, dict {A: text, ...}.
    """
    if isinstance(raw_options, dict):
        texts = [raw_options.get(l, "") for l in LETTERS[:take]]
    elif isinstance(raw_options, list):
        texts = [strip_letter_prefix(o) for o in raw_options[:take]]
    else:
        raise ValueError(f"Unexpected options type: {type(raw_options)}")
    return [f"{LETTERS[i]}) {texts[i]}" for i in range(len(texts))]


# ═══════════════════════════════════════════════════════════════
# PER-FILE CONVERTERS
# ═══════════════════════════════════════════════════════════════

def convert_alpha_numeric_series(data):
    """
    alpha_numeric_series.json:
    List of sets with 'directions' + 'questions'.
    Each question has: question, options (list), answer, explanation.
    """
    results = []
    for s in data:
        directions = s.get("directions", "").strip()
        for q in s["questions"]:
            if q["answer"] not in LETTERS:
                continue
            # Compose question text: directions + question
            q_text = f"Directions: {directions}\n\nQuestion: {q['question']}"
            results.append({
                "topic": TOPIC_SERIES,
                "question_type": "alphanumeric_next_term",
                "question": q_text,
                "choices": format_choices(q["options"]),
                "answer": q["answer"],
                "explanation": q.get("explanation", ""),
            })
    return results


def convert_blood_relation(data):
    """
    blood_relation.json:
    List of sets with 'set_directions' + 'questions'.
    Each question has: question_text, options (list with 'A. ...' prefixes), answer, explanation.
    """
    results = []
    for s in data:
        directions = s.get("set_directions", "").strip()
        for q in s["questions"]:
            if q["answer"] not in LETTERS:
                continue
            # question key is 'question_text' (not 'question')
            q_body = q.get("question_text", q.get("question", ""))
            q_text = f"Read the following information carefully:\n{directions}\n\n{q_body}"
            results.append({
                "topic": TOPIC_BLOOD,
                "question_type": "complex_relation_4hop",
                "question": q_text,
                "choices": format_choices(q["options"]),
                "answer": q["answer"],
                "explanation": q.get("explanation", ""),
            })
    return results


def _detect_seating_type(directions: str) -> str:
    """Heuristic to pick the right question_type sub-tag for seating."""
    lc = directions.lower()
    is_circular = any(kw in lc for kw in ["circular", "circle", "round table"])
    # defaults
    if is_circular:
        return "circular_position_query"
    return "linear_position_query"


def convert_seating_arrangement(data):
    """
    seating_arrangement.json:
    List of sets with 'directions' + 'questions'.
    Each question has: question, options (list, no prefix), answer, explanation.
    """
    results = []
    for s in data:
        directions = s.get("directions", "").strip()
        qtype = _detect_seating_type(directions)
        for q in s["questions"]:
            if q["answer"] not in LETTERS:
                continue
            q_text = f"Read the following information carefully:\n{directions}\n\nQuestion: {q['question']}"
            results.append({
                "topic": TOPIC_SEATING,
                "question_type": qtype,
                "question": q_text,
                "choices": format_choices(q["options"]),
                "answer": q["answer"],
                "explanation": q.get("explanation", ""),
            })
    return results


def _detect_syllogism_type(options) -> str:
    """Heuristic to pick the right question_type sub-tag for syllogism."""
    if isinstance(options, dict):
        vals = " ".join(options.values()).lower()
    else:
        vals = " ".join(str(o) for o in options).lower()
    if "both" in vals and "neither" in vals:
        return "both_neither_conclusion"
    if "does not follow" in vals:
        return "which_does_not_follow"
    return "which_conclusion_follows"


def convert_syllogism_test(data):
    """
    syllogism_test.json:
    Flat list. Each item has: statements, conclusions, options (dict), answer, explanation.
    """
    results = []
    for q in data:
        if q["answer"] not in LETTERS:
            continue
        # Compose question from statements + conclusions
        stmts = "\n".join(f"  {st}" for st in q["statements"])
        concl = "\n".join(f"  {cl}" for cl in q["conclusions"])
        q_text = (
            f"Statements:\n{stmts}\n\n"
            f"Conclusions:\n{concl}\n\n"
            f"Which of the following is correct?"
        )
        qtype = _detect_syllogism_type(q["options"])
        results.append({
            "topic": TOPIC_SYLLOGISMS,
            "question_type": qtype,
            "question": q_text,
            "choices": format_choices(q["options"]),
            "answer": q["answer"],
            "explanation": q.get("explanation", ""),
        })
    return results


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Convert External_Data to standard format")
    parser.add_argument(
        "--input-dir", type=str,
        default=os.path.join(os.path.dirname(__file__), "External_Data"),
        help="Path to External_Data directory",
    )
    parser.add_argument(
        "--output", type=str,
        default=os.path.join(os.path.dirname(__file__), "external", "external_converted.json"),
        help="Output JSON path",
    )
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_path = Path(args.output)

    # File → converter mapping
    converters = {
        "alpha_numeric_series.json": convert_alpha_numeric_series,
        "blood_relation.json":      convert_blood_relation,
        "seating_arrangement.json":  convert_seating_arrangement,
        "syllogism_test.json":       convert_syllogism_test,
    }

    all_items = []
    for fname, converter in converters.items():
        fpath = input_dir / fname
        if not fpath.exists():
            print(f"⚠  Missing: {fpath}  — skipping")
            continue
        with open(fpath) as f:
            data = json.load(f)
        items = converter(data)
        total_raw = (
            sum(len(s["questions"]) for s in data)
            if isinstance(data, list) and len(data) > 0 and "questions" in data[0]
            else len(data)
        )
        print(f"✓  {fname:35s} → {len(items):4d} kept / {total_raw:4d} total  (dropped {total_raw - len(items)} with answer=E)")
        all_items.extend(items)

    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(all_items, f, indent=2, ensure_ascii=False)

    print(f"\n{'─'*60}")
    print(f"Total converted: {len(all_items)}")
    print(f"Saved to: {output_path.resolve()}")

    # Quick breakdown
    from collections import Counter
    topic_counts = Counter(item["topic"].split("/")[0] for item in all_items)
    qtype_counts = Counter(item["question_type"] for item in all_items)
    print(f"\nBy topic:")
    for t, c in sorted(topic_counts.items()):
        print(f"  {t:40s}: {c}")
    print(f"\nBy question_type:")
    for qt, c in sorted(qtype_counts.items()):
        print(f"  {qt:35s}: {c}")

    # Validate
    print(f"\nValidation:")
    errors = 0
    for i, item in enumerate(all_items):
        if item["answer"] not in LETTERS:
            print(f"  ERROR [{i}]: answer={item['answer']} not in A-D")
            errors += 1
        if len(item["choices"]) != 4:
            print(f"  ERROR [{i}]: {len(item['choices'])} choices instead of 4")
            errors += 1
        for j, ch in enumerate(item["choices"]):
            if not ch.startswith(f"{LETTERS[j]}) "):
                print(f"  ERROR [{i}]: choice[{j}] missing '{LETTERS[j]}) ' prefix: {ch[:30]}")
                errors += 1
    if errors == 0:
        print("  ✓ All items pass validation")
    else:
        print(f"  ✗ {errors} validation errors")


if __name__ == "__main__":
    main()
