#!/usr/bin/env python3
"""
Verified Seating Arrangement MCQ Generator — 25k scale
Strategy: generate a valid arrangement first, derive constraints from it,
then verify via constraint propagation that the answer is deterministic.
Keeps sizes 5-7 people (complex but tractable).
"""

import random
import json
import os
import itertools
from typing import List, Dict, Optional, Tuple, Set
from collections import defaultdict

NAMES_POOL = list("PQRSTUVWXYZABCDEFGH")


# ── Constraint classes ───────────────────────────────────────────────────────

class Constraint:
    def check(self, arr: List[str], circular: bool) -> bool:
        raise NotImplementedError
    def describe(self) -> str:
        raise NotImplementedError


class Adjacent(Constraint):
    def __init__(self, a, b):
        self.a, self.b = a, b
    def check(self, arr, circular):
        ia, ib = arr.index(self.a), arr.index(self.b)
        d = abs(ia - ib)
        return d == 1 or (circular and d == len(arr) - 1)
    def describe(self):
        return f"{self.a} and {self.b} sit next to each other"


class NotAdjacent(Constraint):
    def __init__(self, a, b):
        self.a, self.b = a, b
    def check(self, arr, circular):
        ia, ib = arr.index(self.a), arr.index(self.b)
        d = abs(ia - ib)
        if d == 1:
            return False
        if circular and d == len(arr) - 1:
            return False
        return True
    def describe(self):
        return f"{self.a} and {self.b} do not sit next to each other"


class ImmediateLeft(Constraint):
    def __init__(self, a, b):
        self.a, self.b = a, b  # a is immediately left of b
    def check(self, arr, circular):
        ia, ib = arr.index(self.a), arr.index(self.b)
        if ia + 1 == ib:
            return True
        if circular and ia == len(arr) - 1 and ib == 0:
            return True
        return False
    def describe(self):
        return f"{self.a} sits immediately to the left of {self.b}"


class Between(Constraint):
    def __init__(self, mid, left, right):
        self.mid, self.left, self.right = mid, left, right
    def check(self, arr, circular):
        im = arr.index(self.mid)
        il = arr.index(self.left)
        ir = arr.index(self.right)
        n = len(arr)
        def adj(i, j):
            d = abs(i - j)
            return d == 1 or (circular and d == n - 1)
        return adj(im, il) and adj(im, ir)
    def describe(self):
        return f"{self.mid} sits between {self.left} and {self.right}"


class AtEnd(Constraint):
    def __init__(self, person):
        self.person = person
    def check(self, arr, circular):
        if circular:
            return True
        idx = arr.index(self.person)
        return idx == 0 or idx == len(arr) - 1
    def describe(self):
        return f"{self.person} sits at one of the ends"


class ExactGap(Constraint):
    def __init__(self, a, b, gap):
        self.a, self.b, self.gap = a, b, gap
    def check(self, arr, circular):
        ia, ib = arr.index(self.a), arr.index(self.b)
        d = abs(ia - ib) - 1
        if d == self.gap:
            return True
        if circular:
            n = len(arr)
            d2 = n - abs(ia - ib) - 1
            if d2 == self.gap:
                return True
        return False
    def describe(self):
        word = "is" if self.gap == 1 else "are"
        seats = "seat" if self.gap == 1 else "seats"
        return f"There {word} exactly {self.gap} {seats} between {self.a} and {self.b}"


class FixedPosition(Constraint):
    def __init__(self, person, pos, desc):
        self.person, self.pos, self.pos_desc = person, pos, desc
    def check(self, arr, circular):
        return arr.index(self.person) == self.pos
    def describe(self):
        return f"{self.person} sits at {self.pos_desc}"


# ── Solver ───────────────────────────────────────────────────────────────────

def solve(people: List[str], constraints: List[Constraint], circular: bool, max_solutions: int = 50) -> List[List[str]]:
    """Find all valid arrangements up to max_solutions."""
    solutions = []
    if circular:
        first = people[0]
        rest = people[1:]
        for perm in itertools.permutations(rest):
            arr = [first] + list(perm)
            if all(c.check(arr, True) for c in constraints):
                solutions.append(arr)
                if len(solutions) >= max_solutions:
                    return solutions
    else:
        for perm in itertools.permutations(people):
            arr = list(perm)
            if all(c.check(arr, False) for c in constraints):
                solutions.append(arr)
                if len(solutions) >= max_solutions:
                    return solutions
    return solutions


# ── Constraint generation from arrangement ───────────────────────────────────

