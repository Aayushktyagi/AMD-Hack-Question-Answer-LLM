#!/usr/bin/env python3
"""
Programmatic Syllogism MCQ Generator
Generates valid syllogism questions with verified answers using formal logic rules.
"""

import random
import json
import itertools
from typing import List, Dict, Tuple, Optional

# ── Entities pool (diverse categories for variety) ──────────────────────────
ENTITY_POOL = [
    # Animals
    "dogs", "cats", "birds", "fish", "horses", "lions", "tigers", "eagles",
    "dolphins", "elephants", "rabbits", "wolves", "bears", "snakes", "owls",
    # People/Professions
    "doctors", "engineers", "teachers", "artists", "scientists", "lawyers",
    "musicians", "athletes", "writers", "dancers", "soldiers", "pilots",
    "chefs", "students", "professors",
    # Objects
    "books", "pens", "chairs", "tables", "phones", "cars", "keys", "rings",
    "flowers", "trees", "stones", "coins", "toys", "lamps", "clocks",
    # Abstract
    "roses", "metals", "fruits", "gems", "rivers", "mountains", "stars",
    "planets", "clouds", "islands", "crystals", "diamonds", "pearls",
]

# ── Statement types ──────────────────────────────────────────────────────────
# A = All X are Y, E = No X is Y, I = Some X are Y, O = Some X are not Y

class Statement:
    """Represents a categorical statement."""
    def __init__(self, stype: str, subject: str, predicate: str):
        self.stype = stype  # 'A', 'E', 'I', 'O'
        self.subject = subject
        self.predicate = predicate

    def text(self) -> str:
        if self.stype == 'A':
            return f"All {self.subject} are {self.predicate}"
        elif self.stype == 'E':
            return f"No {self.subject} is a {self.predicate.rstrip('s')}" if self.predicate.endswith('s') else f"No {self.subject} is {self.predicate}"
        elif self.stype == 'I':
            return f"Some {self.subject} are {self.predicate}"
        elif self.stype == 'O':
            return f"Some {self.subject} are not {self.predicate}"
        return ""


class Conclusion:
    """Represents a conclusion to evaluate."""
    def __init__(self, stype: str, subject: str, predicate: str):
        self.stype = stype
        self.subject = subject
        self.predicate = predicate

    def text(self) -> str:
        if self.stype == 'A':
            return f"All {self.subject} are {self.predicate}"
        elif self.stype == 'E':
            return f"No {self.subject} is a {self.predicate.rstrip('s')}" if self.predicate.endswith('s') else f"No {self.subject} is {self.predicate}"
        elif self.stype == 'I':
            return f"Some {self.subject} are {self.predicate}"
        elif self.stype == 'O':
            return f"Some {self.subject} are not {self.predicate}"
        return ""


# ── Valid syllogistic inference engine ───────────────────────────────────────
# Using Venn-diagram based rules for 2-premise syllogisms
# Key rules:
#   A+A → A (All X are Y, All Y are Z → All X are Z)
#   A+A → I (All X are Y, All Y are Z → Some X are Z) [by subalternation]
#   A+E → E (All X are Y, No Y is Z → No X is Z)
#   I+A → I (Some X are Y, All Y are Z → Some X are Z)
#   E+I → O (No X is Y, Some Y are Z → Some Z are not X) [careful]
#   A converts to I (All X are Y → Some Y are X)
#   I converts to I (Some X are Y → Some Y are X)
#   E converts to E (No X is Y → No Y is X)

VALID_INFERENCES_2PREMISE = {
    # (premise1_type, premise2_type) → list of (conclusion_type, subj_source, pred_source)
    # For chain: P1(S,M) + P2(M,P) → Conclusion(S,P)
    ('A', 'A'): [('A', 'S', 'P'), ('I', 'P', 'S')],  # All S are M, All M are P → All S are P, Some P are S
    ('A', 'E'): [('E', 'S', 'P'), ('O', 'P', 'S')],   # All S are M, No M is P → No S is P
    ('I', 'A'): [('I', 'S', 'P')],                      # Some S are M, All M are P → Some S are P
    ('A', 'I'): [],                                       # All S are M, Some M are P → nothing definite about S-P
    ('I', 'E'): [('O', 'S', 'P')],                       # Some S are M, No M is P → Some S are not P
    ('E', 'A'): [('O', 'P', 'S')],                       # No S is M, All M are P → Some P are not S
    ('E', 'I'): [('O', 'P', 'S')],                       # No S is M, Some M are P → Some P are not S
    ('I', 'I'): [],                                       # Two particular → nothing definite
    ('E', 'E'): [],                                       # Two negative → nothing definite
    ('O', 'A'): [],                                       # Some S not M, All M are P → nothing
    ('A', 'O'): [],                                       # All S are M, Some M not P → nothing definite about S-P
    ('I', 'O'): [],
    ('O', 'I'): [],
    ('O', 'E'): [],
    ('E', 'O'): [],
    ('O', 'O'): [],
}


