#!/usr/bin/env python3
"""
Programmatic Mixed Series (Alphanumeric) MCQ Generator
Generates series completion questions with verified answers.
"""

import random
import json
import string
from typing import List, Dict, Tuple, Optional


# ── Pattern Templates ────────────────────────────────────────────────────────

def letter_at(pos: int) -> str:
    """Get uppercase letter at position (0=A, 25=Z), wraps around."""
    return chr(65 + (pos % 26))


class SeriesPattern:
    """Base class for series patterns."""
    def generate(self) -> Tuple[List[str], str, str]:
        """Returns (visible_terms, answer, explanation)"""
        raise NotImplementedError


class ArithmeticSeries(SeriesPattern):
    """Simple arithmetic: a, a+d, a+2d, ..."""
    def generate(self) -> Tuple[List[str], str, str]:
        a = random.randint(1, 50)
        d = random.choice([i for i in range(-12, 13) if i != 0])
        length = random.randint(5, 7)
        terms = [a + i * d for i in range(length)]
        visible = [str(t) for t in terms[:-1]]
        answer = str(terms[-1])
        explanation = f"Arithmetic series with common difference {d}. Each term = previous + ({d}). Next: {terms[-2]} + {d} = {terms[-1]}."
        return visible, answer, explanation


class GeometricSeries(SeriesPattern):
    """Geometric: a, a*r, a*r^2, ..."""
    def generate(self) -> Tuple[List[str], str, str]:
        a = random.choice([2, 3, 4, 5, 6, 7])
        r = random.choice([2, 3, -2])
        length = random.randint(5, 6)
        terms = [a * (r ** i) for i in range(length)]
        if any(abs(t) > 10000 for t in terms):
            return self.generate()  # Retry if too large
        visible = [str(t) for t in terms[:-1]]
        answer = str(terms[-1])
        explanation = f"Geometric series with ratio {r}. Each term = previous × {r}. Next: {terms[-2]} × {r} = {terms[-1]}."
        return visible, answer, explanation


class SquareSeries(SeriesPattern):
    """Perfect squares or n^2+k patterns."""
    def generate(self) -> Tuple[List[str], str, str]:
        variant = random.choice(["squares", "squares_plus", "n_times_np1"])
        if variant == "squares":
            start = random.randint(1, 6)
            length = random.randint(5, 7)
            terms = [(start + i) ** 2 for i in range(length)]
            explanation = f"Perfect squares: {start}²={terms[0]}, {start+1}²={terms[1]}, ... {start+length-1}²={terms[-1]}."
        elif variant == "squares_plus":
            k = random.choice([1, 2, -1, 3])
            start = random.randint(1, 6)
            length = random.randint(5, 7)
            terms = [(start + i) ** 2 + k for i in range(length)]
            explanation = f"Pattern: n²+{k}. {start}²+{k}={terms[0]}, {start+1}²+{k}={terms[1]}, ... Next: {start+length-1}²+{k}={terms[-1]}."
        else:  # n*(n+1)
            start = random.randint(1, 6)
            length = random.randint(5, 7)
            terms = [(start + i) * (start + i + 1) for i in range(length)]
            explanation = f"Pattern: n×(n+1). {start}×{start+1}={terms[0]}, ... Next: {start+length-1}×{start+length}={terms[-1]}."
        visible = [str(t) for t in terms[:-1]]
        answer = str(terms[-1])
        return visible, answer, explanation


class CubeSeries(SeriesPattern):
    """Perfect cubes."""
    def generate(self) -> Tuple[List[str], str, str]:
        start = random.randint(1, 5)
        length = random.randint(5, 6)
        terms = [(start + i) ** 3 for i in range(length)]
        visible = [str(t) for t in terms[:-1]]
        answer = str(terms[-1])
        explanation = f"Perfect cubes: {start}³={terms[0]}, {start+1}³={terms[1]}, ... {start+length-1}³={terms[-1]}."
        return visible, answer, explanation


class PrimeSeries(SeriesPattern):
    """Squares of consecutive primes."""
    def generate(self) -> Tuple[List[str], str, str]:
        primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31]
        start = random.randint(0, 4)
        length = random.randint(5, 6)
        variant = random.choice(["primes", "prime_squares"])
        if variant == "primes":
            terms = primes[start:start + length]
            explanation = f"Consecutive prime numbers starting from {primes[start]}. Next prime: {terms[-1]}."
        else:
            terms = [p ** 2 for p in primes[start:start + length]]
            explanation = f"Squares of consecutive primes: {primes[start]}²={terms[0]}, ... {primes[start+length-1]}²={terms[-1]}."
        visible = [str(t) for t in terms[:-1]]
        answer = str(terms[-1])
        return visible, answer, explanation


