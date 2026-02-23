import os
import re
import json
from pathlib import Path

import numpy as np
from bs4 import BeautifulSoup
import html
from convert_mathml_to_latex import *

def replace_dashes(text):
    if not text:
        return ""
    dash_variants = [
        '\u2012',
        '\u2013',
        '\u2014',
        '\u2015',
        '\u2212',
        '&ndash;',
        '&mdash;',
        '&minus;',
        '-',
    ]
    dash_pattern = '|'.join(map(re.escape, dash_variants))
    return re.sub(dash_pattern, '-', text)

def extract_image_links(elements, soup):
    image_links = []

    if not isinstance(elements, list):
        elements = [elements]

    for element in elements:

        for img in element.find_all('img'):
            src = img.get('data-lazy-src') or img.get('src')
            if src:
                if src.startswith('/'):
                    src = "https://openstax.org" + src
                elif not src.startswith('http'):
                    src = "https://openstax.org/" + src
                image_links.append(src)

        for reference_link in element.find_all('a', href=True):
            href = reference_link['href']
            if '#' in href:
                figure_id = href.split('#')[-1]
                figure = soup.find(id=figure_id)
                if figure:
                    for img in figure.find_all('img'):
                        src = img.get('data-lazy-src') or img.get('src')
                        if src:
                            if src.startswith('/'):
                                src = "https://openstax.org" + src
                            elif not src.startswith('http'):
                                src = "https://openstax.org/" + src
                            image_links.append(src)

    image_links = list(set(image_links))

    return image_links if image_links else []

def extract_referenced_tables(elements, soup):
    """
    Finds table references in the given element(s). If a link’s href contains a '#' and
    the fragment indicates a table (e.g. "Table_04_02_03"), then find that table in the soup,
    convert it to LaTeX (with an optional caption), and return the LaTeX code.
    """
    tables_content = []
    if not isinstance(elements, list):
        elements = [elements]

    for element in elements:
        for reference_link in element.find_all('a', href=True):
            href = reference_link['href']
            if '#' in href:
                table_id = href.split('#')[-1]

                if not table_id.startswith("Table_"):
                    continue
                referenced_element = soup.find(id=table_id)
                if referenced_element:
                    table = referenced_element.find('table')
                    if table:
                        caption_div = referenced_element.find('div', class_='os-caption-container')
                        caption = ""
                        if caption_div:
                            caption = caption_div.get_text(separator=" ", strip=True)
                        latex_table = html_table_to_latex(table)
                        tables_content.append(f"{caption}\n{latex_table}")
    return '\n'.join(tables_content) if tables_content else None

def process_content(element):
    if element:

        for link in element.find_all('a', href=True):
            href = link['href']
            if '#' in href and "Table_" in href.split('#')[-1]:

                continue
            else:
                link_text = link.get_text(strip=True)
                link.replace_with(link_text)

        for math_tag in element.find_all('math'):
            latex_version = convert_mathml_to_latex(str(math_tag))
            math_tag.replace_with(f' $${latex_version}$$ ')

        for table in element.find_all('table'):
            latex_table = html_table_to_latex(table)
            table.replace_with(latex_table)

        for os_table_div in element.find_all('div', class_='os-table'):
            table = os_table_div.find('table')
            if table:
                latex_table = html_table_to_latex(table)
                os_table_div.replace_with(latex_table)

def extract_and_process_text(element):
    if element:
        for link in element.find_all('a', href=True):

            href = link['href']
            if '#' in href and "Table_" in href.split('#')[-1]:
                continue
            else:
                link_text = link.get_text(strip=True)
                link.replace_with(link_text)

        process_content(element)
        return element.get_text(separator=" ", strip=True)
    return ""

def extract_question_text(exercise):
    problem = exercise.find("div", {"data-type": "problem"})
    if problem:
        problem_container = problem.find("div", class_="os-problem-container")
        if problem_container:
            return extract_and_process_text(problem_container)
    return ""

def extract_answer_text(soup, solution_id):

    solution_div = soup.find("div", {"id": solution_id})
    if solution_div:
        solution_container = solution_div.find("div", class_="os-solution-container")
        if solution_container:
            text = extract_and_process_text(solution_container)

            table_content = extract_referenced_tables(solution_container, soup)
            if table_content:
                text += "\n" + table_content
            return text
    return ""

def extract_answer_image_links(soup, solution_id):
    solution_div = soup.find("div", {"id": solution_id})
    if solution_div:
        return extract_image_links(solution_div, soup)
    return []

def html_table_to_latex(table):
    num_columns = len(table.find('tr').find_all(['th', 'td']))
    column_spec = "|c" * num_columns + "|"
    latex = "\\begin{table}[h]\n\\centering\n"
    latex += "\\begin{tabular}{" + column_spec + "}\n\\hline\n"
    for row in table.find_all('tr'):
        cells = row.find_all(['th', 'td'])
        latex += ' & '.join(cell.get_text(strip=True) for cell in cells) + " \\\\ \\hline\n"
    latex += "\\end{tabular}\n"
    latex += "\\end{table}"
    return latex

