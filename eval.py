"""
Run o4-mini evaluations on every model answer in the Filtered Questions folders
under the Final Paper Repo Textbooks tree, writing results back in place.
"""

import argparse
import json
import os
import shutil
import time
from pathlib import Path
from typing import Optional

import dotenv
from openai import OpenAI

SCRIPT_DIR = Path(__file__).resolve().parent

DEFAULT_INPUT_DIR = SCRIPT_DIR / "Textbooks"
DEFAULT_OUTPUT_DIR = DEFAULT_INPUT_DIR
TARGET_MODELS = ["o3", "deepseek-chat", "gemini-2.5-pro", "o4-mini", "gpt-5"]
O4_MINI_MODEL = "o4-mini-2025-04-16"
DEFAULT_SLEEP = 0.5

dotenv.load_dotenv(SCRIPT_DIR / "keys.env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_KEY_1")

def build_evaluation_prompt(question_text: str, reference_answer: str, llm_answer: str) -> str:
    """Build the evaluation prompt used in the 500-question sample."""
    prompt = f"""You are evaluating the correctness of an LLM's answer to a textbook question.

Question:
{question_text}

Reference Answer (correct answer):
{reference_answer}

LLM Answer to evaluate:
{llm_answer}

Evaluate whether the LLM answer is correct according to these criteria:

1. **Equivalence**: If the LLM's final answer is mathematically or conceptually equivalent to the provided solution, it should be marked correct, even if it is not written in exactly the same form (for example, simplified algebraic forms, rearranged expressions, or equivalent logical statements).

2. **Multipart questions**: Use an all-or-nothing approach. If any subpart of the response is incorrect, incomplete, or inconsistent with the provided solution, the entire question should be marked incorrect.

3. **Rounding rules**: Answers that differ only due to rounding should be marked correct if they match within 2 significant figures of the expected numeric value. Round-off differences beyond that should be marked incorrect unless explicitly stated otherwise.

4. **Units**: Units must be present and correct. Pay close attention to unit prefixes (e.g., milli-, micro-, kilo-). If the prefix differs but the overall numerical value is equivalent (e.g., 5 mV = 0.005 V), the answer is still correct. If the units are missing, inconsistent, or mismatched (e.g., 5 A instead of 5 V), mark it incorrect.

5. **Open-ended questions**: For open-ended or conceptual questions without a single definitive answer, grade to the best of your ability and judgment based on your understanding of the material and the reasonableness of the response.

Answer ONLY with "True" if the answer is correct according to these criteria, or "False" if it is incorrect. Do not provide any explanation, only "True" or "False"."""
    return prompt

def parse_evaluation_response(response: str) -> Optional[bool]:
    """Interpret the model response as True/False."""
    norm = response.strip().lower()
    if norm.startswith("true") or "true" in norm[:10]:
        return True
    if norm.startswith("false") or "false" in norm[:10]:
        return False
    if norm.startswith("yes"):
        return True
    if norm.startswith("no"):
        return False
    if norm.startswith("1") and not norm.startswith("10"):
        return True
    if norm.startswith("0"):
        return False
    if "correct" in norm[:20] and "incorrect" not in norm[:30]:
        return True
    if "incorrect" in norm[:20]:
        return False
    return None

def create_o4_client() -> OpenAI:
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY not found in environment or keys.env")
    return OpenAI(api_key=OPENAI_API_KEY)

