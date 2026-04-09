#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import subprocess
from collections import defaultdict
from pathlib import Path


MODELS = ["o3", "deepseek-chat", "gemini-2.5-pro", "o4-mini", "gpt-5"]
SPLIT_ORDER = [True, False]  # Image, No Image

CATEGORY_ORDER = [
    "Accounting and Finance",
    "Algebra and Trigonometry",
    "American Government",
    "Biology",
    "Business Law and Ethics",
    "Calculus",
    "Chemistry",
    "College Algebra",
    "Developmental Math",
    "Physics",
    "Precalculus",
    "Sociology",
    "Statistics",
    "U.S. History",
]

TEXTBOOK_ORDER = {
    "Accounting and Finance": ["Accounting V1", "Accounting V2"],
    "Business Law and Ethics": ["Business Ethics", "Business Law", "Intellectual Property"],
    "Calculus": ["Calc V1", "Calc V2", "Calc V3"],
    "Developmental Math": ["Elementary Algebra 2e", "Intermediate Algebra 2e", "Prealgebra 2e"],
    "Physics": ["College Physics 2e", "University Physics V1", "University Physics V2", "University Physics V3"],
    "Statistics": ["Business Stats", "Statistics High School", "Stats 2e"],
}

CATEGORY_DISPLAY = {"Biology": "Biology (Microbiology)"}

TEXTBOOK_DISPLAY = {
    "American Gov 3e": "American Government",
    "Business Stats": "Business Statistics",
    "Calc V1": "Calculus V1",
    "Calc V2": "Calculus V2",
    "Calc V3": "Calculus V3",
    "Chem 2e": "Chemistry",
    "Microbiology": "Biology (Microbiology)",
    "Precalc": "Precalculus",
    "Statistics High School": "High School Statistics",
    "Stats 2e": "Statistics 2e",
    "US History": "U.S. History",
}

SINGLE_TEXTBOOK_CATEGORY_MAP = {
    "Algebra and Trig 2e": "Algebra and Trigonometry",
    "American Gov 3e": "American Government",
    "Chem 2e": "Chemistry",
    "College Algebra": "College Algebra",
    "Microbiology": "Biology",
    "Precalc": "Precalculus",
    "Sociology": "Sociology",
    "US History": "U.S. History",
}

FALLBACK_TEXTBOOK_TO_CATEGORY = {
    textbook: category
    for category, textbooks in TEXTBOOK_ORDER.items()
    for textbook in textbooks
}
FALLBACK_TEXTBOOK_TO_CATEGORY.update(SINGLE_TEXTBOOK_CATEGORY_MAP)

FALLBACK_IGNORED_TEXTBOOKS = {
    "Economics 3e",
    "Macroeconomics 3e",
    "Marketing",
    "Microeconomics 3e",
    "Organic Chem",
    "Python",
}


def _load_textbook_mapping(project_root: Path) -> tuple[dict[str, str], set[str]]:
    mapping_py = project_root / "data_analysis" / "final_final_final" / "analyze_subject_categories.py"
    if not mapping_py.exists():
        return dict(FALLBACK_TEXTBOOK_TO_CATEGORY), set(FALLBACK_IGNORED_TEXTBOOKS)
    spec = importlib.util.spec_from_file_location("analyze_subject_categories", mapping_py)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load mapping from {mapping_py}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return dict(mod.TEXTBOOK_TO_CATEGORY), set(mod.IGNORED_TEXTBOOKS)


def _wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    phat = k / n
    z2 = z * z
    denom = 1.0 + z2 / n
    center = (phat + z2 / (2.0 * n)) / denom
    margin = (z / denom) * math.sqrt((phat * (1.0 - phat) / n) + (z2 / (4.0 * n * n)))
    return max(0.0, center - margin), min(1.0, center + margin)


def _fmt_value(k: int, n: int) -> str:
    lo, hi = _wilson_ci(k, n)
    return f"{100.0 * (k / n):.1f} [{100.0 * lo:.1f}, {100.0 * hi:.1f}]"


def _fmt_model_values(
    per_model: dict[str, tuple[int, int]],
    *,
    force_dash_for_deepseek_image: bool = False,
) -> list[str]:
    accs = {
        m: (per_model[m][0] / per_model[m][1]) if per_model[m][1] > 0 else float("-inf")
        for m in MODELS
    }
    eligible = [
        m for m in MODELS
        if not (force_dash_for_deepseek_image and m == "deepseek-chat") and per_model[m][1] > 0
    ]
    best = max(accs[m] for m in eligible)
    out: list[str] = []
    for model in MODELS:
        if force_dash_for_deepseek_image and model == "deepseek-chat":
            out.append("-")
            continue
        k, n = per_model[model]
        if n <= 0:
            out.append("-")
            continue
        cell = _fmt_value(k, n)
        if accs[model] == best:
            cell = f"\\textbf{{{cell}}}"
        out.append(cell)
    return out


