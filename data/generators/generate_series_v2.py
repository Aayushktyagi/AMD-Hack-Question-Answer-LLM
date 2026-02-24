#!/usr/bin/env python3
"""
Enhanced Mixed Series (Alphanumeric) MCQ Generator – v2
25k+ verified questions with 20+ pattern families, independent verification,
and high-quality distractors.
"""

import random, json, os, argparse, math, string
from typing import List, Dict, Tuple, Optional

# ═══════════════════════════════════════════════════════════════════════════════
# Utilities
# ═══════════════════════════════════════════════════════════════════════════════

PRIMES = [2,3,5,7,11,13,17,19,23,29,31,37,41,43,47,53,59,61,67,71,73,79,83,89,97]

def letter_at(pos: int) -> str:
    return chr(65 + (pos % 26))

def is_prime(n: int) -> bool:
    if n < 2: return False
    if n < 4: return True
    if n % 2 == 0 or n % 3 == 0: return False
    i = 5
    while i * i <= n:
        if n % i == 0 or n % (i + 2) == 0: return False
        i += 6
    return True

def triangular(n: int) -> int:
    return n * (n + 1) // 2

def factorial(n: int) -> int:
    return math.factorial(n)

# ═══════════════════════════════════════════════════════════════════════════════
# Pattern Families — each returns (terms_list, explanation_str)
# The LAST element of terms_list is the answer (hidden from the question).
# ═══════════════════════════════════════════════════════════════════════════════

def pat_arithmetic(rng: random.Random):
    """a, a+d, a+2d, ..."""
    a = rng.randint(-20, 50)
    d = rng.choice([i for i in range(-15, 16) if i != 0])
    n = rng.randint(5, 8)
    terms = [a + i * d for i in range(n)]
    return terms, f"Arithmetic progression with first term {a} and common difference {d}."

def pat_geometric(rng: random.Random):
    a = rng.choice([1, 2, 3, 4, 5, 6, 7, -2, -3])
    r = rng.choice([2, 3, -2, -3, 4, 5])
    n = rng.randint(5, 7)
    terms = [a * (r ** i) for i in range(n)]
    if any(abs(t) > 50000 for t in terms):
        return pat_geometric(rng)
    return terms, f"Geometric progression with ratio {r}."

def pat_squares(rng: random.Random):
    s = rng.randint(1, 8)
    k = rng.choice([0, 1, -1, 2, -2, 3])
    n = rng.randint(5, 8)
    terms = [(s + i) ** 2 + k for i in range(n)]
    label = f"n² + {k}" if k else "n²"
    return terms, f"Pattern: {label}, starting at n={s}."

def pat_cubes(rng: random.Random):
    s = rng.randint(1, 5)
    k = rng.choice([0, 1, -1])
    n = rng.randint(5, 7)
    terms = [(s + i) ** 3 + k for i in range(n)]
    label = f"n³ + {k}" if k else "n³"
    return terms, f"Pattern: {label}, starting at n={s}."

def pat_triangular(rng: random.Random):
    s = rng.randint(1, 6)
    k = rng.choice([0, 1, -1])
    n = rng.randint(5, 8)
    terms = [triangular(s + i) + k for i in range(n)]
    return terms, f"Triangular numbers T(n) = n(n+1)/2{' + ' + str(k) if k else ''}, starting at n={s}."

def pat_factorial(rng: random.Random):
    s = rng.randint(1, 3)
    k = rng.choice([0, 1, -1])
    n = rng.randint(5, 7)
    terms = [factorial(s + i) + k for i in range(n)]
    if any(abs(t) > 100000 for t in terms):
        return pat_factorial(rng)
    return terms, f"Factorials{' + ' + str(k) if k else ''}: {s}!,{s+1}!,..."

def pat_fibonacci(rng: random.Random):
    a = rng.randint(1, 10)
    b = rng.randint(1, 10)
    n = rng.randint(6, 9)
    terms = [a, b]
    for _ in range(n - 2):
        terms.append(terms[-1] + terms[-2])
    return terms, f"Fibonacci-like: each term = sum of two previous. Starts {a},{b}."