def call_o4_mini(client: OpenAI, prompt: str, max_retries: int = 3) -> Optional[str]:
    """Call o4-mini via the Responses API with retries."""
    for attempt in range(max_retries):
        try:
            response = client.responses.create(
                model=O4_MINI_MODEL,
                input=prompt,
                instructions="Formatting reenabled\n",
                reasoning={"effort": "medium", "summary": "auto"},
                store=False,
            )
            if response and getattr(response, "output_text", None):
                return response.output_text
        except AttributeError:

            try:
                completion = client.chat.completions.create(
                    model=O4_MINI_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0,
                    max_tokens=5,
                )
                if completion and completion.choices:
                    return completion.choices[0].message.content
            except Exception as chat_error:
                print(f"    ❌ chat.completions fallback failed: {chat_error}")
        except Exception as e:
            wait = 2 ** attempt
            print(f"    ⚠️  o4-mini call failed ({attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                print(f"    🔁 retrying in {wait}s...")
                time.sleep(wait)
            else:
                print("    ❌ giving up on this evaluation")
    return None

def build_question_text(question: dict) -> str:
    parts = []
    if question.get("Topic"):
        parts.append(f"Topic: {question['Topic']}")
    if question.get("Problem Statement"):
        parts.append(f"Problem Statement: {question['Problem Statement']}")
    if question.get("Question"):
        parts.append(f"Question: {question['Question']}")
    return "\n".join(parts) or "Question text not provided."

def evaluate_answer(question: dict, model_name: str, client: OpenAI, sleep: float) -> bool:
    answer_key = f"{model_name} Answer"
    eval_key = f"{model_name} Eval by o4-mini"

    if eval_key in question and question[eval_key] is not None:
        return False

    llm_answer = question.get(answer_key)
    if not llm_answer:
        return False

    reference_answer = question.get("Answer")
    if not reference_answer:
        return False

    prompt = build_evaluation_prompt(
        build_question_text(question),
        reference_answer,
        llm_answer,
    )

    response_text = call_o4_mini(client, prompt)
    if response_text is None:
        question[eval_key] = None
        return True

    result = parse_evaluation_response(response_text)
    question[eval_key] = result

    if sleep:
        time.sleep(sleep)
    return True

def load_json_records(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"{path} does not contain a list of questions")
    return data

def write_json_records(path: Path, records: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

def _make_question_identity_key(q: dict) -> tuple:
    """
    Build a stable identity key for matching questions between FINAL FILTERED and
    FINAL FILTERED EVAL, even if the eval file was created before new model answers
    were added to the input.

    This intentionally mirrors the "core question" signature used elsewhere:
      Topic, Problem Statement, Question, Image Links, Answer, Answer Image Links
    """
    def _norm_list(v):
        if not v:
            return tuple()
        if isinstance(v, list):
            return tuple(v)
        return (str(v),)

    return (
        str(q.get("Topic", "")),
        str(q.get("Problem Statement", "")),
        str(q.get("Question", "")),
        _norm_list(q.get("Image Links", [])),
        str(q.get("Answer", "")),
        _norm_list(q.get("Answer Image Links", [])),
    )

def _sync_missing_answers_from_input(
    output_records: list[dict],
    input_records: list[dict],
    models: list[str],
) -> bool:
    """
    If the eval file already exists, it can be a stale snapshot missing newly
    generated model answers (especially gpt-5). Sync missing `"{model} Answer"`
    fields from the input file into the output records before evaluation.

    Returns True if any output record was modified.
    """
    input_index = {}
    for rec in input_records:
        if isinstance(rec, dict):
            input_index[_make_question_identity_key(rec)] = rec

    changed = False
    seen_keys = set()

    for out in output_records:
        if not isinstance(out, dict):
            continue
        k = _make_question_identity_key(out)
        seen_keys.add(k)
        src = input_index.get(k)
        if not isinstance(src, dict):
            continue
        for m in models:
            ans_key = f"{m} Answer"
            if (not out.get(ans_key)) and src.get(ans_key):
                out[ans_key] = src.get(ans_key)
                changed = True

    for k, rec in input_index.items():
        if k in seen_keys:
            continue
        output_records.append(dict(rec))
        changed = True

    return changed

def process_json_file(input_path: Path, output_path: Path, client: OpenAI, models: list[str], sleep: float):
    if output_path.exists():
        data = load_json_records(output_path)
        source = "output"

        try:
            input_data = load_json_records(input_path)
            synced = _sync_missing_answers_from_input(data, input_data, models)
        except Exception:
            synced = False
    else:
        data = load_json_records(input_path)
        source = "input"
        synced = False

    changed = False
    missing_reference = 0

    for question in data:
        if not question.get("Answer"):
            missing_reference += 1
            continue
        for model_name in models:
            answer_key = f"{model_name} Answer"
            if "Answer" not in answer_key:
                continue
            if not question.get(answer_key):
                continue
            eval_key = f"{model_name} Eval by o4-mini"
            if eval_key in question and question[eval_key] is not None:
                continue

            print(f"    🔍 Evaluating {model_name} answer...")
            did_update = evaluate_answer(question, model_name, client, sleep)
            if did_update:
                changed = True

    if missing_reference:
        print(f"    ⚠️  {missing_reference} questions missing reference Answer; skipped.")

    if (source == "input") or synced or changed or not output_path.exists():
        write_json_records(output_path, data)
    elif source == "output" and not changed:

        write_json_records(output_path, data)

def mirror_non_json_file(input_path: Path, output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(input_path, output_path)

def process_all_files(input_dir: Path, output_dir: Path, models: list[str], sleep: float, limit: Optional[int] = None):
    client = create_o4_client()
    processed_files = 0

    for dirpath, _, filenames in os.walk(input_dir):
        rel_dir = Path(dirpath).relative_to(input_dir)

        if "Filtered Questions" not in rel_dir.parts:
            continue
        output_subdir = output_dir / rel_dir
        output_subdir.mkdir(parents=True, exist_ok=True)

        for filename in filenames:
            input_path = Path(dirpath) / filename
            output_path = output_subdir / filename

            if limit and processed_files >= limit:
                return

            if filename.lower().endswith(".json"):
                print(f"\n📄 {input_path.relative_to(input_dir)}")
                try:
                    process_json_file(input_path, output_path, client, models, sleep)
                except Exception as exc:
                    print(f"  ❌ Failed to process {input_path}: {exc}")
                processed_files += 1
            else:
                if not output_path.exists():
                    mirror_non_json_file(input_path, output_path)

def count_pending_evaluations(input_dir: Path, output_dir: Path, models: list[str], limit: Optional[int] = None) -> dict:
    """
    Walk the dataset and count how many evaluations are still needed.

    Definition: a question "needs eval" for model M if:
      - it has a non-empty reference `Answer`
      - it has a non-empty `"{M} Answer"`
      - and `"{M} Eval by o4-mini"` is missing or None

    Uses the synced view (output + missing answers from input) so the count
    reflects newly generated answers even when output files are stale.

    Returns a dict with totals and per-model breakdown.
    """
    processed_json_files = 0
    files_with_pending = 0
    pending_by_model = {m: 0 for m in models}

    for dirpath, _, filenames in os.walk(input_dir):
        rel_dir = Path(dirpath).relative_to(input_dir)

        if "Filtered Questions" not in rel_dir.parts:
            continue

        out_subdir = output_dir / rel_dir

        for filename in filenames:
            if limit and processed_json_files >= limit:
                return {
                    "processed_json_files": processed_json_files,
                    "files_with_pending": files_with_pending,
                    "pending_by_model": pending_by_model,
                    "pending_total": sum(pending_by_model.values()),
                }

            if not filename.lower().endswith(".json"):
                continue

            input_path = Path(dirpath) / filename
            output_path = out_subdir / filename

            try:
                input_data = load_json_records(input_path)
            except Exception:
                continue

            if output_path.exists():
                try:
                    data = load_json_records(output_path)
                except Exception:
                    data = list(input_data)
            else:
                data = list(input_data)

            try:
                _sync_missing_answers_from_input(data, input_data, models)
            except Exception:
                pass

            processed_json_files += 1

            file_pending = 0
            for question in data:
                if not isinstance(question, dict):
                    continue
                if not question.get("Answer"):
                    continue
                for model_name in models:
                    answer_key = f"{model_name} Answer"
                    if not question.get(answer_key):
                        continue
                    eval_key = f"{model_name} Eval"
                    if eval_key in question and question[eval_key] is not None:
                        continue
                    pending_by_model[model_name] += 1
                    file_pending += 1

            if file_pending:
                files_with_pending += 1

    return {
        "processed_json_files": processed_json_files,
        "files_with_pending": files_with_pending,
        "pending_by_model": pending_by_model,
        "pending_total": sum(pending_by_model.values()),
    }

def parse_args():
    parser = argparse.ArgumentParser(description="Run o4-mini evaluations across Filtered Questions.")
    parser.add_argument("--input-dir", type=str, default=str(DEFAULT_INPUT_DIR), help="Source root (default: Textbooks)")
    parser.add_argument("--output-dir", type=str, default=str(DEFAULT_OUTPUT_DIR), help="Destination root (default: same as input; in-place updates)")
    parser.add_argument("--models", type=str, default=",".join(TARGET_MODELS), help="Comma-separated model list to evaluate")
    parser.add_argument("--sleep", type=float, default=DEFAULT_SLEEP, help="Delay between requests (seconds)")
    parser.add_argument("--file-limit", type=int, default=None, help="Limit number of JSON files (for testing)")
    parser.add_argument(
        "--report-pending",
        action="store_true",
        help="Scan and report how many questions still need '* Eval by o4-mini' (no API calls).",
    )
    return parser.parse_args()

def main():
    args = parse_args()
    input_dir = Path(args.input_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    model_list = [m.strip() for m in args.models.split(",") if m.strip()]

    if not input_dir.exists():
        raise SystemExit(f"Input directory not found: {input_dir}")

    invalid = [m for m in model_list if not m]
    if invalid:
        raise SystemExit(f"Invalid model names provided: {invalid}")

    print(f"Input directory:  {input_dir}")
    print(f"Output directory: {output_dir}")
    print(f"Models to evaluate: {', '.join(model_list)}")
    print(f"Sleep between calls: {args.sleep}s")
    if args.file_limit:
        print(f"Processing limited to first {args.file_limit} JSON files (testing mode)")

    if args.report_pending:
        report = count_pending_evaluations(input_dir, output_dir, model_list, args.file_limit)
        print("\n📊 Pending evaluations (needs '* Eval by o4-mini'):")
        print(f"  JSON files scanned:      {report['processed_json_files']}")
        print(f"  Files with any pending:  {report['files_with_pending']}")
        print(f"  Pending (total):         {report['pending_total']}")
        for m in model_list:
            print(f"  Pending ({m:>12}):     {report['pending_by_model'][m]}")
        return

    process_all_files(input_dir, output_dir, model_list, args.sleep, args.file_limit)
    print("\n✅ Completed o4-mini evaluations.")

if __name__ == "__main__":
    main()
