#!/usr/bin/env python3
"""Deeper inspection of External_Data answer distribution & option formats."""
import json, os
from collections import Counter

BASE = os.path.join(os.path.dirname(__file__), "External_Data")

for fname in sorted(os.listdir(BASE)):
    if not fname.endswith(".json"):
        continue
    with open(os.path.join(BASE, fname)) as f:
        data = json.load(f)

    print(f"\n{'='*60}")
    print(f"  {fname}")
    print(f"{'='*60}")

    # Collect all questions into flat list
    questions = []
    if isinstance(data, list) and len(data) > 0:
        if "questions" in data[0]:
            # set-based
            for s in data:
                for q in s["questions"]:
                    questions.append(q)
        else:
            # flat (syllogism)
            questions = data

    print(f"Total questions: {len(questions)}")

    # Answer distribution
    dist = Counter(q["answer"] for q in questions)
    print(f"Answer distribution: {dict(sorted(dist.items()))}")

    # How many have answer in {A,B,C,D} vs E
    abcd = sum(1 for q in questions if q["answer"] in "ABCD")
    e_only = sum(1 for q in questions if q["answer"] == "E")
    print(f"  A-D answers: {abcd}  |  E answers: {e_only}")

    # Show sample options
    q0 = questions[0]
    opt_key = "options"
    if isinstance(q0[opt_key], dict):
        print(f"Options format: dict, keys={list(q0[opt_key].keys())}")
        print(f"  Sample: {q0[opt_key]}")
    else:
        print(f"Options format: list of {len(q0[opt_key])}")
        print(f"  Sample: {q0[opt_key]}")

    # Check if options already have letter prefixes
    if isinstance(q0[opt_key], list) and len(q0[opt_key]) > 0:
        first_opt = q0[opt_key][0]
        has_prefix = any(first_opt.startswith(p) for p in ["A.", "A)", "A "])
        print(f"  Has letter prefix: {has_prefix}")
