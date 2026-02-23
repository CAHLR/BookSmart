#!/usr/bin/env python3
"""
Unified solver: run one of the supported models over all questions under
Textbooks/<book>/Filtered Questions/, reading and writing the same JSON files.

Supported models: o3, o4-mini, gpt-5, gemini-2.5-pro, deepseek-chat

API keys from environment (optionally loaded from keys.env in this repo):
  - OpenAI (o3, o4-mini, gpt-5): OPENAI_API_KEY
  - DeepSeek (deepseek-chat): DEEPSEEK_API_KEY
  - Gemini (gemini-2.5-pro): GEMINI_API_KEY

Usage (run from Final Paper Repo):
  python solver.py --model o3
  python solver.py --model deepseek-chat
  python solver.py --model gemini-2.5-pro --keys-env keys.env
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

# Optional: load keys from file
def _load_keys_env(path: str | None) -> None:
    if not path or not os.path.exists(path):
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip().strip('"').strip("'")
                if k and v and k not in os.environ:
                    os.environ[k] = v
    except Exception:
        pass


def _problem_text(q: dict) -> str:
    return " ".join(
        q.get(k, "") or ""
        for k in ("Topic", "Problem Statement", "Question")
    ).strip()


def _iter_question_files(base_dir: Path, questions_subdir: str) -> list[Path]:
    out: list[Path] = []
    for book_dir in base_dir.iterdir():
        if not book_dir.is_dir():
            continue
        qdir = book_dir / questions_subdir
        if not qdir.is_dir():
            continue
        for j in qdir.rglob("*.json"):
            if j.is_file():
                out.append(j)
    return sorted(out)


def _is_valid_questions(path: Path) -> bool:
    try:
        data = path.read_text(encoding="utf-8")
        obj = json.loads(data)
        return isinstance(obj, list) and len(obj) > 0
    except Exception:
        return False


def _is_complete_for_model(path: Path, model_key: str) -> bool:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            return True
        for q in data:
            if not isinstance(q, dict):
                continue
            if not (q.get(model_key) or "").strip():
                return False
        return True
    except Exception:
        return True


# ----- OpenAI (o3, o4-mini, gpt-5) -----
def _get_openai_client(api_key: str):
    from openai import OpenAI
    return OpenAI(api_key=api_key)


def _solve_openai(
    client: Any,
    problem_text: str,
    image_links: list | None,
    api_model: str,
) -> str | None:
    messages: list[dict] = [{
        "role": "user",
        "content": [{"type": "text", "text": f"Please solve: {problem_text}"}],
    }]
    if image_links:
        for url in image_links:
            messages[0]["content"].append({
                "type": "image_url",
                "image_url": {"url": url},
            })
    for attempt in range(5):
        try:
            resp = client.chat.completions.create(
                model=api_model,
                messages=messages,
            )
            return (resp.choices[0].message.content or "").strip() or None
        except Exception as e:
            print(f"❌ Error during completion: {e}")
    return None


# ----- DeepSeek (deepseek-chat) -----
def _get_deepseek_client(api_key: str):
    from openai import OpenAI
    return OpenAI(api_key=api_key, base_url="https://api.deepseek.com")


def _solve_deepseek(
    client: Any,
    problem_text: str,
    image_links: list | None,
    api_model: str,
) -> str | None:
    if image_links:
        return None
    prompt = f"Please solve: {problem_text}"
    messages = [{"role": "user", "content": prompt}]
    for attempt in range(5):
        try:
            resp = client.chat.completions.create(
                model=api_model,
                messages=messages,
            )
            return (resp.choices[0].message.content or "").strip() or None
        except Exception as e:
            print(f"❌ Error during completion: {e}")
    return None


# ----- Gemini (gemini-2.5-pro) -----
def _get_gemini_client(api_key: str):
    from google import genai
    return genai.Client(api_key=api_key)


def _solve_gemini(
    client: Any,
    problem_text: str,
    api_model: str,
) -> str | None:
    prompt = f"Please solve: {problem_text}"
    for attempt in range(5):
        try:
            response = client.models.generate_content(
                model=api_model,
                contents=prompt,
            )
            return (response.text or "").strip() or None
        except Exception as e:
            print(f"❌ Error during completion: {e}")
            wait = 2 ** (attempt + 1)
            print(f"🔁 Retrying in {wait} seconds...")
            time.sleep(wait)
    return None


# ----- Model config: (api_model_name, provider, env_key) -----
MODEL_CONFIG = {
    "o3": ("o3", "openai", "OPENAI_API_KEY"),
    "o4-mini": ("o4-mini", "openai", "OPENAI_API_KEY"),
    "gpt-5": ("gpt-5", "openai", "OPENAI_API_KEY"),
    "deepseek-chat": ("deepseek-chat", "deepseek", "DEEPSEEK_API_KEY"),
    "gemini-2.5-pro": ("gemini-2.5-pro", "gemini", "GEMINI_API_KEY"),
}


def process_file(
    path: Path,
    model: str,
    model_key: str,
    api_model: str,
    provider: str,
    client: Any,
    include_complete: bool,
) -> None:
    try:
        questions = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"❌ Failed to load {path}: {e}")
        return
    if not isinstance(questions, list):
        return
    modified = False
    for q in questions:
        if not isinstance(q, dict):
            continue
        if model_key in q and (q.get(model_key) or "").strip():
            if not include_complete:
                continue
        text = _problem_text(q)
        imgs = q.get("Image Links") or []
        if not isinstance(imgs, list):
            imgs = []
        answer = None
        if provider == "openai":
            answer = _solve_openai(client, text, imgs, api_model)
        elif provider == "deepseek":
            answer = _solve_deepseek(client, text, imgs, api_model)
        elif provider == "gemini":
            answer = _solve_gemini(client, text, api_model)
        if answer:
            q[model_key] = answer
            modified = True
            print(answer)
    if modified:
        path.write_text(
            json.dumps(questions, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a single model over all questions in Textbooks/*/Filtered Questions/.",
    )
    parser.add_argument(
        "--model",
        type=str,
        required=True,
        choices=list(MODEL_CONFIG.keys()),
        help="Model to run: o3, o4-mini, gpt-5, gemini-2.5-pro, deepseek-chat",
    )
    parser.add_argument(
        "--base-dir",
        type=str,
        default="Textbooks",
        help="Root directory containing textbook folders (default: Textbooks)",
    )
    parser.add_argument(
        "--questions-subdir",
        type=str,
        default="Filtered Questions",
        help="Subdirectory under each textbook with question JSONs (default: Filtered Questions)",
    )
    parser.add_argument(
        "--keys-env",
        type=str,
        default=os.environ.get("KEYS_ENV", "keys.env"),
        help="Path to keys.env file; also use KEYS_ENV env var. Keys: OPENAI_API_KEY, DEEPSEEK_API_KEY, GEMINI_API_KEY",
    )
    parser.add_argument(
        "--include-complete",
        action="store_true",
        help="Re-run even on files that already have all answers for this model",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List files that would be processed and exit",
    )
    args = parser.parse_args()

    # This repo = directory containing solver.py
    repo_root = Path(__file__).resolve().parent
    keys_path = args.keys_env
    if keys_path and not Path(keys_path).is_absolute():
        keys_path = str(repo_root / keys_path)
    _load_keys_env(keys_path)

    model = args.model
    api_model, provider, env_key = MODEL_CONFIG[model]
    api_key = os.environ.get(env_key) or os.environ.get(env_key.replace("_KEY", "_API_KEY"))
    if not api_key:
        raise SystemExit(f"❌ Missing API key. Set {env_key} (or load via --keys-env).")

    base_dir = repo_root / args.base_dir if not Path(args.base_dir).is_absolute() else Path(args.base_dir)
    if not base_dir.is_dir():
        raise SystemExit(f"❌ Base directory not found: {base_dir}")

    files = _iter_question_files(base_dir, args.questions_subdir)
    if not args.include_complete:
        model_key = f"{model} Answer"
        files = [p for p in files if not _is_complete_for_model(p, model_key)]
    files = [p for p in files if _is_valid_questions(p)]

    print(f"🧩 Model: {model} (API: {api_model}) | {len(files)} JSON file(s) to process")

    if args.dry_run:
        for p in files[:50]:
            print(p)
        if len(files) > 50:
            print(f"... and {len(files) - 50} more")
        return

    if provider == "openai":
        client = _get_openai_client(api_key)
    elif provider == "deepseek":
        client = _get_deepseek_client(api_key)
    elif provider == "gemini":
        client = _get_gemini_client(api_key)
    else:
        raise SystemExit(f"Unknown provider: {provider}")

    model_key = f"{model} Answer"
    for path in files:
        print(f"🔄 {path.relative_to(base_dir)}")
        process_file(
            path,
            model,
            model_key,
            api_model,
            provider,
            client,
            args.include_complete,
        )


if __name__ == "__main__":
    main()