class DoublingPlusSeries(SeriesPattern):
    """Pattern: a, a*2+k, ..."""
    def generate(self) -> Tuple[List[str], str, str]:
        a = random.randint(1, 10)
        k = random.choice([1, -1, 2, 3])
        length = random.randint(5, 6)
        terms = [a]
        for _ in range(length - 1):
            terms.append(terms[-1] * 2 + k)
            if abs(terms[-1]) > 5000:
                return self.generate()
        visible = [str(t) for t in terms[:-1]]
        answer = str(terms[-1])
        explanation = f"Each term = previous × 2 + ({k}). {terms[-3]}×2+{k}={terms[-2]}, {terms[-2]}×2+{k}={terms[-1]}."
        return visible, answer, explanation


class IncreasingDiffSeries(SeriesPattern):
    """Differences increase by constant: diffs are d, d+k, d+2k, ..."""
    def generate(self) -> Tuple[List[str], str, str]:
        a = random.randint(1, 20)
        d0 = random.randint(1, 5)
        k = random.choice([1, 2, 3])
        length = random.randint(5, 7)
        terms = [a]
        for i in range(length - 1):
            terms.append(terms[-1] + d0 + i * k)
        visible = [str(t) for t in terms[:-1]]
        answer = str(terms[-1])
        diffs = [terms[i+1] - terms[i] for i in range(len(terms)-1)]
        explanation = f"Differences: {', '.join(str(d) for d in diffs[:-1])}, {diffs[-1]} (increasing by {k}). Next: {terms[-2]} + {diffs[-1]} = {terms[-1]}."
        return visible, answer, explanation


class AlphaNumericSeries(SeriesPattern):
    """Letter-Number-Letter patterns like A1Z, B2Y, C3X."""
    def generate(self) -> Tuple[List[str], str, str]:
        variant = random.choice(["ascending_descending", "skip_letters", "double_letter"])

        if variant == "ascending_descending":
            # First ascending, number ascending, last descending
            start1 = random.randint(0, 10)
            start_num = random.randint(1, 5)
            start2 = random.randint(15, 25)
            d1 = random.choice([1, 2])
            d_num = random.choice([1, 2])
            d2 = random.choice([-1, -2])
            length = random.randint(5, 6)
            terms = []
            for i in range(length):
                l1 = letter_at(start1 + i * d1)
                n = start_num + i * d_num
                l2 = letter_at(start2 + i * d2)
                terms.append(f"{l1}{n}{l2}")
            explanation = f"First letters: +{d1}, Numbers: +{d_num}, Last letters: {d2}. Next: {terms[-1]}."

        elif variant == "skip_letters":
            # Two letters + number: AB1, CD4, EF9
            start = random.randint(0, 10)
            length = random.randint(5, 6)
            num_pattern = random.choice(["squares", "linear"])
            terms = []
            for i in range(length):
                l1 = letter_at(start + i * 2)
                l2 = letter_at(start + i * 2 + 1)
                if num_pattern == "squares":
                    n = (i + 1) ** 2
                else:
                    n = (i + 1) * 2
                terms.append(f"{l1}{l2}{n}")
            explanation = f"Letter pairs advance by 2: {terms[0][:2]},{terms[1][:2]},... Numbers: {'perfect squares' if num_pattern == 'squares' else 'multiples of 2'}. Next: {terms[-1]}."

        else:  # double_letter
            # XaY pattern: M2N, O4P, Q8R
            start1 = random.randint(0, 15)
            start2 = start1 + 1
            d = random.choice([2])
            num_start = random.choice([2, 1])
            num_mult = random.choice([2, 3])
            length = random.randint(4, 5)
            terms = []
            n = num_start
            for i in range(length):
                l1 = letter_at(start1 + i * d)
                l2 = letter_at(start2 + i * d)
                terms.append(f"{l1}{n}{l2}")
                n *= num_mult
            explanation = f"Letters skip by {d}: {terms[0][0]},{terms[1][0]},... Numbers: ×{num_mult}. Next: {terms[-1]}."

        visible = terms[:-1]
        answer = terms[-1]
        return visible, answer, explanation


