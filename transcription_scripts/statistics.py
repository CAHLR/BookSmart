import json
import subprocess

import numpy as np
from bs4 import BeautifulSoup, Tag
import html
import re
from convert_mathml_to_latex import *
from json_to_excel import *


def replace_sup_sub(html_string):
    # Replace <sup>...</sup> with ^ followed by the content inside the tags
    html_string = re.sub(r'<sup>(.*?)</sup>', r'^\1', html_string)

    # Replace <sub>...</sub> with _ followed by the content inside the tags
    html_string = re.sub(r'<sub>(.*?)</sub>', r'_\1', html_string)

    html_string = re.sub(r'<[^>]*>', '', html_string)

    return html_string




def extract_image_link(element, soup):
    image_tag = element.find('img')
    if image_tag and image_tag.get('data-lazy-src'):
        return "openstax.org" + image_tag['data-lazy-src']

    # Check if there's a link to a figure in the element
    reference_link = element.find('a', href=True)
    if reference_link:
        figure_id = reference_link['href'].split('#')[-1]
        figure = soup.find(id=figure_id)
        if figure:
            image_tag = figure.find('img')
            if image_tag and image_tag.get('data-lazy-src'):
                return "openstax.org" + image_tag['data-lazy-src']

    # Check for a figure reference in sibling elements
    sibling = element.find_previous_sibling()
    while sibling:
        if sibling.name == 'div' and 'os-figure' in sibling.get('class', []):
            image_tag = sibling.find('img')
            if image_tag and image_tag.get('data-lazy-src'):
                return "openstax.org" + image_tag['data-lazy-src']
        sibling = sibling.find_previous_sibling()

    return None


def process_content(element):
    if element:
        for math_tag in element.find_all('math'):
            latex_version = convert_mathml_to_latex(str(math_tag))
            math_tag.replace_with(f' $${latex_version}$$ ')

        for table in element.find_all('table'):
            latex_table = html_table_to_latex(table)
            table.replace_with(latex_table)

        for link in element.find_all('a', href=True):
            link_text = f"[{link.get_text(strip=True)}]({link['href']})"
            link.replace_with(link_text)

        for chem_tag in element.find_all('p'):
            latex_version = replace_sup_sub(str(chem_tag))
            chem_tag.replace_with(f' {latex_version} ')


def extract_and_process_text(element):
    if element:
        # Replace all <a> tags with their text content
        for link in element.find_all('a', href=True):
            link_text = link.get_text(strip=True)
            link.replace_with(link_text)

        # Process the rest of the content after link replacement
        process_content(element)

        return element.get_text(separator=" ", strip=True)
    return "None"


def extract_question_text(exercise):
    problem = exercise.find("div", {"data-type": "problem"})
    if problem:
        problem_container = problem.find("div", class_="os-problem-container")
        if problem_container:
            return extract_and_process_text(problem_container)
    return "None"

def extract_answer_text(soup, problem_id):
    solution_div = soup.find("div", {"id": f"{problem_id}-solution"})
    if solution_div:
        solution_container = solution_div.find("div", class_="os-solution-container")
        if solution_container:
            return extract_and_process_text(solution_container)
    return "None"

def extract_answer_image_link(soup, problem_id):
    solution_div = soup.find("div", {"id": f"{problem_id}-solution"})
    if solution_div:
        return extract_image_link(solution_div, soup)
    return None

def html_table_to_latex(table):
    num_columns = len(table.find('tr').find_all(['th', 'td']))
    column_spec = "|c" * num_columns + "|"
    latex = "\\begin{tabular}{" + column_spec + "}\n\\hline\n"
    for row in table.find_all('tr'):
        cells = row.find_all(['th', 'td'])
        latex += ' & '.join(cell.text.strip() for cell in cells) + " \\\\ \\hline\n"
    latex += "\\end{tabular}"
    return latex

def process_exercise(exercise, solution_soup, section_title, last_problem_statement):
    problem_statements = []
    current_element = exercise.find_previous_sibling()

    # Collect all preceding <p> tags until you hit a non-<p> or a header
    while current_element and current_element.name == 'p':
        problem_statements.append(extract_and_process_text(current_element))
        current_element = current_element.find_previous_sibling()

    # Reverse to maintain the narrative order as in the document
    problem_statements.reverse()
    complete_problem_statement = " ".join(problem_statements)

    # If the problem statement is empty, use the last known one
    if complete_problem_statement.strip() == "":
        complete_problem_statement = last_problem_statement

    # Continue with existing logic to handle images, questions, and answers
    image_link = extract_image_link(exercise, solution_soup) or "None"
    question = extract_question_text(exercise)
    problem_id = exercise.get('id', '')
    answer = extract_answer_text(solution_soup, problem_id) or "None"
    answer_image_link = extract_answer_image_link(solution_soup, problem_id) or "None"

    return {
        "Topic": section_title,
        "Problem Statement": html.unescape(complete_problem_statement),
        "Question": html.unescape(question),
        "Image Link": image_link,
        "Answer": html.unescape(answer),
        "Answer Image Link": answer_image_link
    }, complete_problem_statement  # Return the updated problem statement


def question_transcription(chapter, input_file_path, solution_file_path, out_path, version="review"):
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

    # Identify sections based on the version
    sections = soup.find_all("section", {"data-depth": "1"})
    title_tag = "h2"

    for section in sections:
        title_element = section.find(title_tag, {"data-type": "document-title"})
        process_content(title_element)
        section_title = title_element.get_text(separator=" ", strip=True) if title_element else "None"

        # Reset the problem statement at the start of a new section
        last_problem_statement = "None"

        exercises = section.find_all("div", {"data-type": "exercise"})

        for exercise in exercises:
            one_problem, last_problem_statement = process_exercise(exercise, solution_soup, section_title, last_problem_statement)
            questions_json.append(one_problem)
            print(one_problem)

    out_dir = os.path.dirname(out_path)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    with open(out_path, 'w', encoding='utf-8') as file:
        json.dump(questions_json, file, indent=4)



def transcribe_reviews(in_prefix, out_prefix, thing, chapter):
    # for i in np.arange(1, 34):
    #     chapter = round(i, 5)
    input_file_path = f'{in_prefix}/ch{i}/{thing}.html'
    solution_file_path = f'{in_prefix}/ch{i}/solutions.html'
    out_path = f'{out_prefix}/ch{i}/ch{chapter}_{thing}_transcribed.json'
    question_transcription(chapter, input_file_path, solution_file_path, out_path, 'review')

if __name__ == "__main__":

    dir = f'../Textbooks Scraped'
    textbook = 'Business Stats'

    chapter_exists = True
    i = 1

    while chapter_exists:
        in_prefix = f'{dir}/{textbook}/HTML'
        out_prefix = f'{dir}/{textbook}/Transcriptions'

        for j in ['practice', 'bringing-it-together-practice', 'homework', 'bringing-it-together-homework']:
            transcribe_reviews(in_prefix, out_prefix, j, i)  # Uncomment to transcribe reviews
        try:
            json_to_excel(dir, textbook, i)
        except:
            chapter_exists = False
        i += 1