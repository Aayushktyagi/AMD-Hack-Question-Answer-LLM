# A-Agent: SFT-trained Qwen2.5-14B-Instruct for answering MCQ questions.
# Loads the merged 16-bit model from SFT training (Train_A-agent_Qwen.ipynb).
# Uses Unsloth FastLanguageModel for 2x faster inference.
import os
import time
import torch
from pathlib import Path
from typing import Optional, List
from unsloth import FastLanguageModel

torch.random.manual_seed(0)
os.environ['HF_HOME']='/workspace/AAIPL/hf_models/'
# ── Model path ──
# Default: merged 16-bit Qwen2.5-14B-Instruct SFT model.
# Override via AAGENT_MODEL_PATH env variable for custom locations.
DEFAULT_AAGENT_MODEL = "/workspace/AAIPL/aagent_qwen25_14_Inst_outputs/checkpoint-150/"


class AAgent(object):
    def __init__(self, **kwargs):
        
        model_name = kwargs.get(
            "model_name",
            os.environ.get("AAGENT_MODEL_PATH", DEFAULT_AAGENT_MODEL),
        )
        max_seq_length = kwargs.get("max_seq_length", 2048)
        print(f"[AAgent] Loading model: {model_name}")

        # Load via Unsloth FastLanguageModel — matches Train_A-agent_Qwen.ipynb
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
            f"[AAgent] Model loaded — "
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

        print(messages)

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
            max_new_tokens=kwargs.get("max_new_tokens", 512),
            pad_token_id=self.tokenizer.pad_token_id,
        )
        if kwargs.get("do_sample", False):
            gen_kwargs["do_sample"] = True
            gen_kwargs["temperature"] = kwargs.get("temperature", 0.1)
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
    # Single message
    ans_agent = AAgent()
    system_prompt = (
        "You are a logical reasoning expert. Answer the given multiple-choice question.\n"
        'Provide your answer as a JSON object with "reasoning" and "answer" (letter A/B/C/D).'
    )
    question = (
        "Statements:\n"
        "1. All dogs are animals.\n"
        "2. All animals are living beings.\n"
        "Conclusions:\n"
        "I. All dogs are living beings.\n"
        "II. Some living beings are dogs.\n\n"
        "A) Only conclusion I follows\n"
        "B) Only conclusion II follows\n"
        "C) Both conclusions I and II follow\n"
        "D) Neither conclusion I nor II follows"
    )
    response, tl, gt = ans_agent.generate_response(
        question,
        system_prompt=system_prompt,
        tgps_show=True,
        max_new_tokens=512,
        temperature=0.1,
        top_p=0.9,
        do_sample=True,
    )
    print(f"Single response: {response}")
    if tl and gt:
        print(
            f"Token length: {tl}, Generation time: {gt:.2f} seconds, "
            f"Tokens per second: {tl/gt:.2f}"
        )
    print("-----------------------------------------------------------")

    # Batch processing
    messages = [
        "Find the next term: 2, 6, 18, 54, ?\nA) 108\nB) 162\nC) 180\nD) 216",
        "A is the father of B. B is the mother of C. What is A to C?\nA) Grandfather\nB) Uncle\nC) Father\nD) Brother",
    ]
    responses, tl, gt = ans_agent.generate_response(
        messages,
        system_prompt=system_prompt,
        max_new_tokens=512,
        temperature=0.1,
        top_p=0.9,
        do_sample=True,
        tgps_show=True,
    )
    print("Responses:")
    for i, resp in enumerate(responses):
        print(f"Message {i+1}: {resp}")
    if tl and gt:
        print(
            f"Token length: {tl}, Generation time: {gt:.2f} seconds, "
            f"Tokens per second: {tl/gt:.2f}"
        )