class LetterOnlySeries(SeriesPattern):
    """Pure letter series: A, C, F, J, O, ..."""
    def generate(self) -> Tuple[List[str], str, str]:
        variant = random.choice(["increasing_gap", "constant_gap", "two_interleaved"])

        if variant == "increasing_gap":
            start = random.randint(0, 5)
            length = random.randint(5, 7)
            positions = [start]
            gap = random.randint(1, 3)
            for i in range(length - 1):
                positions.append(positions[-1] + gap + i)
            terms = [letter_at(p) for p in positions]
            gaps = [positions[i+1] - positions[i] for i in range(len(positions)-1)]
            explanation = f"Gaps between positions: {', '.join(str(g) for g in gaps)} (increasing by 1). Next letter at position {positions[-1]} = {terms[-1]}."

        elif variant == "constant_gap":
            start = random.randint(0, 10)
            gap = random.choice([2, 3, 4, 5])
            length = random.randint(5, 7)
            positions = [start + i * gap for i in range(length)]
            terms = [letter_at(p) for p in positions]
            explanation = f"Letters with constant gap of {gap}: {', '.join(terms[:-1])}, next: {terms[-1]}."

        else:  # two_interleaved letter patterns
            start1 = random.randint(0, 10)
            start2 = random.randint(15, 25)
            d1 = random.choice([1, 2])
            d2 = random.choice([-1, -2])
            length = random.randint(5, 6)
            terms = []
            for i in range(length):
                terms.append(letter_at(start1 + i * d1) + letter_at(start2 + i * d2))
            explanation = f"First letters: +{d1}, Second letters: {d2}. Pattern: {', '.join(terms[:-1])}, next: {terms[-1]}."

        visible = terms[:-1]
        answer = terms[-1]
        return visible, answer, explanation


class FibonacciLikeSeries(SeriesPattern):
    """Fibonacci-like: each term = sum of two previous."""
    def generate(self) -> Tuple[List[str], str, str]:
        a = random.randint(1, 10)
        b = random.randint(1, 10)
        length = random.randint(6, 8)
        terms = [a, b]
        for _ in range(length - 2):
            terms.append(terms[-1] + terms[-2])
        visible = [str(t) for t in terms[:-1]]
        answer = str(terms[-1])
        explanation = f"Each term = sum of two previous: {terms[-3]}+{terms[-2]}={terms[-1]}."
        return visible, answer, explanation


class ThreeLetterGroupSeries(SeriesPattern):
    """Three-letter group patterns like JAK, KBL, LCM."""
    def generate(self) -> Tuple[List[str], str, str]:
        s1 = random.randint(0, 15)
        s2 = random.randint(0, 15)
        s3 = random.randint(0, 15)
        d1 = random.choice([1, 2])
        d2 = random.choice([1, 2, 3])
        d3 = random.choice([1, 2])
        length = random.randint(4, 6)
        terms = []
        for i in range(length):
            l1 = letter_at(s1 + i * d1)
            l2 = letter_at(s2 + i * d2)
            l3 = letter_at(s3 + i * d3)
            terms.append(f"{l1}{l2}{l3}")
        explanation = f"First letters: +{d1}, Middle: +{d2}, Last: +{d3}. Next: {terms[-1]}."
        visible = terms[:-1]
        answer = terms[-1]
        return visible, answer, explanation


# ── Generator orchestration ──────────────────────────────────────────────────

ALL_PATTERNS = [
    ArithmeticSeries, GeometricSeries, SquareSeries, CubeSeries,
    PrimeSeries, DoublingPlusSeries, IncreasingDiffSeries,
    AlphaNumericSeries, LetterOnlySeries, FibonacciLikeSeries,
    ThreeLetterGroupSeries,
]


def generate_distractors(answer: str, num: int = 3) -> List[str]:
    """Generate plausible but incorrect distractors."""
    distractors = set()

    # Try numeric distractors
    try:
        val = int(answer)
        offsets = [-3, -2, -1, 1, 2, 3, 5, -5, 7, -7, 10, -10]
        random.shuffle(offsets)
        for off in offsets:
            d = str(val + off)
            if d != answer:
                distractors.add(d)
            if len(distractors) >= num * 2:
                break
    except ValueError:
        # String/letter answer — modify letters slightly
        for _ in range(num * 3):
            chars = list(answer)
            idx = random.randint(0, len(chars) - 1)
            if chars[idx].isalpha():
                shift = random.choice([-1, 1, 2, -2])
                new_char = chr(((ord(chars[idx].upper()) - 65 + shift) % 26) + 65)
                chars[idx] = new_char
            elif chars[idx].isdigit():
                shift = random.choice([-1, 1, 2, -2, 3])
                new_val = max(0, int(chars[idx]) + shift)
                chars[idx] = str(new_val)
            d = "".join(chars)
            if d != answer:
                distractors.add(d)

    distractor_list = list(distractors)
    random.shuffle(distractor_list)
    return distractor_list[:num]


def generate_series_question() -> Optional[Dict]:
    """Generate a single series MCQ with verified answer."""
    pattern_class = random.choice(ALL_PATTERNS)
    pattern = pattern_class()

    try:
        visible, answer, explanation = pattern.generate()
    except (RecursionError, IndexError, ValueError):
        return None

    if not visible or not answer:
        return None

    # Build question text
    series_str = ", ".join(visible)
    question_text = f"Find the next term in the series: {series_str}, ?"

    # Generate distractors
    distractor_list = generate_distractors(answer, 3)
    if len(distractor_list) < 3:
        return None  # Not enough distractors

    # Place correct answer randomly
    correct_idx = random.randint(0, 3)
    options = distractor_list[:3]
    options.insert(correct_idx, answer)
    answer_letter = chr(65 + correct_idx)  # A, B, C, D

    choices = [f"{chr(65+i)}) {opt}" for i, opt in enumerate(options)]

    return {
        "topic": "Series and Patterns/Mixed Series (Alphanumeric)",
        "question": question_text,
        "choices": choices,
        "answer": answer_letter,
        "explanation": explanation[:300]
    }


