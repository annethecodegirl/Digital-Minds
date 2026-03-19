"""
main.py — Entry point for the LLM Red-Teaming Evaluation Harness.

Usage:
  python main.py                                         # run all prompts
  python main.py --category jailbreaks                   # run only one category
  python main.py --target claude-haiku-4-5               # choose target model
  python main.py --compare claude-sonnet-4-6             # compare two models side by side
  python main.py --dry-run                               # show prompts without calling API
"""

import argparse
import json
import os
import sys
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

from src.runner import ModelRunner
from src.judge import Judge
from src.report import generate_report, generate_comparison_report


PROMPTS_FILE = Path("data/prompts.json")
RESULTS_DIR = Path("results")


def load_prompts(category: str | None = None) -> list[dict]:
    with open(PROMPTS_FILE) as f:
        data = json.load(f)
    prompts = data["prompts"]
    if category:
        prompts = [p for p in prompts if p["category"] == category]
        if not prompts:
            print(f"No prompts found for category: {category}")
            sys.exit(1)
    return prompts


def main():
    parser = argparse.ArgumentParser(description="LLM Red-Teaming Evaluation Harness")
    parser.add_argument("--category", help="Run only prompts in this category")
    parser.add_argument(
        "--target",
        default=os.getenv("TARGET_MODEL", "claude-haiku-4-5"),
        help="Target model to evaluate (default: claude-haiku-4-5)",
    )
    parser.add_argument(
        "--judge",
        default=os.getenv("JUDGE_MODEL", "claude-opus-4-6"),
        help="Judge model to score responses (default: claude-opus-4-6)",
    )
    parser.add_argument(
        "--compare",
        metavar="MODEL_B",
        help="Second model to compare against the target model",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print prompts without calling the API",
    )
    args = parser.parse_args()

    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY not set. Copy .env.example to .env and add your key.")
        sys.exit(1)

    prompts = load_prompts(args.category)

    if args.dry_run:
        models = [args.target] + ([args.compare] if args.compare else [])
        print(f"\n{'='*60}")
        print(f"DRY RUN — {len(prompts)} prompts would be sent to: {', '.join(models)}")
        print(f"{'='*60}")
        for p in prompts:
            print(f"\n[{p['id']}] ({p['category']} / {p['severity']})")
            print(f"  {p['text']}")
        return

    RESULTS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    judge = Judge(model=args.judge)

    if args.compare:
        _run_comparison(args, prompts, judge, timestamp)
    else:
        _run_single(args, prompts, judge, timestamp)


def _run_single(args, prompts, judge, timestamp):
    print(f"\n{'='*60}")
    print(f"LLM Red-Teaming Evaluation Harness")
    print(f"  Target model : {args.target}")
    print(f"  Judge model  : {args.judge}")
    print(f"  Prompts      : {len(prompts)}")
    print(f"{'='*60}\n")

    print("Step 1/2 — Sending prompts to target model...")
    responses = ModelRunner(model=args.target).run_all(prompts)
    print(f"  Done. {len(responses)} responses collected.\n")

    print("Step 2/2 — Judging responses...")
    judgments = judge.evaluate_all(responses)
    print(f"  Done. {len(judgments)} judgments complete.\n")

    html = generate_report(responses, judgments, args.target, args.judge)
    report_path = RESULTS_DIR / f"report_{timestamp}.html"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html)

    raw_results = [
        {
            "prompt_id": j.prompt_id,
            "category": j.category,
            "severity": j.severity,
            "prompt_text": responses[i].prompt_text,
            "response_text": responses[i].response_text,
            "refused": j.refused,
            "refusal_quality": j.refusal_quality,
            "compliance_harm": j.compliance_harm,
            "notes": j.notes,
        }
        for i, j in enumerate(judgments)
    ]
    json_path = RESULTS_DIR / f"results_{timestamp}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(raw_results, f, indent=2)

    total = len(judgments)
    refused = sum(1 for j in judgments if j.refused)
    print(f"{'='*60}")
    print(f"Results Summary")
    print(f"  Total prompts : {total}")
    print(f"  Refused       : {refused} ({refused/total*100:.0f}%)")
    print(f"  Complied      : {total - refused} ({(total-refused)/total*100:.0f}%)")
    print(f"\n  Report saved  : {report_path}")
    print(f"  JSON saved    : {json_path}")
    print(f"{'='*60}\n")
    print("Open the HTML report in your browser to see the full breakdown.")


def _run_comparison(args, prompts, judge, timestamp):
    model_a = args.target
    model_b = args.compare

    print(f"\n{'='*60}")
    print(f"LLM Red-Teaming — Model Comparison")
    print(f"  Model A      : {model_a}")
    print(f"  Model B      : {model_b}")
    print(f"  Judge model  : {args.judge}")
    print(f"  Prompts      : {len(prompts)}")
    print(f"{'='*60}\n")

    print(f"Step 1/4 — Sending prompts to {model_a}...")
    responses_a = ModelRunner(model=model_a).run_all(prompts)
    print(f"  Done.\n")

    print(f"Step 2/4 — Sending prompts to {model_b}...")
    responses_b = ModelRunner(model=model_b).run_all(prompts)
    print(f"  Done.\n")

    print(f"Step 3/4 — Judging {model_a} responses...")
    judgments_a = judge.evaluate_all(responses_a)
    print(f"  Done.\n")

    print(f"Step 4/4 — Judging {model_b} responses...")
    judgments_b = judge.evaluate_all(responses_b)
    print(f"  Done.\n")

    html = generate_comparison_report(
        responses_a, judgments_a, responses_b, judgments_b,
        model_a, model_b, args.judge,
    )
    report_path = RESULTS_DIR / f"comparison_{timestamp}.html"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html)

    raw_results = [
        {
            "prompt_id": ja.prompt_id,
            "category": ja.category,
            "severity": ja.severity,
            "prompt_text": responses_a[i].prompt_text,
            model_a: {
                "response": responses_a[i].response_text,
                "refused": ja.refused,
                "refusal_quality": ja.refusal_quality,
                "compliance_harm": ja.compliance_harm,
                "notes": ja.notes,
            },
            model_b: {
                "response": responses_b[i].response_text,
                "refused": judgments_b[i].refused,
                "refusal_quality": judgments_b[i].refusal_quality,
                "compliance_harm": judgments_b[i].compliance_harm,
                "notes": judgments_b[i].notes,
            },
        }
        for i, ja in enumerate(judgments_a)
    ]
    json_path = RESULTS_DIR / f"comparison_{timestamp}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(raw_results, f, indent=2)

    total = len(judgments_a)
    ref_a = sum(1 for j in judgments_a if j.refused)
    ref_b = sum(1 for j in judgments_b if j.refused)
    disagree = sum(1 for ja, jb in zip(judgments_a, judgments_b) if ja.refused != jb.refused)

    print(f"{'='*60}")
    print(f"Comparison Summary")
    print(f"  {model_a:35s} refused {ref_a}/{total} ({ref_a/total*100:.0f}%)")
    print(f"  {model_b:35s} refused {ref_b}/{total} ({ref_b/total*100:.0f}%)")
    print(f"  Disagreements (one refused, one didn't): {disagree}")
    print(f"\n  Report saved  : {report_path}")
    print(f"  JSON saved    : {json_path}")
    print(f"{'='*60}\n")
    print("Open the HTML report in your browser to see the full side-by-side breakdown.")


if __name__ == "__main__":
    main()
