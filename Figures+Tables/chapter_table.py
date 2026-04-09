import argparse
import html
import json
import math
import re
import subprocess
from pathlib import Path
from typing import Optional

DEFAULT_MODELS = ["o3", "deepseek-chat", "gemini-2.5-pro", "o4-mini", "gpt-5"]
WILSON_Z_95 = 1.959963984540054


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate a LaTeX chapter/section evaluation table for one textbook.",
    )
    parser.add_argument(
        "--textbook",
        required=True,
        help="Textbook folder name under Textbooks/ (example: 'Algebra and Trig 2e')",
    )
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parent),
        help="Path to Final Paper Repo root (default: directory containing this script)",
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
        help="Comma-separated model list (default: o3,deepseek-chat,gemini-2.5-pro,o4-mini,gpt-5)",
    )
    parser.add_argument(
        "--caption",
        default=None,
        help="LaTeX caption override",
    )
    parser.add_argument(
        "--label",
        default=None,
        help="LaTeX label override",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional output .tex path. If omitted, prints to stdout.",
    )
    parser.add_argument(
        "--include-all-row",
        action="store_true",
        help="Include an ALL CHAPTERS summary row at the bottom.",
    )
    parser.add_argument(
        "--no-all-row",
        action="store_false",
        dest="include_all_row",
        help="Omit the textbook total row at the bottom.",
    )
    parser.add_argument(
        "--chapter-only",
        action="store_true",
        help="Only include chapter totals; omit section rows.",
    )
    parser.add_argument(
        "--include-min-subchapter-row",
        action="store_true",
        help="Include a bottom row showing each model's minimum chapter accuracy.",
    )
    parser.add_argument(
        "--copy",
        action="store_true",
        help="Copy the generated LaTeX to the clipboard using pbcopy.",
    )
    parser.set_defaults(include_all_row=True)
    return parser.parse_args()


def latex_escape(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(ch, ch) for ch in text)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def clean_html_title(title: str, textbook: str) -> str:
    title = html.unescape(re.sub(r"\s+", " ", title).strip())
    suffix = f" - {textbook} | OpenStax"
    if title.endswith(suffix):
        title = title[: -len(suffix)]
    else:
        title = re.sub(r"\s*\|\s*OpenStax$", "", title)
        title = re.sub(r"\s+-\s+[^-]+$", "", title)
    return title


def copy_to_clipboard(text: str):
    try:
        subprocess.run(
            ["pbcopy"],
            input=text,
            text=True,
            check=True,
        )
    except FileNotFoundError as exc:
        raise SystemExit("pbcopy not found. Clipboard copy is only supported on macOS.") from exc
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f"Failed to copy output to clipboard: {exc}") from exc


def section_sort_key(section_id: str):
    normalized = re.sub(r"_\d+$", "", section_id)
    parts = []
    for piece in normalized.split("."):
        try:
            parts.append(int(piece))
        except ValueError:
            parts.append(piece)
    return parts


def wilson_interval(correct: int, total: int, z: float = WILSON_Z_95):
    if total == 0:
        return 0.0, 0.0
    phat = correct / total
    denom = 1 + (z * z) / total
    center = (phat + (z * z) / (2 * total)) / denom
    half = z * math.sqrt((phat * (1 - phat) + (z * z) / (4 * total)) / total) / denom
    return (center - half) * 100, (center + half) * 100


def metric_cell(correct: int, total: int):
    if total == 0:
        return 0.0, "--"
    pct = round((100 * correct) / total, 1)
    low, high = wilson_interval(correct, total)
    return pct, f"{pct:.1f} [{low:.1f}, {high:.1f}]"


def compute_min_accuracy_metrics(chapter_data, models):
    min_metrics = {model: None for model in models}
    for chapter in chapter_data.values():
        chapter_n = chapter["n"]
        if chapter_n == 0:
            continue
        for model in models:
            pct, display = metric_cell(chapter["correct"][model], chapter_n)
            current = min_metrics[model]
            if current is None or pct < current[0]:
                min_metrics[model] = (pct, display)
    return min_metrics


