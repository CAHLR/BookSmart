import argparse
import csv
from pathlib import Path
from typing import Optional

from chapter_table import DEFAULT_MODELS, build_table_data, format_chapter_label


def parse_args():
    parser = argparse.ArgumentParser(
        description="Save per-textbook, per-model average and minimum chapter accuracies to CSV.",
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
        default="Figures+Tables/textbook_accuracy_summary.csv",
        help="Output CSV path relative to repo root unless absolute",
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


def round_pct(correct: int, total: int) -> float:
    return round((100 * correct) / total, 1)


def chapter_label_for_row(chapter_num: int, chapter: dict) -> str:
    return format_chapter_label(chapter_num, chapter["title"])


def build_rows(textbooks_root: Path, questions_subdir: str, html_subdir: str, models):
    rows = []
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

        overall_n = sum(chapter["n"] for chapter in chapter_data.values())
        if overall_n == 0:
            continue

        for model in models:
            overall_correct = sum(chapter["correct"][model] for chapter in chapter_data.values())
            min_chapter_num = None
            min_chapter = None
            min_chapter_pct = None
            for chapter_num in sorted(chapter_data):
                chapter = chapter_data[chapter_num]
                chapter_n = chapter["n"]
                if chapter_n == 0:
                    continue
                chapter_pct = round_pct(chapter["correct"][model], chapter_n)
                if min_chapter_pct is None or chapter_pct < min_chapter_pct:
                    min_chapter_pct = chapter_pct
                    min_chapter_num = chapter_num
                    min_chapter = chapter

            if min_chapter is None or min_chapter_num is None or min_chapter_pct is None:
                continue

            rows.append(
                {
                    "textbook": textbook,
                    "model": model,
                    "textbook_questions_n": overall_n,
                    "avg_accuracy_pct": round_pct(overall_correct, overall_n),
                    "min_chapter_accuracy_pct": min_chapter_pct,
                    "min_chapter_number": min_chapter_num,
                    "min_chapter_label": chapter_label_for_row(min_chapter_num, min_chapter),
                    "min_chapter_questions_n": min_chapter["n"],
                }
            )
    return rows


def main():
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    textbooks_root = resolve_textbooks_root(repo_root, args.textbooks_dir)
    models = [model.strip() for model in args.models.split(",") if model.strip()]
    if not models:
        raise SystemExit("No models provided.")

    rows = build_rows(
        textbooks_root=textbooks_root,
        questions_subdir=args.questions_subdir,
        html_subdir=args.html_subdir,
        models=models,
    )
    if not rows:
        raise SystemExit("No textbook accuracy rows generated.")

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = repo_root / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "textbook",
        "model",
        "textbook_questions_n",
        "avg_accuracy_pct",
        "min_chapter_accuracy_pct",
        "min_chapter_number",
        "min_chapter_label",
        "min_chapter_questions_n",
    ]
    with output_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {output_path}")


if __name__ == "__main__":
    main()
