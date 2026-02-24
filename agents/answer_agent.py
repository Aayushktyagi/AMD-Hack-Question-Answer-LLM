#!/usr/bin/python3

import re
import json

from pathlib import Path
from tqdm import tqdm
from typing import List, Tuple, Dict, Any

from .answer_model import AAgent
# from .answer_model_llama import AAgent


def robust_parse_answer(text: str) -> dict | None:
    """
    Robustly parse model output into an answer dict with 'reasoning' and 'answer' keys.

    Handles these known malformed formats:
      1. Valid JSON                          → json.loads() directly
      2. Markdown code fences                → ```json { ... } ``` → strip fences
      3. JSON with leading garbage           → 0"{...}" → extract {…} via brace matching
      4. Field-per-line format               → reasoning"..."\nanswer"B" 
      5. Trailing null lines                 → 0"{...}"\n1null\n2null → strip nulls first
      6. Common JSON fixes                   → trailing commas, etc.

    Returns parsed dict or None if all strategies fail.
    """
    if not text or not isinstance(text, str):
        return None

    text = text.strip()

    # ── Pre-clean: strip trailing null/None lines (e.g., "1null", "2null") ──
    lines = text.split("\n")
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        # Skip lines like "1null", "2null", "0null", "null", "None"
        if re.match(r'^\d*(null|None)$', stripped, re.IGNORECASE):
            continue
        cleaned_lines.append(line)
    text = "\n".join(cleaned_lines).strip()

    if not text:
        return None

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

    # ── Strategy 3: Extract {…} from anywhere (handles leading 0", quotes, etc.) ──
    brace_start = text.find("{")
    brace_end = -1
    if brace_start != -1:
        depth = 0
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
    # Handles:
    #   reasoning"Some reasoning text here."
    #   answer"B"
    field_re = re.compile(r'^(\w+)"(.+)"$', re.MULTILINE)
    field_matches = field_re.findall(text)

    if field_matches:
        result = {}
        for key, value in field_matches:
            key_lower = key.lower()
            if key_lower == "reasoning":
                result["reasoning"] = value
            elif key_lower == "answer":
                result["answer"] = value
            elif key_lower == "explanation":
                result["reasoning"] = value  # map explanation → reasoning

        if "answer" in result:
            if "reasoning" not in result:
                result["reasoning"] = ""
            return result

    # ── Strategy 5: Extract answer letter from free text as last resort ──
    # Look for patterns like "answer is B", "Answer: C", standalone letter after reasoning
    answer_match = re.search(
        r'(?:answer\s*(?:is|:|=)\s*)?\b([A-D])\b',
        text, re.IGNORECASE
    )
    if answer_match:
        answer_letter = answer_match.group(1).upper()
        # Use the rest of the text as reasoning
        reasoning = text[:answer_match.start()].strip()
        if not reasoning:
            reasoning = text
        return {"reasoning": reasoning, "answer": answer_letter}

    # ── Strategy 6: Fix common JSON issues (trailing commas) ──
    if brace_start != -1 and brace_end != -1:
        candidate = text[brace_start : brace_end + 1]
        candidate = re.sub(r",\s*([}\]])", r"\1", candidate)
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass

    return None

