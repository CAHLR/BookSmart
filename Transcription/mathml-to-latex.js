const { MathMLToLaTeX } = require('mathml-to-latex');

const mathml = process.argv[2];

const latex = MathMLToLaTeX.convert(mathml);

console.log(latex);
