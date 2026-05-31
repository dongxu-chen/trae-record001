import type { NamingStyle } from '../../shared/types';

export function toCamelCase(words: string[]): string {
  if (words.length === 0) return '';
  const [first, ...rest] = words;
  return first.toLowerCase() + rest.map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()).join('');
}

export function toSnakeCase(words: string[]): string {
  return words.map(w => w.toLowerCase()).join('_');
}

export function toPascalCase(words: string[]): string {
  return words.map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()).join('');
}

export function toKebabCase(words: string[]): string {
  return words.map(w => w.toLowerCase()).join('-');
}

export function toScreamingSnakeCase(words: string[]): string {
  return words.map(w => w.toUpperCase()).join('_');
}

export function convertStyle(words: string[], style: NamingStyle): string {
  switch (style) {
    case 'camelCase': return toCamelCase(words);
    case 'snake_case': return toSnakeCase(words);
    case 'PascalCase': return toPascalCase(words);
    case 'kebab-case': return toKebabCase(words);
    case 'SCREAMING_SNAKE_CASE': return toScreamingSnakeCase(words);
  }
}

export function parseToWords(input: string): string[] {
  let processed = input;
  processed = processed.replace(/[-_]/g, ' ');
  processed = processed.replace(/([a-z])([A-Z])/g, '$1 $2');
  processed = processed.replace(/([A-Z]+)([A-Z][a-z])/g, '$1 $2');
  processed = processed.toLowerCase();
  
  const words = processed.split(/\s+/)
    .map(w => w.trim())
    .filter(w => w.length > 0 && /^[a-z]+$/.test(w));
  
  return words;
}

export function detectNamingStyle(name: string): NamingStyle | null {
  if (/^[A-Z][A-Z0-9]*(_[A-Z0-9]+)*$/.test(name)) {
    return 'SCREAMING_SNAKE_CASE';
  }
  if (/^[a-z][a-z0-9]*(_[a-z0-9]+)*$/.test(name)) {
    return 'snake_case';
  }
  if (/^[a-z][a-zA-Z0-9]*$/.test(name) && /[A-Z]/.test(name)) {
    return 'camelCase';
  }
  if (/^[A-Z][a-zA-Z0-9]*$/.test(name)) {
    return 'PascalCase';
  }
  if (/^[a-z][a-z0-9]*(-[a-z0-9]+)*$/.test(name)) {
    return 'kebab-case';
  }
  return null;
}