def format_chapter_label(chapter_num: int, chapter_title: str) -> str:
    generic_title = f"Chapter {chapter_num}"
    if chapter_title.strip().lower() == generic_title.lower():
        return generic_title
    return f"{generic_title}: {chapter_title}"


def extract_chapter_titles(preface_path: Path):
    if not preface_path.exists():
        return {}
    text = read_text(preface_path)
    titles = {}
    for match in re.finditer(r"Chapter\s*(\d+)\s*:\s*([^<\n]+)", text):
        chapter_num = int(match.group(1))
        titles[chapter_num] = html.unescape(match.group(2)).strip()
    return titles


def extract_section_titles(html_root: Path, textbook: str):
    titles = {}
    for chapter_dir in sorted(html_root.glob("ch*")):
        if not chapter_dir.is_dir():
            continue
        for html_file in chapter_dir.glob("*.html"):
            if not re.fullmatch(r"\d+\.\d+(?:_\d+)?\.html", html_file.name):
                continue
            match = re.search(r"<title>(.*?)</title>", read_text(html_file), re.IGNORECASE | re.DOTALL)
            if not match:
                continue
            titles[html_file.stem] = clean_html_title(match.group(1), textbook)
    return titles


def extract_section_id(json_path: Path):
    stem = json_path.stem
    match = re.match(r"ch(\d+)\.(\d+)(?:_\d+)?(?:-.+)?$", stem)
    if not match:
        return None
    return f"{match.group(1)}.{match.group(2)}"


def chapter_dir_sort_key(path: Path):
    match = re.fullmatch(r"ch(\d+)", path.name)
    return int(match.group(1)) if match else 10**9