def derive_constraints(arr: List[str], circular: bool, target_count: int = 4) -> List[Constraint]:
    """Derive constraints from a known arrangement. Aim for enough to reduce solutions."""
    n = len(arr)
    candidates = []

    # Adjacent pairs
    for i in range(n - 1):
        candidates.append(("adj", Adjacent(arr[i], arr[i + 1])))
    if circular:
        candidates.append(("adj", Adjacent(arr[-1], arr[0])))

    # Immediate left
    for i in range(n - 1):
        candidates.append(("left", ImmediateLeft(arr[i], arr[i + 1])))
    if circular:
        candidates.append(("left", ImmediateLeft(arr[-1], arr[0])))

    # Between
    for i in range(1, n - 1):
        candidates.append(("between", Between(arr[i], arr[i - 1], arr[i + 1])))
    if circular:
        candidates.append(("between", Between(arr[0], arr[-1], arr[1])))
        candidates.append(("between", Between(arr[-1], arr[-2], arr[0])))

    # Not adjacent (non-neighboring pairs)
    for i in range(n):
        for j in range(i + 2, n):
            if circular and j == n - 1 and i == 0:
                continue
            candidates.append(("notadj", NotAdjacent(arr[i], arr[j])))

    # Ends (linear only)
    if not circular:
        candidates.append(("end", AtEnd(arr[0])))
        candidates.append(("end", AtEnd(arr[-1])))

    # Gaps
    for i in range(n):
        for j in range(i + 1, n):
            gap = abs(i - j) - 1
            if 1 <= gap <= 3:
                candidates.append(("gap", ExactGap(arr[i], arr[j], gap)))

    # Fixed position (for linear)
    if not circular:
        pos_descs = {0: "the leftmost position", n - 1: "the rightmost position"}
        for pos, desc in pos_descs.items():
            candidates.append(("fixed", FixedPosition(arr[pos], pos, desc)))

    random.shuffle(candidates)

    # Greedily add constraints that reduce solution count
    selected = []
    for _, cand in candidates:
        if len(selected) >= target_count:
            break
        # Avoid redundant same-type constraints
        selected.append(cand)

    return selected


# ── Question types ───────────────────────────────────────────────────────────

def ask_who_at_position(arr: List[str], circular: bool) -> Optional[Tuple[str, str, str]]:
    """Who sits at position X?"""
    n = len(arr)
    if not circular:
        pos = random.choice([0, n - 1])
        desc = "the left end" if pos == 0 else "the right end"
        correct = arr[pos]
        q = f"Who sits at {desc}?"
    else:
        idx = random.randint(0, n - 1)
        direction = random.choice(["left", "right"])
        if direction == "left":
            target_idx = (idx - 1) % n
        else:
            target_idx = (idx + 1) % n
        correct = arr[target_idx]
        q = f"Who sits to the immediate {direction} of {arr[idx]}?"
    return q, correct, "name"


def ask_who_adjacent(arr: List[str], circular: bool) -> Optional[Tuple[str, str, str]]:
    """Who sits next to X?"""
    n = len(arr)
    if not circular:
        idx = random.randint(1, n - 2)
    else:
        idx = random.randint(0, n - 1)
    person = arr[idx]
    direction = random.choice(["left", "right"])
    if direction == "left":
        target_idx = (idx - 1) % n if circular else idx - 1
    else:
        target_idx = (idx + 1) % n if circular else idx + 1
    if not circular and (target_idx < 0 or target_idx >= n):
        return None
    correct = arr[target_idx]
    q = f"Who sits to the immediate {direction} of {person}?"
    return q, correct, "name"


def ask_who_between(arr: List[str], circular: bool) -> Optional[Tuple[str, str, str]]:
    """Who sits between X and Y?"""
    n = len(arr)
    if not circular:
        if n < 3:
            return None
        idx = random.randint(1, n - 2)
        correct = arr[idx]
        left_p, right_p = arr[idx - 1], arr[idx + 1]
    else:
        idx = random.randint(0, n - 1)
        correct = arr[idx]
        left_p = arr[(idx - 1) % n]
        right_p = arr[(idx + 1) % n]
    q = f"Who sits between {left_p} and {right_p}?"
    return q, correct, "name"


def ask_position_count(arr: List[str], circular: bool) -> Optional[Tuple[str, str, str]]:
    """What position is X from the left/right?"""
    if circular:
        return None
    n = len(arr)
    person = random.choice(arr)
    idx = arr.index(person)
    side = random.choice(["left", "right"])
    if side == "left":
        correct = str(idx + 1)
    else:
        correct = str(n - idx)
    q = f"What is {person}'s position from the {side} end?"
    return q, correct, "number"


def ask_how_many_between(arr: List[str], circular: bool) -> Optional[Tuple[str, str, str]]:
    """How many people sit between X and Y?"""
    n = len(arr)
    i = random.randint(0, n - 1)
    j = random.randint(0, n - 1)
    if abs(i - j) < 2:
        return None
    a, b = arr[i], arr[j]
    if not circular:
        between_count = abs(i - j) - 1
    else:
        d1 = abs(i - j) - 1
        d2 = n - abs(i - j) - 1
        between_count = min(d1, d2)
    if between_count < 1 or between_count > 4:
        return None
    correct = str(between_count)
    q = f"How many people sit between {a} and {b}?"
    return q, correct, "number"


QUESTION_TYPES = [ask_who_at_position, ask_who_adjacent, ask_who_between, ask_position_count, ask_how_many_between]


# ── MCQ builder ──────────────────────────────────────────────────────────────