def get_valid_conclusions(statements: List[Statement], entities: List[str]) -> List[Conclusion]:
    """Determine valid conclusions from given statements using syllogistic rules."""
    valid = []

    if len(statements) == 2:
        s1, s2 = statements
        # Try to find middle term and chain
        # Case: S-M, M-P (s1.predicate == s2.subject)
        if s1.predicate == s2.subject:
            S, M, P = s1.subject, s1.predicate, s2.predicate
            key = (s1.stype, s2.stype)
            if key in VALID_INFERENCES_2PREMISE:
                for (ctype, subj_src, pred_src) in VALID_INFERENCES_2PREMISE[key]:
                    subj = S if subj_src == 'S' else P
                    pred = P if pred_src == 'P' else S
                    valid.append(Conclusion(ctype, subj, pred))

        # Also check conversion: Some X are Y → Some Y are X
        # A: All X are Y → Some Y are X
        for s in statements:
            if s.stype == 'A':
                valid.append(Conclusion('I', s.predicate, s.subject))
            elif s.stype == 'I':
                valid.append(Conclusion('I', s.predicate, s.subject))
            elif s.stype == 'E':
                valid.append(Conclusion('E', s.predicate, s.subject))

    elif len(statements) == 3:
        s1, s2, s3 = statements
        # Chain: s1(A,B), s2(B,C), s3(C,D)
        # First combine s1+s2, then combine result with s3
        if s1.predicate == s2.subject and s2.predicate == s3.subject:
            # Two-step chain
            mid1 = get_valid_conclusions([s1, s2], entities)
            for mc in mid1:
                temp_stmt = Statement(mc.stype, mc.subject, mc.predicate)
                chain2 = get_valid_conclusions([temp_stmt, s3], entities)
                valid.extend(chain2)
            mid2 = get_valid_conclusions([s2, s3], entities)
            for mc in mid2:
                temp_stmt = Statement(mc.stype, mc.subject, mc.predicate)
                chain2 = get_valid_conclusions([s1, temp_stmt], entities)
                valid.extend(chain2)
            # Also add direct conversions
            for s in statements:
                if s.stype == 'A':
                    valid.append(Conclusion('I', s.predicate, s.subject))
                elif s.stype == 'I':
                    valid.append(Conclusion('I', s.predicate, s.subject))
                elif s.stype == 'E':
                    valid.append(Conclusion('E', s.predicate, s.subject))

    # Deduplicate
    seen = set()
    deduped = []
    for c in valid:
        key = (c.stype, c.subject, c.predicate)
        if key not in seen:
            seen.add(key)
            deduped.append(c)
    return deduped


def is_valid_conclusion(conclusion: Conclusion, valid_conclusions: List[Conclusion]) -> bool:
    """Check if a conclusion matches any valid conclusion."""
    for vc in valid_conclusions:
        if vc.stype == conclusion.stype and vc.subject == conclusion.subject and vc.predicate == conclusion.predicate:
            return True
    return False


def generate_invalid_conclusion(entities: List[str], valid_conclusions: List[Conclusion]) -> Conclusion:
    """Generate a plausible but INVALID conclusion."""
    attempts = 0
    while attempts < 100:
        stype = random.choice(['A', 'E', 'I', 'O'])
        subj = random.choice(entities)
        pred = random.choice([e for e in entities if e != subj])
        c = Conclusion(stype, subj, pred)
        if not is_valid_conclusion(c, valid_conclusions):
            return c
        attempts += 1
    # Fallback
    return Conclusion('A', entities[-1], entities[0])


