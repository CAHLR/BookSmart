import os
import json
import time
from pathlib import Path

import dotenv
from openai import OpenAI

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR / "Textbooks"
ALL_QUESTIONS_DIRNAME = "All Questions"

dotenv.load_dotenv(SCRIPT_DIR / "keys.env")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_KEY_1")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY (or OPENAI_KEY_1) not set in environment or keys.env")

client = OpenAI(api_key=OPENAI_API_KEY)

SOLVABLE_PROMPT = (
    "You are determining whether a question is complete and self-contained. "
    "Given a question (with images, if any) and an answer, decide if there is enough information "
    "in the question alone to produce an answer of similar specificity—not necessarily correctness or exact steps.\n\n"

    "Respond ONLY with 'true' or 'false'.\n\n"

    "Mark the question as 'true' (i.e., solvable) if it includes all the necessary information required to solve it, "
    "even if the answer provided is incorrect or incomplete. Do NOT evaluate the quality, correctness, or detail of the answer itself.\n\n"

    "Mark it as 'false' (i.e., incomplete or confusing) if any of the following are true:\n"
    "1) The question refers to a required image, table, figure, appendix, or other media that is missing.\n"
    "   -If an image is referenced and an image link is provided, assume it is the correct image.\n"
    "   -If a table is referenced and the question contains something that resembles a table (including any lists of numbers), assume it is the correct table.\n"
    "2) The question relies on information from another question or external source, and cannot be solved on its own.\n"
    "   -If another question or source is referenced, but not required to solve the question, the question should be labelled as solvable.\n"
    "3) A highly intelligent person with access to any technological tools could not reproduce an answer at a similar level of detail due to missing key data.\n"
    "4) The question includes unrelated or extraneous content (e.g., an additional unrelated question, or an irrelevant method) that could confuse which part to answer.\n"
    "   -Small amount of additional information are okay. Only mark as unsolvable if the additional content would hinder someone from arriving at the desired solution.\n"

    "Ignore any question numbers, headers, or metadata in the 'Topic' field. These are not relevant to your judgment.\n"
    "If you are ever uncertain, respond with 'true'."
)

def ask_gpt_solvability(system_prompt, user_content, image_links=None, max_retries=10):
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": [{"type": "text", "text": user_content}]}
    ]

    if image_links:
        for url in image_links:
            messages[1]["content"].append({
                "type": "image_url",
                "image_url": {"url": url}
            })

    attempt = 0
    while attempt < max_retries:
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=messages
            )
            reply = response.choices[0].message.content.strip().lower()
            print(reply)
            if "true" in reply:
                return True
            elif "false" in reply:
                return False
            else:
                continue
        except Exception as e:
            print(f"Error on attempt {attempt + 1}: {e}")
            attempt += 1
            time.sleep(5)

    print("Max retries reached. Returning False.")
    return False

def process_file(input_path, output_path):
    with open(input_path, "r", encoding="utf-8") as f:
        questions = json.load(f)

    for q in questions:
        text_parts = [q.get(k, "") for k in ["Topic", "Problem Statement", "Question"] if q.get(k)]
        question_text = " ".join(text_parts)
        answer = q.get("Answer", "")
        combined = f"Question: {question_text}\nAnswer: {answer}"

        image_links = q.get("Image Links", [])
        solvable = ask_gpt_solvability(SOLVABLE_PROMPT, combined, image_links)
        q["Solvable"] = solvable

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(questions, f, indent=4)

def main():

    if not BASE_DIR.is_dir():
        print(f"Base textbooks dir not found: {BASE_DIR}")
        return

    for book_dir in sorted(p for p in BASE_DIR.iterdir() if p.is_dir()):
        book = book_dir.name
        in_root = book_dir / ALL_QUESTIONS_DIRNAME
        out_root = in_root

        if not in_root.is_dir():
            print(f"Skipping {book}: no {ALL_QUESTIONS_DIRNAME} folder")
            continue

        for dirpath, _, files in os.walk(str(in_root)):
            for fn in files:
                if not fn.lower().endswith(".json"):
                    continue

                inp = os.path.join(dirpath, fn)
                rel = os.path.relpath(inp, in_root)
                out = os.path.join(out_root, rel)

                print(f"Processing {inp} → {out}")
                process_file(inp, out)

if __name__ == "__main__":
    main()
