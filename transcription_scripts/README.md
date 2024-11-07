## Usage

Package requirements:

```
pip install beautifulsoup4 numpy
```

All transcription scripts are quite similar to one another, with slight changes between each to accomodate for the differences between textbooks for different textbooks.

Below is each transcription script along with the textbooks it can transcribe:

`science_humanities.py`:
- Business Ethics
- Business Law I Essentials
- Introduction to Intellectual Property
- Principles of Accounting, Volume 1: Financial Accounting
- Principles of Accounting, Volume 2: Managerial Accounting
- Principles of Economics 3e
- Principles of Macroeconomics 3e
- Principles of Microeconomics 3e
- U.S. History
- Chemistry 2e
- Chemistry: Atoms First 2e
- College Physics 2e
- College Physics For AP® Courses 2e
- Microbiology
- University Physics Volume 1
- University Physics Volume 2
- University Physics Volume 3
- American Government 3e
- Introduction to Sociology 3e

`algebra.py`:
- Algebra and Trigonometry 2e
- College Algebra 2e
- College Algebra 2e with Corequisite Support
- Elementary Algebra 2e
- Intermediate Algebra 2e
- Prealgebra 2e
- Precalculus 2e

`calculus.py`:
- Calculus Volume 1
- Calculus Volume 2
- Calculus Volume 3

`statistics.py`:
- Introductory Business Statistics 2e
- Introductory Statistics 2e
- Statistics

`python.py`:
- Introduction to Python Programming


At the bottom of the `science_humanities.py` file, you will see a section like this:

```python
if __name__ == "__main__":
  dir = f'../Textbooks Scraped'
  textbook = 'Accounting V1'
  
  
  exercise_types = [
      'review-exercises'
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
  
  chapter_exists = True
  i = 1
  
  while chapter_exists:
      in_prefix = f'{dir}/{textbook}/HTML'
      out_prefix = f'{dir}/{textbook}/Transcriptions'
  
      for j in exercise_types:
          transcribe_reviews(in_prefix, out_prefix, j, i) 
      try:
          json_to_excel(dir, textbook, i)
      except:
          chapter_exists = False
      i += 1
```

This script assumes a file structure that looks like this:

```
root/
├── transcription_scripts/
│   ├── algebra.py
│   ├── science_humanities.py
│   ...
│   ├── json_to_excel.py
│   ├── convert_mathml_to_latex.py
│   ├── mathml-to-latex.js
├── Textbooks Scraped/
│   ├── Accounting V1/
│   │   └── HTML
│   ├── Accounting V2/
│   │   └── HTML
│   ...
```

Either modify your structure to match this, or modify the `dir`, `in_prefix`, and `out_prefix` variables in the section shown. 

Then, simply replace the `textbook` variable with your desired textbook. Ensure that the textbook name chosen is the same as one of the textbooks stored in the textbook directory. Ensure that `json_to_excel.py`, `convert_mathml_to_latex.py`, `mathml-to-latex.js` are in the same directory as the transcription scripts. Do not edit any other variables, including `exercise_types`, `chapter_exists`, etc.

All the other scripts have a similar section like this at the bottom. For each one, only edit the `textbook` variable (and file paths if necessary).

Run the script, and it should output both a JSON and Excel transcription of each chapter in the textbook in a separate directory of your textbook. It will also print each exercise it transcribes.

## How it Works

Each script first iterates over each chapter of each textbook and determines which HTML files to looks at based on the textbook type. For instance, the `algebra.py` script has the most complicated version of this, with 3 different functions, `transcribe_reviews`, `transcribe_practice_tests`, and `transcribe_lessons` for processing and retrieving the relevant file types that all use different formats. 
  

