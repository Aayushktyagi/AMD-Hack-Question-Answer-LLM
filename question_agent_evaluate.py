import json
import os
from google import genai
from z3 import *
import ast
from transformers import AutoTokenizer
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen3-4B", padding_side='left')
from typing import Dict, Any, List

def count_tokens_q(text: str) -> int:
    """Count the number of tokens using Qwen3-4B tokenizer"""
    return len(tokenizer.encode(text, add_special_tokens=False))

def count_tokens(text: str) -> int:
    required_keys = ['topic', 'question', 'choices', 'answer']
    if all((key in text) for key in required_keys):
        total_tokens = 0
        for key in required_keys:
            if key == 'choices':
                total_tokens += sum(count_tokens_q(choice) for choice in text[key])
            else:
                total_tokens += count_tokens_q(text[key])
        return total_tokens, total_tokens+count_tokens_q(text.get('explanation', 'None'))
    return None, None

def basic_checks(q2: Dict[str, str])->bool:
    # check required keys
    required_keys = ['topic', 'question', 'choices', 'answer']
    if all((key in q2) for key in required_keys):
        # check choices format
        checks = all(isinstance(choice, str) and len(choice) > 2 and choice[0].upper() in 'ABCD' for choice in q2['choices'])
        if isinstance(q2['choices'], list) and len(q2['choices']) == 4 and checks:
            # check answer format
            # Check token length
            check_len = sum(count_tokens_q(q2[k]) for k in ['question', 'answer'])
            check_len += sum(count_tokens_q(choice) for choice in q2['choices']) - 15
            if check_len < 130:
                if check_len + count_tokens_q(q2.get('explanation', 'None')) <= 1024:
                    # Extra Checks: (PLUS checks) len(q2['answer']) == 1 and q2['answer'].upper() in 'ABCD':
                    if isinstance(q2['answer'], str):
                        return True
    return False

def get_gemini_prediction(prompt, model, text_format=None):
    client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY", ""))

    response = client.models.generate_content(
    model=model,
    contents=prompt,
    config={
        "response_mime_type": "application/json",
    },
    )  
    return response.text

def get_qwen_prediction(prompt, model, text_format=None):
    pass  # Implement Qwen prediction logic here

def compute_metrics(content: Dict[str, str|Any], model) -> Dict[str, Any]:
    metrics = {}
    topic = content["topic"]
    question = content["question"]
    choices = content["choices"]
    answer = content["answer"]    
    explanation = content["explanation"]

    prompt = f"""Evaluate the following question and answer pair. Check the following aspects and return a JSON with the results: (i) Topic Correctness: Does the question belong to the stated topic? (ii) Difficulty Level: Evaluate the question based on the complexity of the question and the reasoning required. (iii) Answer Correctness: Is the provided answer correct based on the question and choices? (iv) Explanation Quality: Evaluate the quality of the explanation provided for the answer. (return a score between 1 to 5) (v) Choice Similarity: Assess how similar the choices are to each other. (return a score between 1 to 5, where 1 means very similar and 5 means very different). 
    
    Rubric for Topic Correctness: 1-2: The question is not relevant to the stated topic or is only tangentially related. 3: The question is somewhat relevant to the topic but may include some unrelated elements. 4-5: The question is highly relevant and directly pertains to the stated topic.

    Rubric for Difficulty Level: 1: The question can be answered with basic recall or simple reasoning. 2: The question requires some level of analysis, synthesis, or multi-step reasoning. 3: The question demands complex reasoning, critical thinking, and may involve multiple concepts or steps to arrive at the answer.

    Rubric for Answer Correctness: 0: The provided answer is incorrect based on the question and choices. 1: The provided answer is correct based on the question and choices.

    Rubric for Explanation Quality: 1: The explanation is unclear, incomplete, or does not justify the answer. 2: The explanation provides some justification but may lack clarity or depth. 3: The explanation is clear and provides a reasonable justification for the answer. 4: The explanation is detailed, well-structured, and effectively justifies the answer. 5: The explanation is comprehensive, insightful, and provides an excellent justification for the answer.

    Rubric for Choice Similarity: 1: All choices are very similar to each other, making it difficult to distinguish between them. 2: Most choices are similar, with only minor differences. 3: Choices have a mix of similarities and differences, with no clear pattern. 4: Most choices are different from each other, with only minor similarities. 5: All choices are very different from each other, making it easy to distinguish between them.
    
    Return the results in the following JSON format: {{"topic_correctness": <score>, "difficulty_level": <score>, "answer_correctness": <score>, "explanation_quality": <score>, "choice_similarity": <score>}}. Here is the question and answer pair: \n\nTopic: {topic}\nQuestion: {question}\nChoices: {choices}\nAnswer: {answer}\nExplanation: {explanation}"""

    text_format = {
        "type": "object",
        "properties": {
            "topic_correctness": {"type": "integer", "minimum": 1, "maximum": 5},
            "difficulty_level": {"type": "integer", "minimum": 1, "maximum": 3},
            "answer_correctness": {"type": "integer", "minimum": 0, "maximum": 1},
            "explanation_quality": {"type": "integer", "minimum": 1, "maximum": 5},
            "choice_similarity": {"type": "integer", "minimum": 1, "maximum": 5}
        },
        "required": ["topic_correctness", "difficulty_level", "answer_correctness", "explanation_quality", "choice_similarity"]
    }
    if model.startswith("gemini"):
        response = get_gemini_prediction(prompt, model=model, text_format=text_format)
    elif model.startswith("qwen"):
        response = get_qwen_prediction(prompt, model=model, text_format=text_format)
    else:
        raise ValueError("Unsupported model specified.")

    try:
        response_json = json.loads(response)
        metrics = {
            "topic_correctness": response_json.get("topic_correctness"),
            "difficulty_level": response_json.get("difficulty_level"),
            "answer_correctness": response_json.get("answer_correctness"),
            "explanation_quality": response_json.get("explanation_quality"),
            "choice_similarity": response_json.get("choice_similarity")
        }
        return metrics, True
    except json.JSONDecodeError:
        print(f"Error decoding JSON response: {response}")

    return response, False