def generate_odd_one_out() -> Optional[Dict]:
    """Generate 'find the wrong number' type question."""
    pattern = random.choice(["powers_of_2", "squares", "cubes", "primes", "arithmetic"])

    if pattern == "powers_of_2":
        terms = [2**i for i in range(7)]
        wrong_idx = random.randint(2, 5)
        original = terms[wrong_idx]
        offset = random.choice([1, -1, 2, -2])
        terms[wrong_idx] += offset
        wrong_val = terms[wrong_idx]
        explanation = f"Powers of 2: the series should be {', '.join(str(2**i) for i in range(7))}. {wrong_val} should be {original}."
    elif pattern == "squares":
        start = random.randint(1, 5)
        terms = [(start+i)**2 for i in range(7)]
        wrong_idx = random.randint(2, 5)
        original = terms[wrong_idx]
        terms[wrong_idx] += random.choice([1, -1, 2, 3])
        wrong_val = terms[wrong_idx]
        explanation = f"Perfect squares sequence. {wrong_val} should be {original}."
    elif pattern == "cubes":
        start = random.randint(1, 4)
        terms = [(start+i)**3 for i in range(6)]
        wrong_idx = random.randint(2, 4)
        original = terms[wrong_idx]
        terms[wrong_idx] += random.choice([1, -1, 2, 3])
        wrong_val = terms[wrong_idx]
        explanation = f"Perfect cubes sequence. {wrong_val} should be {original}."
    elif pattern == "primes":
        primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31]
        start = random.randint(0, 3)
        terms = primes[start:start+7]
        wrong_idx = random.randint(2, 5)
        original = terms[wrong_idx]
        # Replace with a non-prime
        terms[wrong_idx] = original + 1
        if terms[wrong_idx] in primes:
            terms[wrong_idx] = original + 2
        wrong_val = terms[wrong_idx]
        explanation = f"All are prime numbers except {wrong_val}. It should be {original}."
    else:  # arithmetic
        a = random.randint(1, 10)
        d = random.randint(2, 7)
        terms = [a + i*d for i in range(7)]
        wrong_idx = random.randint(2, 5)
        original = terms[wrong_idx]
        terms[wrong_idx] += random.choice([1, -1, 2])
        wrong_val = terms[wrong_idx]
        explanation = f"Arithmetic series with difference {d}. {wrong_val} should be {original}."

    question_text = f"Find the wrong number in the series: {', '.join(str(t) for t in terms)}"

    # Options: the wrong value + 3 other values from the series
    other_vals = [t for i, t in enumerate(terms) if i != wrong_idx]
    distractors = random.sample(other_vals, min(3, len(other_vals)))

    correct_idx = random.randint(0, 3)
    options = distractors[:3]
    options.insert(correct_idx, wrong_val)
    answer_letter = chr(65 + correct_idx)

    choices = [f"{chr(65+i)}) {opt}" for i, opt in enumerate(options)]

    return {
        "topic": "Series and Patterns/Mixed Series (Alphanumeric)",
        "question": question_text,
        "choices": choices,
        "answer": answer_letter,
        "explanation": explanation[:300]
    }


def generate_dataset(num_questions: int = 200, seed: int = 42) -> List[Dict]:
    """Generate a full dataset of series questions."""
    random.seed(seed)
    questions = []
    seen = set()

    # 80% next-term, 20% odd-one-out
    num_next = int(num_questions * 0.8)
    num_odd = num_questions - num_next

    attempts = 0
    while len(questions) < num_next and attempts < num_next * 20:
        q = generate_series_question()
        if q and q["question"] not in seen:
            seen.add(q["question"])
            questions.append(q)
        attempts += 1

    attempts = 0
    while len(questions) < num_questions and attempts < num_odd * 20:
        q = generate_odd_one_out()
        if q and q["question"] not in seen:
            seen.add(q["question"])
            questions.append(q)
        attempts += 1

    random.shuffle(questions)
    return questions


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate series MCQs")
    parser.add_argument("--num", type=int, default=200, help="Number of questions")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--output", type=str, default="data/generated/mixed_series.json")
    args = parser.parse_args()

    questions = generate_dataset(args.num, args.seed)
    import os
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(questions, f, indent=2)
    print(f"Generated {len(questions)} series questions → {args.output}")
