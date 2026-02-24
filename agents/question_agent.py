#!/usr/bin/python3

from tqdm import tqdm
from pathlib import Path
from typing import List, Tuple, Dict, Any

from .question_model import QAgent
# from .question_model_llama import QAgent

import random
import json
import re


def robust_parse_question(text: str) -> dict | None:
    """
    Robustly parse model output into a question dict.
    
    Handles these known malformed formats:
      1. Valid JSON                          → json.loads() directly
      2. JSON with leading garbage           → 0"{ ... }" → extract {…} via regex
      3. Markdown code fences                → ```json { ... } ``` → strip fences
      4. Field-per-line format               → topic"val"\nquestion"val"\n0"A)..."\n...
      5. Partial JSON (missing outer braces) → reconstruct from key"value" pairs
    
    Returns parsed dict or None if all strategies fail.
    """
    if not text or not isinstance(text, str):
        return None

    text = text.strip()

    # ── Strategy 1: Direct JSON parse ──
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except (json.JSONDecodeError, TypeError):
        pass

    # ── Strategy 2: Strip markdown code fences, then parse ──
    cleaned = re.sub(r"^```(?:json)?\s*", "", text)
    cleaned = re.sub(r"\s*```\s*$", "", cleaned).strip()
    if cleaned != text:
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass

    # ── Strategy 3: Extract {…} from anywhere in the string (handles leading 0, quotes, etc.) ──
    # Find the outermost { ... } block
    brace_start = text.find("{")
    if brace_start != -1:
        # Walk forward to find matching closing brace
        depth = 0
        brace_end = -1
        in_string = False
        escape_next = False
        for idx in range(brace_start, len(text)):
            ch = text[idx]
            if escape_next:
                escape_next = False
                continue
            if ch == "\\":
                escape_next = True
                continue
            if ch == '"' and not escape_next:
                in_string = not in_string
                continue
            if not in_string:
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        brace_end = idx
                        break
        if brace_end != -1:
            json_candidate = text[brace_start : brace_end + 1]
            try:
                parsed = json.loads(json_candidate)
                if isinstance(parsed, dict):
                    return parsed
            except (json.JSONDecodeError, TypeError):
                pass

    # ── Strategy 4: Field-per-line format ──
    # Pattern: key"value" on each line, with choices as 0"A) ...", 1"B) ...", etc.
    # Example:
    #   topic"Logical Reasoning/Syllogisms"
    #   question"Which conclusion follows?"
    #   0"A) Option one"
    #   1"B) Option two"
    #   2"C) Option three"
    #   3"D) Option four"
    #   answer"A"
    #   explanation"Because..."
    
    # Check if we see the field-per-line pattern (key"value" without colon separator)
    field_re = re.compile(r'^(\w+)"(.+)"$', re.MULTILINE)
    choice_re = re.compile(r'^(\d+)"(.+)"$', re.MULTILINE)
    
    field_matches = field_re.findall(text)
    choice_matches = choice_re.findall(text)
    
    if len(field_matches) >= 3:  # At least topic, question, answer
        result = {}
        choices = []
        
        for key, value in field_matches:
            key_lower = key.lower()
            if key_lower == "topic":
                result["topic"] = value
            elif key_lower == "question":
                result["question"] = value
            elif key_lower == "answer":
                result["answer"] = value
            elif key_lower == "explanation":
                result["explanation"] = value
        
        # Collect numbered choices (0"A) ...", 1"B) ...", etc.)
        for idx_str, value in choice_matches:
            choices.append(value)
        
        if choices:
            result["choices"] = choices
        
        # Validate we have the minimum required fields
        if "topic" in result and "question" in result and "choices" in result:
            if "answer" not in result:
                result["answer"] = ""
            if "explanation" not in result:
                result["explanation"] = ""
            return result

    # ── Strategy 5: Try to fix common JSON issues (trailing commas, single quotes) ──
    if brace_start != -1 and brace_end != -1:
        candidate = text[brace_start : brace_end + 1]
        # Remove trailing commas before } or ]
        candidate = re.sub(r",\s*([}\]])", r"\1", candidate)
        # Try replacing single quotes with double quotes (risky but worth a shot)
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass

    return None