def _combine_entry(entry: dict[bool, dict[str, object]]) -> dict[str, tuple[int, int]]:
    combined = {m: [0, 0] for m in MODELS}
    for split in SPLIT_ORDER:
        for model in MODELS:
            combined[model][0] += entry[split]["models"][model][0]
            combined[model][1] += entry[split]["models"][model][1]
    return {m: (combined[m][0], combined[m][1]) for m in MODELS}


def _compute_min_textbook_values(
    stats: dict[str, dict[bool, dict[str, object]]],
) -> list[str] | None:
    min_per_model: dict[str, tuple[float, str] | None] = {model: None for model in MODELS}
    for textbook in stats:
        combined = _combine_entry(stats[textbook])
        for model in MODELS:
            k, n = combined[model]
            if n <= 0:
                continue
            acc = k / n
            display = _fmt_value(k, n)
            current = min_per_model[model]
            if current is None or acc < current[0]:
                min_per_model[model] = (acc, display)

    if not all(value is not None for value in min_per_model.values()):
        return None

    best = max(value[0] for value in min_per_model.values() if value is not None)
    out: list[str] = []
    for model in MODELS:
        value = min_per_model[model]
        assert value is not None
        cell = value[1]
        if value[0] == best:
            cell = f"\\textbf{{{cell}}}"
        out.append(cell)
    return out


def _collect_stats(textbooks_root: Path, project_root: Path):
    textbook_to_category, ignored_textbooks = _load_textbook_mapping(project_root)

    stats: dict[str, dict[bool, dict[str, object]]] = defaultdict(
        lambda: {
            True: {"n": 0, "models": {m: [0, 0] for m in MODELS}},
            False: {"n": 0, "models": {m: [0, 0] for m in MODELS}},
        }
    )
    for path in sorted(textbooks_root.rglob("*.json")):
        if "Filtered Questions" not in path.parts:
            continue
        textbook = path.relative_to(textbooks_root).parts[0]
        if textbook in ignored_textbooks or textbook not in textbook_to_category:
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(data, list):
            continue
        for q in data:
            if not isinstance(q, dict):
                continue
            split = bool(q.get("Image Links") or [])
            stats[textbook][split]["n"] += 1
            for model in MODELS:
                value = q.get(f"{model} Eval")
                if isinstance(value, bool):
                    stats[textbook][split]["models"][model][1] += 1
                    if value:
                        stats[textbook][split]["models"][model][0] += 1

    category_to_textbooks: dict[str, list[str]] = defaultdict(list)
    for textbook in stats:
        category_to_textbooks[textbook_to_category[textbook]].append(textbook)

    category_stats: dict[str, dict[bool, dict[str, object]]] = {}
    for category, textbooks in category_to_textbooks.items():
        agg = {
            True: {"n": 0, "models": {m: [0, 0] for m in MODELS}},
            False: {"n": 0, "models": {m: [0, 0] for m in MODELS}},
        }
        for textbook in textbooks:
            for split in SPLIT_ORDER:
                agg[split]["n"] += stats[textbook][split]["n"]
                for model in MODELS:
                    agg[split]["models"][model][0] += stats[textbook][split]["models"][model][0]
                    agg[split]["models"][model][1] += stats[textbook][split]["models"][model][1]
        category_stats[category] = agg

    all_stats = {
        True: {"n": 0, "models": {m: [0, 0] for m in MODELS}},
        False: {"n": 0, "models": {m: [0, 0] for m in MODELS}},
    }
    for textbook in stats:
        for split in SPLIT_ORDER:
            all_stats[split]["n"] += stats[textbook][split]["n"]
            for model in MODELS:
                all_stats[split]["models"][model][0] += stats[textbook][split]["models"][model][0]
                all_stats[split]["models"][model][1] += stats[textbook][split]["models"][model][1]

    return stats, category_to_textbooks, category_stats, all_stats


