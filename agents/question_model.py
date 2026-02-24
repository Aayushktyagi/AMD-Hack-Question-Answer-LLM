# Q-Agent: GRPO-trained Qwen2.5-14B-Instruct for question generation.
# Loads the merged 16-bit model from GRPO training (Train_Q_Agent_GRPO.ipynb).
# Uses Unsloth FastLanguageModel for 2x faster inference.
import os
import time
import torch
from pathlib import Path
from typing import Optional, List
from unsloth import FastLanguageModel

torch.random.manual_seed(0)
os.environ['HF_HOME'] = '/workspace/AAIPL/hf_models/'

# ── Model path ──
# Default: merged 16-bit GRPO model saved alongside the training notebook.
# Override via QAGENT_MODEL_PATH env variable for custom locations.
DEFAULT_QAGENT_MODEL = str(
    Path(__file__).parent.parent / "qagent_grpo_merged_16bit"
)


class QAgent(object):
    def __init__(self, **kwargs):
        model_name = kwargs.get(
            "model_name",
            os.environ.get("QAGENT_MODEL_PATH", DEFAULT_QAGENT_MODEL),
        )
        max_seq_length = kwargs.get("max_seq_length", 2048)
        print(f"[QAgent] Loading model: {model_name}")

        # Load via Unsloth FastLanguageModel — matches Train_Q_Agent_GRPO.ipynb
        self.model, self.tokenizer = FastLanguageModel.from_pretrained(
            model_name=model_name,
            max_seq_length=max_seq_length,
            dtype=torch.bfloat16,      # BF16 for ROCm / MI300X
            load_in_4bit=False,         # Full precision
            trust_remote_code=True,
        )
        # Enable Unsloth's native 2x faster inference
        FastLanguageModel.for_inference(self.model)

        # Ensure pad token is set & use left-padding for batched generation
        self.tokenizer.padding_side = "left"
        if self.tokenizer.pad_token_id is None:
            self.tokenizer.pad_token_id = self.tokenizer.eos_token_id

        print(
            f"[QAgent] Model loaded — "
            f"{sum(p.numel() for p in self.model.parameters()):,} params"
        )

    def generate_response(
        self, message: str | List[str], system_prompt: Optional[str] = None, **kwargs
    ) -> str:
        if system_prompt is None:
            system_prompt = "You are a helpful assistant."
        if isinstance(message, str):
            message = [message]

        # Prepare all messages for batch processing
        all_messages = []
        for msg in message:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": msg},
            ]
            all_messages.append(messages)

        # convert all messages to text format (Qwen2.5 chat template)
        texts = []
        for messages in all_messages:
            text = self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
            texts.append(text)

        # tokenize all texts together with padding
        model_inputs = self.tokenizer(
            texts, return_tensors="pt", padding=True, truncation=True
        ).to(self.model.device)

        tgps_show_var = kwargs.get("tgps_show", False)

        # Build generation kwargs — pass through sampling params
        gen_kwargs = dict(
            max_new_tokens=kwargs.get("max_new_tokens", 1024),
            pad_token_id=self.tokenizer.pad_token_id,
        )
        if kwargs.get("do_sample", False):
            gen_kwargs["do_sample"] = True
            gen_kwargs["temperature"] = kwargs.get("temperature", 0.7)
            gen_kwargs["top_p"] = kwargs.get("top_p", 0.9)
        if "repetition_penalty" in kwargs:
            gen_kwargs["repetition_penalty"] = kwargs["repetition_penalty"]

        # conduct batch text completion
        if tgps_show_var:
            start_time = time.time()
        generated_ids = self.model.generate(**model_inputs, **gen_kwargs)
        if tgps_show_var:
            generation_time = time.time() - start_time

        # decode the batch
        batch_outs = []
        if tgps_show_var:
            token_len = 0
        for i, (input_ids, generated_sequence) in enumerate(
            zip(model_inputs.input_ids, generated_ids)
        ):
            # extract only the newly generated tokens
            output_ids = generated_sequence[len(input_ids):]

            # compute total tokens generated
            if tgps_show_var:
                token_len += len(output_ids)

            # decode the full result
            content = self.tokenizer.decode(
                output_ids, skip_special_tokens=True
            ).strip("\n")
            batch_outs.append(content)

        if tgps_show_var:
            return (
                batch_outs[0] if len(batch_outs) == 1 else batch_outs,
                token_len,
                generation_time,
            )
        return batch_outs[0] if len(batch_outs) == 1 else batch_outs, None, None


if __name__ == "__main__":
    # ── System prompt matching SFT training data (qagent_chatml_train.json) ──
    system_prompt = (
        "You are a competitive question generator for logical reasoning challenges. \n"
        "Generate a challenging multiple-choice question (MCQ) in valid JSON format for the given topic.\n"
        "The question must have exactly 4 choices (A, B, C, D) with exactly one correct answer.\n"
        "Include a clear explanation of why the correct answer is right."
    )

    model = QAgent()

    # Single example generation — user prompt matches training data format
    prompt = (
        "Generate a syllogism MCQ presenting two conclusions from given premises. "
        "The choices should be: Only I follows / Only II follows / Both follow / Neither follows.\n"
        "Topic: Logical Reasoning/Syllogisms\n"
        "Question Type: both_neither_conclusion"
    )

    response, tl, tm = model.generate_response(
        prompt,
        system_prompt=system_prompt,
        tgps_show=True,
        max_new_tokens=1024,
        temperature=0.7,
        top_p=0.9,
        do_sample=True,
    )
    print("Single example response:")
    print("Response: ", response)
    if tl and tm:
        print(
            f"Total tokens: {tl}, Time taken: {tm:.2f} seconds, "
            f"TGPS: {tl/tm:.2f} tokens/sec"
        )
    print("+-------------------------------------------------\n\n")

    # Multi example generation
    prompts = [
        "Generate a numeric series MCQ asking for the next term. Use patterns such as arithmetic, geometric, squares, cubes, Fibonacci, or mixed operations.\n"
        "Topic: Series and Patterns/Mixed Series (Alphanumeric)\n"
        "Question Type: numeric_next_term",

        "Generate a complex blood relations MCQ involving 4 relationship hops.\n"
        "Topic: Blood Relations and Family Tree/Family tree logic\n"
        "Question Type: complex_relation_4hop",

        "Generate a circular seating arrangement MCQ asking who sits between two persons.\n"
        "Topic: Puzzles/Seating Arrangements (Linear, Circular)\n"
        "Question Type: circular_between_query",
    ]
    responses, tl, tm = model.generate_response(
        prompts,
        system_prompt=system_prompt,
        tgps_show=True,
        max_new_tokens=1024,
        temperature=0.7,
        top_p=0.9,
        do_sample=True,
    )
    print("\nMulti example responses:")
    for i, resp in enumerate(responses):
        print(f"Response {i+1}: {resp}")
    if tl and tm:
        print(
            f"Total tokens: {tl}, Time taken: {tm:.2f} seconds, "
            f"TGPS: {tl/tm:.2f} tokens/sec"
        )
