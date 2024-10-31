import os
import re
import json
import numpy as np
from bs4 import BeautifulSoup
import html
from convert_mathml_to_latex import *
from json_to_excel import *


def replace_dashes(text):
    # Define Unicode and HTML expressions for dashes
    dash_variants = [
        '\u2012',  # Figure dash
        '\u2013',  # En dash
        '\u2014',  # Em dash
        '\u2015',  # Horizontal bar
        '\u2212',  # Minus sign
        '&ndash;',  # HTML en dash
        '&mdash;',  # HTML em dash
        '&minus;',  # HTML minus
        '-',  # Hyphen (for completeness)
    ]

    # Create a regular expression pattern that matches any of the dash variants
    dash_pattern = '|'.join(map(re.escape, dash_variants))

    # Replace all dash variants with the standard minus sign
    return re.sub(dash_pattern, '-', text)

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


# def process_content(element):
#     if element:
#         for math_tag in element.find_all('math'):
#             latex_version = convert_mathml_to_latex(str(math_tag))
#             math_tag.replace_with(f' $${latex_version}$$ ')
#
#         for table in element.find_all('table'):
#             latex_table = html_table_to_latex(table)
#             table.replace_with(latex_table)
#
#         for link in element.find_all('a', href=True):
#             link_text = f"[{link.get_text(strip=True)}]({link['href']})"
#             link.replace_with(link_text)


def process_content(element):
    if element:
        # Strip away the link but keep the text for titles
        for link in element.find_all('a', href=True):
            link_text = link.get_text(strip=True)  # Get only the text from the link
            link.replace_with(link_text)  # Replace the <a> tag with just the text

        for math_tag in element.find_all('math'):
            latex_version = convert_mathml_to_latex(str(math_tag))
            math_tag.replace_with(f' $${latex_version}$$ ')

        for table in element.find_all('table'):
            latex_table = html_table_to_latex(table)
            table.replace_with(latex_table)


def extract_and_process_text(element):
    if element:
        for link in element.find_all('a', href=True):
            link_text = link.get_text(strip=True)
            link.replace_with(link_text)

        process_content(element)

        return element.get_text(separator=" ", strip=True)
    return "None"


# def extract_question_text(exercise):
#     problem_container = exercise.find("div", {"class": "os-problem-container"})
#
#     if problem_container:
#         # Extract the question stem
#         question_stem = problem_container.find("div", {"data-type": "question-stem"})
#         question_text = extract_and_process_text(question_stem) if question_stem else "None"
#
#         # Process the multiple-choice options (forcing capital letters)
#         answer_list = problem_container.find("ol", {"data-type": "question-answers"})
#         if answer_list:
#             choices = answer_list.find_all("li", {"data-type": "question-answer"})
#             options_text = []
#             for idx, choice in enumerate(choices):
#                 # Extract the answer content and prepend with "A.", "B.", etc.
#                 answer_content = choice.find("div", {"data-type": "answer-content"})
#                 if answer_content:
#                     option_text = f'{chr(65 + idx)}. {extract_and_process_text(answer_content)}'
#                     options_text.append(option_text)
#
#             # Combine the question and the options into one string
#             return f"{question_text} {' '.join(options_text)}"
#
#     return "None"

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


def extract_question_text(exercise):
    problem_container = exercise.find("div", {"class": "os-problem-container"})

    if problem_container:
        # Extract the question stem
        question_stem = problem_container.find("div", {"data-type": "question-stem"})
        question_text = extract_and_process_text(question_stem) if question_stem else "None"

        # Process the multiple-choice options (forcing capital letters)
        answer_list = problem_container.find("ol", {"data-type": "question-answers"})
        if answer_list:
            choices = answer_list.find_all("li", {"data-type": "question-answer"})
            options_text = []
            for idx, choice in enumerate(choices):
                # Extract the answer content and prepend with "A.", "B.", etc.
                answer_content = choice.find("div", {"data-type": "answer-content"})
                if answer_content:
                    option_text = f'{chr(65 + idx)}. {extract_and_process_text(answer_content)}'
                    options_text.append(option_text)

            # Combine the question and the options into one string
            return f"{question_text} {' '.join(options_text)}"

    return "None"