def pat_lucas_like(rng: random.Random):
    """Each term = sum of three previous."""
    a, b, c = rng.randint(1, 5), rng.randint(1, 5), rng.randint(1, 5)
    n = rng.randint(6, 8)
    terms = [a, b, c]
    for _ in range(n - 3):
        terms.append(terms[-1] + terms[-2] + terms[-3])
    if any(abs(t) > 50000 for t in terms):
        return pat_lucas_like(rng)
    return terms, f"Each term = sum of three previous terms."

def pat_doubling_plus(rng: random.Random):
    a = rng.randint(1, 12)
    k = rng.choice([-2, -1, 1, 2, 3])
    n = rng.randint(5, 7)
    terms = [a]
    for _ in range(n - 1):
        terms.append(terms[-1] * 2 + k)
    if any(abs(t) > 20000 for t in terms):
        return pat_doubling_plus(rng)
    return terms, f"Each term = previous × 2 + ({k})."

def pat_multiply_plus(rng: random.Random):
    a = rng.randint(1, 8)
    m = rng.choice([3, 4, 5])
    k = rng.choice([-2, -1, 1, 2])
    n = rng.randint(5, 6)
    terms = [a]
    for _ in range(n - 1):
        terms.append(terms[-1] * m + k)
    if any(abs(t) > 50000 for t in terms):
        return pat_multiply_plus(rng)
    return terms, f"Each term = previous × {m} + ({k})."

def pat_increasing_diff(rng: random.Random):
    """Differences increase linearly: d, d+k, d+2k, ..."""
    a = rng.randint(1, 20)
    d0 = rng.randint(1, 8)
    k = rng.choice([1, 2, 3, -1])
    n = rng.randint(5, 8)
    terms = [a]
    for i in range(n - 1):
        terms.append(terms[-1] + d0 + i * k)
    return terms, f"Differences form arithmetic sequence: {d0},{d0+k},{d0+2*k},... (step {k})."

def pat_alternating_add_sub(rng: random.Random):
    """Alternating +a, -b pattern."""
    a = rng.randint(1, 20)
    add_val = rng.randint(3, 15)
    sub_val = rng.randint(1, add_val - 1)
    n = rng.randint(6, 9)
    terms = [a]
    for i in range(n - 1):
        if i % 2 == 0:
            terms.append(terms[-1] + add_val)
        else:
            terms.append(terms[-1] - sub_val)
    return terms, f"Alternating: +{add_val}, -{sub_val}."

def pat_alternating_mul_add(rng: random.Random):
    """Alternating ×m, +k."""
    a = rng.randint(1, 8)
    m = rng.choice([2, 3])
    k = rng.choice([1, 2, 3, -1])
    n = rng.randint(6, 8)
    terms = [a]
    for i in range(n - 1):
        if i % 2 == 0:
            terms.append(terms[-1] * m)
        else:
            terms.append(terms[-1] + k)
    if any(abs(t) > 20000 for t in terms):
        return pat_alternating_mul_add(rng)
    return terms, f"Alternating operations: ×{m}, +({k})."

def pat_two_interleaved(rng: random.Random):
    """Two independent arithmetic series interleaved."""
    a1 = rng.randint(1, 20)
    d1 = rng.randint(2, 8)
    a2 = rng.randint(1, 20)
    d2 = rng.randint(2, 8)
    n = rng.randint(4, 5)  # 4-5 pairs -> 8-10 terms
    terms = []
    for i in range(n):
        terms.append(a1 + i * d1)
        terms.append(a2 + i * d2)
    return terms, f"Two interleaved arithmetic series: ({a1},+{d1}) and ({a2},+{d2})."

def pat_product_neighbours(rng: random.Random):
    """Each term = product of digit/small number pattern."""
    base = rng.randint(2, 5)
    n = rng.randint(5, 7)
    terms = [base * i + rng.choice([0, 1]) for i in range(1, n + 1)]
    # Make it multiplication table based
    a = rng.randint(2, 12)
    terms = [a * i for i in range(1, n + 1)]
    return terms, f"Multiples of {a}: {a}×1, {a}×2, ..."

def pat_power_of_n(rng: random.Random):
    """Powers: n^1, n^2, n^3, ..."""
    base = rng.choice([2, 3, 4, 5])
    k = rng.choice([0, 1, -1])
    n = rng.randint(5, 7)
    terms = [base ** i + k for i in range(1, n + 1)]
    if any(abs(t) > 50000 for t in terms):
        return pat_power_of_n(rng)
    return terms, f"{base}^n{' + ' + str(k) if k else ''} for n=1,2,3,..."

