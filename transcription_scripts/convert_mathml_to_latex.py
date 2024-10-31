import subprocess

def convert_mathml_to_latex(mathml):
    try:
        # Attempt 1: Use plurimath
        result = subprocess.run(
            ['plurimath', 'convert', '-i', mathml, '-f', 'mathml', '-t', 'latex'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,  # Capture errors
            text=True
        )

        if result.returncode == 0:
            return result.stdout.strip()
        else:
            error_message = result.stderr.strip()
            print(f"Plurimath error: {error_message}")

    except Exception as e:
        print(f"Plurimath exception: {str(e)}")

    print("Falling back to Node.js conversion...")

    try:
        # Attempt 2: Use Node.js script
        result = subprocess.run(
            ['node', 'mathml-to-latex.js', mathml],
            capture_output=True,
            text=True,
            check=True
        )

        output = result.stdout.strip()
        return output[:len(output) // 2].strip()

    except subprocess.CalledProcessError as e:
        print(f"Node.js error: {e.stderr}")
        return None

    except Exception as e:
        print(f"Node.js exception: {str(e)}")
        return None