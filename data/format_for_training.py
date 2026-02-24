#!/usr/bin/env python3
"""
Format generated MCQ datasets into training-ready formats for:
  1. Q-Agent (SFT): teach the model to GENERATE questions in the correct JSON MCQ format
  2. A-Agent (SFT): teach the model to ANSWER MCQ questions correctly

Supports output formats:
  - Alpaca (instruction/input/output) for Unsloth
  - ChatML (messages list) for transformers / Qwen
"""

import os
import json
import random
from typing import List, Dict


# ── Q-Agent: generate questions ──────────────────────────────────────────────

QAGENT_SYSTEM_PROMPT = """You are a competitive question generator for logical reasoning challenges. 
Generate a challenging multiple-choice question (MCQ) in valid JSON format for the given topic.
The question must have exactly 4 choices (A, B, C, D) with exactly one correct answer.
Include a clear explanation of why the correct answer is right."""

QAGENT_TOPICS = {
    "Logical Reasoning/Syllogisms": [
        "Generate a syllogism-based MCQ with two premises and a conclusion to evaluate.",
        "Create a logical reasoning MCQ based on categorical syllogisms.",
        "Generate an MCQ testing deductive reasoning with All/Some/No statements.",
    ],
    "Blood Relations and Family Tree/Family tree logic": [
        "Generate a blood relations MCQ involving family relationship chains.",
        "Create an MCQ where the solver must trace family tree relationships.",
        "Generate a family relationship puzzle as an MCQ.",
    ],
    "Series and Patterns/Mixed Series (Alphanumeric)": [
        "Generate a number/letter series completion MCQ.",
        "Create an MCQ asking for the next term in a mixed alphanumeric series.",
        "Generate a series pattern recognition MCQ.",
    ],
    "Puzzles/Seating Arrangements (Linear, Circular)": [
        "Generate a seating arrangement MCQ for persons in a row.",
        "Create a circular seating arrangement puzzle as an MCQ.",
        "Generate a linear/circular seating constraint puzzle.",
    ],
}

# ── Per-subtype Q-Agent instructions ─────────────────────────────────────────
# Maps question_type → specific generation instruction for the Q-Agent

QAGENT_SUBTYPE_INSTRUCTIONS = {
    # ── Syllogisms ──
    "both_neither_conclusion": "Generate a syllogism MCQ presenting two conclusions from given premises. The choices should be: Only I follows / Only II follows / Both follow / Neither follows.",
    "which_conclusion_follows": "Generate a syllogism MCQ with 4 conclusion options where the solver must identify which one logically follows from the premises.",
    "which_does_not_follow": "Generate a syllogism MCQ with 4 conclusion options where the solver must identify which one does NOT logically follow from the premises.",
    "count_valid_conclusions": "Generate a syllogism MCQ listing 4-5 conclusions and asking how many of them logically follow from the premises.",
    "true_false_determine": "Generate a syllogism MCQ presenting a single conclusion and asking whether it is Definitely True, Definitely False, or Cannot Be Determined.",
    "strengthen_weaken_premise": "Generate a syllogism MCQ asking which additional premise would make a given conclusion necessarily true.",
    # ── Series ──
    "numeric_next_term": "Generate a numeric series MCQ asking for the next term. Use patterns such as arithmetic, geometric, squares, cubes, Fibonacci, triangular numbers, or mixed operations.",
    "alphanumeric_next_term": "Generate an alphanumeric series MCQ asking for the next term. Use patterns combining letters and numbers with systematic progression.",
    "missing_term": "Generate a series MCQ with a missing term in the middle (shown as '?'). The solver must identify the pattern and fill in the blank.",
    "odd_one_out": "Generate a series MCQ where one number is wrong. The solver must find the incorrect term that breaks the pattern.",
    # ── Blood Relations ──
    "simple_relation_2hop": "Generate a simple blood relations MCQ involving 2 relationship hops (e.g., A's father's wife). The chain should be short and direct.",
    "moderate_relation_3hop": "Generate a moderate blood relations MCQ involving 3 relationship hops. Include intermediate family members that the solver must trace through.",
    "complex_relation_4hop": "Generate a complex blood relations MCQ involving 4 relationship hops. The chain should pass through multiple generations or in-laws.",
    "extended_relation_5hop": "Generate a challenging blood relations MCQ involving 5 relationship hops. The chain should be long and require careful tracking of family connections.",
    # ── Seating Arrangements ──
    "linear_position_query": "Generate a linear seating arrangement MCQ asking who sits at a specific position (leftmost, rightmost, etc.).",
    "linear_adjacent_query": "Generate a linear seating arrangement MCQ asking who sits immediately next to a given person.",
    "linear_between_query": "Generate a linear seating arrangement MCQ asking who sits between two given persons.",
    "linear_position_count": "Generate a linear seating arrangement MCQ asking what position number a person occupies from a given end.",
    "linear_gap_count": "Generate a linear seating arrangement MCQ asking how many people sit between two given persons.",
    "circular_position_query": "Generate a circular seating arrangement MCQ asking who sits to the immediate left or right of a given person.",
    "circular_adjacent_query": "Generate a circular seating arrangement MCQ asking who sits immediately next to a given person at a circular table.",
    "circular_between_query": "Generate a circular seating arrangement MCQ asking who sits between two given persons at a circular table.",
    "circular_gap_count": "Generate a circular seating arrangement MCQ asking how many people sit between two given persons at a circular table.",
}


