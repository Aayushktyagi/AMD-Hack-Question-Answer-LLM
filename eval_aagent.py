#!/usr/bin/env python3
"""
A-Agent Inference & Evaluation Script
─────────────────────────────────────
Loads the trained A-Agent model, runs batched inference on the validation set,
dumps every response to a JSONL file for later analysis, and prints confusion
metrics + per-topic / per-class breakdowns.

Usage:
    python eval_aagent.py                          # defaults
    python eval_aagent.py --model /path/to/merged  # custom model path
    python eval_aagent.py --batch-size 16           # smaller batch for less VRAM
    python eval_aagent.py --output results.jsonl    # custom output path

Output JSONL format (one JSON object per line):
{
    "idx": 0,
    "topic": "Syllogisms",
    "gt_answer": "C",
    "pred_answer": "C",           // null if parse failed
    "correct": true,
    "response_raw": "{\"answer\": \"C\", \"reasoning\": \"...\"}",
    "parse_method": "json",       // "json" | "regex" | "scan" | "fail"
    "user_prompt": "Statements: ..."
}
"""

import argparse
import json
import os
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
from tqdm.auto import tqdm

# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

def parse_args():
    p = argparse.ArgumentParser(description="A-Agent batched eval + response dump")
    p.add_argument("--model", type=str,
                   default="/workspace/AAIPL/aagent_gptoss_merged_16bit",
                   help="Path to merged model or LoRA checkpoint")
    p.add_argument("--data-dir", type=str,
                   default="/workspace/AAIPL/hf_models/hub/datasets--Aayushktyagi--SFT_Apti/snapshots/f5199fdcda9db63487aeca763201aa4c05ef11f2",
                   help="Dataset snapshot directory")
    p.add_argument("--val-file", type=str, default="aagent_chatml_val.json",
                   help="Validation JSON filename inside data-dir")
    p.add_argument("--output", type=str, default="aagent_eval_responses.jsonl",
                   help="Output JSONL path for dumped responses")
    p.add_argument("--batch-size", type=int, default=32,
                   help="Eval batch size (tune for VRAM)")
    p.add_argument("--max-new-tokens", type=int, default=512,
                   help="Max tokens to generate per sample")
    p.add_argument("--max-seq-length", type=int, default=2048,
                   help="Max sequence length for model")
    p.add_argument("--temperature", type=float, default=0.1)
    p.add_argument("--top-p", type=float, default=0.9)
    p.add_argument("--repetition-penalty", type=float, default=1.2)
    p.add_argument("--use-outlines", action="store_true",
                   help="Use outlines JSONLogitsProcessor for structured output")
    p.add_argument("--hf-home", type=str, default="/workspace/AAIPL/hf_models/",
                   help="HF_HOME cache directory")
    return p.parse_args()


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

CLASSES = ["A", "B", "C", "D"]
CLASS_TO_IDX = {c: i for i, c in enumerate(CLASSES)}


def detect_topic(user_content: str) -> str:
    """Heuristic topic detection from user prompt text."""
    lc = user_content.lower()
    if "syllogism" in lc or "Statements:" in user_content:
        return "Syllogisms"
    elif "blood" in lc or "father" in lc or "mother" in lc:
        return "Blood Relations"
    elif "seated" in lc or "seating" in lc:
        return "Seating Arrangements"
    elif "series" in lc or "next term" in lc or "Find the" in user_content:
        return "Series"
    return "Other"


def extract_answer(response: str):
    """
    Try to extract answer letter from model response.
    Returns (pred_letter, method) where method is one of:
    'json', 'regex', 'scan', 'fail'
    """
    # 1. Full JSON parse
    try:
        parsed = json.loads(response)
        ans = parsed.get("answer")
        if ans in CLASSES:
            return ans, "json"
    except Exception:
        pass

    # 2. Regex-style key extraction from partial/broken JSON
    for letter in CLASSES:
        if f'"answer": "{letter}"' in response or f'"answer":"{letter}"' in response:
            return letter, "regex"

    # # 3. First A-D character in first 20 chars
    # for ch in response.strip()[:20]:
    #     if ch in "ABCD":
    #         return ch, "scan"

    return None, "fail"


def print_confusion(confusion, classes, title=""):
    """Pretty-print a confusion matrix."""
    if title:
        print(f"\n{title}")
    header = "       " + "".join(f"  Pred {c}" for c in classes)
    print(header)
    for r, cls in enumerate(classes):
        row_str = f"  GT {cls}: " + "".join(f"{confusion[r][c]:7d}" for c in range(len(classes)))
        print(row_str)