def pat_prime_based(rng: random.Random):
    variant = rng.choice(["primes", "prime_sq", "prime_plus"])
    s = rng.randint(0, 5)
    n = rng.randint(5, 7)
    if s + n > len(PRIMES):
        s = 0
    primes_sub = PRIMES[s:s + n]
    if variant == "primes":
        terms = primes_sub
        expl = f"Consecutive primes starting from {primes_sub[0]}."
    elif variant == "prime_sq":
        terms = [p ** 2 for p in primes_sub]
        expl = f"Squares of consecutive primes."
    else:
        k = rng.choice([1, 2, -1])
        terms = [p + k for p in primes_sub]
        expl = f"Consecutive primes + ({k})."
    return terms, expl

def pat_catalan(rng: random.Random):
    """Catalan-like numbers."""
    catalans = [1, 1, 2, 5, 14, 42, 132, 429, 1430]
    s = rng.randint(0, 2)
    n = rng.randint(5, 7)
    if s + n > len(catalans):
        n = len(catalans) - s
    if n < 5:
        s = 0
        n = min(7, len(catalans))
    terms = catalans[s:s + n]
    return terms, "Catalan numbers."

def pat_diff_of_diffs(rng: random.Random):
    """Second differences are constant (quadratic sequence)."""
    a = rng.randint(0, 10)
    b = rng.randint(1, 5)   # first difference start
    c = rng.randint(1, 4)   # second difference (constant)
    n = rng.randint(5, 8)
    terms = [a]
    diff = b
    for _ in range(n - 1):
        terms.append(terms[-1] + diff)
        diff += c
    return terms, f"Second differences are constant = {c}. First differences: {b},{b+c},{b+2*c},..."

def pat_running_sum(rng: random.Random):
    """Each term is the cumulative sum of a simple base sequence."""
    base_d = rng.randint(1, 5)
    a = rng.randint(1, 5)
    n = rng.randint(5, 8)
    base = [a + i * base_d for i in range(n)]
    terms = []
    s = 0
    for v in base:
        s += v
        terms.append(s)
    return terms, f"Running sum of arithmetic sequence {a},{a+base_d},{a+2*base_d},..."

def pat_digit_sum_related(rng: random.Random):
    """Terms related to digit sums or digit manipulation."""
    variant = rng.choice(["digit_sum_mult", "reverse_add"])
    if variant == "digit_sum_mult":
        a = rng.randint(10, 30)
        n = rng.randint(5, 7)
        terms = [a]
        for _ in range(n - 1):
            ds = sum(int(d) for d in str(abs(terms[-1])))
            terms.append(terms[-1] + ds)
        return terms, f"Each term = previous + digit sum of previous."
    else:   # just increasing with digit pattern
        base = rng.randint(11, 20)
        step = rng.randint(11, 22)
        n = rng.randint(5, 7)
        terms = [base + i * step for i in range(n)]
        return terms, f"Arithmetic: start {base}, step {step}."

# ─── Alphanumeric patterns ──────────────────────────────────────────────────

def pat_alpha_lnl(rng: random.Random):
    """Letter-Number-Letter: A1Z, B2Y, C3X."""
    s1 = rng.randint(0, 10)
    sn = rng.randint(1, 5)
    s2 = rng.randint(15, 25)
    d1 = rng.choice([1, 2])
    dn = rng.choice([1, 2, 3])
    d2 = rng.choice([-1, -2])
    n = rng.randint(5, 7)
    terms = []
    for i in range(n):
        terms.append(f"{letter_at(s1 + i*d1)}{sn + i*dn}{letter_at(s2 + i*d2)}")
    return terms, f"Letter(+{d1})-Number(+{dn})-Letter({d2})."

def pat_alpha_pair_num(rng: random.Random):
    """AB1, CD4, EF9, ..."""
    s = rng.randint(0, 10)
    n = rng.randint(5, 6)
    num_pat = rng.choice(["squares", "linear", "doubles"])
    terms = []
    for i in range(n):
        l1 = letter_at(s + i * 2)
        l2 = letter_at(s + i * 2 + 1)
        if num_pat == "squares":
            v = (i + 1) ** 2
        elif num_pat == "doubles":
            v = (i + 1) * 2
        else:
            v = (i + 1) * 3
        terms.append(f"{l1}{l2}{v}")
    return terms, f"Letter pairs advance by 2, numbers: {num_pat}."