def format_qagent_alpaca(question: Dict) -> Dict:
    """Format one question as Q-Agent Alpaca training sample."""
    topic = question["topic"]
    question_type = question.get("question_type", "")

    # Use subtype-specific instruction if available, else fall back to topic-level
    if question_type and question_type in QAGENT_SUBTYPE_INSTRUCTIONS:
        instruction = QAGENT_SUBTYPE_INSTRUCTIONS[question_type]
    else:
        matching_prompts = []
        for key, prompts in QAGENT_TOPICS.items():
            if key in topic or topic in key:
                matching_prompts = prompts
                break
        if not matching_prompts:
            matching_prompts = [f"Generate a challenging MCQ for the topic: {topic}"]
        instruction = random.choice(matching_prompts)

    # The output is the question itself in the expected JSON format
    output_json = {
        "topic": question["topic"],
        "question": question["question"],
        "choices": question["choices"],
        "answer": question["answer"],
        "explanation": question["explanation"],
    }

    # Build user content with topic and question_type
    user_parts = [f"Topic: {topic}"]
    if question_type:
        user_parts.append(f"Question Type: {question_type}")

    return {
        "instruction": instruction,
        "input": "\n".join(user_parts),
        "output": json.dumps(output_json, ensure_ascii=False),
    }


def format_qagent_chatml(question: Dict) -> Dict:
    """Format one question as Q-Agent ChatML training sample."""
    topic = question["topic"]
    question_type = question.get("question_type", "")

    # Use subtype-specific instruction if available, else fall back to topic-level
    if question_type and question_type in QAGENT_SUBTYPE_INSTRUCTIONS:
        instruction = QAGENT_SUBTYPE_INSTRUCTIONS[question_type]
    else:
        matching_prompts = []
        for key, prompts in QAGENT_TOPICS.items():
            if key in topic or topic in key:
                matching_prompts = prompts
                break
        if not matching_prompts:
            matching_prompts = [f"Generate a challenging MCQ for the topic: {topic}"]
        instruction = random.choice(matching_prompts)

    output_json = {
        "topic": question["topic"],
        "question": question["question"],
        "choices": question["choices"],
        "answer": question["answer"],
        "explanation": question["explanation"],
    }

    # Build user content with topic and question_type
    user_parts = [instruction, f"Topic: {topic}"]
    if question_type:
        user_parts.append(f"Question Type: {question_type}")

    return {
        "messages": [
            {"role": "system", "content": QAGENT_SYSTEM_PROMPT},
            {"role": "user", "content": "\n".join(user_parts)},
            {"role": "assistant", "content": json.dumps(output_json, ensure_ascii=False)},
        ]
    }


# ── A-Agent: answer questions ────────────────────────────────────────────────

AAGENT_SYSTEM_PROMPT = """You are a logical reasoning expert. Answer the given multiple-choice question.
Output constraint: 
You must answer the question and output ONLY valid JSON.

JSON schema:
{
  "properties": {
    "reasoning": {
      "title": "Reasoning",
      "type": "string"
    },
    "answer": {
      "enum": [
        "A",
        "B",
        "C",
        "D"
      ],
      "title": "Answer",
      "type": "string"
    }
  },
  "required": [
    "reasoning",
    "answer"
  ],
  "title": "Answer",
  "type": "object"
}"""


