#!/usr/bin/env python3
"""
Programmatic Seating Arrangement MCQ Generator
Generates linear and circular seating problems with constraint-solving verification.
"""

import random
import json
import itertools
from typing import List, Dict, Optional, Tuple


# ── Name Pool ────────────────────────────────────────────────────────────────

NAMES = [
    "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z",
    "A", "B", "C", "D", "E", "F", "G", "H",
]


# ── Constraint Types ─────────────────────────────────────────────────────────

class Constraint:
    """Base constraint class."""
    def check(self, arrangement: List[str], is_circular: bool) -> bool:
        raise NotImplementedError

    def describe(self) -> str:
        raise NotImplementedError


class AdjacentConstraint(Constraint):
    """Two people sit next to each other."""
    def __init__(self, a: str, b: str):
        self.a = a
        self.b = b

    def check(self, arr: List[str], is_circular: bool) -> bool:
        ia, ib = arr.index(self.a), arr.index(self.b)
        diff = abs(ia - ib)
        if diff == 1:
            return True
        if is_circular and diff == len(arr) - 1:
            return True
        return False

    def describe(self) -> str:
        return f"{self.a} and {self.b} are adjacent (sit next to each other)"


class NotAdjacentConstraint(Constraint):
    """Two people do NOT sit next to each other."""
    def __init__(self, a: str, b: str):
        self.a = a
        self.b = b

    def check(self, arr: List[str], is_circular: bool) -> bool:
        ia, ib = arr.index(self.a), arr.index(self.b)
        diff = abs(ia - ib)
        if diff == 1:
            return False
        if is_circular and diff == len(arr) - 1:
            return False
        return True

    def describe(self) -> str:
        return f"{self.a} and {self.b} do NOT sit next to each other"


class FixedPositionConstraint(Constraint):
    """A person sits at a specific position."""
    def __init__(self, person: str, position: int, position_desc: str):
        self.person = person
        self.position = position
        self.position_desc = position_desc

    def check(self, arr: List[str], is_circular: bool) -> bool:
        return arr.index(self.person) == self.position

    def describe(self) -> str:
        return f"{self.person} sits at {self.position_desc}"


class LeftOfConstraint(Constraint):
    """A sits immediately to the left of B (linear: lower index)."""
    def __init__(self, a: str, b: str):
        self.a = a
        self.b = b

    def check(self, arr: List[str], is_circular: bool) -> bool:
        ia, ib = arr.index(self.a), arr.index(self.b)
        if ia + 1 == ib:
            return True
        if is_circular and ia == len(arr) - 1 and ib == 0:
            return True
        return False

    def describe(self) -> str:
        return f"{self.a} sits immediately to the left of {self.b}"


class BetweenConstraint(Constraint):
    """C sits between A and B (i.e. C is adjacent to both A and B)."""
    def __init__(self, middle: str, left: str, right: str):
        self.middle = middle
        self.left = left
        self.right = right

    def check(self, arr: List[str], is_circular: bool) -> bool:
        im = arr.index(self.middle)
        il = arr.index(self.left)
        ir = arr.index(self.right)
        n = len(arr)

        def is_adjacent(i, j):
            diff = abs(i - j)
            return diff == 1 or (is_circular and diff == n - 1)

        return is_adjacent(im, il) and is_adjacent(im, ir)

    def describe(self) -> str:
        return f"{self.middle} sits between {self.left} and {self.right}"


class ExactGapConstraint(Constraint):
    """Exactly k seats between A and B."""
    def __init__(self, a: str, b: str, gap: int):
        self.a = a
        self.b = b
        self.gap = gap

    def check(self, arr: List[str], is_circular: bool) -> bool:
        ia, ib = arr.index(self.a), arr.index(self.b)
        diff = abs(ia - ib) - 1  # seats between
        if diff == self.gap:
            return True
        if is_circular:
            n = len(arr)
            other_diff = n - abs(ia - ib) - 1
            if other_diff == self.gap:
                return True
        return False

    def describe(self) -> str:
        return f"There {'is' if self.gap == 1 else 'are'} exactly {self.gap} seat{'s' if self.gap != 1 else ''} between {self.a} and {self.b}"