def process_exercise(exercise, solution_soup, section_title, soup, section_problem_statement, problem_statement_elements):

    anchor = exercise.find("a", class_="os-number")
    if anchor and anchor.has_attr("data-page-fragment"):
        solution_id = anchor["data-page-fragment"]
    else:
        solution_id = exercise.get('id', '') + "-solution"

    elements_to_extract = problem_statement_elements + [exercise]
    image_links = extract_image_links(elements_to_extract, soup)

    question = extract_question_text(exercise)

    answer = extract_answer_text(solution_soup, solution_id) or ""
    answer_image_links = extract_answer_image_links(solution_soup, solution_id) or []

    table_content = extract_referenced_tables(exercise, soup)
    if table_content:
        question += "\n" + table_content

    problem_table_content = extract_referenced_tables(problem_statement_elements, soup)
    if problem_table_content:
        section_problem_statement += "\n" + problem_table_content

    return {
        "Topic": replace_dashes(html.unescape(section_title)),
        "Problem Statement": replace_dashes(html.unescape(section_problem_statement)),
        "Question": replace_dashes(html.unescape(question)),
        "Image Links": [replace_dashes(html.unescape(link)) for link in image_links],
        "Answer": replace_dashes(html.unescape(answer)),
        "Answer Image Links": [replace_dashes(html.unescape(link)) for link in answer_image_links]
    }

def _verify_answers_in_place(out_path: str, html_path: str) -> None:
    """
    Apply the fix_algebra2-style check: for each question, find the matching
    exercise in the chapter HTML by substring match on the Question text, and
    clear Answer / Answer Image Links if that exercise does NOT have os-hasSolution.
    """
    try:
        with open(out_path, "r", encoding="utf-8") as jf:
            data = json.load(jf)
    except Exception as e:
        print(f"[_verify_answers_in_place] Failed to read JSON {out_path}: {e}")
        return

    try:
        with open(html_path, "r", encoding="utf-8") as hf:
            soup = BeautifulSoup(hf.read(), "html.parser")
    except Exception as e:
        print(f"[_verify_answers_in_place] Failed to read HTML {html_path}: {e}")
        return

    changed = False
    exercises = soup.find_all("div", {"data-type": "exercise"})

    for q in data:
        if not isinstance(q, dict):
            continue
        q_text = (q.get("Question") or "").strip()
        if not q_text:
            continue
        match = next(
            (div for div in exercises if div.get("id") and q_text in div.get_text(strip=False)),
            None,
        )
        if match and "os-hasSolution" not in (match.get("class") or []):
            q["Answer"] = ""
            q["Answer Image Links"] = []
            changed = True

    if changed:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

def question_transcription(
    chapter,
    input_file_path,
    solution_file_path,
    out_path,
    version="review",
    write_to_file: bool = True,
):
    try:
        with open(input_file_path, "r", encoding="utf-8") as file:
            html_content = file.read()
    except Exception as e:
        print(f"Failed to read input file {input_file_path}: {e}")
        return

    print("========================================")
    print(f"STARTING: {chapter}")
    print("========================================")

    soup = BeautifulSoup(html_content, "html.parser")

    try:
        with open(solution_file_path, "r", encoding="utf-8") as file:
            solution_html_content = file.read()
        solution_soup = BeautifulSoup(solution_html_content, "html.parser")
    except Exception as e:
        print(f"Failed to read solution file {solution_file_path}: {e}")
        return

    questions_json = []

    if version == "test":
        sections = [soup.find("section", class_="practice-test")]
        title_tag = "h3"
    elif version == "lesson":
        section_start = soup.find('div', class_="os-eos os-section-exercises-container", attrs={"data-uuid-key": ".section-exercises"})
        sections = section_start.find_all("section", {"data-depth": "2"}) if section_start else []
        title_tag = "h3"
    elif version == "try it":

        sections = soup.find_all(
            "div",
            {"data-type": "note"},
            class_=lambda classes: classes and ("try" in classes and "ui-has-child-title" in classes)
        )

        title_tag = "h2"
    elif version == "review":
        review_section = soup.find('section', class_='review-exercises')
        if review_section:
            sections = review_section.find_all('section', {'data-depth': '2'})
        else:
            sections = []
        title_tag = 'h2'
    else:
        sections = soup.find_all("section", {"data-depth": "1"})
        title_tag = "h2"

    if not sections:
        print(f"No sections found for version={version!r} (e.g. missing container or wrong HTML structure).")
    else:
        print(f"Found {len(sections)} section(s) for version={version!r}.")

    for section in sections:

        if version == "try it":
            title_element = section.find("h2", class_="os-title")
        else:
            title_element = section.find(title_tag, {"data-type": "title"})

        if title_element:
            process_content(title_element)
            section_title = title_element.get_text(separator=" ", strip=True)
        else:
            section_title = ""

        current_problem_statement = ''
        problem_statement_elements = []

        if version == "try it":
            container = section.find("div", class_="os-note-body")
        else:
            container = section

        for elem in container.find_all(recursive=False):
            if elem.name == 'p':
                process_content(elem)
                current_problem_statement = elem.get_text(separator=" ", strip=True)
                problem_statement_elements = [elem]

                next_elem = elem.find_next_sibling()
                while next_elem and (
                    (next_elem.name == 'div' and (('os-figure' in next_elem.get('class', [])) or (next_elem.get('data-type') in ['media', 'equation']))) or
                    (next_elem.name == 'span' and next_elem.get('data-type') == 'media')
                ):
                    process_content(next_elem)
                    problem_statement_elements.append(next_elem)
                    current_problem_statement += "\n" + next_elem.get_text(separator=" ", strip=True)
                    next_elem = next_elem.find_next_sibling()
            elif elem.name == 'div' and elem.get('data-type') == 'exercise':
                exercise = elem
                one_problem = process_exercise(exercise, solution_soup, section_title, soup, current_problem_statement, problem_statement_elements)
                questions_json.append(one_problem)
                if one_problem:
                    print(one_problem)
                    print()
                else:
                    print("  [Skipped exercise: process_exercise returned None (e.g. solution_id fallback used).]")

    n_total = len(questions_json)
    n_valid = sum(1 for q in questions_json if q is not None)
    print(f"Extracted {n_valid} question(s) from {n_total} exercise(s).")

    if write_to_file:
        out_dir = os.path.dirname(out_path)
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)

        with open(out_path, "w", encoding="utf-8") as file:
            json.dump(questions_json, file, indent=4)

        _verify_answers_in_place(out_path, input_file_path)

    return questions_json

