#!/usr/bin/env python3
"""
Convert CLUTRR CSV datasets into AAIPL blood relation MCQ JSON format.
Reads all CLUTRR data_* directories and produces one combined JSON in parsed/.
"""

import os
import json
import random
import pandas as pd
import glob
import re

random.seed(42)

CLUTRR_DATA_DIR = "/Users/aayushtyagi/Aayush/PhD/Learning/Hackathron/AMD_Hackathron/clutrr/data"
OUTPUT_DIR = "/Users/aayushtyagi/Aayush/PhD/Learning/Hackathron/AMD_Hackathron/AAIPL/data/parsed"

# All possible family relations for distractor generation
RELATIONS = [
    "father", "mother", "son", "daughter", "brother", "sister",
    "grandfather", "grandmother", "grandson", "granddaughter",
    "uncle", "aunt", "nephew", "niece", "cousin",
    "husband", "wife", "father-in-law", "mother-in-law",
    "son-in-law", "daughter-in-law", "brother-in-law", "sister-in-law",
]


def parse_task_info(csv_filename: str) -> dict:
    """Extract task number and chain length from filename like '1.3_train.csv'."""
    base = os.path.basename(csv_filename)
    match = re.match(r"(\d+)\.(\d+)_(train|test)\.csv", base)
    if match:
        return {
            "task": int(match.group(1)),
            "chain_length": int(match.group(2)),
            "split": match.group(3),
        }
    return None


def generate_distractors(correct_answer: str, n: int = 3) -> list:
    """Generate plausible but incorrect relationship distractors."""
    pool = [r for r in RELATIONS if r.lower() != correct_answer.lower()]
    random.shuffle(pool)
    return pool[:n]


def clutrr_row_to_mcq(row, task_info: dict) -> dict:
    """Convert a single CLUTRR CSV row to AAIPL MCQ format."""
    story = row["story"].strip()
    target = row["target"].strip()
    query = row["query"]  # e.g. "('Harold', 'Sharon')"

    # Parse query tuple
    try:
        # query is like "('Harold', 'Sharon')" or "['Harold', 'Sharon']"
        names = re.findall(r"'([^']+)'", query)
        if len(names) >= 2:
            person_a, person_b = names[0], names[1]
        else:
            return None
    except Exception:
        return None

    # Build question text
    # Remove bracket markers from story: [Name] -> Name
    clean_story = story.replace("[", "").replace("]", "")
    question_text = (
        f"Read the following information carefully:\n{clean_story}\n"
        f"How is {person_b} related to {person_a}?"
    )

    # Build choices
    distractors = generate_distractors(target, 3)
    if len(distractors) < 3:
        return None

    correct_idx = random.randint(0, 3)
    options = distractors[:3]
    options.insert(correct_idx, target.capitalize())
    # Capitalize all options
    options = [o.capitalize() for o in options]
    answer_letter = chr(65 + correct_idx)

    choices = [f"{chr(65 + i)}) {opt}" for i, opt in enumerate(options)]

    # Build explanation from proof_state if available
    explanation = f"Following the family relationship chain in the story, {person_b} is the {target} of {person_a}."
    if "f_comb" in row and pd.notna(row["f_comb"]):
        explanation += f" Relation path: {row['f_comb']}."

    task_chain = f"{task_info['task']}.{task_info['chain_length']}"

    return {
        "topic": "Blood Relations and Family Tree/Family tree logic",
        "question": question_text,
        "choices": choices,
        "answer": answer_letter,
        "explanation": explanation,
        "task_chain_length": task_chain,
    }


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    all_questions = []
    data_dirs = sorted(glob.glob(os.path.join(CLUTRR_DATA_DIR, "data_*/")))

    if not data_dirs:
        # Try without trailing slash
        data_dirs = sorted(glob.glob(os.path.join(CLUTRR_DATA_DIR, "data_*")))
        data_dirs = [d for d in data_dirs if os.path.isdir(d)]

    print(f"Found {len(data_dirs)} CLUTRR data directories")

    for data_dir in data_dirs:
        csv_files = glob.glob(os.path.join(data_dir, "*.csv"))
        for csv_file in csv_files:
            task_info = parse_task_info(csv_file)
            if task_info is None:
                print(f"  Skipping {csv_file} (can't parse task info)")
                continue

            df = pd.read_csv(csv_file)
            converted = 0
            for _, row in df.iterrows():
                mcq = clutrr_row_to_mcq(row, task_info)
                if mcq:
                    all_questions.append(mcq)
                    converted += 1

            task_chain = f"{task_info['task']}.{task_info['chain_length']}"
            print(f"  {os.path.basename(csv_file)}: {converted}/{len(df)} rows converted (task {task_chain}, {task_info['split']})")

    random.shuffle(all_questions)

    # Save combined file
    out_path = os.path.join(OUTPUT_DIR, "blood_relations_clutrr.json")
    with open(out_path, "w") as f:
        json.dump(all_questions, f, indent=2, ensure_ascii=False)
    print(f"\nTotal: {len(all_questions)} MCQs → {out_path}")

    # Print breakdown
    from collections import Counter
    task_counts = Counter(q["task_chain_length"] for q in all_questions)
    print("\nBreakdown by task.chain_length:")
    for k, v in sorted(task_counts.items()):
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
