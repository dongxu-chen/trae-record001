import * as prettier from 'prettier/standalone';
import * as prettierBabel from 'prettier/plugins/babel';
import * as prettierEstree from 'prettier/plugins/estree';
import * as prettierTypescript from 'prettier/plugins/typescript';

export async function formatTypeScript(code: string): Promise<string> {
  try {
    const formatted = await prettier.format(code, {
      parser: 'typescript',
      plugins: [prettierBabel, prettierEstree, prettierTypescript],
      semi: true,
      singleQuote: true,
      trailingComma: 'es5',
      tabWidth: 2,
      printWidth: 80,
      arrowParens: 'always',
      endOfLine: 'lf',
    });
    return formatted;
  } catch (error) {
    console.error('TypeScript formatting error:', error);
    return code;
  }
}

export async function formatJava(code: string): Promise<string> {
  try {
    const formatted = await prettier.format(code, {
      parser: 'babel',
      plugins: [prettierBabel, prettierEstree],
      semi: true,
      singleQuote: false,
      tabWidth: 4,
      printWidth: 100,
      arrowParens: 'always',
      endOfLine: 'lf',
    });
    return formatted;
  } catch (error) {
    console.error('Java formatting error:', error);
    return code;
  }
}

export function formatJavaSimple(code: string): string {
  let result = code;
  let indentLevel = 0;
  const lines = result.split('\n');
  const formattedLines: string[] = [];

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) {
      formattedLines.push('');
      continue;
    }

    if (trimmed.startsWith('}') || trimmed.startsWith(')') || trimmed.startsWith(']')) {
      indentLevel = Math.max(0, indentLevel - 1);
    }

    const indent = '    '.repeat(indentLevel);
    formattedLines.push(indent + trimmed);

    const openBraces = (trimmed.match(/{/g) || []).length;
    const closeBraces = (trimmed.match(/}/g) || []).length;
    indentLevel += openBraces - closeBraces;

    if (trimmed.endsWith('{') && !trimmed.startsWith('}')) {
      indentLevel = Math.max(0, indentLevel);
    }
  }

  return formattedLines.join('\n');
}
