// convertMathML.js
const { MathMLToLaTeX } = require('mathml-to-latex');

// Retrieve MathML input from command line arguments
const mathml = process.argv[2];

// Convert MathML to LaTeX
const latex = MathMLToLaTeX.convert(mathml);

// Output the result
console.log(latex);
