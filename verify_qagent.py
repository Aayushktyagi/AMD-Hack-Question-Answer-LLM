#!/usr/bin/env python3
"""Quick verification of qagent_chatml format with question_type tags."""
import json
from collections import Counter

with open("data/final/qagent_chatml_train.json") as f:
    data = json.load(f)

print(f"Total: {len(data)} samples\n")

# Show samples from different subtypes
seen_types = set()
for item in data:
    user_content = item["messages"][1]["content"]
    for line in user_content.split("\n"):
        if "Question Type:" in line:
            qtype = line.split("Question Type:")[1].strip()
            if qtype not in seen_types:
                seen_types.add(qtype)
                print(f"=== {qtype} ===")
                print(f"User: {user_content[:300]}")
                print()
            break
    if len(seen_types) >= 6:
        break

# Count distribution
qt_counts = Counter()
has_qt = 0
no_qt = 0
for item in data:
    user_content = item["messages"][1]["content"]
    found = False
    for line in user_content.split("\n"):
        if "Question Type:" in line:
            qtype = line.split("Question Type:")[1].strip()
            qt_counts[qtype] += 1
            has_qt += 1
            found = True
            break
    if not found:
        no_qt += 1

print(f"\n--- Distribution ---")
print(f"With question_type: {has_qt}")
print(f"Without question_type: {no_qt}")
print()
for k, v in sorted(qt_counts.items()):
    print(f"  {k}: {v}")