def format_aagent_alpaca(question: Dict) -> Dict:
    """Format one question as A-Agent Alpaca training sample."""
    # Build the question text
    choices_str = "\n".join(question["choices"])
    q_text = f"{question['question']}\n\n{choices_str}"

    answer_json = {
        "reasoning": question.get("explanation", ""),
        "answer": question["answer"],
    }

    return {
        "instruction": "Answer the following multiple-choice question. Provide your reasoning first, then the correct option letter.",
        "input": q_text,
        "output": json.dumps(answer_json, ensure_ascii=False),
    }


def format_aagent_chatml(question: Dict) -> Dict:
    """Format one question as A-Agent ChatML training sample."""
    choices_str = "\n".join(question["choices"])
    q_text = f"{question['question']}\n\n{choices_str}"

    answer_json = {
        "reasoning": question.get("explanation", ""),
        "answer": question["answer"],
    }

    return {
        "messages": [
            {"role": "system", "content": AAGENT_SYSTEM_PROMPT},
            {"role": "user", "content": q_text},
            {"role": "assistant", "content": json.dumps(answer_json, ensure_ascii=False)},
        ]
    }


# ── Main ─────────────────────────────────────────────────────────────────────

def load_all_questions(data_dirs: List[str]) -> List[Dict]:
    """Load all questions from multiple directories."""
    questions = []
    for d in data_dirs:
        if not os.path.isdir(d):
            continue
        for fname in os.listdir(d):
            if fname.endswith(".json") and fname != "all_topics_combined.json":
                fpath = os.path.join(d, fname)
                with open(fpath) as f:
                    data = json.load(f)
                if isinstance(data, list):
                    questions.extend(data)
    return questions


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Format datasets for Q-Agent and A-Agent training")
    parser.add_argument("--input-dirs", nargs="+",
                        default=["data/curated", "data/generated"],
                        help="Input directories containing JSON question files")
    parser.add_argument("--output-dir", type=str, default="data/final",
                        help="Output directory for training-ready files")
    parser.add_argument("--format", choices=["alpaca", "chatml", "both"], default="both",
                        help="Output format (default: both)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--val-split", type=float, default=0.1,
                        help="Validation split ratio (default: 0.1)")
    args = parser.parse_args()

    random.seed(args.seed)
    os.makedirs(args.output_dir, exist_ok=True)

    # Load all questions
    questions = load_all_questions(args.input_dirs)
    print(f"Loaded {len(questions)} total questions")

    if not questions:
        print("No questions found! Generate data first with run_all.py")
        return

    # Shuffle and split
    random.shuffle(questions)
    n_val = max(1, int(len(questions) * args.val_split))
    val_questions = questions[:n_val]
    train_questions = questions[n_val:]

    print(f"Train: {len(train_questions)}, Val: {len(val_questions)}")

    # Topic distribution
    topic_counts = {}
    for q in questions:
        t = q.get("topic", "Unknown")
        topic_counts[t] = topic_counts.get(t, 0) + 1
    print("\nTopic distribution:")
    for t, c in sorted(topic_counts.items()):
        print(f"  {t}: {c}")

    # Format and save
    formats_to_generate = []
    if args.format in ("alpaca", "both"):
        formats_to_generate.append("alpaca")
    if args.format in ("chatml", "both"):
        formats_to_generate.append("chatml")

    for fmt in formats_to_generate:
        for agent in ["qagent", "aagent"]:
            for split_name, split_data in [("train", train_questions), ("val", val_questions)]:
                if agent == "qagent":
                    formatter = format_qagent_alpaca if fmt == "alpaca" else format_qagent_chatml
                else:
                    formatter = format_aagent_alpaca if fmt == "alpaca" else format_aagent_chatml

                formatted = [formatter(q) for q in split_data]

                outpath = os.path.join(args.output_dir, f"{agent}_{fmt}_{split_name}.json")
                with open(outpath, "w") as f:
                    json.dump(formatted, f, indent=2, ensure_ascii=False)
                print(f"  → {outpath} ({len(formatted)} samples)")

    print(f"\nDone! Training files saved to {args.output_dir}/")


if __name__ == "__main__":
    main()