def build_table(
    textbooks_root: Path,
    project_root: Path,
    *,
    include_min_textbook_row: bool = False,
) -> str:
    stats, category_to_textbooks, category_stats, all_stats = _collect_stats(textbooks_root, project_root)

    lines = [
        r"\begingroup",
        r"\scriptsize",
        r"\setlength{\tabcolsep}{3pt}",
        r"\renewcommand{\arraystretch}{1.15}",
        r"\begin{longtable}{>{\raggedright\arraybackslash}p{0.34\textwidth} r c c c c c}",
        r"\caption{Accuracy (\%) with 95\% confidence intervals and number of questions ($n$).}",
        r"\label{tab:true_accuracy_by_category_models}\\",
        r"\toprule",
        r"\textbf{Category / Textbook} & \textbf{$n$} & \textbf{o3} & \textbf{deepseek-chat} & \textbf{gemini-2.5-pro} & \textbf{o4-mini} & \textbf{gpt-5} \\",
        r"\midrule",
        r"\endfirsthead",
        "",
        r"\toprule",
        r"\textbf{Category / Textbook} & \textbf{$n$} & \textbf{o3} & \textbf{deepseek-chat} & \textbf{gemini-2.5-pro} & \textbf{o4-mini} & \textbf{gpt-5} \\",
        r"\midrule",
        r"\multicolumn{7}{l}{\emph{Table \thetable\ continued}} \\",
        r"\midrule",
        r"\endhead",
        "",
        r"\midrule",
        r"\multicolumn{7}{r}{\emph{Continued on next page}} \\",
        r"\endfoot",
        "",
        r"\bottomrule",
        r"\endlastfoot",
        "",
    ]

    for category in CATEGORY_ORDER:
        textbooks = TEXTBOOK_ORDER.get(category, sorted(category_to_textbooks.get(category, [])))
        textbooks = [t for t in textbooks if t in category_to_textbooks.get(category, [])]
        if not textbooks:
            continue

        if len(textbooks) == 1:
            textbook = textbooks[0]
            entry = _combine_entry(stats[textbook])
            n = sum(stats[textbook][split]["n"] for split in SPLIT_ORDER)
            display = CATEGORY_DISPLAY.get(category, TEXTBOOK_DISPLAY.get(textbook, category))
            values = _fmt_model_values(entry)
            lines.append(f"\\textbf{{{display}}} & {n:,} & " + " & ".join(values) + r" \\")
            lines.append(r"\midrule")
            lines.append("")
            continue

        lines.append(rf"\multicolumn{{7}}{{l}}{{\textbf{{{category}}}}} \\")
        for textbook in textbooks:
            entry = _combine_entry(stats[textbook])
            n = sum(stats[textbook][split]["n"] for split in SPLIT_ORDER)
            display = TEXTBOOK_DISPLAY.get(textbook, textbook)
            values = _fmt_model_values(entry)
            lines.append(rf"\quad {display} & {n:,} & " + " & ".join(values) + r" \\")

        lines.append(r"\cmidrule(l){2-7}")
        entry = _combine_entry(category_stats[category])
        n = sum(category_stats[category][split]["n"] for split in SPLIT_ORDER)
        values = _fmt_model_values(entry)
        lines.append(rf"\quad \emph{{Category Total}} & {n:,} & " + " & ".join(values) + r" \\")
        lines.append(r"\midrule")
        lines.append("")

    all_values = _fmt_model_values(
        {m: (all_stats[True]["models"][m][0] + all_stats[False]["models"][m][0], all_stats[True]["models"][m][1] + all_stats[False]["models"][m][1]) for m in MODELS}
    )
    total_n = all_stats[True]["n"] + all_stats[False]["n"]
    lines.append(rf"\textbf{{ALL TEXTBOOKS}} & {total_n:,} & " + " & ".join(all_values) + r" \\")
    if include_min_textbook_row:
        min_values = _compute_min_textbook_values(stats)
        if min_values is not None:
            lines.append(r"\textbf{Min. Accuracy Textbook} & -- & " + " & ".join(min_values) + r" \\")
    lines.append(r"\end{longtable}")
    lines.append(r"\endgroup")
    return "\n".join(lines)


