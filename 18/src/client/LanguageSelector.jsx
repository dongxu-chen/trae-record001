import { useState, useRef, useEffect } from 'react';

const LANGUAGES = [
  {
    value: 'javascript',
    label: 'JavaScript',
    icon: '🟨',
    version: 'Node.js 18',
    defaultCode: `console.log('Hello, JavaScript!');

const numbers = [1, 2, 3, 4, 5];
const doubled = numbers.map(n => n * 2);
console.log('Original:', numbers);
console.log('Doubled:', doubled);

const user = {
  name: 'Code Sandbox',
  language: 'JavaScript',
  timestamp: new Date().toISOString()
};
console.log('User:', user);
`
  },
  {
    value: 'python',
    label: 'Python',
    icon: '🐍',
    version: 'Python 3.11',
    defaultCode: `print('Hello, Python!')

numbers = [1, 2, 3, 4, 5]
doubled = [n * 2 for n in numbers]
print('Original:', numbers)
print('Doubled:', doubled)

user = {
    'name': 'Code Sandbox',
    'language': 'Python',
    'timestamp': __import__('datetime').datetime.utcnow().isoformat()
}
print('User:', user)
`
  },
  {
    value: 'java',
    label: 'Java',
    icon: '☕',
    version: 'OpenJDK 17',
    defaultCode: `System.out.println("Hello, Java!");

int[] numbers = {1, 2, 3, 4, 5};
int[] doubled = new int[numbers.length];
for (int i = 0; i < numbers.length; i++) {
    doubled[i] = numbers[i] * 2;
}

log("log", "Original:", java.util.Arrays.toString(numbers));
log("log", "Doubled:", java.util.Arrays.toString(doubled));

java.util.Map<String, Object> user = new java.util.HashMap<>();
user.put("name", "Code Sandbox");
user.put("language", "Java");
user.put("timestamp", java.time.Instant.now().toString());
log("log", "User:", user);
`
  },
  {
    value: 'go',
    label: 'Go',
    icon: '🔵',
    version: 'Go 1.21',
    defaultCode: `captureOutput("log", "Hello, Go!")

numbers := []int{1, 2, 3, 4, 5}
doubled := make([]int, len(numbers))
for i, n := range numbers {
    doubled[i] = n * 2
}

captureOutput("log", "Original:", numbers)
captureOutput("log", "Doubled:", doubled)

type User struct {
    Name      string ` + "`json:\"name\"`" + `
    Language  string ` + "`json:\"language\"`" + `
    Timestamp string ` + "`json:\"timestamp\"`" + `
}

user := User{
    Name:      "Code Sandbox",
    Language:  "Go",
    Timestamp: time.Now().UTC().Format(time.RFC3339),
}
captureOutput("log", "User:", user)
`
  }
];

function LanguageSelector({ value, onChange, disabled }) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);
  const currentLang = LANGUAGES.find(l => l.value === value) || LANGUAGES[0];

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelect = (language) => {
    if (language.value !== value) {
      onChange(language.value, language.defaultCode);
    }
    setIsOpen(false);
  };

  return (
    <div className="language-selector" ref={dropdownRef}>
      <button
        className="language-trigger"
        onClick={() => !disabled && setIsOpen(!isOpen)}
        disabled={disabled}
      >
        <span className="language-icon">{currentLang.icon}</span>
        <span className="language-name">{currentLang.label}</span>
        <span className={`dropdown-arrow ${isOpen ? 'open' : ''}`}>▼</span>
      </button>

      {isOpen && (
        <div className="language-dropdown">
          {LANGUAGES.map((lang) => (
            <div
              key={lang.value}
              className={`language-option ${lang.value === value ? 'selected' : ''}`}
              onClick={() => handleSelect(lang)}
            >
              <span className="language-icon">{lang.icon}</span>
              <div className="language-info">
                <span className="language-label">{lang.label}</span>
                <span className="language-version">{lang.version}</span>
              </div>
              {lang.value === value && (
                <span className="check-mark">✓</span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default LanguageSelector;
export { LANGUAGES };
