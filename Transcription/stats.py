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

def process_ordered_list(ol):
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

def process_unordered_list(ul):
    items = []
    for li in ul.find_all("li", recursive=False):
        li_text = li.get_text(separator=" ", strip=True)
        items.append(f"- {li_text}")
    return " ".join(items)

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
    return list(set(image_links))

def extract_referenced_tables(elements, soup):
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
                        caption = caption_div.get_text(separator=" ", strip=True) if caption_div else ""
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
            if not table.find_parent("div", class_="os-table"):
                latex_table = html_table_to_latex(table)
                table.replace_with(latex_table)
        for os_table_div in element.find_all('div', class_="os-table"):
            table = os_table_div.find('table')
            if table:
                latex_table = html_table_to_latex(table)
                os_table_div.replace_with(latex_table)

        for ol in element.find_all('ol'):
            ol_text = process_ordered_list(ol)
            ol.replace_with(ol_text)

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
    transcription = {
        "Topic": replace_dashes(html.unescape(section_title)),
        "Problem Statement": replace_dashes(html.unescape(section_problem_statement)),
        "Question": replace_dashes(html.unescape(question)),
        "Image Links": [replace_dashes(html.unescape(link)) for link in image_links],
        "Answer": replace_dashes(html.unescape(answer)),
        "Answer Image Links": [replace_dashes(html.unescape(link)) for link in answer_image_links]
    }
    return transcription

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
    sections = soup.find_all("section", {"data-depth": "1"})
    title_tag = "h2"
    for section in sections:
        title_element = section.find(title_tag, {"data-type": "document-title"})
        if title_element:
            process_content(title_element)
            section_title = title_element.get_text(separator=" ", strip=True)
        else:
            section_title = ""

        current_problem_statement = ''
        problem_statement_elements = []
        ps_used = False

        for elem in section.find_all(recursive=False):
            if elem.name == 'p':
                process_content(elem)
                p_text = elem.get_text(separator=" ", strip=True)

                if not current_problem_statement or ps_used:
                    current_problem_statement = p_text
                    problem_statement_elements = [elem]
                    ps_used = False
                else:

                    current_problem_statement += " " + p_text
                    problem_statement_elements.append(elem)
                next_elem = elem.find_next_sibling()

                while next_elem and (
                    (next_elem.name == 'div' and (
                        ('os-figure' in next_elem.get('class', [])) or
                        ('os-table' in next_elem.get('class', [])) or
                        (next_elem.get('data-type') in ['media', 'equation'])
                    )) or
                    (next_elem.name == 'span' and next_elem.get('data-type') == 'media') or
                    (next_elem.name in ['ol', 'ul'])
                ):
                    process_content(next_elem)
                    problem_statement_elements.append(next_elem)
                    if next_elem.name == 'ol' and next_elem.get("type", "").lower() == "a":
                        current_problem_statement += " " + process_ordered_list(next_elem)
                    elif next_elem.name == 'ul':
                        current_problem_statement += " " + process_unordered_list(next_elem)
                    else:
                        current_problem_statement += " " + next_elem.get_text(separator=" ", strip=True)
                    next_elem = next_elem.find_next_sibling()
            elif elem.name == 'div' and elem.get('data-type') == 'exercise':
                one_problem = process_exercise(elem, solution_soup, section_title, soup,
                                               current_problem_statement, problem_statement_elements)
                if one_problem is not None:
                    questions_json.append(one_problem)
                    print(one_problem)

                ps_used = True

    if write_to_file:
        out_dir = os.path.dirname(out_path)
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
        with open(out_path, 'w', encoding='utf-8') as file:
            json.dump(questions_json, file, indent=4)
    return questions_json

def transcribe_reviews(in_prefix, out_prefix, thing, chapter, write_to_file=True):
    input_file_path = f'{in_prefix}/ch{chapter}/{thing}.html'
    solution_file_path = f'{in_prefix}/ch{chapter}/solutions.html'
    out_path = f'{out_prefix}/ch{chapter}/ch{chapter}_{thing}_transcribed.json'
    question_transcription(chapter, input_file_path, solution_file_path, out_path, 'review', write_to_file=write_to_file)

def process_textbook(textbook, start=1, types=None, write_to_file=True):
    base = Path(__file__).resolve().parent.parent / "Textbooks"
    html_root = base / textbook / "HTML"
    out_root = base / textbook / "All Questions"
    chapter_exists = True
    i = start
    while chapter_exists:
        in_prefix = str(html_root)
        out_prefix = str(out_root)
        for j in ['homework', 'bringing-it-together-homework', 'practice', 'bringing-it-together-practice']:
            transcribe_reviews(in_prefix, out_prefix, j, i, write_to_file=write_to_file)
        i += 1
        if i > 100:
            chapter_exists = False

if __name__ == "__main__":
    textbooks = [
        "Business Stats",
        "Statistics High School",
        "Stats 2e"
    ]
    for i in textbooks:
        process_textbook(i)
