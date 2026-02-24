#!/usr/bin/env python3
"""
Programmatic Blood Relations / Family Tree MCQ Generator
Builds random family trees and creates relationship-chain questions.
"""

import random
import json
from typing import List, Dict, Optional, Tuple
from collections import deque


# ── Family Graph Engine ──────────────────────────────────────────────────────

MALE_NAMES = [
    "Arun", "Binu", "Charan", "Dev", "Eshan", "Faisal", "Gopal",
    "Hari", "Ishaan", "Jay", "Karthik", "Lakshman", "Mohan", "Naveen",
    "Om", "Pranav", "Qasim", "Rahul", "Suresh", "Tarun", "Umesh",
    "Vijay", "Waseem", "Yash", "Zaheer", "Ajay", "Bharat", "Dinesh",
    "Gaurav", "Hemant", "Kunal", "Manoj", "Nikhil", "Pankaj", "Rajesh",
    "Sanjay", "Tushar",
]

FEMALE_NAMES = [
    "Anita", "Bindu", "Chitra", "Deepa", "Esha", "Fatima", "Gita",
    "Hema", "Isha", "Jaya", "Kavita", "Lata", "Meera", "Nisha",
    "Ojaswi", "Priya", "Qamar", "Rina", "Sita", "Tara", "Uma",
    "Vani", "Wafa", "Yamini", "Zara", "Aruna", "Bharti", "Divya",
    "Gauri", "Heena", "Komal", "Madhuri", "Neelam", "Padma", "Radha",
    "Sarita", "Tanvi",
]


class Person:
    __slots__ = ("name", "gender", "spouse", "father", "mother", "children")

    def __init__(self, name: str, gender: str):
        self.name = name
        self.gender = gender  # "M" or "F"
        self.spouse: Optional["Person"] = None
        self.father: Optional["Person"] = None
        self.mother: Optional["Person"] = None
        self.children: List["Person"] = []


class FamilyTree:
    """Build a random multi-generation family tree."""

    def __init__(self, seed=None):
        if seed is not None:
            random.seed(seed)
        self.people: Dict[str, Person] = {}
        self.male_pool = list(MALE_NAMES)
        self.female_pool = list(FEMALE_NAMES)
        random.shuffle(self.male_pool)
        random.shuffle(self.female_pool)

    def _get_name(self, gender: str) -> str:
        pool = self.male_pool if gender == "M" else self.female_pool
        if not pool:
            raise ValueError("Ran out of names")
        return pool.pop()

    def add_person(self, gender: str) -> Person:
        name = self._get_name(gender)
        p = Person(name, gender)
        self.people[name] = p
        return p

    def marry(self, p1: Person, p2: Person):
        p1.spouse = p2
        p2.spouse = p1

    def add_child(self, father: Person, mother: Person, gender: str) -> Person:
        child = self.add_person(gender)
        child.father = father
        child.mother = mother
        father.children.append(child)
        mother.children.append(child)
        return child

    def build_random_tree(self, generations=3, max_children_per_couple=3) -> List[Person]:
        """Build a random family tree with given generations."""
        # Generation 0: grandparents (1-2 couples)
        gen0_couples = []
        n_couples = random.randint(1, 2)
        for _ in range(n_couples):
            gf = self.add_person("M")
            gm = self.add_person("F")
            self.marry(gf, gm)
            gen0_couples.append((gf, gm))

        all_people = []
        prev_gen = gen0_couples

        for gen_num in range(1, generations):
            current_gen_singles = []
            for father, mother in prev_gen:
                all_people.extend([father, mother])
                n_children = random.randint(1, max_children_per_couple)
                for _ in range(n_children):
                    g = random.choice(["M", "F"])
                    child = self.add_child(father, mother, g)
                    current_gen_singles.append(child)

            # Pair some of them with spouses (from outside)
            current_gen_couples = []
            random.shuffle(current_gen_singles)
            for child in current_gen_singles:
                if gen_num < generations - 1 and random.random() < 0.7:
                    spouse_gender = "F" if child.gender == "M" else "M"
                    spouse = self.add_person(spouse_gender)
                    self.marry(child, spouse)
                    if child.gender == "M":
                        current_gen_couples.append((child, spouse))
                    else:
                        current_gen_couples.append((spouse, child))
                else:
                    all_people.append(child)

            prev_gen = current_gen_couples

        # Add last generation people
        for father, mother in prev_gen:
            all_people.extend([father, mother])

        return list(self.people.values())


# ── Relationship Computation ─────────────────────────────────────────────────

