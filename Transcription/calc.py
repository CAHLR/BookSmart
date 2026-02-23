import os
import re
import json
import numpy as np
from bs4 import BeautifulSoup
import html
from pathlib import Path

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

def extract_answer_text(soup, problem_id):
    solution_div = soup.find("div", {"id": problem_id})
    if solution_div:
        solution_container = solution_div.find("div", class_="os-solution-container")
        if solution_container:
            text = extract_and_process_text(solution_container)

            table_content = extract_referenced_tables(solution_container, soup)
            if table_content:
                text += "\n" + table_content
            return text
    return ""

def extract_answer_image_links(soup, problem_id):
    solution_div = soup.find("div", {"id": problem_id})
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

def process_ordered_list(ol):
    """
    Processes an <ol> element. If the ordered list has a type attribute of "a", then each list item
    is prefixed with its corresponding lowercase letter (e.g., a), b), c), etc.). Otherwise, numbered items are used.
    """
    list_type = ol.get("type", "").lower()
    items = []
    if list_type == "a":
        letter_index = ord('a')
        for li in ol.find_all("li", recursive=False):
            li_text = li.get_text(separator=" ", strip=True)
            items.append(f"{chr(letter_index)}) {li_text}")
            letter_index += 1
    else:
        index = 1
        for li in ol.find_all("li", recursive=False):
            li_text = li.get_text(separator=" ", strip=True)
            items.append(f"{index}) {li_text}")
            index += 1
    return " ".join(items)

def process_exercise(exercise, solution_soup, section_title, soup, section_problem_statement, problem_statement_elements):
    anchor = exercise.find("a", class_="os-number")
    if anchor and anchor.has_attr("data-page-fragment"):
        solution_id = anchor["data-page-fragment"]
    else:
        solution_id = exercise.get('id', '') + "-solution"

    elements_to_extract = problem_statement_elements + [exercise]
    image_links = extract_image_links(elements_to_extract, soup)

    question = extract_question_text(exercise)

    if "os-hasSolution" in exercise.get("class", []):
        answer = extract_answer_text(solution_soup, solution_id) or ""
        answer_image_links = extract_answer_image_links(solution_soup, solution_id) or []
    else:
        answer = ""
        answer_image_links = []

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

def question_transcription(chapter, input_file_path, solution_file_path, out_path, version="review", write_to_file=True):
    try:
        with open(input_file_path, "r", encoding="utf-8") as file:
            html_content = file.read()
    except Exception as e:
        print(f"Failed to read the file due to: {str(e)}")
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
        print(f"Failed to read the solution file due to: {str(e)}")
        return

    questions_json = []

    if version == "checkpoint":

        sections = soup.find_all(
            "div",
            {"data-type": "note"},
            class_=lambda classes: classes and ("checkpoint" in classes and "ui-has-child-title" in classes)
        )
        title_tag = "h2"
    elif version == "lesson":
        section_start = soup.find('div', class_="os-eos os-section-exercises-container", attrs={"data-uuid-key": ".section-exercises"})

        sections = section_start.find_all("section", {"data-depth": "1"}) if section_start else []
        title_tag = "h2"
    elif version == "review":

        review_section = soup.find('section', class_='review-exercises')
        if review_section:
            sections = [review_section]
        else:
            sections = []
        title_tag = 'h3'
    else:
        sections = soup.find_all("section", {"data-depth": "1"})
        title_tag = "h2"

    for section in sections:

        if version == "checkpoint":
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

        if version == "checkpoint":
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
                        (next_elem.name == 'div' and (
                                ('os-figure' in next_elem.get('class', [])) or
                                ('os-table' in next_elem.get('class', [])) or
                                (next_elem.get('data-type') in ['media', 'equation'])
                        )) or
                        (next_elem.name == 'span' and next_elem.get('data-type') == 'media') or
                        (next_elem.name == 'ol')
                ):
                    process_content(next_elem)
                    problem_statement_elements.append(next_elem)
                    if next_elem.name == 'ol' and next_elem.get("type", "").lower() == "a":
                        current_problem_statement += " " + process_ordered_list(next_elem)
                    else:
                        current_problem_statement += " " + next_elem.get_text(separator=" ", strip=True)
                    next_elem = next_elem.find_next_sibling()
            elif elem.name == 'div' and elem.get('data-type') == 'exercise':
                exercise = elem
                one_problem = process_exercise(exercise, solution_soup, section_title, soup, current_problem_statement,
                                               problem_statement_elements)
                questions_json.append(one_problem)
                if one_problem:
                    print(one_problem)
                    print()

    if write_to_file:
        out_dir = os.path.dirname(out_path)
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
        with open(out_path, 'w', encoding='utf-8') as file:
            json.dump(questions_json, file, indent=4)

    return questions_json

