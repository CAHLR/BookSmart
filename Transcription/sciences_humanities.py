import os
import re
import json
import numpy as np
from pathlib import Path
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

def replace_sup_sub(html_string):

    html_string = re.sub(r'<sup>(.*?)</sup>', r'^\1', html_string)
    html_string = re.sub(r'<sub>(.*?)</sub>', r'_\1', html_string)
    return html_string

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

        for p in element.find_all('p'):
            p_html = str(p)
            replaced = replace_sup_sub(p_html)
            new_p = BeautifulSoup(replaced, "html.parser")
            p.replace_with(new_p)

        for ol in element.find_all('ol'):
            choices = ol.find_all('li')
            for idx, li in enumerate(choices):
                prefix = f'{chr(65 + idx)}. '
                li.insert(0, prefix)

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

def extract_image_links(elements, soup):
    image_links = []
    if not isinstance(elements, list):
        elements = [elements]
    for element in elements:
        if element:

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
    return list(set(image_links))

def extract_referenced_tables(elements, soup):
    """
    Finds any table references (links with fragments like "#Table_...") within the given elements.
    Returns the LaTeX code for these tables (with any optional caption) concatenated together.
    """
    tables_content = []
    if not isinstance(elements, list):
        elements = [elements]
    for element in elements:
        if element:
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

def process_exercise(exercise, solution_soup, section_title, soup, section_problem_statement="",
                     problem_statement_elements=None):
    anchor = exercise.find("a", class_="os-number")
    if anchor and anchor.has_attr("data-page-fragment"):
        solution_id = anchor["data-page-fragment"]
    else:
        solution_id = exercise.get('id', '') + "-solution"

    if problem_statement_elements is None:
        problem_statement_elements = []

    elements_to_extract = problem_statement_elements + [exercise]
    image_links = extract_image_links(elements_to_extract, soup)

    question = extract_question_text(exercise)

    answer = ""
    answer_image_links = []
    if "os-hasSolution" in exercise.get("class", []):
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

def has_solutions(soup):
    return bool(soup.find("div", class_="os-hasSolution"))

def question_transcription(chapter, input_file_path, solution_file_path, out_path, version="review", write_to_file=True):
    try:
        with open(input_file_path, "r", encoding="utf-8") as file:
            html_content = file.read()
    except Exception as e:

        return

    print("========================================")
    print(f"STARTING: Chapter {chapter}")
    print("========================================")

    soup = BeautifulSoup(html_content, "html.parser")

    if not has_solutions(soup):

        return

    try:
        with open(solution_file_path, "r", encoding="utf-8") as file:
            solution_html_content = file.read()
        solution_soup = BeautifulSoup(solution_html_content, "html.parser")
    except Exception as e:

        return

    questions_json = []

    if version == "try it":
        sections = soup.find_all(
            "div",
            {"data-type": "note"},
            class_=lambda classes: classes and "ui-has-child-title" in classes
        )
        title_tag = "h2"
    else:
        sections = soup.find_all("section", {"data-depth": "1"})
        title_tag = "h2"

    for section in sections:
        if version == "try it":
            title_element = section.find("h2", class_="os-title")
        else:
            title_element = section.find(title_tag, {"data-type": "document-title"})

        if title_element:
            process_content(title_element)
            section_title = title_element.get_text(separator=" ", strip=True)
        else:
            section_title = ""

        current_problem_statement = ""
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
            elif elem.name == 'div' and elem.get('data-type') == 'exercise':
                exercise = elem
                one_problem = process_exercise(
                    exercise,
                    solution_soup,
                    section_title,
                    soup,
                    current_problem_statement,
                    problem_statement_elements
                )
                if one_problem and one_problem["Problem Statement"] == "" and "true-false" in input_file_path:
                    one_problem["Problem Statement"] = "True or False?"
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

def transcribe_exercises(in_prefix, out_prefix, problem_type, chapter, write_to_file=True):
    input_file_path = f'{in_prefix}/ch{chapter}/{problem_type}.html'
    solution_file_path = f'{in_prefix}/ch{chapter}/answer_key.html'
    out_path = f'{out_prefix}/ch{chapter}/ch{chapter}-{problem_type}.json'
    question_transcription(chapter, input_file_path, solution_file_path, out_path, 'review', write_to_file=write_to_file)

def transcribe_try_it(in_prefix, out_prefix, chapter, write_to_file=True):
    for i in np.arange(chapter, chapter+1, 0.1):
        chapter = round(i, 5)
        input_file_path = f'{in_prefix}/ch{str(chapter).split(".")[0]}/{chapter}.html'
        solution_file_path = f'{in_prefix}/ch{str(chapter).split(".")[0]}/answer_key.html'
        try_it_out_path = f'{out_prefix}/ch{str(chapter).split(".")[0]}/ch{chapter}-try-it.json'
        question_transcription(chapter, input_file_path, solution_file_path, try_it_out_path, 'try it', write_to_file=write_to_file)

def process_textbook(textbook, start=1, types=None, write_to_file=True):
    base = Path(__file__).resolve().parent.parent / "Textbooks"
    html_root = base / textbook / "HTML"
    out_root = base / textbook / "All Questions"
    chapter_exists = True
    chapter = start

    if types is None:
        types = [
            'exercises',
            'review-exercises',
            'problems-exercises',
            'conceptual-questions',
            'problems',
            'challenge-problems',
            'additional-problems',
            'multiple-choice',
            'fill-in-the-blank',
            'true-false',
            'review-questions',
            'section-quiz',
            'self-check-questions',
            'assessment-questions',
            'questions'
        ]

    while chapter_exists:
        in_prefix = str(html_root)
        out_prefix = str(out_root)

        transcribe_try_it(in_prefix, out_prefix, chapter, write_to_file=write_to_file)
        for etype in types:
            transcribe_exercises(in_prefix, out_prefix, etype, chapter, write_to_file=write_to_file)
        chapter += 1
        if chapter > 100:
            chapter_exists = False

if __name__ == "__main__":
    textbooks = [
        'Chem 2e',
        'Microbiology',
        'College Physics 2e',
        'University Physics V1',
        'University Physics V2',
        'University Physics V3',
        'Business Ethics',
        'Business Law',
        'Intellectual Property',
        'Accounting V1',
        'Accounting V2',
        'US History',
        'American Gov 3e',
        'Sociology',
    ]

    for textbook in textbooks:
        process_textbook(textbook)