class EndConstraint(Constraint):
    """A person sits at one of the ends (linear only)."""
    def __init__(self, person: str):
        self.person = person

    def check(self, arr: List[str], is_circular: bool) -> bool:
        if is_circular:
            return True  # No ends in circular
        idx = arr.index(self.person)
        return idx == 0 or idx == len(arr) - 1

    def describe(self) -> str:
        return f"{self.person} sits at one of the ends"


class FacingConstraint(Constraint):
    """For two-row linear: A faces B."""
    pass  # Placeholder for future extension


# ── Constraint Solver ────────────────────────────────────────────────────────

def solve_arrangement(people: List[str], constraints: List[Constraint],
                      is_circular: bool) -> List[List[str]]:
    """Brute-force solve: find all valid arrangements."""
    solutions = []

    if is_circular:
        # Fix first person to break rotational symmetry
        first = people[0]
        rest = people[1:]
        for perm in itertools.permutations(rest):
            arr = [first] + list(perm)
            if all(c.check(arr, True) for c in constraints):
                solutions.append(arr)
            if len(solutions) > 200:  # Cap for performance
                break
    else:
        for perm in itertools.permutations(people):
            arr = list(perm)
            if all(c.check(arr, False) for c in constraints):
                solutions.append(arr)
            if len(solutions) > 200:
                break

    return solutions


# ── Question Builder ─────────────────────────────────────────────────────────

def generate_linear_arrangement(n_people: int = 5) -> Optional[Dict]:
    """Generate a linear seating arrangement question."""
    if n_people > 7:
        n_people = 7  # Cap for brute-force tractability

    names = random.sample(NAMES, n_people)
    random.shuffle(names)

    # Generate a random valid arrangement first
    arrangement = list(names)
    random.shuffle(arrangement)

    # Build constraints based on this arrangement
    constraints = []
    constraint_descs = []

    n_constraints = random.randint(3, min(5, n_people + 1))

    constraint_types = ["adjacent", "left_of", "between", "end", "not_adjacent", "gap"]
    used_pairs = set()

    for _ in range(n_constraints * 3):  # Over-generate, dedup
        if len(constraints) >= n_constraints:
            break

        ctype = random.choice(constraint_types)

        if ctype == "adjacent":
            i = random.randint(0, n_people - 2)
            a, b = arrangement[i], arrangement[i + 1]
            if (a, b) in used_pairs or (b, a) in used_pairs:
                continue
            used_pairs.add((a, b))
            constraints.append(AdjacentConstraint(a, b))
            constraint_descs.append(constraints[-1].describe())

        elif ctype == "left_of":
            i = random.randint(0, n_people - 2)
            a, b = arrangement[i], arrangement[i + 1]
            if (a, b) in used_pairs or (b, a) in used_pairs:
                continue
            used_pairs.add((a, b))
            constraints.append(LeftOfConstraint(a, b))
            constraint_descs.append(constraints[-1].describe())

        elif ctype == "between" and n_people >= 3:
            i = random.randint(1, n_people - 2)
            m = arrangement[i]
            l, r = arrangement[i - 1], arrangement[i + 1]
            if m in [c.middle for c in constraints if isinstance(c, BetweenConstraint)]:
                continue
            constraints.append(BetweenConstraint(m, l, r))
            constraint_descs.append(constraints[-1].describe())

        elif ctype == "end":
            person = random.choice([arrangement[0], arrangement[-1]])
            if any(isinstance(c, EndConstraint) and c.person == person for c in constraints):
                continue
            constraints.append(EndConstraint(person))
            constraint_descs.append(constraints[-1].describe())

        elif ctype == "not_adjacent":
            i = random.randint(0, n_people - 1)
            j = random.randint(0, n_people - 1)
            if abs(i - j) <= 1:
                continue
            a, b = arrangement[i], arrangement[j]
            if (a, b) in used_pairs or (b, a) in used_pairs:
                continue
            used_pairs.add((a, b))
            constraints.append(NotAdjacentConstraint(a, b))
            constraint_descs.append(constraints[-1].describe())

        elif ctype == "gap":
            i = random.randint(0, n_people - 1)
            j = random.randint(0, n_people - 1)
            if i == j:
                continue
            gap = abs(i - j) - 1
            if gap < 1 or gap > 3:
                continue
            a, b = arrangement[i], arrangement[j]
            if (a, b) in used_pairs or (b, a) in used_pairs:
                continue
            used_pairs.add((a, b))
            constraints.append(ExactGapConstraint(a, b, gap))
            constraint_descs.append(constraints[-1].describe())

    if len(constraints) < 3:
        return None

    # Verify: solve and check solution uniqueness
    solutions = solve_arrangement(names, constraints, False)

    if len(solutions) == 0:
        return None  # Shouldn't happen since we built from valid arrangement
    if len(solutions) > 20:
        return None  # Too many solutions, constraints too weak

    valid_arrangement = solutions[0]

    return _build_mcq(valid_arrangement, solutions, constraints, constraint_descs,
                      is_circular=False, names=names)