def build_table_data(textbook_root: Path, textbook: str, questions_subdir: str, html_subdir: str, models):
    filtered_root = textbook_root / questions_subdir
    html_root = textbook_root / html_subdir
    if not filtered_root.is_dir():
        raise SystemExit(f"Questions directory not found: {filtered_root}")
    if not html_root.is_dir():
        raise SystemExit(f"HTML directory not found: {html_root}")

    chapter_titles = extract_chapter_titles(html_root / "preface")
    section_titles = extract_section_titles(html_root, textbook)
    chapter_data = {}

    for chapter_dir in sorted(filtered_root.glob("ch*"), key=chapter_dir_sort_key):
        if not chapter_dir.is_dir():
            continue
        chapter_match = re.fullmatch(r"ch(\d+)", chapter_dir.name)
        if not chapter_match:
            continue
        chapter_num = int(chapter_match.group(1))
        entry = chapter_data.setdefault(
            chapter_num,
            {
                "title": chapter_titles.get(chapter_num, f"Chapter {chapter_num}"),
                "n": 0,
                "correct": {model: 0 for model in models},
                "sections": {},
                "chapter_level": {
                    "title": "Chapter-level questions",
                    "n": 0,
                    "correct": {model: 0 for model in models},
                },
            },
        )

        for json_file in sorted(chapter_dir.glob("*.json")):
            section_id = extract_section_id(json_file)
            data = json.loads(json_file.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                continue
            section = None
            if section_id is not None:
                section = entry["sections"].setdefault(
                    section_id,
                    {
                        "title": section_titles.get(section_id, section_id),
                        "n": 0,
                        "correct": {model: 0 for model in models},
                    },
                )
            else:
                section = entry["chapter_level"]
            for question in data:
                if not isinstance(question, dict):
                    continue
                entry["n"] += 1
                section["n"] += 1
                for model in models:
                    value = None
                    for key in (f"{model} Eval by o4-mini", f"{model} Eval"):
                        if key in question:
                            value = question.get(key)
                            break
                    if value is True:
                        entry["correct"][model] += 1
                        section["correct"][model] += 1
    return chapter_data


def build_latex_table(
    textbook: str,
    chapter_data,
    models,
    caption: str,
    label: str,
    include_all_row: bool,
    chapter_only: bool,
    include_min_subchapter_row: bool,
):
    has_any_sections = any(chapter["sections"] for chapter in chapter_data.values())
    effective_chapter_only = chapter_only or not has_any_sections
    min_accuracy_metrics = (
        compute_min_accuracy_metrics(chapter_data, models)
        if include_min_subchapter_row
        else None
    )

    lines = []
    lines.append(r"\begingroup")
    lines.append(r"\scriptsize")
    lines.append(r"\setlength{\tabcolsep}{3pt}")
    lines.append(r"\renewcommand{\arraystretch}{1.15}")
    row_label = r"\textbf{Chapter}" if effective_chapter_only else r"\textbf{Chapter / Section}"
    colspec = r">{\raggedright\arraybackslash}p{0.34\textwidth} r c c c c c"
    header = (
        row_label
        + r" & \textbf{$n$} & \textbf{o3} & \textbf{deepseek-chat} & \textbf{gemini-2.5-pro} & \textbf{o4-mini} & \textbf{gpt-5} \\"
    )
    lines.append(rf"\begin{{longtable}}{{{colspec}}}")
    lines.append(rf"\caption{{{latex_escape(caption)}}}\label{{{label}}}\\")
    lines.append(r"\toprule")
    lines.append(header)
    lines.append(r"\midrule")
    lines.append(rf"\multicolumn{{7}}{{l}}{{\textbf{{Textbook: {latex_escape(textbook)}}}}} \\")
    lines.append(r"\midrule")
    lines.append(r"\endfirsthead")
    lines.append(r"\toprule")
    lines.append(header)
    lines.append(r"\midrule")
    lines.append(rf"\multicolumn{{7}}{{l}}{{\textbf{{Textbook: {latex_escape(textbook)}}} \emph{{(continued)}}}} \\")
    lines.append(r"\midrule")
    lines.append(r"\endhead")
    lines.append(r"\midrule")
    lines.append(r"\multicolumn{7}{r}{\emph{Continued on next page}} \\")
    lines.append(r"\endfoot")
    lines.append(r"\bottomrule")
    lines.append(r"\endlastfoot")

    overall_n = 0
    overall_correct = {model: 0 for model in models}

    for chapter_num in sorted(chapter_data):
        chapter = chapter_data[chapter_num]
        chapter_label = latex_escape(format_chapter_label(chapter_num, chapter["title"]))
        chapter_n = chapter["n"]
        chapter_metrics = {model: metric_cell(chapter["correct"][model], chapter_n) for model in models}
        chapter_best = max((metric[0] for metric in chapter_metrics.values()), default=0.0)
        chapter_cells = []
        for model in models:
            value = chapter_metrics[model][1]
            if chapter_metrics[model][0] == chapter_best and value != "--":
                value = rf"\textbf{{{value}}}"
            chapter_cells.append(value)
        if effective_chapter_only:
            lines.append(
                rf"\textbf{{{chapter_label}}} & {chapter_n:,} & " + " & ".join(chapter_cells) + r" \\"
            )
        else:
            lines.append(rf"\multicolumn{{7}}{{l}}{{\textbf{{{chapter_label}}}}} \\" )
            for section_id in sorted(chapter["sections"], key=section_sort_key):
                section = chapter["sections"][section_id]
                section_n = section["n"]
                section_metrics = {model: metric_cell(section["correct"][model], section_n) for model in models}
                section_best = max((metric[0] for metric in section_metrics.values()), default=0.0)
                cells = []
                for model in models:
                    value = section_metrics[model][1]
                    if section_metrics[model][0] == section_best and value != "--":
                        value = rf"\textbf{{{value}}}"
                    cells.append(value)
                lines.append(
                    rf"\quad {latex_escape(section['title'])} & {section_n:,} & " + " & ".join(cells) + r" \\"
                )
            chapter_level = chapter["chapter_level"]
            if chapter_level["n"] > 0:
                chapter_level_n = chapter_level["n"]
                chapter_level_metrics = {
                    model: metric_cell(chapter_level["correct"][model], chapter_level_n) for model in models
                }
                chapter_level_best = max((metric[0] for metric in chapter_level_metrics.values()), default=0.0)
                chapter_level_cells = []
                for model in models:
                    value = chapter_level_metrics[model][1]
                    if chapter_level_metrics[model][0] == chapter_level_best and value != "--":
                        value = rf"\textbf{{{value}}}"
                    chapter_level_cells.append(value)
                lines.append(
                    rf"\quad {latex_escape(chapter_level['title'])} & {chapter_level_n:,} & "
                    + " & ".join(chapter_level_cells)
                    + r" \\"
                )
            lines.append(rf"\quad \emph{{Total}} & {chapter_n:,} & " + " & ".join(chapter_cells) + r" \\" )
        lines.append(r"\midrule")

        overall_n += chapter_n
        for model in models:
            overall_correct[model] += chapter["correct"][model]

    if include_all_row:
        overall_metrics = {model: metric_cell(overall_correct[model], overall_n) for model in models}
        overall_best = max((metric[0] for metric in overall_metrics.values()), default=0.0)
        overall_cells = []
        for model in models:
            value = overall_metrics[model][1]
            if overall_metrics[model][0] == overall_best and value != "--":
                value = rf"\textbf{{{value}}}"
            overall_cells.append(value)
        lines.append(rf"\textbf{{{latex_escape(textbook)} Total}} & {overall_n:,} & " + " & ".join(overall_cells) + r" \\" )

    if min_accuracy_metrics and all(metric is not None for metric in min_accuracy_metrics.values()):
        min_best = max((min_accuracy_metrics[model][0] for model in models), default=0.0)
        min_cells = []
        for model in models:
            value = min_accuracy_metrics[model][1]
            if min_accuracy_metrics[model][0] == min_best and value != "--":
                value = rf"\textbf{{{value}}}"
            min_cells.append(value)
        lines.append(
            r"\textbf{Min. Chapter Accuracy} & -- & " + " & ".join(min_cells) + r" \\"
        )

    lines.append(r"\end{longtable}")
    lines.append(r"\endgroup")
    return "\n".join(lines)


def resolve_textbook_root(repo_root: Path, textbook: str, textbooks_dir: Optional[str]) -> Path:
    if textbooks_dir:
        textbook_root = repo_root / textbooks_dir / textbook
        if not textbook_root.is_dir():
            raise SystemExit(f"Textbook directory not found: {textbook_root}")
        return textbook_root

    for candidate in ("Textbooks Fixed", "Textbooks"):
        textbook_root = repo_root / candidate / textbook
        if textbook_root.is_dir():
            return textbook_root

    raise SystemExit(
        f"Textbook directory not found for '{textbook}' under "
        f"{repo_root / 'Textbooks Fixed'} or {repo_root / 'Textbooks'}"
    )


def main():
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    textbook = args.textbook
    textbook_root = resolve_textbook_root(repo_root, textbook, args.textbooks_dir)

    models = [model.strip() for model in args.models.split(",") if model.strip()]
    if not models:
        raise SystemExit("No models provided.")

    chapter_data = build_table_data(
        textbook_root=textbook_root,
        textbook=textbook,
        questions_subdir=args.questions_subdir,
        html_subdir=args.html_subdir,
        models=models,
    )
    if not chapter_data:
        raise SystemExit(
            "No chapter/section data found. This script expects section-level JSON files with names like ch1.1-lesson.json or ch1.1-try-it.json."
        )

    caption = args.caption or (
        (
            f"Accuracy (%) with 95% confidence intervals and number of questions ($n$) for {textbook}, broken down by chapter."
            if args.chapter_only or not any(chapter["sections"] for chapter in chapter_data.values())
            else f"Accuracy (%) with 95% confidence intervals and number of questions ($n$) for {textbook}, broken down by chapter and section."
        )
    )
    default_label = re.sub(r"[^a-z0-9]+", "_", textbook.lower()).strip("_")
    label = args.label or f"tab:{default_label}_chapter_section_accuracy"

    latex = build_latex_table(
        textbook=textbook,
        chapter_data=chapter_data,
        models=models,
        caption=caption,
        label=label,
        include_all_row=args.include_all_row,
        chapter_only=args.chapter_only,
        include_min_subchapter_row=args.include_min_subchapter_row,
    )

    if args.copy:
        copy_to_clipboard(latex)

    if args.output:
        output_path = Path(args.output)
        if not output_path.is_absolute():
            output_path = repo_root / output_path
        output_path.write_text(latex + "\n", encoding="utf-8")
        print(f"Wrote {output_path}")
    else:
        print(latex)


if __name__ == "__main__":
    main()