def build_image_split_table(textbooks_root: Path, project_root: Path) -> str:
    stats, category_to_textbooks, category_stats, all_stats = _collect_stats(textbooks_root, project_root)

    lines = [
        r"\begingroup",
        r"\scriptsize",
        r"\setlength{\tabcolsep}{3pt}",
        r"\renewcommand{\arraystretch}{1.15}",
        r"\begin{longtable}{>{\raggedright\arraybackslash}p{0.28\textwidth} l r c c c c c}",
        r"\caption{Accuracy (\%) with 95\% confidence intervals and number of questions ($n$), split by whether the input contains images.}",
        r"\label{tab:true_accuracy_by_category_models_image_split}\\",
        r"\toprule",
        r"\textbf{Category / Textbook} & \textbf{Split} & \textbf{$n$} & \textbf{o3} & \textbf{deepseek-chat} & \textbf{gemini-2.5-pro} & \textbf{o4-mini} & \textbf{gpt-5} \\",
        r"\midrule",
        r"\endfirsthead",
        r"\toprule",
        r"\textbf{Category / Textbook} & \textbf{Split} & \textbf{$n$} & \textbf{o3} & \textbf{deepseek-chat} & \textbf{gemini-2.5-pro} & \textbf{o4-mini} & \textbf{gpt-5} \\",
        r"\midrule",
        r"\multicolumn{8}{l}{\emph{Table \thetable\ continued}} \\",
        r"\midrule",
        r"\endhead",
        r"\midrule",
        r"\multicolumn{8}{r}{\emph{Continued on next page}} \\",
        r"\endfoot",
        r"\bottomrule",
        r"\endlastfoot",
    ]

    def append_split_rows(label: str, entry: dict[bool, dict[str, object]], prefix: str = "") -> None:
        present = [split for split in SPLIT_ORDER if entry[split]["n"] > 0]
        if not present:
            return
        if len(present) == 1:
            split = present[0]
            values = _fmt_model_values(
                {m: tuple(entry[split]["models"][m]) for m in MODELS},
                force_dash_for_deepseek_image=bool(split),
            )
            lines.append(
                f"{prefix}{label} &  & {entry[split]['n']:,} & " + " & ".join(values) + r" \\"
            )
            return
        first = True
        for split in present:
            values = _fmt_model_values(
                {m: tuple(entry[split]["models"][m]) for m in MODELS},
                force_dash_for_deepseek_image=bool(split),
            )
            left = f"{prefix}{label}" if first else ""
            split_label = "Image" if split else "No Image"
            lines.append(
                f"{left} & {split_label} & {entry[split]['n']:,} & " + " & ".join(values) + r" \\"
            )
            first = False

    def append_combined_total_row(
        entry: dict[bool, dict[str, object]],
        prefix: str = "",
        label: str = "",
    ) -> None:
        present = [split for split in SPLIT_ORDER if entry[split]["n"] > 0]
        if len(present) < 2:
            return
        combined = _combine_entry(entry)
        n = sum(entry[split]["n"] for split in SPLIT_ORDER)
        if n <= 0:
            return
        values = _fmt_model_values(combined)
        lines.append(
            f"{prefix}{label} & Total & {n:,} & " + " & ".join(values) + r" \\"
        )

    for category in CATEGORY_ORDER:
        textbooks = TEXTBOOK_ORDER.get(category, sorted(category_to_textbooks.get(category, [])))
        textbooks = [t for t in textbooks if t in category_to_textbooks.get(category, [])]
        if not textbooks:
            continue

        if len(textbooks) == 1:
            textbook = textbooks[0]
            display = CATEGORY_DISPLAY.get(category, TEXTBOOK_DISPLAY.get(textbook, category))
            append_split_rows(display, stats[textbook])
            append_combined_total_row(stats[textbook])
            lines.append(r"\midrule")
            continue

        lines.append(rf"\multicolumn{{8}}{{l}}{{\textbf{{{category}}}}} \\")
        for textbook in textbooks:
            display = TEXTBOOK_DISPLAY.get(textbook, textbook)
            append_split_rows(display, stats[textbook], prefix=r"\quad ")
            append_combined_total_row(stats[textbook], prefix=r"\quad ")
        lines.append(r"\cmidrule(l){2-8}")
        append_split_rows(r"\quad \emph{Category Total}", category_stats[category])
        append_combined_total_row(category_stats[category])
        lines.append(r"\midrule")

    append_split_rows(r"\textbf{ALL TEXTBOOKS}", all_stats)
    append_combined_total_row(all_stats)
    lines.append(r"\end{longtable}")
    lines.append(r"\endgroup")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Print updated category accuracy LaTeX table and copy it to clipboard."
    )
    parser.add_argument(
        "--textbooks-root",
        type=str,
        default="Textbooks Fixed",
        help='Root containing textbook folders (default: "Textbooks Fixed").',
    )
    parser.add_argument(
        "--no-clipboard",
        action="store_true",
        help="Print only; do not copy the table to the clipboard.",
    )
    parser.add_argument(
        "--image-split",
        action="store_true",
        help="Print the image/no-image split version of the table.",
    )
    parser.add_argument(
        "--include-min-textbook-row",
        action="store_true",
        help="Include a bottom row showing each model's minimum textbook accuracy.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent
    project_root = repo_root.parent
    textbooks_root = Path(args.textbooks_root)
    if not textbooks_root.is_absolute():
        textbooks_root = project_root / textbooks_root
    if not textbooks_root.is_dir():
        raise SystemExit(f"Textbooks root not found: {textbooks_root}")

    table = (
        build_image_split_table(textbooks_root, project_root)
        if args.image_split
        else build_table(
            textbooks_root,
            project_root,
            include_min_textbook_row=args.include_min_textbook_row,
        )
    )
    print(table)

    if not args.no_clipboard:
        try:
            subprocess.run(["pbcopy"], input=table, text=True, check=True)
            print("\nCopied table to clipboard.")
        except Exception as e:
            print(f"\nFailed to copy to clipboard: {e}")


if __name__ == "__main__":
    main()