def generate_syllogism_question(difficulty: str = "medium") -> Optional[Dict]:
    """Generate a single syllogism MCQ with verified answer."""

    # Pick entities
    entities = random.sample(ENTITY_POOL, 3 if difficulty != "hard" else 4)

    if difficulty == "easy":
        # 2 statements, straightforward chain
        patterns = [
            (['A', 'A'], entities[:3]),  # All-All chain
            (['A', 'E'], entities[:3]),  # All-No chain
            (['I', 'A'], entities[:3]),  # Some-All chain
        ]
    elif difficulty == "medium":
        patterns = [
            (['A', 'A'], entities[:3]),
            (['A', 'E'], entities[:3]),
            (['I', 'A'], entities[:3]),
            (['I', 'E'], entities[:3]),
            (['E', 'A'], entities[:3]),
            (['E', 'I'], entities[:3]),
            (['A', 'I'], entities[:3]),  # No valid conclusion possible
            (['I', 'I'], entities[:3]),  # No valid conclusion possible
        ]
    else:  # hard - 3 statements
        patterns = [
            (['A', 'A', 'A'], entities[:4]),
            (['I', 'A', 'E'], entities[:4]),
            (['A', 'I', 'A'], entities[:4]),
            (['A', 'A', 'I'], entities[:4]),
            (['A', 'E', 'I'], entities[:4]),
        ]

    stmt_types, ents = random.choice(patterns)

    # Build statements as a chain
    statements = []
    for i, stype in enumerate(stmt_types):
        statements.append(Statement(stype, ents[i], ents[i + 1]))

    # Get valid conclusions
    valid_concs = get_valid_conclusions(statements, ents)

    # Generate two candidate conclusions
    # Strategy: pick mix of valid and invalid
    all_entity_pairs = [(a, b) for a in ents for b in ents if a != b]

    if len(valid_concs) >= 2:
        # Both valid
        c1, c2 = random.sample(valid_concs[:5], min(2, len(valid_concs)))
        c1_valid, c2_valid = True, True
    elif len(valid_concs) == 1:
        c1 = valid_concs[0]
        c2 = generate_invalid_conclusion(ents, valid_concs)
        c1_valid, c2_valid = True, False
        # Randomly swap
        if random.random() > 0.5:
            c1, c2 = c2, c1
            c1_valid, c2_valid = c2_valid, c1_valid
    else:
        # No valid conclusions — generate two invalid ones
        c1 = generate_invalid_conclusion(ents, valid_concs)
        c2 = generate_invalid_conclusion(ents, valid_concs)
        while c1.text() == c2.text():
            c2 = generate_invalid_conclusion(ents, valid_concs)
        c1_valid, c2_valid = False, False

    # Determine correct answer
    if c1_valid and c2_valid:
        answer = "C"
        answer_text = "Both conclusions I and II follow"
    elif c1_valid and not c2_valid:
        answer = "A"
        answer_text = "Only conclusion I follows"
    elif not c1_valid and c2_valid:
        answer = "B"
        answer_text = "Only conclusion II follows"
    else:
        answer = "D"
        answer_text = "Neither conclusion I nor II follows"

    # Build question text
    stmt_text = "\n".join([f"{i+1}. {s.text()}." for i, s in enumerate(statements)])
    conc_text = f"I. {c1.text()}.\nII. {c2.text()}."

    question_text = f"Statements:\n{stmt_text}\nConclusions:\n{conc_text}"

    choices = [
        "A) Only conclusion I follows",
        "B) Only conclusion II follows",
        "C) Both conclusions I and II follow",
        "D) Neither conclusion I nor II follows"
    ]

    # Build explanation
    explanations = []
    for i, (conc, valid) in enumerate([(c1, c1_valid), (c2, c2_valid)]):
        num = "I" if i == 0 else "II"
        if valid:
            explanations.append(f"Conclusion {num} ('{conc.text()}') follows from the given statements.")
        else:
            explanations.append(f"Conclusion {num} ('{conc.text()}') does not necessarily follow from the statements.")
    explanation = " ".join(explanations) + f" Therefore, {answer_text.lower()}."

    return {
        "topic": "Logical Reasoning/Syllogisms",
        "question": question_text,
        "choices": choices,
        "answer": answer,
        "explanation": explanation[:300]  # Keep under token limit
    }


def generate_dataset(num_questions: int = 100, seed: int = 42) -> List[Dict]:
    """Generate a full dataset of syllogism questions."""
    random.seed(seed)
    questions = []

    # Distribution: 30% easy, 40% medium, 30% hard
    difficulties = (
        ["easy"] * int(num_questions * 0.3) +
        ["medium"] * int(num_questions * 0.4) +
        ["hard"] * (num_questions - int(num_questions * 0.3) - int(num_questions * 0.4))
    )
    random.shuffle(difficulties)

    seen = set()
    attempts = 0
    for diff in difficulties:
        while attempts < num_questions * 10:
            q = generate_syllogism_question(diff)
            if q and q["question"] not in seen:
                seen.add(q["question"])
                questions.append(q)
                break
            attempts += 1

    return questions


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate syllogism MCQs")
    parser.add_argument("--num", type=int, default=200, help="Number of questions")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--output", type=str, default="data/generated/syllogisms.json")
    args = parser.parse_args()

    questions = generate_dataset(args.num, args.seed)
    import os
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(questions, f, indent=2)
    print(f"Generated {len(questions)} syllogism questions → {args.output}")