def transcribe_try_it(in_prefix, out_prefix, chapter):
    for i in np.arange(chapter, chapter+1, 0.1):
        chapter = round(i, 5)
        input_file_path = f'{in_prefix}/ch{str(chapter).split(".")[0]}/{chapter}.html'
        solution_file_path = f'{in_prefix}/ch{str(chapter).split(".")[0]}/answer_key.html'
        try_it_out_path = f'{out_prefix}/ch{str(chapter).split(".")[0]}/ch{chapter}-try-it.json'
        question_transcription(chapter, input_file_path, solution_file_path, try_it_out_path, 'try it')

def transcribe_lessons(in_prefix, out_prefix, chapter):
    for i in np.arange(chapter, chapter+1, 0.1):
        chapter = round(i, 5)
        input_file_path = f'{in_prefix}/ch{str(chapter).split(".")[0]}/{chapter}.html'
        solution_file_path = f'{in_prefix}/ch{str(chapter).split(".")[0]}/answer_key.html'
        lesson_out_path = f'{out_prefix}/ch{str(chapter).split(".")[0]}/ch{chapter}-lesson.json'
        question_transcription(chapter, input_file_path, solution_file_path, lesson_out_path, 'lesson')

def transcribe_reviews(in_prefix, out_prefix, chapter):
    input_file_path = f'{in_prefix}/ch{chapter}/review-exercises.html'
    solution_file_path = f'{in_prefix}/ch{chapter}/answer_key.html'
    out_path = f'{out_prefix}/ch{chapter}/ch{chapter}-review-exercises.json'
    question_transcription(chapter, input_file_path, solution_file_path, out_path, 'review')

def transcribe_practice_tests(in_prefix, out_prefix, chapter):
    input_file_path = f'{in_prefix}/ch{chapter}/practice-test.html'
    solution_file_path = f'{in_prefix}/ch{chapter}/answer_key.html'
    out_path = f'{out_prefix}/ch{chapter}/ch{chapter}-practice-test.json'
    question_transcription(chapter, input_file_path, solution_file_path, out_path, 'test')

def process_textbook(textbook, start=1, types=None):
    """
    Transcribe all chapters for a given algebra-family textbook from the local
    Final Paper Repo structure into All Questions JSON, then apply algebra fixes.

    Expects HTML under:
      Final Paper Repo/Textbooks/{textbook}/HTML/...

    And writes JSON under:
      Final Paper Repo/Textbooks/{textbook}/All Questions/...
    """
    base = Path(__file__).resolve().parent.parent / "Textbooks"
    chapter_exists = True
    i = start

    correlate = {
        "try_it": transcribe_try_it,
        "lesson": transcribe_lessons,
        "review": transcribe_reviews,
        "test": transcribe_practice_tests,
    }

    while chapter_exists:
        html_root = base / textbook / "HTML"
        out_root = base / textbook / "All Questions"
        in_prefix = str(html_root)
        out_prefix = str(out_root)

        if not types:
            transcribe_try_it(in_prefix, out_prefix, i)
            transcribe_lessons(in_prefix, out_prefix, i)
            transcribe_reviews(in_prefix, out_prefix, i)
            transcribe_practice_tests(in_prefix, out_prefix, i)
        else:
            for j in types:
                correlate[j](in_prefix, out_prefix, i)

        i += 1
        if i > 100:
            chapter_exists = False

if __name__ == "__main__":

    textbooks = [
        "Algebra and Trig 2e",
        "College Algebra",
        "Elementary Algebra 2e",
        "Intermediate Algebra 2e",
        "Prealgebra 2e",
        "Precalc"
    ]

    for name in textbooks:
        process_textbook(name, start=1)
