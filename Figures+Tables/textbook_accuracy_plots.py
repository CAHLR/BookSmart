import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


MODEL_ORDER = ["o3", "deepseek-chat", "gemini-2.5-pro", "o4-mini", "gpt-5"]
MODEL_COLORS = {
    "o3": "#2563eb",
    "deepseek-chat": "#dc2626",
    "gemini-2.5-pro": "#7c3aed",
    "o4-mini": "#ea580c",
    "gpt-5": "#059669",
}
GRADE_BANDS = [
    ("F", 0),
    ("D-", 60),
    ("D", 63),
    ("D+", 67),
    ("C-", 70),
    ("C", 73),
    ("C+", 77),
    ("B-", 80),
    ("B", 83),
    ("B+", 87),
    ("A-", 90),
    ("A", 93),
    ("A+", 97),
]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate PNG plots from textbook accuracy summary CSV.",
    )
    parser.add_argument(
        "--csv",
        default="Figures+Tables/textbook_accuracy_summary.csv",
        help="Input CSV path relative to repo root unless absolute.",
    )
    parser.add_argument(
        "--output-dir",
        default="Figures+Tables",
        help="Directory for output PNG files relative to repo root unless absolute.",
    )
    return parser.parse_args()


def resolve_path(repo_root: Path, path_str: str) -> Path:
    path = Path(path_str)
    if not path.is_absolute():
        path = repo_root / path
    return path


def load_rows(csv_path: Path):
    with csv_path.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        rows = []
        for row in reader:
            rows.append(
                {
                    "textbook": row["textbook"],
                    "model": row["model"],
                    "avg_accuracy_pct": float(row["avg_accuracy_pct"]),
                    "min_chapter_accuracy_pct": float(row["min_chapter_accuracy_pct"]),
                }
            )
    return rows


def plot_min_bar(rows, output_path: Path):
    textbooks = sorted(
        {row["textbook"] for row in rows},
        key=lambda textbook: sum(
            row["min_chapter_accuracy_pct"] for row in rows if row["textbook"] == textbook
        )
        / len(MODEL_ORDER),
    )

    grouped = {
        textbook: {row["model"]: row["min_chapter_accuracy_pct"] for row in rows if row["textbook"] == textbook}
        for textbook in textbooks
    }

    group_height = len(MODEL_ORDER) + 1.6
    bar_height = 0.78
    y_positions = []
    y_labels = []

    fig_height = max(10, 0.48 * len(textbooks) + 2.5)
    fig, ax = plt.subplots(figsize=(14, fig_height))

    for group_index, textbook in enumerate(textbooks):
        base = group_index * group_height
        values = grouped[textbook]
        y_labels.append(base + (len(MODEL_ORDER) - 1) / 2)
        y_positions.append(textbook)
        for model_index, model in enumerate(MODEL_ORDER):
            y = base + model_index
            ax.barh(
                y,
                values[model],
                height=bar_height,
                color=MODEL_COLORS[model],
                edgecolor="none",
                label=model if group_index == 0 else None,
            )

    ax.set_yticks(y_labels)
    ax.set_yticklabels(textbooks, fontsize=9)
    ax.set_xlim(0, 100)
    ax.set_xlabel("Minimum chapter accuracy (%)")
    ax.set_title("Minimum Chapter Accuracy by Textbook and Model", pad=12)
    ax.grid(axis="x", color="#e5e7eb", linewidth=1)
    ax.set_axisbelow(True)
    ax.invert_yaxis()
    ax.legend(loc="lower right", ncol=3, frameon=False)
    fig.tight_layout()
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def cumulative_counts(rows, model: str, field: str):
    model_rows = [row for row in rows if row["model"] == model]
    return [sum(1 for row in model_rows if row[field] >= threshold) for _, threshold in GRADE_BANDS]


def plot_grade_cdf(rows, output_path: Path, field: str, title: str):
    fig, ax = plt.subplots(figsize=(8.5, 6))
    x = list(range(len(GRADE_BANDS)))
    labels = [label for label, _ in GRADE_BANDS]
    textbook_count = len({row["textbook"] for row in rows})

    for model in MODEL_ORDER:
        counts = cumulative_counts(rows, model, field)

        ax.plot(
            x,
            counts,
            color=MODEL_COLORS[model],
            linewidth=2.5,
            marker="o",
            markersize=4,
            label=model,
        )

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=12)
    ax.set_ylim(0, textbook_count)
    ax.tick_params(axis="y", labelsize=12)
    ax.grid(axis="y", color="#e5e7eb", linewidth=1)
    ax.grid(axis="x", color="#f1f5f9", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.legend(loc="lower left", ncol=2, frameon=False, fontsize=12)

    fig.suptitle(
        title,
        fontsize=18,
        y=0.98,
    )
    fig.supxlabel("Grade threshold", fontsize=13)
    fig.supylabel("Number of textbooks", fontsize=13)
    fig.tight_layout(rect=(0.03, 0.03, 1, 0.95))
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def main():
    args = parse_args()
    repo_root = Path(__file__).resolve().parent.parent
    csv_path = resolve_path(repo_root, args.csv)
    output_dir = resolve_path(repo_root, args.output_dir)

    if not csv_path.is_file():
        raise SystemExit(f"CSV not found: {csv_path}")
    output_dir.mkdir(parents=True, exist_ok=True)

    rows = load_rows(csv_path)
    if not rows:
        raise SystemExit("No rows loaded from CSV.")

    bar_path = output_dir / "textbook_min_chapter_accuracy_barplot.png"
    avg_cdf_path = output_dir / "textbook_avg_accuracy_grade_cdf.png"
    min_cdf_path = output_dir / "textbook_min_chapter_accuracy_grade_cdf.png"

    plot_min_bar(rows, bar_path)
    plot_grade_cdf(
        rows,
        avg_cdf_path,
        "avg_accuracy_pct",
        "Average Accuracy CDF",
    )
    plot_grade_cdf(
        rows,
        min_cdf_path,
        "min_chapter_accuracy_pct",
        "Minimum Chapter Accuracy CDF",
    )

    print(f"Wrote {bar_path}")
    print(f"Wrote {avg_cdf_path}")
    print(f"Wrote {min_cdf_path}")


if __name__ == "__main__":
    main()