class AnsweringAgent(object):
    r"""Agent responsible for answering MCQ questions with confidence scoring"""

    def __init__(self, select_prompt1: bool = True, **kwargs):
        self.agent = AAgent(**kwargs)
        self.select_prompt1 = select_prompt1

    def build_prompt(self, question_data: Dict[str, str | Any]) -> Tuple[str, str]:
        """Generate an answer to the given MCQ question with confidence and reasoning"""

        # ── System prompts matching the SFT training data (AAGENT_SYSTEM_PROMPT) ──
        sys_prompt1 = (
           "You are a meticulous logical reasoning expert. Your task is to solve multiple-choice questions with high precision.\nOutput constraint: \nYou must answer the question and output ONLY valid JSON.\n\nJSON schema:\n{\n  \"properties\": {\n    \"reasoning\": {\n      \"title\": \"Reasoning\",\n      \"type\": \"string\"\n    },\n    \"answer\": {\n      \"enum\": [\n        \"A\",\n        \"B\",\n        \"C\",\n        \"D\"\n      ],\n      \"title\": \"Answer\",\n      \"type\": \"string\"\n    }\n  },\n  \"required\": [\n    \"reasoning\",\n    \"answer\"\n  ],\n  \"title\": \"Answer\",\n  \"type\": \"object\"\n}"
        )
        sys_prompt2 = (
            "You are a logical reasoning expert. Answer the given multiple-choice question.\n"
            "Output constraint: \n"
            "You must answer the question and output ONLY valid JSON.\n\n"
            "JSON schema:\n"
            "{\n"
            '  "properties": {\n'
            '    "reasoning": {\n'
            '      "title": "Reasoning",\n'
            '      "type": "string"\n'
            "    },\n"
            '    "answer": {\n'
            '      "enum": [\n'
            '        "A",\n'
            '        "B",\n'
            '        "C",\n'
            '        "D"\n'
            "      ],\n"
            '      "title": "Answer",\n'
            '      "type": "string"\n'
            "    }\n"
            "  },\n"
            '  "required": [\n'
            '    "reasoning",\n'
            '    "answer"\n'
            "  ],\n"
            '  "title": "Answer",\n'
            '  "type": "object"\n'
            "}"
        )

        # tmpl = (
        #     "Question: {}\n"
        #     "Choices: {}\n\n"
        # )

        # prompt = tmpl.format(
            # question_data["question"], self._format_choices(question_data["choices"])
        # )
        prompt = question_data['question']+' '+' '.join(question_data['choices'])
        print(prompt)

        return prompt, sys_prompt1 if self.select_prompt1 else sys_prompt2

    def answer_question(
        self, question_data: Dict | List[Dict], **kwargs
    ) -> Tuple[List[Dict], int | None, float | None]:
        """Generate answer(s) for the given question(s)"""
        if isinstance(question_data, list):
            prompt = []
            for qd in question_data:
                p, sp = self.build_prompt(qd)
                prompt.append(p)
        else:
            prompt, sp = self.build_prompt(question_data)

        resp, tl, gt = self.agent.generate_response(prompt, sp, **kwargs)

        if (
            isinstance(resp, list) and all(isinstance(r, str) for r in resp)
        ) or isinstance(resp, str):
            return resp, tl, gt
        else:
            # Fallback: return empty string(s) preserving the expected 3-tuple
            if isinstance(resp, list):
                return [""] * len(resp), tl, gt
            return "", tl, gt

    @staticmethod
    def _parse_and_normalize(raw: str) -> dict | str:
        """Parse a raw model output string into a clean answer dict in-place.
        Returns the parsed dict if successful, or the original string if not."""
        # Try direct JSON first
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict) and "answer" in parsed:
                ans = parsed["answer"].strip()
                if len(ans) == 1:
                    parsed["answer"] = ans.upper()
                elif ans and ans[0].upper() in "ABCD":
                    parsed["answer"] = ans[0].upper()
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass

        # Try robust parser
        parsed = robust_parse_answer(raw)
        if parsed is not None and "answer" in parsed:
            ans = parsed["answer"].strip()
            if len(ans) == 1:
                parsed["answer"] = ans.upper()
            elif ans and ans[0].upper() in "ABCD":
                parsed["answer"] = ans[0].upper()
            return parsed

        return raw  # Return original if all parsing fails

    def answer_batches(
        self, questions: List[Dict], batch_size: int = 5, **kwargs
    ) -> Tuple[List[Dict], List[int | None], List[float | None]]:
        """Answer questions in batches, with in-place robust parsing of model outputs."""
        answers = []
        tls, gts = [], []
        total_batches = (len(questions) + batch_size - 1) // batch_size
        pbar = tqdm(total=total_batches, desc="STEPS: ", unit="batch")
        for i in range(0, len(questions), batch_size):
            batch_questions = questions[i : i + batch_size]
            batch_answers, tl, gt = self.answer_question(batch_questions, **kwargs)
            answers.extend(batch_answers)
            tls.append(tl)
            gts.append(gt)
            pbar.update(1)

        pbar.close()

        # ── In-place robust parsing: convert raw strings → clean dicts ──
        parse_stats = {"direct_json": 0, "robust_parsed": 0, "raw": 0}
        for i, a in enumerate(answers):
            if isinstance(a, dict):
                parse_stats["direct_json"] += 1
                continue
            if not isinstance(a, str):
                parse_stats["raw"] += 1
                continue
            result = self._parse_and_normalize(a)
            if isinstance(result, dict):
                answers[i] = result
                if a != json.dumps(result):  # was actually fixed
                    parse_stats["robust_parsed"] += 1
                else:
                    parse_stats["direct_json"] += 1
            else:
                parse_stats["raw"] += 1
        print(f"[answer_batches] Parse stats: {parse_stats}")

        return answers, tls, gts

    def count_tokens_a(self, text: str) -> int:
        """Count the number of tokens in the text using the agent's tokenizer"""
        if not hasattr(self.agent, "tokenizer"):
            raise AttributeError("The agent does not have a tokenizer attribute.")
        return len(self.agent.tokenizer.encode(text, add_special_tokens=False))

    def filter_answers(self, ans: List[str | Dict[str, str]]) -> List[Dict[str, str]]:
        r"""Filter answers to ensure they are in the correct format"""

        def basic_checks(a1: Dict[str, str]) -> bool:
            # check required keys
            required_keys = ["answer"]
            if all((key in a1) and isinstance(a1[key], str) for key in required_keys):
                if len(a1["answer"]) == 1 and (a1["answer"] not in "ABCDabcd"):
                    return False
                check_len = self.count_tokens_a(a1["answer"])
                if check_len < 50:
                    check_len += self.count_tokens_a(a1.get("reasoning", "None"))
                    if check_len < 512:
                        # check answer format - EXTRA checks
                        # if len(a1['answer']) == 1 and a1['answer'].upper() in 'ABCD':
                        return True
            return False

        filtered_answers = []
        for i, a in enumerate(ans):
            if isinstance(a, dict):
                if basic_checks(a):
                    filtered_answers.append(a)
                else:
                    filtered_answers.append(None)
                    print(f"Skipping invalid answer at index {i}: {a}")
            elif isinstance(a, str):
                # Use robust parser instead of plain json.loads
                a1 = robust_parse_answer(a)
                if a1 is not None and basic_checks(a1):
                    filtered_answers.append(a1)
                else:
                    filtered_answers.append(None)
                    print(f"Skipping unparseable answer at index {i}: {a[:100]}...")
            else:
                # If the answer is neither a dict nor a str, skip it
                print(f"Skipping unsupported type at index {i}: {type(a)}")
                filtered_answers.append(None)
        return filtered_answers

    def save_answers(self, answers: List[str], file_path: str | Path) -> None:
        """Save generated answers to a JSON file"""
        # check for existence of dir
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w") as f:
            json.dump([a for a in answers], f, indent=4)

    def _format_choices(self, choices: List[str]) -> str:
        r"""Format the choices for better readability"""
        formatted = []
        for choice in choices:
            # Ensure each choice starts with a letter if not already formatted
            if not re.match(r"^[A-D]\)", choice.strip()):
                # Extract letter from existing format or assign based on position
                letter = chr(65 + len(formatted))  # A, B, C, D
                formatted.append(f"{letter}) {choice.strip()}")
            else:
                formatted.append(choice.strip())
        return " ".join(formatted)


