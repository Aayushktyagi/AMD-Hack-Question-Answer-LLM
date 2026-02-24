#!/usr/bin/env python3
"""Quick inspection of External_Data files."""
import json, os

BASE = os.path.join(os.path.dirname(__file__), "External_Data")

# ── alpha_numeric_series ──
with open(os.path.join(BASE, "alpha_numeric_series.json")) as f:
    data = json.load(f)
print("=== alpha_numeric_series.json ===")
print(f"Sets: {len(data)}")
total_q = sum(len(s["questions"]) for s in data)
print(f"Total questions: {total_q}")
answers = set()
opts_counts = set()
for s in data:
    for q in s["questions"]:
        answers.add(q["answer"])
        opts_counts.add(len(q["options"]))
print(f"Answer values: {sorted(answers)}")
print(f"Options counts: {opts_counts}")
print(f"Q keys: {list(data[0]['questions'][0].keys())}")
print()

# ── blood_relation ──
with open(os.path.join(BASE, "blood_relation.json")) as f:
    data = json.load(f)
print("=== blood_relation.json ===")
print(f"Sets: {len(data)}")
total_q = sum(len(s["questions"]) for s in data)
print(f"Total questions: {total_q}")
answers = set()
opts_counts = set()
for s in data:
    for q in s["questions"]:
        answers.add(q["answer"])
        opts_counts.add(len(q["options"]))
print(f"Answer values: {sorted(answers)}")
print(f"Options counts: {opts_counts}")
print(f"Q keys: {list(data[0]['questions'][0].keys())}")
# Check option format
print(f"Sample options: {data[0]['questions'][0]['options'][:3]}")
print()

# ── seating_arrangement ──
with open(os.path.join(BASE, "seating_arrangement.json")) as f:
    data = json.load(f)
print("=== seating_arrangement.json ===")
print(f"Sets: {len(data)}")
total_q = sum(len(s["questions"]) for s in data)
print(f"Total questions: {total_q}")
answers = set()
opts_counts = set()
for s in data:
    for q in s["questions"]:
        answers.add(q["answer"])
        opts_counts.add(len(q["options"]))
print(f"Answer values: {sorted(answers)}")
print(f"Options counts: {opts_counts}")
print(f"Q keys: {list(data[0]['questions'][0].keys())}")
print(f"Sample options: {data[0]['questions'][0]['options'][:3]}")
print()

# ── syllogism_test ──
with open(os.path.join(BASE, "syllogism_test.json")) as f:
    data = json.load(f)
print("=== syllogism_test.json ===")
print(f"Items: {len(data)}")
answers = set()
for q in data:
    answers.add(q["answer"])
print(f"Answer values: {sorted(answers)}")
print(f"Options type: {type(data[0]['options']).__name__}")
if isinstance(data[0]["options"], dict):
    print(f"Options keys: {list(data[0]['options'].keys())}")
print(f"Q keys: {list(data[0].keys())}")
print(f"Sample #2: {json.dumps(data[1], indent=2)[:600]}")