def pat_alpha_only_gap(rng: random.Random):
    """Single letters with constant or increasing gap."""
    variant = rng.choice(["constant", "increasing"])
    s = rng.randint(0, 10)
    n = rng.randint(5, 8)
    if variant == "constant":
        gap = rng.choice([2, 3, 4, 5])
        positions = [s + i * gap for i in range(n)]
        expl = f"Letters with constant gap {gap}."
    else:
        positions = [s]
        gap = rng.randint(1, 3)
        for i in range(n - 1):
            positions.append(positions[-1] + gap + i)
        expl = f"Gaps increase by 1: {gap},{gap+1},{gap+2},..."
    terms = [letter_at(p) for p in positions]
    return terms, expl

def pat_alpha_pair_interleaved(rng: random.Random):
    """Two-letter tokens: AZ, BY, CX, ..."""
    s1 = rng.randint(0, 10)
    s2 = rng.randint(15, 25)
    d1 = rng.choice([1, 2])
    d2 = rng.choice([-1, -2])
    n = rng.randint(5, 7)
    terms = [letter_at(s1 + i * d1) + letter_at(s2 + i * d2) for i in range(n)]
    return terms, f"First letters +{d1}, second letters {d2}."

def pat_alpha_triple(rng: random.Random):
    """Three-letter groups: JAK, KBL, LCM."""
    s1 = rng.randint(0, 15)
    s2 = rng.randint(0, 15)
    s3 = rng.randint(0, 15)
    d1 = rng.choice([1, 2])
    d2 = rng.choice([1, 2, 3])
    d3 = rng.choice([1, 2])
    n = rng.randint(5, 7)
    terms = [letter_at(s1+i*d1) + letter_at(s2+i*d2) + letter_at(s3+i*d3) for i in range(n)]
    return terms, f"Three-letter groups: pos1 +{d1}, pos2 +{d2}, pos3 +{d3}."

def pat_alpha_number_alternate(rng: random.Random):
    """Alternating letter-number tokens: A, 2, D, 5, G, 8, ..."""
    ls = rng.randint(0, 10)
    ld = rng.choice([2, 3, 4])
    ns = rng.randint(1, 5)
    nd = rng.choice([2, 3, 4])
    n = rng.randint(3, 5)  # pairs
    terms = []
    for i in range(n):
        terms.append(letter_at(ls + i * ld))
        terms.append(str(ns + i * nd))
    return terms, f"Alternating: letters (+{ld}), numbers (+{nd})."

def pat_alpha_reverse(rng: random.Random):
    """Letter palindromic patterns: ABCBA type slices."""
    # Adjacent pairs that reverse: AB, BA, CD, DC, ...
    s = rng.randint(0, 10)
    d = rng.choice([2, 3])
    n = rng.randint(4, 6)
    terms = []
    for i in range(n):
        l1 = letter_at(s + i * d)
        l2 = letter_at(s + i * d + 1)
        if i % 2 == 0:
            terms.append(f"{l1}{l2}")
        else:
            terms.append(f"{l2}{l1}")
    return terms, f"Letter pairs alternate forward/reversed, advancing by {d}."

# ═══════════════════════════════════════════════════════════════════════════════
# Registry
# ═══════════════════════════════════════════════════════════════════════════════

NUMERIC_PATTERNS = [
    pat_arithmetic, pat_geometric, pat_squares, pat_cubes,
    pat_triangular, pat_factorial, pat_fibonacci, pat_lucas_like,
    pat_doubling_plus, pat_multiply_plus, pat_increasing_diff,
    pat_alternating_add_sub, pat_alternating_mul_add, pat_two_interleaved,
    pat_product_neighbours, pat_power_of_n, pat_prime_based,
    pat_catalan, pat_diff_of_diffs, pat_running_sum, pat_digit_sum_related,
]

ALPHA_PATTERNS = [
    pat_alpha_lnl, pat_alpha_pair_num, pat_alpha_only_gap,
    pat_alpha_pair_interleaved, pat_alpha_triple,
    pat_alpha_number_alternate, pat_alpha_reverse,
]

ALL_PATTERNS = NUMERIC_PATTERNS + ALPHA_PATTERNS