def process_exercise(exercise, solution_soup, section_title):
    problem_statements = []

    # Adjust to handle the 'injected-exercise' HTML structure
    sibling = exercise.find_previous_sibling("p")
    while sibling:
        problem_statements.insert(0, extract_and_process_text(sibling))
        sibling = sibling.find_previous_sibling("p")

    if problem_statements:
        problem_statement = ' '.join(problem_statements)
        process_exercise.current_problem_statement = problem_statement
    else:
        problem_statement = getattr(process_exercise, 'current_problem_statement', "None")

    image_link = extract_image_link(exercise, solution_soup) or "None"

    # Extract the question text (this handles multiple choice)
    question = extract_question_text(exercise)

    # Get the problem ID for the solution lookup
    problem_id = exercise.get('id', '')
    answer = extract_answer_text(solution_soup, problem_id) or "None"
    answer_image_link = extract_answer_image_link(solution_soup, problem_id) or "None"

    return {
        "Topic": replace_dashes(html.unescape(section_title)),
        "Problem Statement": replace_dashes(html.unescape(problem_statement)),
        "Question": replace_dashes(html.unescape(question)),
        "Image Link": replace_dashes(html.unescape(image_link)),
        "Answer": replace_dashes(html.unescape(answer)),
        "Answer Image Link": replace_dashes(html.unescape(answer_image_link))
    }


def question_transcription(chapter, input_file_path, solution_file_path, out_path, version="review"):
    try:
        with open(input_file_path, "r", encoding="utf-8") as file:
            html_content = file.read()
    except Exception as e:
        print(f"Failed to read the file due to: {str(e)}")
        return

    soup = BeautifulSoup(html_content, "html.parser")

    try:
        with open(solution_file_path, "r", encoding="utf-8") as file:
            solution_html_content = file.read()
        solution_soup = BeautifulSoup(solution_html_content, "html.parser")
    except Exception as e:
        print(f"Failed to read the solution file due to: {str(e)}")
        return

    questions_json = []

    # Adjusted to find injected exercises and regular exercises
    if version == "lesson":
        # Handle injected exercises in "lesson" version
        sections = soup.find_all("div", {"data-type": "injected-exercise"})
        title_tag = "h3"
    elif version == "try it":
        # Handle exercises under the "try it" version
        sections = soup.find_all("div", {"data-type": "note"}, class_=lambda x: x and "try ui-has-child-title" in x)
        title_tag = "h2"
    else:
        # General case for other sections
        sections = soup.find_all("section", {"data-depth": "1"})
        title_tag = "h2"

    for section in sections:
        # Adjust title handling for injected exercises and regular sections
        if version == "try it":
            previous_section = section.find_previous("section", {"data-depth": "1"})
            if previous_section:
                title_element = previous_section.find(title_tag, {"data-type": "title"})
            else:
                title_element = None
        else:
            title_element = section.find(title_tag, {"data-type": "title"})

        if title_element:
            process_content(title_element)
            section_title = title_element.get_text(separator=" ", strip=True)
        else:
            section_title = "None"

        # Extract all exercises (injected or regular)
        exercises = section.find_all("div", {"data-type": "exercise"}) + section.find_all("div", {
            "data-type": "exercise-question"})

        for exercise in exercises:
            one_problem = process_exercise(exercise, solution_soup, section_title)
            questions_json.append(one_problem)
            print(one_problem)

    out_dir = os.path.dirname(out_path)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    with open(out_path, 'w', encoding='utf-8') as file:
        json.dump(questions_json, file, indent=4)


def transcribe_lessons(in_prefix, out_prefix, chapter):
    for i in np.arange(chapter, chapter+1, 0.1):
        chapter = round(i, 5)
        input_file_path = f'{in_prefix}/ch{str(chapter).split(".")[0]}/{chapter}.html'
        solution_file_path = f'{in_prefix}/ch{str(chapter).split(".")[0]}/answer_key.html'
        lesson_out_path = f'{out_prefix}/ch{str(chapter).split(".")[0]}/ch{chapter}-lesson.json'
        try_it_out_path = f'{out_prefix}/ch{str(chapter).split(".")[0]}/ch{chapter}-try-it.json'
        question_transcription(chapter, input_file_path, solution_file_path,lesson_out_path, 'lesson')
        question_transcription(chapter, input_file_path, solution_file_path, try_it_out_path, 'try it')

if __name__ == "__main__":

    dir = f'../Textbooks Scraped'
    textbook = 'Python'

    chapter_exists = True
    i = 1

    while chapter_exists:
        in_prefix = f'{dir}/{textbook}/HTML'
        out_prefix = f'{dir}/{textbook}/Transcriptions'

        transcribe_lessons(in_prefix, out_prefix, i)      # To transcribe lessons
        # transcribe_reviews(in_prefix, out_prefix, i)    # Uncomment to transcribe reviews
        # transcribe_practice_tests(in_prefix, out_prefix, i)  # Uncomment to transcribe practice tests
        try:
            json_to_excel(dir, textbook, i)
        except:
            chapter_exists = False
        i += 1