def generate_circular_arrangement(n_people: int = 5) -> Optional[Dict]:
    """Generate a circular seating arrangement question."""
    if n_people > 6:
        n_people = 6  # Smaller for circular

    names = random.sample(NAMES, n_people)
    arrangement = list(names)
    random.shuffle(arrangement)

    constraints = []
    constraint_descs = []
    n_constraints = random.randint(3, min(5, n_people))
    used_pairs = set()

    for _ in range(n_constraints * 3):
        if len(constraints) >= n_constraints:
            break

        ctype = random.choice(["adjacent", "left_of", "not_adjacent", "between", "gap"])

        if ctype == "adjacent":
            i = random.randint(0, n_people - 1)
            j = (i + 1) % n_people
            a, b = arrangement[i], arrangement[j]
            if (a, b) in used_pairs or (b, a) in used_pairs:
                continue
            used_pairs.add((a, b))
            constraints.append(AdjacentConstraint(a, b))
            constraint_descs.append(constraints[-1].describe())

        elif ctype == "left_of":
            i = random.randint(0, n_people - 1)
            j = (i + 1) % n_people
            a, b = arrangement[i], arrangement[j]
            if (a, b) in used_pairs or (b, a) in used_pairs:
                continue
            used_pairs.add((a, b))
            constraints.append(LeftOfConstraint(a, b))
            constraint_descs.append(constraints[-1].describe())

        elif ctype == "not_adjacent":
            i = random.randint(0, n_people - 1)
            j = random.randint(0, n_people - 1)
            ci = (i + 1) % n_people
            pi = (i - 1) % n_people
            if j == ci or j == pi or j == i:
                continue
            a, b = arrangement[i], arrangement[j]
            if (a, b) in used_pairs or (b, a) in used_pairs:
                continue
            used_pairs.add((a, b))
            constraints.append(NotAdjacentConstraint(a, b))
            constraint_descs.append(constraints[-1].describe())

        elif ctype == "between":
            i = random.randint(0, n_people - 1)
            l_idx = (i - 1) % n_people
            r_idx = (i + 1) % n_people
            m = arrangement[i]
            l, r = arrangement[l_idx], arrangement[r_idx]
            if m in [c.middle for c in constraints if isinstance(c, BetweenConstraint)]:
                continue
            constraints.append(BetweenConstraint(m, l, r))
            constraint_descs.append(constraints[-1].describe())

        elif ctype == "gap":
            i = random.randint(0, n_people - 1)
            j = random.randint(0, n_people - 1)
            if i == j:
                continue
            # Circular gap (min distance - 1)
            dist = min(abs(i - j), n_people - abs(i - j))
            gap = dist - 1
            if gap < 1 or gap > 2:
                continue
            a, b = arrangement[i], arrangement[j]
            if (a, b) in used_pairs or (b, a) in used_pairs:
                continue
            used_pairs.add((a, b))
            constraints.append(ExactGapConstraint(a, b, gap))
            constraint_descs.append(constraints[-1].describe())

    if len(constraints) < 3:
        return None

    solutions = solve_arrangement(names, constraints, True)

    if len(solutions) == 0:
        return None
    if len(solutions) > 20:
        return None

    valid_arrangement = solutions[0]

    return _build_mcq(valid_arrangement, solutions, constraints, constraint_descs,
                      is_circular=True, names=names)