def print_class_metrics(confusion, classes, indent="  "):
    """Print per-class precision / recall / F1 from a confusion matrix."""
    print(f"{indent}{'Class':>5s}  {'Prec':>9s}  {'Recall':>9s}  {'F1':>9s}  {'Support':>7s}")
    macro_p, macro_r, macro_f1 = 0, 0, 0
    n = 0
    for idx, cls in enumerate(classes):
        tp = confusion[idx][idx]
        fn = confusion[idx].sum() - tp
        fp = confusion[:, idx].sum() - tp
        support = confusion[idx].sum()
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0
        print(f"{indent}{cls:>5s}  {prec:>9.4f}  {rec:>9.4f}  {f1:>9.4f}  {support:>7d}")
        if support > 0:
            macro_p += prec; macro_r += rec; macro_f1 += f1; n += 1
    if n > 0:
        print(f"{indent}{'Macro':>5s}  {macro_p/n:>9.4f}  {macro_r/n:>9.4f}  {macro_f1/n:>9.4f}")


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    args = parse_args()

    # ── Environment ──
    # os.environ["HF_HOME"] = args.hf_home
    import torch
    from unsloth import FastLanguageModel

    # ── Load model ──
    print(f"Loading model: {args.model}")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=args.model,
        max_seq_length=args.max_seq_length,
        dtype=torch.bfloat16,
        load_in_4bit=False,
        trust_remote_code=True,
    )
    FastLanguageModel.for_inference(model)
    print(f"  Parameters: {sum(p.numel() for p in model.parameters()):,}")
    print(f"  Device: {next(model.parameters()).device}")

    # ── Structured output (optional) ──
    json_processor = None
    if args.use_outlines:
        try:
            from pydantic import BaseModel
            from typing import Literal
            from outlines.processors import JSONLogitsProcessor

            class AAgentResponse(BaseModel):
                answer: Literal["A", "B", "C", "D"]
                reasoning: str

            json_processor = JSONLogitsProcessor(
                schema=AAgentResponse,
                tokenizer=tokenizer,
                whitespace_pattern=r"[\n\t ]*",
            )
            print("  ✓ outlines JSONLogitsProcessor enabled")
        except Exception as e:
            print(f"  ⚠ outlines failed: {e}  — falling back to free generation")

    # ── Load data ──
    val_path = os.path.join(args.data_dir, args.val_file)
    print(f"\nLoading validation data: {val_path}")
    with open(val_path) as f:
        val_raw = json.load(f)
    print(f"  Samples: {len(val_raw)}")

    # ── Pre-process ──
    samples = []
    skipped = 0
    for item in val_raw:
        msgs = item["messages"]
        try:
            gt = json.loads(msgs[-1]["content"])["answer"]
        except Exception:
            skipped += 1
            continue
        user_content = msgs[1]["content"] if len(msgs) > 1 else ""
        samples.append({
            "gt_answer": gt,
            "topic_key": detect_topic(user_content),
            "prompt_msgs": msgs[:-1],
            "user_prompt": user_content,
        })
    print(f"  Valid: {len(samples)}  |  Skipped (bad GT): {skipped}")

    # ── Generation config ──
    gen_config = dict(
        max_new_tokens=args.max_new_tokens,
        temperature=args.temperature,
        do_sample=True,
        top_p=args.top_p,
        repetition_penalty=args.repetition_penalty,
    )
    print(f"\nGeneration config: {gen_config}")
    print(f"Batch size: {args.batch_size}")
    print(f"Output: {args.output}\n")

    # ── Left-pad for batched generation ──
    orig_padding_side = tokenizer.padding_side
    tokenizer.padding_side = "left"
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token_id = tokenizer.eos_token_id

    # ── Inference loop ──
    correct = 0
    total = 0
    parse_fails = 0
    topic_stats = defaultdict(lambda: {"correct": 0, "total": 0})
    confusion = np.zeros((4, 4), dtype=int)
    topic_confusion = defaultdict(lambda: np.zeros((4, 4), dtype=int))
    parse_method_counts = defaultdict(int)

    num_batches = (len(samples) + args.batch_size - 1) // args.batch_size
    output_path = Path(args.output)
    t0 = time.time()

    with open(output_path, "w") as fout:
        for batch_idx in tqdm(range(num_batches), desc="Eval batches"):
            start = batch_idx * args.batch_size
            end = min(start + args.batch_size, len(samples))
            batch = samples[start:end]

            prompt_texts = [
                tokenizer.apply_chat_template(
                    s["prompt_msgs"], add_generation_prompt=True, tokenize=False
                )
                for s in batch
            ]
            inputs = tokenizer(
                prompt_texts,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=args.max_seq_length,
            ).to(model.device)

            prompt_len = inputs["input_ids"].shape[1]

            gen_kwargs = dict(**inputs, **gen_config, pad_token_id=tokenizer.pad_token_id)
            if json_processor is not None:
                gen_kwargs["logits_processor"] = [json_processor]

            outputs = model.generate(**gen_kwargs)

            for i, s in enumerate(batch):
                response = tokenizer.decode(
                    outputs[i][prompt_len:], skip_special_tokens=True
                )

                pred, method = extract_answer(response)
                parse_method_counts[method] += 1

                is_correct = False
                if pred and pred in CLASS_TO_IDX and s["gt_answer"] in CLASS_TO_IDX:
                    total += 1
                    gt_idx = CLASS_TO_IDX[s["gt_answer"]]
                    pred_idx = CLASS_TO_IDX[pred]
                    confusion[gt_idx][pred_idx] += 1
                    topic_confusion[s["topic_key"]][gt_idx][pred_idx] += 1
                    topic_stats[s["topic_key"]]["total"] += 1
                    if pred == s["gt_answer"]:
                        correct += 1
                        topic_stats[s["topic_key"]]["correct"] += 1
                        is_correct = True
                else:
                    parse_fails += 1

                # Dump response record
                record = {
                    "idx": start + i,
                    "topic": s["topic_key"],
                    "gt_answer": s["gt_answer"],
                    "pred_answer": pred,
                    "correct": is_correct,
                    "parse_method": method,
                    "response_raw": response,
                    "user_prompt": s["user_prompt"][:500],  # truncate for size
                }
                fout.write(json.dumps(record, ensure_ascii=False) + "\n")

            # Progress
            processed = end
            if processed % 500 < args.batch_size or batch_idx == num_batches - 1:
                acc = 100 * correct / total if total > 0 else 0
                print(f"  [{processed}/{len(samples)}] acc: {correct}/{total} = {acc:.1f}%  fails: {parse_fails}")

    tokenizer.padding_side = orig_padding_side
    elapsed = time.time() - t0

    # ═══════════════════════════════════════════════════════════
    # RESULTS
    # ═══════════════════════════════════════════════════════════

    print(f"\n{'═'*60}")
    print(f"A-AGENT VALIDATION RESULTS")
    print(f"{'═'*60}")
    print(f"Samples: {len(val_raw)} total  |  {len(samples)} valid  |  {skipped} GT-skipped")
    print(f"Overall Accuracy: {correct}/{total} = {100*correct/total:.2f}%")
    print(f"Parse failures: {parse_fails}")
    print(f"Parse methods: {dict(parse_method_counts)}")
    print(f"Time: {elapsed:.0f}s ({elapsed/60:.1f} min)  |  {elapsed/len(samples):.2f}s/sample")
    print(f"Responses saved to: {output_path.resolve()}")

    # Per-Topic Accuracy
    print(f"\n{'─'*60}")
    print("Per-Topic Accuracy:")
    print(f"{'─'*60}")
    for topic, stats in sorted(topic_stats.items()):
        t_acc = 100 * stats["correct"] / stats["total"] if stats["total"] > 0 else 0
        print(f"  {topic:25s}: {stats['correct']:5d}/{stats['total']:5d} = {t_acc:.1f}%")

    # Overall Confusion Matrix
    print_confusion(confusion, CLASSES, f"{'─'*60}\nConfusion Matrix (rows=GT, cols=Pred):\n{'─'*60}")

    # Per-Class Metrics
    print(f"\n{'─'*60}")
    print("Per-Class Metrics:")
    print(f"{'─'*60}")
    print_class_metrics(confusion, CLASSES)

    # Per-Topic breakdown
    print(f"\n{'═'*60}")
    print("PER-TOPIC CONFUSION MATRICES & CLASS METRICS")
    print(f"{'═'*60}")
    for topic in sorted(topic_confusion.keys()):
        cm = topic_confusion[topic]
        t_total = cm.sum()
        t_correct = sum(cm[i][i] for i in range(4))
        t_acc = 100 * t_correct / t_total if t_total > 0 else 0
        print(f"\n┌─ {topic} (n={int(t_total)}, acc={t_acc:.1f}%) ─┐")
        header = "       " + "".join(f"  Pred {c}" for c in CLASSES)
        print(header)
        for r, cls in enumerate(CLASSES):
            row_str = f"  GT {cls}: " + "".join(f"{int(cm[r][c]):7d}" for c in range(4))
            print(row_str)
        print_class_metrics(cm, CLASSES, indent="  ")

    # Save summary JSON alongside JSONL
    summary_path = output_path.with_suffix(".summary.json")
    summary = {
        "model": args.model,
        "val_file": val_path,
        "total_samples": len(val_raw),
        "valid_samples": len(samples),
        "gt_skipped": skipped,
        "accuracy": round(100 * correct / total, 4) if total > 0 else 0,
        "correct": correct,
        "total_evaluated": total,
        "parse_fails": parse_fails,
        "parse_methods": dict(parse_method_counts),
        "per_topic": {
            t: {"correct": s["correct"], "total": s["total"],
                "accuracy": round(100 * s["correct"] / s["total"], 2) if s["total"] > 0 else 0}
            for t, s in sorted(topic_stats.items())
        },
        "confusion_matrix": confusion.tolist(),
        "elapsed_seconds": round(elapsed, 1),
        "gen_config": gen_config,
    }
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nSummary saved to: {summary_path.resolve()}")


if __name__ == "__main__":
    main()