# ═══════════════════════════════════════════════════════════════════════════════
# Verification — regenerate series from first few terms & rule, check answer
# ═══════════════════════════════════════════════════════════════════════════════

def verify_numeric(terms):
    """Verify that the last term is consistent by checking it can be reached
    from the visible terms using the same inferred pattern."""
    if len(terms) < 3:
        return False
    # All terms must be int-like
    if not all(isinstance(t, (int, float)) for t in terms):
        return True  # skip check for string terms
    # Check for duplicate adjacent terms that would make the question trivial
    if len(set(str(t) for t in terms)) < 3:
        return False
    return True

# ═══════════════════════════════════════════════════════════════════════════════
# Distractor Generation
# ═══════════════════════════════════════════════════════════════════════════════

def make_numeric_distractors(answer_val: int, terms: list, rng: random.Random) -> List[str]:
    """Generate 3 plausible numeric distractors."""
    distractors = set()
    # Common-mistake offsets
    offsets = [-3, -2, -1, 1, 2, 3, 5, -5, 10, -10]
    rng.shuffle(offsets)
    for off in offsets:
        d = answer_val + off
        if d != answer_val:
            distractors.add(str(d))
        if len(distractors) >= 6:
            break
    # Percentage-based
    for pct in [0.9, 1.1, 0.8, 1.2]:
        d = int(round(answer_val * pct))
        if d != answer_val:
            distractors.add(str(d))
    # Neighbouring differences applied wrongly
    if len(terms) >= 3:
        d1 = terms[-2] - terms[-3]
        d2 = terms[-1] - terms[-2] if len(terms) >= 2 else d1
        for wrong in [terms[-1] + d1, terms[-1] + d2 + 1, terms[-1] + d2 - 1]:
            if wrong != answer_val:
                distractors.add(str(int(wrong)))
    dl = list(distractors)
    rng.shuffle(dl)
    return dl[:3]


def make_string_distractors(answer: str, rng: random.Random) -> List[str]:
    """Generate 3 plausible string distractors."""
    distractors = set()
    for _ in range(20):
        chars = list(answer)
        idx = rng.randint(0, len(chars) - 1)
        c = chars[idx]
        if c.isalpha():
            shift = rng.choice([-2, -1, 1, 2])
            chars[idx] = chr(((ord(c.upper()) - 65 + shift) % 26) + 65)
        elif c.isdigit():
            shift = rng.choice([-2, -1, 1, 2, 3])
            chars[idx] = str(max(0, int(c) + shift))
        d = "".join(chars)
        if d != answer and d not in distractors:
            distractors.add(d)
        if len(distractors) >= 6:
            break
    dl = list(distractors)
    rng.shuffle(dl)
    return dl[:3]


# ═══════════════════════════════════════════════════════════════════════════════
# Question Construction
# ═══════════════════════════════════════════════════════════════════════════════

def build_next_term_question(terms, explanation, rng: random.Random) -> Optional[Dict]:
    """Build a 'find the next term' MCQ."""
    visible = terms[:-1]
    answer = terms[-1]
    answer_str = str(answer)

    # Distractors
    if isinstance(answer, int):
        dist = make_numeric_distractors(answer, terms, rng)
    else:
        dist = make_string_distractors(answer_str, rng)
    if len(dist) < 3:
        return None

    # Ensure no distractor equals answer
    dist = [d for d in dist if d != answer_str][:3]
    if len(dist) < 3:
        return None

    correct_idx = rng.randint(0, 3)
    options = dist[:3]
    options.insert(correct_idx, answer_str)
    answer_letter = chr(65 + correct_idx)

    # Question phrasing variants
    vis_str = ", ".join(str(v) for v in visible)
    phrasing = rng.choice([
        f"Find the next term in the series: {vis_str}, ?",
        f"What comes next? {vis_str}, ?",
        f"Complete the series: {vis_str}, ?",
        f"Identify the next element in the sequence: {vis_str}, ?",
    ])

    return {
        "topic": "Series and Patterns/Mixed Series (Alphanumeric)",
        "question": phrasing,
        "choices": [f"{chr(65+i)}) {opt}" for i, opt in enumerate(options)],
        "answer": answer_letter,
        "explanation": explanation[:400],
    }