def _build_mcq(arrangement: List[str], solutions: List[List[str]],
               constraints: List[Constraint], constraint_descs: List[str],
               is_circular: bool, names: List[str]) -> Optional[Dict]:
    """Build an MCQ from a solved arrangement."""

    # Pick question type
    q_type = random.choice(["who_sits_at", "who_adjacent", "who_between", "position_of"])
    n = len(arrangement)

    if q_type == "who_sits_at":
        # "Who sits at position X?"
        if not is_circular:
            pos_options = {0: "the left end", n-1: "the right end"}
            pos = random.choice([0, n-1])
            pos_desc = pos_options[pos]
        else:
            # "Who sits opposite to X?" (only if even number)
            if n % 2 == 0:
                idx = random.randint(0, n - 1)
                opp_idx = (idx + n // 2) % n
                person_asking = arrangement[idx]
                correct = arrangement[opp_idx]
                question = f"Who sits directly opposite to {person_asking}?"
            else:
                # "Who sits to the immediate left of X?"
                idx = random.randint(0, n - 1)
                left_idx = (idx - 1) % n
                person_asking = arrangement[idx]
                correct = arrangement[left_idx]
                question = f"Who sits to the immediate left of {person_asking}?"

            if is_circular and n % 2 == 0:
                pass  # question and correct already set
            elif is_circular:
                pass  # question and correct already set
            # Build question for circular case
            setting = "circular table" if is_circular else "row (left to right)"
            clue_str = ". ".join(constraint_descs) + "."
            full_question = f"{n} persons {', '.join(names)} are seated around a {setting}. {clue_str} {question}"

            # Distractors
            others = [p for p in names if p != correct]
            random.shuffle(others)
            distractors = others[:3]

            correct_idx = random.randint(0, 3)
            options = distractors[:3]
            options.insert(correct_idx, correct)
            answer_letter = chr(65 + correct_idx)

            choices = [f"{chr(65+i)}) {opt}" for i, opt in enumerate(options)]
            explanation = f"Arrangement: {' - '.join(arrangement)}. {correct} is the answer."

            return {
                "topic": "Puzzles/Seating Arrangements (Linear, Circular)",
                "question": full_question,
                "choices": choices,
                "answer": answer_letter,
                "explanation": explanation[:300]
            }

        # Linear position question
        correct = arrangement[pos]
        setting = "row (left to right)"
        clue_str = ". ".join(constraint_descs) + "."
        question = f"{n} persons {', '.join(names)} are seated in a {setting}. {clue_str} Who sits at {pos_desc}?"

        others = [p for p in names if p != correct]
        random.shuffle(others)

        correct_idx = random.randint(0, 3)
        options = others[:3]
        options.insert(correct_idx, correct)
        answer_letter = chr(65 + correct_idx)

        choices = [f"{chr(65+i)}) {opt}" for i, opt in enumerate(options)]
        explanation = f"Arrangement: {' - '.join(arrangement)}. {correct} sits at {pos_desc}."

        return {
            "topic": "Puzzles/Seating Arrangements (Linear, Circular)",
            "question": question,
            "choices": choices,
            "answer": answer_letter,
            "explanation": explanation[:300]
        }

    elif q_type == "who_adjacent":
        idx = random.randint(1 if not is_circular else 0, n - 2 if not is_circular else n - 1)
        person = arrangement[idx]

        # Who sits to the left?
        if is_circular:
            left_idx = (idx - 1) % n
        else:
            if idx == 0:
                return None
            left_idx = idx - 1
        correct = arrangement[left_idx]

        setting = "circular table" if is_circular else "row (left to right)"
        clue_str = ". ".join(constraint_descs) + "."
        question = f"{n} persons {', '.join(names)} are seated {'around' if is_circular else 'in'} a {setting}. {clue_str} Who sits to the immediate left of {person}?"

        others = [p for p in names if p != correct and p != person]
        random.shuffle(others)

        correct_idx_q = random.randint(0, 3)
        options = others[:3]
        options.insert(correct_idx_q, correct)
        answer_letter = chr(65 + correct_idx_q)

        choices = [f"{chr(65+i)}) {opt}" for i, opt in enumerate(options)]
        explanation = f"Arrangement: {' - '.join(arrangement)}. {correct} is to the left of {person}."

        return {
            "topic": "Puzzles/Seating Arrangements (Linear, Circular)",
            "question": question,
            "choices": choices,
            "answer": answer_letter,
            "explanation": explanation[:300]
        }

    elif q_type == "who_between":
        if n < 3:
            return None
        if not is_circular:
            idx = random.randint(1, n - 2)
            correct = arrangement[idx]
            left_p = arrangement[idx - 1]
            right_p = arrangement[idx + 1]
        else:
            idx = random.randint(0, n - 1)
            correct = arrangement[idx]
            left_p = arrangement[(idx - 1) % n]
            right_p = arrangement[(idx + 1) % n]

        setting = "circular table" if is_circular else "row (left to right)"
        clue_str = ". ".join(constraint_descs) + "."
        question = f"{n} persons {', '.join(names)} are seated {'around' if is_circular else 'in'} a {setting}. {clue_str} Who sits between {left_p} and {right_p}?"

        others = [p for p in names if p not in (correct, left_p, right_p)]
        random.shuffle(others)

        correct_idx_q = random.randint(0, 3)
        options = others[:3]
        if len(options) < 3:
            return None
        options.insert(correct_idx_q, correct)
        answer_letter = chr(65 + correct_idx_q)

        choices = [f"{chr(65+i)}) {opt}" for i, opt in enumerate(options)]
        explanation = f"Arrangement: {' - '.join(arrangement)}. {correct} sits between {left_p} and {right_p}."

        return {
            "topic": "Puzzles/Seating Arrangements (Linear, Circular)",
            "question": question,
            "choices": choices,
            "answer": answer_letter,
            "explanation": explanation[:300]
        }

    elif q_type == "position_of":
        person = random.choice(arrangement)
        correct_pos = arrangement.index(person)

        if not is_circular:
            # Count from left
            pos_from_left = correct_pos + 1
            pos_from_right = n - correct_pos
            side = random.choice(["left", "right"])
            if side == "left":
                correct_ans = str(pos_from_left)
                question_suffix = f"What is {person}'s position from the left end?"
            else:
                correct_ans = str(pos_from_right)
                question_suffix = f"What is {person}'s position from the right end?"
        else:
            return None  # Position-counting doesn't apply well to circular

        setting = "row (left to right)"
        clue_str = ". ".join(constraint_descs) + "."
        question = f"{n} persons {', '.join(names)} are seated in a {setting}. {clue_str} {question_suffix}"

        # Numeric distractors
        all_positions = [str(i) for i in range(1, n + 1)]
        distractors = [p for p in all_positions if p != correct_ans]
        random.shuffle(distractors)

        correct_idx_q = random.randint(0, 3)
        options = distractors[:3]
        options.insert(correct_idx_q, correct_ans)
        answer_letter = chr(65 + correct_idx_q)

        choices = [f"{chr(65+i)}) {opt}" for i, opt in enumerate(options)]
        explanation = f"Arrangement: {' - '.join(arrangement)}. {person} is at position {correct_ans} from the {side}."

        return {
            "topic": "Puzzles/Seating Arrangements (Linear, Circular)",
            "question": question,
            "choices": choices,
            "answer": answer_letter,
            "explanation": explanation[:300]
        }

    return None


# ── Dataset Generation ───────────────────────────────────────────────────────

def generate_dataset(num_questions: int = 200, seed: int = 42) -> List[Dict]:
    """Generate a full dataset of seating arrangement questions."""
    random.seed(seed)
    questions = []
    seen = set()

    attempts = 0
    while len(questions) < num_questions and attempts < num_questions * 50:
        # Alternate between linear and circular
        n_people = random.choice([4, 5, 5, 6, 6, 7])
        if random.random() < 0.5:
            q = generate_linear_arrangement(n_people)
        else:
            q = generate_circular_arrangement(min(n_people, 6))

        if q and q["question"] not in seen:
            seen.add(q["question"])
            questions.append(q)
        attempts += 1

        # Progress feedback
        if attempts % 500 == 0 and attempts > 0:
            print(f"  ... {len(questions)}/{num_questions} generated ({attempts} attempts)")

    random.shuffle(questions)
    return questions[:num_questions]


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate seating arrangement MCQs")
    parser.add_argument("--num", type=int, default=200, help="Number of questions")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--output", type=str, default="data/generated/seating_arrangements.json")
    args = parser.parse_args()

    questions = generate_dataset(args.num, args.seed)
    import os
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(questions, f, indent=2)
    print(f"Generated {len(questions)} seating arrangement questions → {args.output}")
