import argparse
import json
from pathlib import Path
from typing import Optional

from chapter_table import (
    DEFAULT_MODELS,
    build_table_data,
    format_chapter_label,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Export textbook/chapter/section accuracy data for the GitHub Pages site.",
    )
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parent.parent),
        help="Path to repo root (default: parent of this script directory)",
    )
    parser.add_argument(
        "--textbooks-dir",
        default=None,
        help=(
            "Top-level textbook directory under the repo root. "
            "Defaults to 'Textbooks Fixed' when present, otherwise 'Textbooks'."
        ),
    )
    parser.add_argument(
        "--questions-subdir",
        default="Filtered Questions",
        help="Question JSON subdirectory under each textbook (default: Filtered Questions)",
    )
    parser.add_argument(
        "--html-subdir",
        default="HTML",
        help="HTML subdirectory under each textbook (default: HTML)",
    )
    parser.add_argument(
        "--models",
        default=",".join(DEFAULT_MODELS),
        help="Comma-separated model list",
    )
    parser.add_argument(
        "--output",
        default="docs/data/accuracy-site-data.json",
        help="Output JSON path relative to repo root unless absolute",
    )
    return parser.parse_args()


def resolve_textbooks_root(repo_root: Path, textbooks_dir: Optional[str]) -> Path:
    if textbooks_dir:
        root = Path(textbooks_dir)
        if not root.is_absolute():
            root = repo_root / root
        if not root.is_dir():
            raise SystemExit(f"Textbooks root not found: {root}")
        return root

    for candidate in ("Textbooks Fixed", "Textbooks"):
        root = repo_root / candidate
        if root.is_dir():
            return root

    raise SystemExit(
        f"No textbook root found under {repo_root / 'Textbooks Fixed'} or {repo_root / 'Textbooks'}"
    )


def pct(correct: int, total: int) -> Optional[float]:
    if total <= 0:
        return None
    return round((100.0 * correct) / total, 1)


def metrics_for_models(correct_map, total: int, models):
    return {
        model: {
            "correct": correct_map[model],
            "n": total,
            "pct": pct(correct_map[model], total),
        }
        for model in models
    }


def section_sort_key(section_id: str):
    parts = []
    for piece in section_id.split("."):
        try:
            parts.append(int(piece))
        except ValueError:
            parts.append(piece)
    return parts


def build_site_payload(textbooks_root: Path, questions_subdir: str, html_subdir: str, models):
    textbooks = []
    for textbook_root in sorted(path for path in textbooks_root.iterdir() if path.is_dir()):
        if not (textbook_root / questions_subdir).is_dir():
            continue
        if not (textbook_root / html_subdir).is_dir():
            continue

        textbook = textbook_root.name
        chapter_data = build_table_data(
            textbook_root=textbook_root,
            textbook=textbook,
            questions_subdir=questions_subdir,
            html_subdir=html_subdir,
            models=models,
        )
        if not chapter_data:
            continue

        total_n = sum(chapter["n"] for chapter in chapter_data.values())
        total_correct = {
            model: sum(chapter["correct"][model] for chapter in chapter_data.values()) for model in models
        }

        chapters = []
        for chapter_num in sorted(chapter_data):
            chapter = chapter_data[chapter_num]
            sections = []
            for section_id in sorted(chapter["sections"], key=section_sort_key):
                section = chapter["sections"][section_id]
                sections.append(
                    {
                        "id": section_id,
                        "title": section["title"],
                        "n": section["n"],
                        "metrics": metrics_for_models(section["correct"], section["n"], models),
                    }
                )

            chapter_level = None
            if chapter["chapter_level"]["n"] > 0:
                chapter_level = {
                    "title": chapter["chapter_level"]["title"],
                    "n": chapter["chapter_level"]["n"],
                    "metrics": metrics_for_models(
                        chapter["chapter_level"]["correct"],
                        chapter["chapter_level"]["n"],
                        models,
                    ),
                }

            chapters.append(
                {
                    "number": chapter_num,
                    "title": chapter["title"],
                    "label": format_chapter_label(chapter_num, chapter["title"]),
                    "n": chapter["n"],
                    "metrics": metrics_for_models(chapter["correct"], chapter["n"], models),
                    "sections": sections,
                    "chapterLevel": chapter_level,
                }
            )

        textbooks.append(
            {
                "name": textbook,
                "n": total_n,
                "metrics": metrics_for_models(total_correct, total_n, models),
                "chapters": chapters,
            }
        )

    return {
        "models": models,
        "textbookCount": len(textbooks),
        "textbooks": textbooks,
    }


def main():
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    textbooks_root = resolve_textbooks_root(repo_root, args.textbooks_dir)
    models = [model.strip() for model in args.models.split(",") if model.strip()]
    if not models:
        raise SystemExit("No models provided.")

    payload = build_site_payload(
        textbooks_root=textbooks_root,
        questions_subdir=args.questions_subdir,
        html_subdir=args.html_subdir,
        models=models,
    )

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = repo_root / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