RELATIONSHIP_NAMES = {
    ("father",): lambda g: "father",
    ("mother",): lambda g: "mother",
    ("spouse",): lambda g: "wife" if g == "F" else "husband",
    ("father", "father"): lambda g: "paternal grandfather",
    ("father", "mother"): lambda g: "paternal grandmother",
    ("mother", "father"): lambda g: "maternal grandfather",
    ("mother", "mother"): lambda g: "maternal grandmother",
    ("father", "spouse"): lambda g: "mother" if g == "F" else "stepfather",
    ("mother", "spouse"): lambda g: "father" if g == "M" else "stepmother",
}

def get_siblings(person: Person) -> List[Person]:
    """Get all siblings (same father AND mother)."""
    siblings = []
    if person.father:
        for c in person.father.children:
            if c is not person and c.mother is person.mother:
                siblings.append(c)
    return siblings


def get_relationship_label(source: Person, target: Person) -> Optional[str]:
    """Determine the human-readable relationship of target TO source.
    i.e. 'target is the ___ of source'."""

    if target is source:
        return None

    # Direct parent
    if target is source.father:
        return "father"
    if target is source.mother:
        return "mother"

    # Spouse
    if target is source.spouse:
        return "wife" if target.gender == "F" else "husband"

    # Child
    if target in source.children:
        return "son" if target.gender == "M" else "daughter"

    # Sibling
    siblings = get_siblings(source)
    if target in siblings:
        return "brother" if target.gender == "M" else "sister"

    # Grandparent
    if source.father:
        if target is source.father.father:
            return "paternal grandfather"
        if target is source.father.mother:
            return "paternal grandmother"
    if source.mother:
        if target is source.mother.father:
            return "maternal grandfather"
        if target is source.mother.mother:
            return "maternal grandmother"

    # Uncle / Aunt (father's siblings)
    if source.father:
        for sib in get_siblings(source.father):
            if target is sib:
                return "uncle" if target.gender == "M" else "aunt"
            if target is sib.spouse:
                return "uncle" if target.gender == "M" else "aunt"
    if source.mother:
        for sib in get_siblings(source.mother):
            if target is sib:
                return "uncle" if target.gender == "M" else "aunt"
            if target is sib.spouse:
                return "uncle" if target.gender == "M" else "aunt"

    # Nephew / Niece (sibling's child)
    for sib in get_siblings(source):
        if target in sib.children:
            return "nephew" if target.gender == "M" else "niece"

    # Son-in-law / Daughter-in-law (child's spouse)
    for child in source.children:
        if target is child.spouse:
            return "son-in-law" if target.gender == "M" else "daughter-in-law"

    # Father-in-law / Mother-in-law (spouse's parent)
    if source.spouse:
        if target is source.spouse.father:
            return "father-in-law"
        if target is source.spouse.mother:
            return "mother-in-law"

    # Brother-in-law / Sister-in-law (spouse's sibling)
    if source.spouse:
        for sib in get_siblings(source.spouse):
            if target is sib:
                return "brother-in-law" if target.gender == "M" else "sister-in-law"

    # Cousin
    if source.father:
        for uncle in get_siblings(source.father):
            if target in uncle.children:
                return "cousin"
    if source.mother:
        for aunt in get_siblings(source.mother):
            if target in aunt.children:
                return "cousin"

    # Grandchild
    for child in source.children:
        if target in child.children:
            return "grandson" if target.gender == "M" else "granddaughter"

    return None


# ── Question Generation ──────────────────────────────────────────────────────

def build_relationship_chain(tree: FamilyTree, chain_len: int = 2) -> Optional[Tuple[Person, Person, str, str]]:
    """Build a chain of relationships and return (start, end, clue_text, answer_relationship)."""
    people = list(tree.people.values())
    random.shuffle(people)

    for start in people:
        chain = [start]
        clues = []
        for _ in range(chain_len):
            current = chain[-1]
            neighbors = []

            # Collect navigable neighbors
            if current.father:
                neighbors.append((current.father, f"{current.name}'s father"))
            if current.mother:
                neighbors.append((current.mother, f"{current.name}'s mother"))
            if current.spouse:
                neighbors.append((current.spouse, f"{current.name}'s {'wife' if current.spouse.gender == 'F' else 'husband'}"))
            for c in current.children:
                neighbors.append((c, f"{current.name}'s {'son' if c.gender == 'M' else 'daughter'}"))
            for s in get_siblings(current):
                neighbors.append((s, f"{current.name}'s {'brother' if s.gender == 'M' else 'sister'}"))

            # Filter: don't revisit
            neighbors = [(p, desc) for p, desc in neighbors if p not in chain]
            if not neighbors:
                break

            next_p, desc = random.choice(neighbors)
            chain.append(next_p)
            clues.append(desc)

        if len(chain) < chain_len + 1:
            continue

        # Get relationship of final person to start
        rel = get_relationship_label(start, chain[-1])
        if rel:
            clue_text = " → ".join(clues)
            return start, chain[-1], clue_text, rel

    return None


