export const LANGUAGE_OPTIONS = [
  { value: 'plaintext', label: 'Plain Text' },
  { value: 'javascript', label: 'JavaScript' },
  { value: 'typescript', label: 'TypeScript' },
  { value: 'python', label: 'Python' },
  { value: 'java', label: 'Java' },
  { value: 'csharp', label: 'C#' },
  { value: 'cpp', label: 'C++' },
  { value: 'go', label: 'Go' },
  { value: 'rust', label: 'Rust' },
  { value: 'ruby', label: 'Ruby' },
  { value: 'php', label: 'PHP' },
  { value: 'swift', label: 'Swift' },
  { value: 'kotlin', label: 'Kotlin' },
  { value: 'sql', label: 'SQL' },
  { value: 'html', label: 'HTML' },
  { value: 'css', label: 'CSS' },
  { value: 'json', label: 'JSON' },
  { value: 'yaml', label: 'YAML' },
  { value: 'xml', label: 'XML' },
  { value: 'markdown', label: 'Markdown' },
  { value: 'shell', label: 'Shell' },
  { value: 'dockerfile', label: 'Dockerfile' },
] as const

export const FILE_EXTENSION_MAP: Record<string, string> = {
  js: 'javascript',
  jsx: 'javascript',
  ts: 'typescript',
  tsx: 'typescript',
  py: 'python',
  java: 'java',
  cs: 'csharp',
  cpp: 'cpp',
  c: 'cpp',
  h: 'cpp',
  go: 'go',
  rs: 'rust',
  rb: 'ruby',
  php: 'php',
  swift: 'swift',
  kt: 'kotlin',
  sql: 'sql',
  html: 'html',
  htm: 'html',
  css: 'css',
  scss: 'css',
  less: 'css',
  json: 'json',
  yaml: 'yaml',
  yml: 'yaml',
  xml: 'xml',
  md: 'markdown',
  sh: 'shell',
  bash: 'shell',
  dockerfile: 'dockerfile',
}

export function getLanguageFromPath(filePath: string): string {
  const ext = filePath.split('.').pop()?.toLowerCase() || ''
  return FILE_EXTENSION_MAP[ext] || 'plaintext'
}

export const SAMPLE_OLD_CODE = `function greet(name) {
  console.log("Hello, " + name);
  return true;
}

function calculateSum(a, b) {
  return a + b;
}

function processData(data) {
  const result = data.filter(item => item.active);
  console.log("Processing data...");
  return result;
}

class User {
  constructor(name, email) {
    this.name = name;
    this.email = email;
  }

  getInfo() {
    return this.name + " (" + this.email + ")";
  }
}`

export const SAMPLE_NEW_CODE = `function greet(name, greeting = "Hello") {
  console.log(greeting + ", " + name + "!");
  return greeting;
}

function calculateSum(a, b, c = 0) {
  return a + b + c;
}

function calculateProduct(...numbers) {
  return numbers.reduce((acc, n) => acc * n, 1);
}

function processData(data, options = {}) {
  const { verbose = false } = options;
  const result = data.filter(item => item.active && item.verified);
  if (verbose) {
    console.log("Processing data...");
    console.log("Found " + result.length + " items");
  }
  return result;
}

class User {
  constructor(name, email, role = "viewer") {
    this.name = name;
    this.email = email;
    this.role = role;
  }

  getInfo() {
    return this.name + " (" + this.email + ") [" + this.role + "]";
  }

  hasPermission(action) {
    return this.role === "admin" || action === "read";
  }
}`