# ── System prompt — EXACT match to SFT training data (qagent_chatml_train.json) ──
QAGENT_SYSTEM_PROMPT = (
    "You are a competitive question generator for logical reasoning challenges. \n"
    "Generate a challenging multiple-choice question (MCQ) in valid JSON format for the given topic.\n"
    "The question must have exactly 4 choices (A, B, C, D) with exactly one correct answer.\n"
    "Include a clear explanation of why the correct answer is right."
)

# ── Per-subtype generation instructions (same as SFT + GRPO training) ──
SUBTYPE_INSTRUCTIONS = {
    "both_neither_conclusion": "Generate a syllogism MCQ presenting two conclusions from given premises. The choices should be: Only I follows / Only II follows / Both follow / Neither follows.",
    "which_conclusion_follows": "Generate a syllogism MCQ with 4 conclusion options where the solver must identify which one logically follows from the premises.",
    "which_does_not_follow": "Generate a syllogism MCQ with 4 conclusion options where the solver must identify which one does NOT logically follow from the premises.",
    "numeric_next_term": "Generate a numeric series MCQ asking for the next term. Use patterns such as arithmetic, geometric, squares, cubes, Fibonacci, or mixed operations.",
    "alphanumeric_next_term": "Generate an alphanumeric series MCQ asking for the next term. Use patterns combining letters and numbers with systematic progression.",
    "missing_term": "Generate a series MCQ with a missing term in the middle (shown as '?'). The solver must identify the pattern and fill in the blank.",
    "odd_one_out": "Generate a series MCQ where one number is wrong. The solver must find the incorrect term that breaks the pattern.",
    "simple_relation_2hop": "Generate a simple blood relations MCQ involving 2 relationship hops (e.g., A's father's wife).",
    "moderate_relation_3hop": "Generate a moderate blood relations MCQ involving 3 relationship hops.",
    "complex_relation_4hop": "Generate a complex blood relations MCQ involving 4 relationship hops.",
    "extended_relation_5hop": "Generate a challenging blood relations MCQ involving 5 relationship hops.",
    "linear_position_query": "Generate a linear seating arrangement MCQ asking who sits at a specific position.",
    "linear_adjacent_query": "Generate a linear seating arrangement MCQ asking who sits immediately next to a person.",
    "circular_position_query": "Generate a circular seating arrangement MCQ asking who sits to the left or right of a person.",
    "circular_adjacent_query": "Generate a circular seating arrangement MCQ asking who sits next to a person at a circular table.",
    "circular_between_query": "Generate a circular seating arrangement MCQ asking who sits between two persons.",
}

# ── Map subtopic → available question subtypes ──
SUBTYPES_BY_TOPIC = {
    "Syllogisms": ["both_neither_conclusion", "which_conclusion_follows", "which_does_not_follow"],
    "Mixed Series (Alphanumeric)": ["numeric_next_term", "alphanumeric_next_term", "missing_term", "odd_one_out"],
    "Family tree logic": ["simple_relation_2hop", "moderate_relation_3hop", "complex_relation_4hop", "extended_relation_5hop"],
    "Seating Arrangements (Linear, Circular)": ["linear_position_query", "linear_adjacent_query", "circular_position_query", "circular_adjacent_query", "circular_between_query"],
}

SUBTYPES_BY_TOPIC_HARD = {
    "Syllogisms": ["both_neither_conclusion", "which_does_not_follow"],
    "Mixed Series (Alphanumeric)": ["odd_one_out", "missing_term", "alphanumeric_next_term"],
    "Family tree logic": ["extended_relation_5hop", "complex_relation_4hop"],
    "Seating Arrangements (Linear, Circular)": ["circular_between_query", "circular_adjacent_query", "circular_position_query"],
}