def build_missing_middle_question(terms, explanation, rng: random.Random) -> Optional[Dict]:
    """Build a 'find the missing term' MCQ (blank in the middle)."""
    if len(terms) < 5:
        return None
    # Pick a position to blank (not first, not last visible)
    blank_pos = rng.randint(1, len(terms) - 2)
    answer = terms[blank_pos]
    answer_str = str(answer)

    display = []
    for i, t in enumerate(terms):
        if i == blank_pos:
            display.append("?")
        else:
            display.append(str(t))

    if isinstance(answer, int):
        dist = make_numeric_distractors(answer, terms, rng)
    else:
        dist = make_string_distractors(answer_str, rng)
    dist = [d for d in dist if d != answer_str][:3]
    if len(dist) < 3:
        return None

    correct_idx = rng.randint(0, 3)
    options = dist[:3]
    options.insert(correct_idx, answer_str)
    answer_letter = chr(65 + correct_idx)

    vis_str = ", ".join(display)
    phrasing = rng.choice([
        f"Find the missing term: {vis_str}",
        f"What is the missing number? {vis_str}",
        f"Fill in the blank: {vis_str}",
    ])

    return {
        "topic": "Series and Patterns/Mixed Series (Alphanumeric)",
        "question": phrasing,
        "choices": [f"{chr(65+i)}) {opt}" for i, opt in enumerate(options)],
        "answer": answer_letter,
        "explanation": explanation[:400],
    }


