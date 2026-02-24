#!/usr/bin/env python3
"""Retroactively add question_type tags to curated + CLUTRR datasets."""
import json
import re
import os


def infer_syllogism_type(q_text):
    """Infer syllogism question_type from question text."""
    if "does NOT follow" in q_text or "does not follow" in q_text:
        return "which_does_not_follow"
    elif "How many" in q_text and "follow" in q_text:
        return "count_valid_conclusions"
    elif "Is this conclusion" in q_text or "Definitely true" in q_text.lower() or "Cannot be determined" in q_text:
        return "true_false_determine"
    elif "additional statement" in q_text or "additional premise" in q_text:
        return "strengthen_weaken_premise"
    elif "Which of the following" in q_text and "conclusion" in q_text.lower():
        return "which_conclusion_follows"
    elif "Conclusions:" in q_text and ("I." in q_text or "1." in q_text):
        return "both_neither_conclusion"
    else:
        return "both_neither_conclusion"  # default for syllogisms


def infer_series_type(q_text):
    """Infer series question_type from question text."""
    q_lower = q_text.lower()
    if "wrong number" in q_lower or "wrong term" in q_lower:
        return "odd_one_out"
    elif "missing" in q_lower or "blank" in q_lower or "?" in q_text.split(",")[-2:-1]:
        return "missing_term"
    # Check if alphanumeric
    has_alpha = bool(re.search(r'[A-Za-z].*\d|\d.*[A-Za-z]', q_text.split("?")[0]))
    if has_alpha:
        return "alphanumeric_next_term"
    return "numeric_next_term"


def infer_seating_type(q_text):
    """Infer seating question_type from question text."""
    is_circular = "circular" in q_text.lower()
    prefix = "circular" if is_circular else "linear"
    
    q_lower = q_text.lower()
    if "how many" in q_lower and "between" in q_lower:
        return f"{prefix}_gap_count"
    elif "between" in q_lower and "who" in q_lower:
        return f"{prefix}_between_query"
    elif "position" in q_lower and ("from" in q_lower or "number" in q_lower):
        return f"{prefix}_position_count"
    elif "next to" in q_lower or "adjacent" in q_lower or "immediate" in q_lower:
        return f"{prefix}_adjacent_query"
    elif "who" in q_lower and ("end" in q_lower or "left" in q_lower or "right" in q_lower or "middle" in q_lower):
        return f"{prefix}_position_query"
    else:
        return f"{prefix}_position_query"


def infer_blood_type(q_text, hops=None):
    """Infer blood relations question_type. CLUTRR data doesn't have hops, so guess from text."""
    if hops:
        HOPS_MAP = {2: "simple_relation_2hop", 3: "moderate_relation_3hop", 
                    4: "complex_relation_4hop", 5: "extended_relation_5hop"}
        return HOPS_MAP.get(hops, "moderate_relation_3hop")
    
    # Count relationship phrases to estimate complexity
    rel_words = ["father", "mother", "brother", "sister", "son", "daughter", 
                 "wife", "husband", "uncle", "aunt", "nephew", "niece",
                 "grandfather", "grandmother", "grandson", "granddaughter"]
    
    # Count sentences or relationship mentions
    sentences = [s.strip() for s in q_text.replace(";", ".").split(".") if s.strip()]
    rel_count = sum(1 for s in sentences if any(w in s.lower() for w in rel_words))
    
    if rel_count <= 2:
        return "simple_relation_2hop"
    elif rel_count <= 3:
        return "moderate_relation_3hop"
    elif rel_count <= 4:
        return "complex_relation_4hop"
    else:
        return "extended_relation_5hop"


def tag_file(filepath):
    """Add question_type to all items in a JSON file."""
    with open(filepath) as f:
        data = json.load(f)
    
    tagged = 0
    for item in data:
        if "question_type" in item:
            continue
        
        topic = item.get("topic", "")
        q_text = item.get("question", "")
        hops = item.get("hops")
        
        if "Syllogism" in topic:
            item["question_type"] = infer_syllogism_type(q_text)
        elif "Series" in topic or "Pattern" in topic:
            item["question_type"] = infer_series_type(q_text)
        elif "Seating" in topic:
            item["question_type"] = infer_seating_type(q_text)
        elif "Blood" in topic or "Family" in topic:
            item["question_type"] = infer_blood_type(q_text, hops)
        else:
            item["question_type"] = "unknown"
        
        tagged += 1
    
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"  {filepath}: tagged {tagged}/{len(data)} items")
    return tagged


if __name__ == "__main__":
    base = os.path.dirname(os.path.abspath(__file__))
    
    files = [
        os.path.join(base, "curated", "syllogisms.json"),
        os.path.join(base, "curated", "blood_relations.json"),
        os.path.join(base, "curated", "seating_arrangements.json"),
        os.path.join(base, "curated", "mixed_series.json"),
        os.path.join(base, "parsed", "blood_relations_clutrr.json"),
    ]
    
    total = 0
    for f in files:
        if os.path.exists(f):
            total += tag_file(f)
    
    print(f"\nTotal tagged: {total}")
