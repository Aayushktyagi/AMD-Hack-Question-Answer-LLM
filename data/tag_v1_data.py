#!/usr/bin/env python3
"""Tag v1 generated datasets with question_type."""
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
from tag_missing_subtypes import infer_syllogism_type, infer_series_type, infer_seating_type, infer_blood_type

base = os.path.dirname(os.path.abspath(__file__))
files = [
    os.path.join(base, "generated", "syllogisms.json"),
    os.path.join(base, "generated", "blood_relations.json"),
    os.path.join(base, "generated", "seating_arrangements.json"),
    os.path.join(base, "generated", "mixed_series.json"),
]

for fname in files:
    if not os.path.exists(fname):
        print(f"SKIP: {fname}")
        continue
    with open(fname) as f:
        data = json.load(f)
    tagged = 0
    for item in data:
        if "question_type" in item:
            continue
        topic = item.get("topic", "")
        q_text = item.get("question", "")
        hops = item.get("hops")
        if "Syllogism" in topic:
            item["question_type"] = infer_syllogism_type(q_text)
        elif "Series" in topic or "Pattern" in topic:
            item["question_type"] = infer_series_type(q_text)
        elif "Seating" in topic:
            item["question_type"] = infer_seating_type(q_text)
        elif "Blood" in topic or "Family" in topic:
            item["question_type"] = infer_blood_type(q_text, hops)
        tagged += 1
    with open(fname, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"{os.path.basename(fname)}: tagged {tagged}/{len(data)}")

print("Done!")