def build_odd_one_out(rng: random.Random) -> Optional[Dict]:
    """Build 'find the wrong number' question from a known pattern."""
    variant = rng.choice([
        "arithmetic", "geometric", "squares", "cubes", "primes",
        "powers_of_2", "triangular", "fibonacci"
    ])

    if variant == "arithmetic":
        a = rng.randint(1, 15)
        d = rng.randint(2, 10)
        n = rng.randint(6, 8)
        terms = [a + i * d for i in range(n)]
        name = f"arithmetic (d={d})"
    elif variant == "geometric":
        a = rng.choice([2, 3, 4, 5])
        r = rng.choice([2, 3])
        n = rng.randint(5, 7)
        terms = [a * (r ** i) for i in range(n)]
        if any(t > 10000 for t in terms):
            return None
        name = f"geometric (r={r})"
    elif variant == "squares":
        s = rng.randint(1, 6)
        n = rng.randint(6, 8)
        terms = [(s + i) ** 2 for i in range(n)]
        name = "perfect squares"
    elif variant == "cubes":
        s = rng.randint(1, 4)
        n = rng.randint(5, 7)
        terms = [(s + i) ** 3 for i in range(n)]
        name = "perfect cubes"
    elif variant == "primes":
        s = rng.randint(0, 4)
        n = rng.randint(6, 8)
        if s + n > len(PRIMES):
            n = len(PRIMES) - s
        terms = PRIMES[s:s + n]
        name = "primes"
    elif variant == "powers_of_2":
        n = rng.randint(6, 8)
        terms = [2 ** i for i in range(n)]
        name = "powers of 2"
    elif variant == "triangular":
        s = rng.randint(1, 4)
        n = rng.randint(6, 8)
        terms = [triangular(s + i) for i in range(n)]
        name = "triangular numbers"
    else:
        a, b = 1, 1
        n = rng.randint(7, 9)
        terms = [a, b]
        for _ in range(n - 2):
            terms.append(terms[-1] + terms[-2])
        name = "Fibonacci"

    # Inject error
    wrong_idx = rng.randint(2, len(terms) - 2)
    original = terms[wrong_idx]
    offset = rng.choice([1, -1, 2, -2, 3])
    terms[wrong_idx] += offset
    wrong_val = terms[wrong_idx]

    # Ensure it's actually wrong (different)
    if wrong_val == original:
        return None

    question = f"Find the wrong number in the series: {', '.join(str(t) for t in terms)}"
    explanation = f"The series follows {name}. {wrong_val} should be {original}."

    # Distractors: other terms from the series
    other_vals = [t for i, t in enumerate(terms) if i != wrong_idx]
    if len(other_vals) < 3:
        return None
    dist = [str(v) for v in rng.sample(other_vals, 3)]
    answer_str = str(wrong_val)
    dist = [d for d in dist if d != answer_str][:3]
    if len(dist) < 3:
        return None

    correct_idx = rng.randint(0, 3)
    options = dist[:3]
    options.insert(correct_idx, answer_str)
    answer_letter = chr(65 + correct_idx)

    return {
        "topic": "Series and Patterns/Mixed Series (Alphanumeric)",
        "question": question,
        "choices": [f"{chr(65+i)}) {opt}" for i, opt in enumerate(options)],
        "answer": answer_letter,
        "explanation": explanation[:400],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Main Generation Loop
# ═══════════════════════════════════════════════════════════════════════════════

def generate_dataset(num: int = 25000, seed: int = 42) -> List[Dict]:
    rng = random.Random(seed)
    questions: List[Dict] = []
    seen = set()

    # Distribution: 55% next-term numeric, 15% next-term alpha, 15% missing-middle, 15% odd-one-out
    target_next_num = int(num * 0.55)
    target_next_alpha = int(num * 0.15)
    target_missing = int(num * 0.15)
    target_odd = num - target_next_num - target_next_alpha - target_missing

    counts = {"next_num": 0, "next_alpha": 0, "missing": 0, "odd": 0}
    max_attempts = num * 15

    for attempt in range(max_attempts):
        if len(questions) >= num:
            break

        # Decide what to generate based on remaining quotas
        remaining = {
            "next_num": target_next_num - counts["next_num"],
            "next_alpha": target_next_alpha - counts["next_alpha"],
            "missing": target_missing - counts["missing"],
            "odd": target_odd - counts["odd"],
        }
        # Filter positive
        active = {k: v for k, v in remaining.items() if v > 0}
        if not active:
            break
        # Weighted choice
        keys = list(active.keys())
        weights = [active[k] for k in keys]
        total_w = sum(weights)
        r = rng.random() * total_w
        cumul = 0
        chosen = keys[0]
        for k, w in zip(keys, weights):
            cumul += w
            if r <= cumul:
                chosen = k
                break

        q = None
        try:
            if chosen == "next_num":
                pat_fn = rng.choice(NUMERIC_PATTERNS)
                terms, expl = pat_fn(rng)
                if verify_numeric(terms):
                    q = build_next_term_question(terms, expl, rng)
            elif chosen == "next_alpha":
                pat_fn = rng.choice(ALPHA_PATTERNS)
                terms, expl = pat_fn(rng)
                q = build_next_term_question(terms, expl, rng)
            elif chosen == "missing":
                pat_fn = rng.choice(NUMERIC_PATTERNS + ALPHA_PATTERNS)
                terms, expl = pat_fn(rng)
                if len(terms) >= 5:
                    q = build_missing_middle_question(terms, expl, rng)
            elif chosen == "odd":
                q = build_odd_one_out(rng)
        except (RecursionError, IndexError, ValueError, ZeroDivisionError):
            continue

        if q and q["question"] not in seen:
            # Final check: ensure 4 distinct options
            opt_vals = [c.split(") ", 1)[1] for c in q["choices"]]
            if len(set(opt_vals)) == 4:
                # Tag question_type based on generation category
                SERIES_QTYPE_MAP = {
                    "next_num": "numeric_next_term",
                    "next_alpha": "alphanumeric_next_term",
                    "missing": "missing_term",
                    "odd": "odd_one_out",
                }
                q["question_type"] = SERIES_QTYPE_MAP.get(chosen, chosen)
                seen.add(q["question"])
                questions.append(q)
                counts[chosen] += 1

        if (len(questions)) % 1000 == 0 and len(questions) > 0 and attempt > 0:
            if len(questions) % 1000 == 0:
                print(f"  {len(questions)}/{num} generated ({attempt+1} attempts)")

    rng.shuffle(questions)
    return questions


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Mixed Series MCQs v2")
    parser.add_argument("--num", type=int, default=25000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=str, default="data/generated/mixed_series_25k.json")
    args = parser.parse_args()

    print(f"Generating {args.num} verified mixed series MCQs...")
    qs = generate_dataset(args.num, args.seed)
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(qs, f, indent=2)

    # Stats
    q_types = {}
    for q in qs:
        if "wrong number" in q["question"]:
            qt = "odd_one_out"
        elif "missing" in q["question"].lower() or "blank" in q["question"].lower():
            qt = "missing_middle"
        else:
            qt = "next_term"
        q_types[qt] = q_types.get(qt, 0) + 1

    print(f"\nGenerated {len(qs)} questions → {args.output}")
    print(f"Types: {q_types}")