def main(input_file: str, model:str):

    with open(input_file, 'r') as file:
        data = json.load(file)

    macro_topic_accuracy = 0
    macro_violation_percentage = 0
    macro_total_tokens_without_explanation = 0
    macro_total_tokens_with_explanation = 0
    macro_difficulty_distribution = 0
    macro_choice_similarity_average = 0
    macro_answer_correctness_percentage = 0
    valid_responses_count = 0

    for content in data:
        metrics, success = compute_metrics(content, model)
        if success:
            content["metrics"] = metrics
            macro_topic_accuracy += metrics["topic_correctness"]
            macro_violation_percentage += 1 - int(basic_checks(content))
            macro_difficulty_distribution += metrics["difficulty_level"]
            macro_choice_similarity_average += metrics["choice_similarity"]
            macro_answer_correctness_percentage += metrics["answer_correctness"]
            tokens_without_explanation, tokens_with_explanation = count_tokens(content)
            if tokens_without_explanation is not None and tokens_with_explanation is not None:
                macro_total_tokens_without_explanation += tokens_without_explanation
                macro_total_tokens_with_explanation += tokens_with_explanation
            valid_responses_count += 1

        else:
            content["metrics"] = {"error": "Failed to compute metrics", "raw_output": metrics}

    if valid_responses_count > 0:
        macro_topic_accuracy /= valid_responses_count
        macro_violation_percentage /= valid_responses_count
        macro_choice_similarity_average /= valid_responses_count
        macro_answer_correctness_percentage /= valid_responses_count
        macro_total_tokens_without_explanation /= valid_responses_count
        macro_total_tokens_with_explanation /= valid_responses_count

    macro_metrics = {
        "TOPIC_ACCURACY": macro_topic_accuracy,
        "VIOLATION_PERCENTAGE": macro_violation_percentage,
        "DIFFICULTY_DISTRIBUTION": macro_difficulty_distribution,
        "CHOICE_SIMILARITY_AVERAGE": macro_choice_similarity_average,
        "ANSWER_CORRECTNESS_PERCENTAGE": macro_answer_correctness_percentage,
        "AVERAGE_TOKENS_WITHOUT_EXPLANATION": macro_total_tokens_without_explanation,
        "AVERAGE_TOKENS_WITH_EXPLANATION": macro_total_tokens_with_explanation,
        "VALID_RESPONSES_COUNT": valid_responses_count
    }

    output_file = input_file.replace('.json', f'_evaluated_{model}.json').replace('data', 'outputs')
    with open(output_file, 'w') as file:
        json.dump(macro_metrics, file, indent=4)

    print(f"Macro Metrics: {json.dumps(macro_metrics, indent=4)}")

if __name__ == "__main__":
    # Example usage
    import argparse
    parser = argparse.ArgumentParser(description="Evaluate question-answer pairs and compute metrics.")
    parser.add_argument("--input_file", type=str, required=True, help="Path to the input JSON file containing question-answer pairs.")
    parser.add_argument("--model", type=str, default="gemini-3-pro-preview", help="Model name to use for evaluation.")
    args = parser.parse_args()
    
    main(args.input_file, args.model)

