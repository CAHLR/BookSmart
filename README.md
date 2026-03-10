# BookSmart

Pipeline for extracting textbook questions from HTML, filtering to LLM-solvable ones, running multiple LLMs on them, and evaluating answers with o4-mini.

This benchmark repository contains problems curated from textbooks published by [OpenStax](https://openstax.org/) under the [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/) license. All copies and derivatives of this content must retain attribution to OpenStax, the original publisher.

**Prerequisites:** You already have the textbook HTMLs (one folder per book under `Textbooks/<book>/HTML/`). The steps below produce question JSONs in **All Questions**, then a filtered set in **Filtered Questions**, then model answers and evaluations.

---

## 1. Directory layout (target)

After the full workflow, each textbook looks like:

```
Textbooks/
  <Book Name>/
    HTML/                    # Input: chapter/section HTML files (you have these)
    All Questions/           # Step 1 output: one JSON per section (e.g. ch1/ch1-problems.json)
    Filtered Questions/      # Step 2–3 output: subset of questions used for solving & eval
```

- **HTML**: Source HTML for each chapter/section (and answer keys). Layout depends on book type (algebra vs calc vs stats vs sciences/humanities).
- **All Questions**: JSON files with the same relative paths as the HTML structure. Each JSON is a list of question objects with `Topic`, `Problem Statement`, `Question`, `Image Links`, `Answer`, `Answer Image Links`.
- **Filtered Questions**: Same folder/file structure as All Questions, but only questions that are solvable, have a reference answer, and no images in the answer (see Step 3).

---

## 2. Step 1 — Transcription (HTML → All Questions)

Transcription scripts parse the HTML and write question JSONs into `Textbooks/<book>/All Questions/`. Each script is keyed to a family of textbooks (different HTML layouts).

Run from the **Final Paper Repo** root. Scripts live in `Transcription/` and resolve paths relative to the repo (e.g. `Textbooks/<book>/HTML` and `Textbooks/<book>/All Questions`).

### 2.1 Algebra (and Trig, College Algebra, Precalc, etc.)

- **Script:** `Transcription/algebra.py`
- **Textbooks:** Algebra and Trig 2e, College Algebra, Elementary Algebra 2e, Intermediate Algebra 2e, Prealgebra 2e, Precalc
- **Input:** `Textbooks/<book>/HTML/chN/<section>.html` and `answer_key.html`
- **Output:** `Textbooks/<book>/All Questions/chN/chN-<section>.json` (try-it, lesson, review-exercises, practice-test)

```bash
cd "Final Paper Repo"
python Transcription/algebra.py
```

### 2.2 Calculus

- **Script:** `Transcription/calc.py`
- **Textbooks:** Calc V1, Calc V2, Calc V3
- **Input:** `Textbooks/<book>/HTML/chN/<section>.html` and `answer_key.html`
- **Output:** `Textbooks/<book>/All Questions/chN/chN-<section>.json`

```bash
python Transcription/calc.py
```

### 2.3 Sciences & humanities (physics, chemistry, biology, business, history, etc.)

- **Script:** `Transcription/sciences_humanities.py`
- **Textbooks:** Chem 2e, Microbiology, College Physics 2e, University Physics V1/V2/V3, Business Ethics, Business Law, Intellectual Property, Accounting V1/V2, US History, American Gov 3e, Sociology
- **Input:** `Textbooks/<book>/HTML/chN/<type>.html` (e.g. exercises, problems, review-questions) and `answer_key.html`
- **Output:** `Textbooks/<book>/All Questions/chN/chN-<type>.json`

```bash
python Transcription/sciences_humanities.py
```

### 2.4 Statistics

- **Script:** `Transcription/stats.py`
- **Textbooks:** Business Stats, Statistics High School, Stats 2e
- **Input:** `Textbooks/<book>/HTML/chN/<thing>.html` (homework, practice, bringing-it-together-*) and `solutions.html`
- **Output:** `Textbooks/<book>/All Questions/chN/chN_<thing>_transcribed.json`

```bash
python Transcription/stats.py
```

### 2.5 Transcription dependencies

- Python: `beautifulsoup4`, `numpy` (see `requirements.txt`). MathML→LaTeX uses **plurimath** (Ruby gem) if available, else falls back to Node `mathml-to-latex` (see `Transcription/convert_mathml_to_latex.py` and `Transcription/mathml-to-latex.js`).
- Optional: `gem install plurimath` for better MathML conversion.

---

## 3. Step 2 — Solvability (filter.py)

`filter.py` reads every JSON under `Textbooks/<book>/All Questions/` and adds a **Solvable** field to each question. It uses GPT-4o to decide whether the question is complete and self-contained (all information needed to solve it is present in the question and any linked images). It writes back into the same All Questions files (in place).

- **Script:** `filter.py`
- **Input/output:** `Textbooks/<book>/All Questions/**/*.json` (updated in place)

Requirements:

- `OPENAI_API_KEY` or `OPENAI_KEY_1` in environment or in `keys.env` (see below).

```bash
python filter.py
```

---

## 4. Step 3 — Build Filtered Questions

After Step 2, you need a **Filtered Questions** set that the solver and eval scripts use. This set should contain only questions that:

1. Have **Solvable** = true (from filter.py).
2. Have a non-empty **Answer** (reference answer exists).
3. Have **no images in the answer** (i.e. **Answer Image Links** is empty or not used), so that LLM answers can be evaluated without comparing to images.

You create `Textbooks/<book>/Filtered Questions/` by copying (or symlinking) the same directory/file structure as All Questions, but only including JSON files that have been filtered so every question in them meets the three conditions above. Filtering can be done with a small script: for each JSON in All Questions, load it, drop questions where `Solvable` is not true, or `Answer` is empty, or `Answer Image Links` is non-empty; if the resulting list is non-empty, write it to the corresponding path under `Filtered Questions/`. The repo does not include this script; you can add one or do the filter manually.

Result: `Textbooks/<book>/Filtered Questions/` with the same relative paths as in All Questions (e.g. `ch1/ch1-problems.json`).

---

## 5. Step 4 — Run models (solver.py)

`solver.py` runs one chosen model over **all** JSON files under `Textbooks/*/Filtered Questions/`. For each question it calls the model API, then writes the model’s answer into the same JSON under a key like `"o3 Answer"` or `"gemini-2.5-pro Answer"`.

- **Script:** `solver.py`
- **Input/output:** `Textbooks/<book>/Filtered Questions/**/*.json` (read and written in place)

### 5.1 Supported models

| Model            | Provider  | Environment variable   |
|-----------------|----------|-------------------------|
| o3              | OpenAI   | `OPENAI_API_KEY`        |
| o4-mini         | OpenAI   | `OPENAI_API_KEY`        |
| gpt-5            | OpenAI   | `OPENAI_API_KEY`        |
| deepseek-chat   | DeepSeek | `DEEPSEEK_API_KEY`      |
| gemini-2.5-pro  | Google   | `GEMINI_API_KEY`        |

### 5.2 Setting API keys

Either set the variables in your environment or put them in a file (e.g. `keys.env` in the repo root) and point the solver at it:

- **keys.env** (one per line, no spaces around `=`):  
  `OPENAI_API_KEY=sk-...`  
  `DEEPSEEK_API_KEY=...`  
  `GEMINI_API_KEY=...`

Then run:

```bash
python solver.py --model o3 --keys-env keys.env
```

If you don’t pass `--keys-env`, the script looks for `keys.env` in the repo root by default (or use env var `KEYS_ENV` to override the path). Keys are loaded only if not already set in the environment.

### 5.3 Usage

```bash
# Run one model over all Filtered Questions
python solver.py --model o3
python solver.py --model deepseek-chat
python solver.py --model gemini-2.5-pro

# Custom keys file
python solver.py --model o4-mini --keys-env /path/to/keys.env

# See which files would be processed (no API calls)
python solver.py --model gpt-5 --dry-run

# Re-run even on files that already have answers for this model
python solver.py --model o3 --include-complete
```

Options:

- `--base-dir`: Root containing textbook folders (default: `Textbooks`).
- `--questions-subdir`: Subdirectory under each book with question JSONs (default: `Filtered Questions`).
- `--keys-env`: Path to env file for API keys.
- `--include-complete`: Don’t skip files where every question already has an answer for the chosen model.
- `--dry-run`: List files that would be processed and exit.

---

## 6. Step 5 — Evaluate answers (eval.py)

`eval.py` walks `Textbooks/` and only processes paths under **Filtered Questions**. For each question that has a reference **Answer** and a model answer (e.g. `"o3 Answer"`), it calls **o4-mini** to judge whether the model answer is correct. It writes the result back into the same JSON under a key like `"o3 Eval by o4-mini"` (True/False).

- **Script:** `eval.py`
- **Input/output:** `Textbooks/<book>/Filtered Questions/**/*.json` (updated in place)

Requirements:

- `OPENAI_API_KEY` (or `OPENAI_KEY_1`) for o4-mini.

Keys can be in the environment or in `keys.env` in the repo root (eval loads `keys.env` from the script directory).

```bash
# Run evaluations (default: all TARGET_MODELS, same input/output dir)
python eval.py

# Custom dirs and model list
python eval.py --input-dir Textbooks --output-dir Textbooks --models "o3,deepseek-chat,gpt-5"

# Throttle and limit for testing
python eval.py --sleep 1.0 --file-limit 5

# Only report how many evaluations are still pending (no API calls)
python eval.py --report-pending
```

Default models evaluated: `o3`, `deepseek-chat`, `gemini-2.5-pro`, `o4-mini`, `gpt-5`. Evaluations are skipped for questions that already have a non-null `"<model> Eval by o4-mini"` value.

---

## 7. Workflow summary

1. **HTML in place** — `Textbooks/<book>/HTML/` for each book.
2. **Transcription** — Run the right script(s) in `Transcription/` (algebra, calc, sciences_humanities, stats) to fill `Textbooks/<book>/All Questions/`.
3. **Solvability** — Run `filter.py` to add `Solvable` to every question in All Questions.
4. **Filtered set** — Build `Textbooks/<book>/Filtered Questions/` keeping only questions with `Solvable` true, non-empty `Answer`, and no answer images.
5. **Solve** — Run `solver.py --model <name>` for each model (o3, o4-mini, gpt-5, deepseek-chat, gemini-2.5-pro); set the corresponding API keys via env or `keys.env`.
6. **Evaluate** — Run `eval.py` to add `"<model> Eval by o4-mini"` to each question in Filtered Questions using o4-mini.

---

## 8. Python setup

From the repo root:

```bash
pip install -r requirements.txt
```

See `requirements.txt` for the list (e.g. beautifulsoup4, google-genai, numpy, openai, python-dotenv). Optional: Ruby `plurimath` and Node `mathml-to-latex` for transcription (see Step 2.5).

---

## 9. Script reference

| Script | Purpose |
|--------|--------|
| `Transcription/algebra.py` | HTML → All Questions for algebra-family books |
| `Transcription/calc.py` | HTML → All Questions for calculus |
| `Transcription/sciences_humanities.py` | HTML → All Questions for sciences/humanities |
| `Transcription/stats.py` | HTML → All Questions for statistics |
| `filter.py` | Add Solvable (GPT-4o) to All Questions |
| `solver.py` | Run one LLM on all Filtered Questions, write `<model> Answer` |
| `eval.py` | Run o4-mini to add `<model> Eval by o4-mini` in Filtered Questions |