# Example usage
if __name__ == "__main__":
    import json
    import yaml
    import argparse
    from utils.build_prompt import auto_json, option_extractor_prompt

    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # python -m agents.answer_agent --input_file outputs/filtered_questions.json --output_file outputs/answers.json --batch_size 5 --verbose
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    argparser = argparse.ArgumentParser(description="Run the Answering Agent")
    argparser.add_argument(
        "--input_file",
        type=str,
        default="outputs/filtered_questions.json",
        help="Path to the input JSON file with questions",
    )
    argparser.add_argument(
        "--output_file",
        type=str,
        default="outputs/answers.json",
        help="Path to save the answers",
    )
    argparser.add_argument(
        "--batch_size", type=int, default=5, help="Batch size for processing questions"
    )
    argparser.add_argument(
        "--verbose", action="store_true", help="Enable verbose output"
    )
    args = argparser.parse_args()

    SELECT_PROMPT1 = True  # Use the SFT-trained system prompt

    # Load sample questions (assuming they're saved from QuestioningAgent)
    with open(args.input_file, "r") as f:
        sample_questions = json.load(f)

    agent = AnsweringAgent(select_prompt1=SELECT_PROMPT1)

    # gen_kwargs = {"tgps_show": True, "max_new_tokens": 512, "temperature": 0.1, "top_p": 0.9, "do_sample": True}
    gen_kwargs = {"tgps_show": True}
    with open("agen.yaml", "r") as f:
        gen_kwargs.update(yaml.safe_load(f))
    answer, tls, gts = agent.answer_batches(
        questions=sample_questions, batch_size=args.batch_size, **gen_kwargs
    )
    ans = []
    parse_stats = {"direct_json": 0, "robust_parsed": 0, "llm_fallback": 0, "failed": 0}
    for idx, (q, a) in enumerate(zip(sample_questions, answer)):
        if args.verbose:
            print(f"\n=== Question {idx+1} ===")
            print(f"Question: {q.get('question', 'N/A')}")
            print(f"Expected: {q.get('answer', 'N/A')}")
            print(f"Model Answer:\n{a}")

        # If answer_batches already parsed this into a dict, accept it directly
        if isinstance(a, dict) and "answer" in a:
            parse_stats["direct_json"] += 1
            ans.append(a)
            continue

        # From here, a must be a string
        a_str = str(a)

        # Try 1: Direct JSON
        try:
            parsed = json.loads(a_str)
            if isinstance(parsed, dict) and "answer" in parsed:
                val = parsed["answer"].strip()
                parsed["answer"] = val[0].upper() if len(val) != 1 else val.upper()
                parse_stats["direct_json"] += 1
                ans.append(parsed)
                continue
        except (json.JSONDecodeError, TypeError):
            pass

        # Try 2: Robust parser (handles leading garbage, field-per-line, null lines, etc.)
        parsed = robust_parse_answer(a_str)
        if parsed is not None and "answer" in parsed:
            print(f"[robust_parse] Fixed malformed answer at index {idx}")
            val = parsed["answer"].strip()
            parsed["answer"] = val[0].upper() if len(val) != 1 else val.upper()
            parse_stats["robust_parsed"] += 1
            ans.append(parsed)
            continue

        # Try 3: LLM self-reflection fallback (expensive — last resort)
        print(f"[llm_fallback] Could not parse index {idx}, using LLM extraction...")
        llm_result = agent.agent.generate_response(auto_json(a_str))
        if isinstance(llm_result, tuple):
            llm_result = llm_result[0]
        llm_parsed = robust_parse_answer(str(llm_result))
        if llm_parsed is not None and "answer" in llm_parsed:
            val = llm_parsed["answer"].strip()
            llm_parsed["answer"] = val[0].upper() if len(val) != 1 else val.upper()
            a = llm_parsed
            parse_stats["llm_fallback"] += 1
        else:
            a = str(llm_result)
            parse_stats["failed"] += 1
        ans.append(a)

    print(f"\nParse stats: {parse_stats}")
    print(f"  Direct JSON: {parse_stats['direct_json']}/{len(answer)}")
    print(f"  Robust fixed: {parse_stats['robust_parsed']}/{len(answer)}")
    print(f"  LLM fallback: {parse_stats['llm_fallback']}/{len(answer)}")
    print(f"  Failed: {parse_stats['failed']}/{len(answer)}")

    if args.verbose:
        if gen_kwargs.get("tgps_show", False):
            for idx, (tl, gt) in enumerate(zip(tls, gts)):
                print(f"BATCH - {idx}")
                print(f"Tokens: {tl}, Time: {gt:.3f} seconds")
                print(f"TGPS: {tl/gt:.3f} seconds")
            print("\n" + "=" * 50)
            print(
                f"Total Time: {sum(gts):.3f} seconds; Total Tokens: {sum(tls)}; TGPS: {sum(tls)/sum(gts):.3f} seconds"
            )

    # Save answers
    agent.save_answers(ans, args.output_file)
    filtered_file_name = args.output_file.replace(
        "answers.json", "filtered_answers.json"
    )
    agent.save_answers(agent.filter_answers(ans), filtered_file_name)
