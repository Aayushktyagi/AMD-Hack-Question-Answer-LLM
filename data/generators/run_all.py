#!/usr/bin/env python3
"""
Master runner: generate all datasets and combine them.
"""

import os
import sys
import json

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from generate_syllogisms import generate_dataset as gen_syllogisms
from generate_series import generate_dataset as gen_series
from generate_blood_relations import generate_dataset as gen_blood
from generate_seating import generate_dataset as gen_seating


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate all AAIPL training datasets")
    parser.add_argument("--num-per-topic", type=int, default=200,
                        help="Number of questions per topic (default: 200)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--output-dir", type=str, default="data/generated",
                        help="Output directory for generated datasets")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    # ── Generate each topic ──────────────────────────────────────────────
    generators = {
        "syllogisms": gen_syllogisms,
        "mixed_series": gen_series,
        "blood_relations": gen_blood,
        "seating_arrangements": gen_seating,
    }

    all_questions = []

    for name, gen_fn in generators.items():
        print(f"\n{'='*60}")
        print(f"Generating {name} ({args.num_per_topic} questions)...")
        print(f"{'='*60}")

        questions = gen_fn(num_questions=args.num_per_topic, seed=args.seed)
        print(f"  ✓ Generated {len(questions)} {name} questions")

        # Save individual topic file
        outpath = os.path.join(args.output_dir, f"{name}.json")
        with open(outpath, "w") as f:
            json.dump(questions, f, indent=2)
        print(f"  → Saved to {outpath}")

        all_questions.extend(questions)

    # ── Save combined dataset ────────────────────────────────────────────
    import random
    random.seed(args.seed)
    random.shuffle(all_questions)

    combined_path = os.path.join(args.output_dir, "all_topics_combined.json")
    with open(combined_path, "w") as f:
        json.dump(all_questions, f, indent=2)

    print(f"\n{'='*60}")
    print(f"TOTAL: {len(all_questions)} questions across all topics")
    print(f"Combined → {combined_path}")
    print(f"{'='*60}")

    # ── Summary stats ────────────────────────────────────────────────────
    topic_counts = {}
    for q in all_questions:
        t = q.get("topic", "Unknown")
        topic_counts[t] = topic_counts.get(t, 0) + 1

    print("\nBreakdown:")
    for t, c in sorted(topic_counts.items()):
        print(f"  {t}: {c}")


if __name__ == "__main__":
    main()