class QuestioningAgent(object):
    r"""Agent responsible for generating questions"""

    def __init__(self, **kwargs):
        self.agent = QAgent(**kwargs)

    def build_prompt(
        self,
        topic: str,
        wadvsys: bool = True,
        wicl: bool = True,
        inc_samples: List[Dict[str, str]] | None = None,
    ) -> Tuple[str, str]:
        """
        Build system + user prompt matching SFT training data format.
        
        Training data format (qagent_chatml_train.json):
          system: QAGENT_SYSTEM_PROMPT (fixed 4 lines)
          user:   "{instruction}\\nTopic: {parent}/{child}\\nQuestion Type: {subtype}"
        """
        sys_prompt = QAGENT_SYSTEM_PROMPT

        # Extract subtopic from "Parent/Child" format
        parts = topic.split("/")
        subtopic = parts[-1] if len(parts) > 1 else topic

        # Pick a random subtype for this subtopic
        available_subtypes = SUBTYPES_BY_TOPIC.get(subtopic, [])
        if available_subtypes:
            subtype = random.choice(available_subtypes)
            instruction = SUBTYPE_INSTRUCTIONS.get(subtype, f"Generate a challenging MCQ on: {topic}")
        else:
            subtype = ""
            instruction = f"Generate a challenging MCQ on: {topic}"

        # Build user prompt in training data format
        user_parts = [instruction, f"Topic: {topic}"]
        if subtype:
            user_parts.append(f"Question Type: {subtype}")

        prompt = "\n".join(user_parts)

        return prompt, sys_prompt

    def generate_question(
        self,
        topic: Tuple[str, str] | List[Tuple[str, str]],
        wadvsys: bool = True,
        wicl: bool = True,
        inc_samples: Dict[str, List[Dict[str, str]]] | None = None,
        **gen_kwargs,
    ) -> Tuple[List[str], int | None, float | None]:
        """Generate a question prompt for the LLM"""
        if isinstance(topic, list):
            prompt = []
            for t in topic:
                p, sp = self.build_prompt(
                    f"{t[0]}/{t[1]}", wadvsys, wicl,
                    inc_samples.get(t[1]) if inc_samples else None,
                )
                prompt.append(p)
        else:
            prompt, sp = self.build_prompt(
                f"{topic[0]}/{topic[1]}", wadvsys, wicl,
                inc_samples.get(topic[1]) if inc_samples else None,
            )

        resp, tl, gt = self.agent.generate_response(prompt, sp, **gen_kwargs)

        if (
            isinstance(resp, list) and all(isinstance(r, str) for r in resp)
        ) or isinstance(resp, str):
            return resp, tl, gt
        else:
            return (
                "",
                tl,
                gt if not isinstance(resp, list) else [""] * len(resp),
                tl,
                gt,
            )

    def generate_batches(
        self,
        num_questions: int,
        topics: Dict[str, List[str]],
        batch_size: int = 5,
        wadvsys: bool = True,
        wicl: bool = True,
        inc_samples: Dict[str, List[Dict[str, str]]] | None = None,
        **kwargs,
    ) -> Tuple[List[str], List[int | None], List[float | None]]:
        r"""
        Generate questions in batches
        ---

        Args:
            - num_questions (int): Total number of questions to generate.
            - topics (Dict[str, List[str]]): Dictionary of topics with subtopics.
            - batch_size (int): Number of questions to generate in each batch.
            - wadvsys (bool): Whether to use advance prompt.
            - wicl (bool): Whether to include in-context learning (ICL) samples.
            - inc_samples (Dict[str, List[Dict[str, str]]]|None): In-context learning samples for the topics.
            - **kwargs: Additional keyword arguments for question generation.

        Returns:
            - Tuple[List[str], List[int | None], List[float | None]]: Generated questions, token lengths, and generation times.
        """
        extended_topics = self.populate_topics(topics, num_questions)
        questions = []
        tls, gts = [], []
        # Calculate total batches including the partial last batch
        total_batches = (len(extended_topics) + batch_size - 1) // batch_size
        pbar = tqdm(total=total_batches, desc="STEPS: ")

        for i in range(0, len(extended_topics), batch_size):
            batch_topics = extended_topics[i : i + batch_size]
            batch_questions = self.generate_question(
                batch_topics, wadvsys, wicl, inc_samples, **kwargs
            )
            questions.extend(batch_questions[0]), tls.append(
                batch_questions[1]
            ), gts.append(batch_questions[2])
            pbar.update(1)
        # for last batch with less than batch_size
        if len(extended_topics) % batch_size != 0:
            batch_topics = extended_topics[-(len(extended_topics) % batch_size) :]
            batch_questions = self.generate_question(
                batch_topics, wadvsys, wicl, inc_samples, **kwargs
            )
            questions.extend(batch_questions[0]), tls.append(
                batch_questions[1]
            ), gts.append(batch_questions[2])
            pbar.update(1)
        pbar.close()
        return questions, tls, gts

    def count_tokens_q(self, text: str) -> int:
        """Count the number of tokens using model.tokenizer"""
        if not hasattr(self.agent, "tokenizer"):
            raise AttributeError("The agent does not have a tokenizer attribute.")
        return len(self.agent.tokenizer.encode(text, add_special_tokens=False))

    def filter_questions(
        self, questions: List[str | Dict[str, str | Any]]
    ) -> List[Dict[str, str | Any]]:
        def basic_checks(q2: Dict[str, str]) -> bool:
            # check required keys
            required_keys = ["topic", "question", "choices", "answer"]
            if all((key in q2) for key in required_keys):
                # check choices format
                checks = all(
                    isinstance(choice, str)
                    and len(choice) > 2
                    and choice[0].upper() in "ABCD"
                    for choice in q2["choices"]
                )
                if (
                    isinstance(q2["choices"], list)
                    and len(q2["choices"]) == 4
                    and checks
                ):
                    # check answer format
                    # Check token length
                    check_len = sum(
                        self.count_tokens_q(q2[k]) for k in ["question", "answer"]
                    )
                    check_len += (
                        sum(self.count_tokens_q(choice) for choice in q2["choices"])
                        - 15
                    )
                    if check_len < 130:
                        if (
                            check_len
                            + self.count_tokens_q(q2.get("explanation", "None"))
                            <= 1024
                        ):
                            # Extra Checks: (PLUS checks) len(q2['answer']) == 1 and q2['answer'].upper() in 'ABCD':
                            if isinstance(q2["answer"], str):
                                return True
            return False

        correct_format_question = []
        for i, q in enumerate(questions):
            if isinstance(q, dict):
                if basic_checks(q):
                    correct_format_question.append(q)
            elif isinstance(q, str):
                # Use robust parser instead of plain json.loads
                q1 = robust_parse_question(q)
                if q1 is not None and basic_checks(q1):
                    correct_format_question.append(q1)
                else:
                    print(f"Skipping unparseable question at index {i}: {q[:100]}...")
                    continue
            else:
                continue
        if len(correct_format_question) >= 0.5 * len(questions):
            return correct_format_question
        return list()

    def save_questions(self, questions: Any, file_path: str | Path) -> None:
        """Save generated questions to a JSON file"""
        # Ensure dir exist
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        # Save to JSON file
        with open(file_path, "w") as f:
            json.dump(questions, f, indent=4)

    def populate_topics(
        self, topics: Dict[str, List[str]], num_questions: int
    ) -> List[str]:
        """Populate topics randomly to generate num_questions number of topics"""
        if not isinstance(topics, dict):
            raise ValueError(
                "Topics must be a dictionary with topic names as keys and lists of subtopics as values."
            )

        all_subtopics = [(t, st) for t, sublist in topics.items() for st in sublist]
        if not all_subtopics:
            raise ValueError("No subtopics found in the provided topics dictionary.")

        selected_topics = random.choices(all_subtopics, k=num_questions)
        return selected_topics

    @staticmethod
    def load_icl_samples(file_path: str | Path) -> Dict[str, List[Dict[str, str]]]:
        """Load in-context learning samples from a JSON file"""
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File {file_path} does not exist.")
        with open(file_path, "r") as f:
            samples = json.load(f)
        if not isinstance(samples, dict):
            raise ValueError("Samples must be inside dictionary.")
        return samples