def transcribe_checkpoints(in_prefix, out_prefix, chapter):

    for i in np.arange(chapter, chapter+1, 0.1):
        chapter_val = round(i, 5)
        input_file_path = f'{in_prefix}/ch{str(chapter_val).split(".")[0]}/{chapter_val}.html'
        solution_file_path = f'{in_prefix}/ch{str(chapter_val).split(".")[0]}/answer_key.html'
        checkpoint_out_path = f'{out_prefix}/ch{str(chapter_val).split(".")[0]}/ch{chapter_val}-checkpoint.json'
        question_transcription(chapter_val, input_file_path, solution_file_path, checkpoint_out_path, 'checkpoint')

def transcribe_lessons(in_prefix, out_prefix, chapter):
    for i in np.arange(chapter, chapter+1, 0.1):
        chapter_val = round(i, 5)
        input_file_path = f'{in_prefix}/ch{str(chapter_val).split(".")[0]}/{chapter_val}.html'
        solution_file_path = f'{in_prefix}/ch{str(chapter_val).split(".")[0]}/answer_key.html'
        lesson_out_path = f'{out_prefix}/ch{str(chapter_val).split(".")[0]}/ch{chapter_val}-lesson.json'
        question_transcription(chapter_val, input_file_path, solution_file_path, lesson_out_path, 'lesson')

def transcribe_reviews(in_prefix, out_prefix, chapter):
    input_file_path = f'{in_prefix}/ch{chapter}/review-exercises.html'
    solution_file_path = f'{in_prefix}/ch{chapter}/answer_key.html'
    out_path = f'{out_prefix}/ch{chapter}/ch{chapter}-review-exercises.json'
    question_transcription(chapter, input_file_path, solution_file_path, out_path, 'review')

def process_textbook(textbook, start=1, types=None):
    """
    Read HTML from Final Paper Repo/Textbooks/{textbook}/HTML/
    Write JSON to Final Paper Repo/Textbooks/{textbook}/All Questions/
    """
    base = Path(__file__).resolve().parent.parent / "Textbooks"
    html_root = base / textbook / "HTML"
    out_root = base / textbook / "All Questions"

    if not html_root.is_dir():
        print(f"Skipping {textbook}: no HTML folder at {html_root}")
        return

    chapter_exists = True
    i = start

    correlate = {
        "checkpoint": transcribe_checkpoints,
        "lesson": transcribe_lessons,
        "review": transcribe_reviews,
    }

    while chapter_exists:
        in_prefix = str(html_root)
        out_prefix = str(out_root)
        if not types:
            transcribe_checkpoints(in_prefix, out_prefix, i)
            transcribe_lessons(in_prefix, out_prefix, i)
            transcribe_reviews(in_prefix, out_prefix, i)
        else:
            for j in types:
                correlate[j](in_prefix, out_prefix, i)
        i += 1
        if i > 100:
            chapter_exists = False

if __name__ == "__main__":
    textbooks = [
        "Calc V1",
        "Calc V2",
        "Calc V3",
    ]

    for name in textbooks:
        process_textbook(name, start=1)