CODED_OPERATORS = {
    "father": ["+", "$", "#F"],
    "mother": ["@", "%", "#M"],
    "brother": ["*", "^B", "&B"],
    "sister": ["*S", "^S", "&S"],
    "son": ["!S", "$S", "#SON"],
    "daughter": ["!D", "$D", "#D"],
    "spouse": ["~", "=", "#SP"],
}


def build_coded_question(tree: FamilyTree) -> Optional[Dict]:
    """Build a question using coded relationship operators like A + B means A is the father of B."""
    people = list(tree.people.values())
    random.shuffle(people)

    # Pick 2-3 step chain
    chain_len = random.choice([2, 3])
    result = build_relationship_chain(tree, chain_len)
    if not result:
        return None

    start, end, clue_text, answer = result

    # Build natural language question
    question_text = (
        f"Study the following relationship chain: {clue_text}. "
        f"How is {end.name} related to {start.name}?"
    )

    return question_text, answer, end.gender


def build_statement_question(tree: FamilyTree) -> Optional[Dict]:
    """Build a question with natural language statements introducing relationships."""
    people = list(tree.people.values())
    random.shuffle(people)

    # Pick 2-4 step chain
    chain_len = random.choice([2, 3, 4])
    result = build_relationship_chain(tree, chain_len)
    if not result:
        return None

    start, end, clue_text, answer = result

    # Convert chain description to narrative statements
    steps = clue_text.split(" → ")
    statements = []
    for step in steps:
        statements.append(step)

    intro = "Given the following family relationships: " + "; ".join(statements) + "."
    question_text = f"{intro} How is {end.name} related to {start.name}?"

    return question_text, answer, end.gender


def generate_distractors(answer: str, gender: str) -> List[str]:
    """Generate relationship distractors of appropriate gender."""
    male_rels = ["father", "brother", "uncle", "son", "husband", "nephew",
                 "paternal grandfather", "maternal grandfather", "cousin",
                 "son-in-law", "brother-in-law", "grandson"]
    female_rels = ["mother", "sister", "aunt", "daughter", "wife", "niece",
                   "paternal grandmother", "maternal grandmother", "cousin",
                   "daughter-in-law", "sister-in-law", "granddaughter"]
    neutral = ["cousin"]

    pool = set()
    if gender == "M":
        pool.update(male_rels)
    else:
        pool.update(female_rels)
    pool.update(neutral)
    pool.discard(answer)

    pool_list = list(pool)
    random.shuffle(pool_list)
    return pool_list[:5]  # extras in case of duplicates


def generate_blood_relation_question(tree: FamilyTree) -> Optional[Dict]:
    """Generate a single blood relation MCQ."""
    variant = random.choice(["statement", "statement", "coded"])

    if variant == "coded":
        result = build_coded_question(tree)
    else:
        result = build_statement_question(tree)

    if result is None:
        return None

    question_text, answer, gender = result

    distractors = generate_distractors(answer, gender)
    if len(distractors) < 3:
        return None

    # Build options
    correct_idx = random.randint(0, 3)
    options = distractors[:3]
    options.insert(correct_idx, answer)
    answer_letter = chr(65 + correct_idx)

    choices = [f"{chr(65+i)}) {opt.capitalize()}" for i, opt in enumerate(options)]

    return {
        "topic": "Blood Relations and Family Tree/Family tree logic",
        "question": question_text,
        "choices": choices,
        "answer": answer_letter,
        "explanation": f"Following the relationship chain: {answer}."
    }


def generate_dataset(num_questions: int = 200, seed: int = 42) -> List[Dict]:
    """Generate a full dataset of blood relation questions."""
    random.seed(seed)
    questions = []
    seen_questions = set()

    attempts = 0
    while len(questions) < num_questions and attempts < num_questions * 30:
        # Build a fresh tree for variety
        tree = FamilyTree()
        try:
            tree.build_random_tree(
                generations=random.choice([2, 3]),
                max_children_per_couple=random.choice([2, 3])
            )
        except ValueError:
            attempts += 1
            continue

        # Generate several questions from this tree
        for _ in range(5):
            q = generate_blood_relation_question(tree)
            if q and q["question"] not in seen_questions:
                seen_questions.add(q["question"])
                questions.append(q)
                if len(questions) >= num_questions:
                    break
        attempts += 1

    random.shuffle(questions)
    return questions[:num_questions]


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate blood relation MCQs")
    parser.add_argument("--num", type=int, default=200, help="Number of questions")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--output", type=str, default="data/generated/blood_relations.json")
    args = parser.parse_args()

    questions = generate_dataset(args.num, args.seed)
    import os
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(questions, f, indent=2)
    print(f"Generated {len(questions)} blood relation questions → {args.output}")