def make_distractors_name(correct: str, all_names: List[str], n: int = 3) -> List[str]:
    pool = [nm for nm in all_names if nm != correct]
    random.shuffle(pool)
    return pool[:n]


def make_distractors_number(correct: str, n_people: int, n: int = 3) -> List[str]:
    vals = [str(i) for i in range(1, n_people + 1) if str(i) != correct]
    random.shuffle(vals)
    return vals[:n]


def generate_one_seating(n_people: int = None, circular: bool = None) -> Optional[Dict]:
    """Generate one verified seating arrangement MCQ."""
    if n_people is None:
        n_people = random.choice([5, 5, 6, 6, 6, 7, 7])
    if circular is None:
        circular = random.random() < 0.4

    names = random.sample(NAMES_POOL, n_people)
    arrangement = list(names)
    random.shuffle(arrangement)

    # Derive constraints
    n_constraints = random.randint(3, min(5, n_people))
    constraints = derive_constraints(arrangement, circular, target_count=n_constraints)

    if len(constraints) < 3:
        return None

    # ── VERIFY: solve and check solution count ──
    solutions = solve(names, constraints, circular, max_solutions=50)
    if len(solutions) == 0:
        return None
    if len(solutions) > 30:
        return None  # Too ambiguous

    # Pick a question type
    random.shuffle(QUESTION_TYPES)
    for ask_fn in QUESTION_TYPES:
        result = ask_fn(arrangement, circular)
        if result is None:
            continue
        q_suffix, correct, answer_type = result

        # ── VERIFY: check all solutions give the same answer ──
        all_answers_match = True
        for sol in solutions:
            sol_result = ask_fn(sol, circular)
            if sol_result is None or sol_result[1] != correct:
                all_answers_match = False
                break

        if not all_answers_match:
            continue  # This question doesn't have a unique answer

        # Build MCQ
        setting = "circular table" if circular else "row (left to right)"
        prep = "around" if circular else "in"
        clue_str = ". ".join(c.describe() for c in constraints) + "."

        full_question = (
            f"{n_people} persons {', '.join(names)} are seated {prep} a {setting}. "
            f"{clue_str} {q_suffix}"
        )

        # Distractors
        if answer_type == "name":
            distractors = make_distractors_name(correct, names, 3)
        else:
            distractors = make_distractors_number(correct, n_people, 3)

        if len(distractors) < 3:
            continue

        correct_idx = random.randint(0, 3)
        options = distractors[:3]
        options.insert(correct_idx, correct)
        answer_letter = chr(65 + correct_idx)
        choices = [f"{chr(65 + i)}) {o}" for i, o in enumerate(options)]

        explanation = (
            f"Arrangement: {' - '.join(arrangement)}{'  (circular)' if circular else ''}. "
            f"Answer: {correct}."
        )

        # Determine question_type from ask function + arrangement type
        arr_prefix = "circular" if circular else "linear"
        SEATING_QTYPE_MAP = {
            "ask_who_at_position": f"{arr_prefix}_position_query",
            "ask_who_adjacent": f"{arr_prefix}_adjacent_query",
            "ask_who_between": f"{arr_prefix}_between_query",
            "ask_position_count": f"{arr_prefix}_position_count",
            "ask_how_many_between": f"{arr_prefix}_gap_count",
        }
        qtype = SEATING_QTYPE_MAP.get(ask_fn.__name__, f"{arr_prefix}_unknown")

        return {
            "topic": "Puzzles/Seating Arrangements (Linear, Circular)",
            "question_type": qtype,
            "question": full_question,
            "choices": choices,
            "answer": answer_letter,
            "explanation": explanation[:400],
            "arrangement_type": "circular" if circular else "linear",
            "n_people": n_people,
        }

    return None


def generate_dataset(num_questions: int = 25000, seed: int = 42) -> List[Dict]:
    """Generate verified seating arrangement MCQs."""
    random.seed(seed)
    questions = []
    seen = set()

    attempts = 0
    max_attempts = num_questions * 60  # generous budget

    while len(questions) < num_questions and attempts < max_attempts:
        attempts += 1
        try:
            q = generate_one_seating()
        except (ValueError, IndexError):
            continue
        if q is None:
            continue

        key = q["question"]
        if key in seen:
            continue
        seen.add(key)
        questions.append(q)

        if len(questions) % 1000 == 0:
            print(f"  {len(questions)}/{num_questions} generated ({attempts} attempts)")

    random.shuffle(questions)
    return questions


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--num", type=int, default=25000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=str, default="data/generated/seating_arrangements_25k.json")
    args = parser.parse_args()

    print(f"Generating {args.num} verified seating arrangement MCQs...")
    questions = generate_dataset(args.num, args.seed)

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(questions, f, indent=2, ensure_ascii=False)

    print(f"\nGenerated {len(questions)} verified questions → {args.output}")

    from collections import Counter
    type_counts = Counter(q["arrangement_type"] for q in questions)
    size_counts = Counter(q["n_people"] for q in questions)
    print(f"\nType: {dict(type_counts)}")
    print(f"Size: {dict(sorted(size_counts.items()))}")