# Example usage
if __name__ == "__main__":
    import argparse
    import yaml

    # ++++++++++++++++++++++++++
    # Run: python -m agents.question_agent --num_questions 20 --output_file outputs/questions.json --batch_size 5 --verbose
    # ++++++++++++++++++++++++++

    argparser = argparse.ArgumentParser(
        description="Generate questions using the QuestioningAgent."
    )
    argparser.add_argument(
        "--num_questions",
        type=int,
        default=10,
        help="Total number of questions to generate.",
    )
    argparser.add_argument(
        "--output_file",
        type=str,
        default="outputs/questions.json",
        help="Output file name to save the generated questions.",
    )
    argparser.add_argument(
        "--batch_size", type=int, default=5, help="Batch size for generating questions."
    )
    argparser.add_argument(
        "--verbose", action="store_true", help="Enable verbose output for debugging."
    )
    args = argparser.parse_args()

    inc_samples = QuestioningAgent.load_icl_samples("assets/topics_example.json")

    # Load topics.json file.
    with open("assets/topics.json") as f:
        topics = json.load(f)

    agent = QuestioningAgent()
    # gen_kwargs = {"tgps_show": True, "max_new_tokens": 1024, "temperature": 0.1, "top_p": 0.9, "do_sample": True}
    gen_kwargs = {"tgps_show": True}
    with open("qgen.yaml", "r") as f:
        gen_kwargs.update(yaml.safe_load(f))

    question, tls, gts = agent.generate_batches(
        num_questions=args.num_questions,
        topics=topics,
        batch_size=args.batch_size,
        wadvsys=True,
        wicl=True,
        inc_samples=inc_samples,
        **gen_kwargs,
    )
    print(f"Generated {len(question)} questions!")
    if args.verbose:
        for q in question:
            print(q, flush=True)
        print("\n" + "=" * 50 + "\n\n")
        if gen_kwargs.get("tgps_show", False):
            print("Time taken per batch generation:", gts)
            print("Tokens generated per batch:", tls)
            print(
                f"Total Time Taken: {sum(gts):.3f} seconds; Total Tokens: {sum(tls)}; TGPS: {sum(tls)/sum(gts):.3f} seconds\n\n"
            )
        print("\n" + "+" * 50 + "\n")

    # Parse & normalize each question — robust parser first, LLM fallback last
    ques = []
    parse_stats = {"direct_json": 0, "robust_parsed": 0, "llm_fallback": 0, "failed": 0}
    for i, q in enumerate(question):
        # Try 1: Direct JSON
        try:
            parsed = json.loads(q)
            if isinstance(parsed, dict):
                ques.append(json.dumps(parsed))  # re-serialize clean JSON
                parse_stats["direct_json"] += 1
                continue
        except (json.JSONDecodeError, TypeError):
            pass

        # Try 2: Robust parser (handles leading garbage, field-per-line, code fences, etc.)
        parsed = robust_parse_question(q)
        if parsed is not None:
            print(f"[robust_parse] Fixed malformed output at index {i}")
            ques.append(json.dumps(parsed))
            parse_stats["robust_parsed"] += 1
            continue

        # Try 3: LLM self-reflection fallback (expensive — last resort)
        print(f"[llm_fallback] Could not parse index {i}, using LLM extraction...")
        prompt = (
            "Extract **ONLY** the topic, question, choices, answer, and explanation while discarding the rest.\n"
            "Also please remove JSON code block text with backticks** like **```json** and **```**.\n\n"
            "String:\n"
            "{}\n\n"
            "Given Format:\n"
            "{{\n"
            '  "topic": "...",\n'
            '  "question": "...",\n'
            '  "choices": ["A) ...", "B) ...", "C) ...", "D) ..."],\n'
            '  "answer": "Only the option letter (A, B, C, or D)",\n'
            '  "explanation": "..."\n'
            "}}"
        )
        llm_result = agent.agent.generate_response(
            prompt.format(q),
            "You are an expert JSON extractor.",
            max_new_tokens=1024,
            temperature=0.0,
            do_sample=False,
        )
        # Try to parse the LLM result too
        if isinstance(llm_result, tuple):
            llm_result = llm_result[0]  # generate_response returns (text, tl, gt)
        llm_parsed = robust_parse_question(str(llm_result))
        if llm_parsed is not None:
            ques.append(json.dumps(llm_parsed))
            parse_stats["llm_fallback"] += 1
        else:
            ques.append(str(llm_result))  # keep raw as last resort
            parse_stats["failed"] += 1

    print(f"\nParse stats: {parse_stats}")
    print(f"  Direct JSON: {parse_stats['direct_json']}/{len(question)}")
    print(f"  Robust fixed: {parse_stats['robust_parsed']}/{len(question)}")
    print(f"  LLM fallback: {parse_stats['llm_fallback']}/{len(question)}")
    print(f"  Failed: {parse_stats['failed']}/{len(question)}")
    # Save the questions for later analysis
    agent.save_questions(ques, args.output_file)
    filtered_file_name = args.output_file.replace(
        "questions.json", "filtered_questions.json"
    )
    agent.save_questions(agent.filter_questions(ques), filtered_file_name)
    print(f"Saved to {args.output_file}!")

    # ========================================================================================
