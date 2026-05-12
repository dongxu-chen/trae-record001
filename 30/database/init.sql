CREATE TABLE IF NOT EXISTS exams (
  id SERIAL PRIMARY KEY,
  title VARCHAR(255) NOT NULL,
  description TEXT,
  duration_minutes INTEGER NOT NULL,
  total_questions INTEGER NOT NULL,
  randomize_questions BOOLEAN DEFAULT true,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS questions (
  id SERIAL PRIMARY KEY,
  exam_id INTEGER NOT NULL REFERENCES exams(id) ON DELETE CASCADE,
  question_text TEXT NOT NULL,
  option_a VARCHAR(255) NOT NULL,
  option_b VARCHAR(255) NOT NULL,
  option_c VARCHAR(255) NOT NULL,
  option_d VARCHAR(255) NOT NULL,
  correct_answer VARCHAR(1) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS exam_results (
  id SERIAL PRIMARY KEY,
  exam_id INTEGER NOT NULL REFERENCES exams(id),
  student_name VARCHAR(100) NOT NULL,
  score INTEGER NOT NULL,
  passed BOOLEAN NOT NULL,
  total_questions INTEGER NOT NULL,
  correct_answers INTEGER NOT NULL,
  violation_count INTEGER DEFAULT 0,
  tab_switch_count INTEGER DEFAULT 0,
  copy_paste_count INTEGER DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(exam_id, student_name)
);

CREATE TABLE IF NOT EXISTS user_answers (
  id SERIAL PRIMARY KEY,
  result_id INTEGER NOT NULL REFERENCES exam_results(id) ON DELETE CASCADE,
  question_id INTEGER NOT NULL REFERENCES questions(id),
  user_answer VARCHAR(1) NOT NULL,
  is_correct BOOLEAN NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS proctor_events (
  id SERIAL PRIMARY KEY,
  exam_id INTEGER NOT NULL REFERENCES exams(id),
  student_name VARCHAR(100) NOT NULL,
  event_type VARCHAR(50) NOT NULL,
  event_data JSONB,
  severity VARCHAR(20) DEFAULT 'info',
  ip_address VARCHAR(45),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS proctor_snapshots (
  id SERIAL PRIMARY KEY,
  exam_id INTEGER NOT NULL REFERENCES exams(id),
  student_name VARCHAR(100) NOT NULL,
  file_path VARCHAR(500) NOT NULL,
  file_size INTEGER,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_proctor_events_exam ON proctor_events(exam_id);
CREATE INDEX IF NOT EXISTS idx_proctor_events_student ON proctor_events(student_name);
CREATE INDEX IF NOT EXISTS idx_proctor_events_type ON proctor_events(event_type);
CREATE INDEX IF NOT EXISTS idx_proctor_snapshots_exam ON proctor_snapshots(exam_id);
CREATE INDEX IF NOT EXISTS idx_proctor_snapshots_student ON proctor_snapshots(student_name);

INSERT INTO exams (title, description, duration_minutes, total_questions, randomize_questions, is_active)
VALUES 
('JavaScript 基础测试', '测试 JavaScript 基础知识，包括变量、函数、数组等概念', 30, 5, true, true),
('React 核心概念', '测试 React 核心概念，包括组件、状态管理、生命周期等', 45, 6, true, true);

INSERT INTO questions (exam_id, question_text, option_a, option_b, option_c, option_d, correct_answer)
VALUES 
(1, 'JavaScript 中哪个方法用于向数组末尾添加元素？', 'push()', 'pop()', 'shift()', 'unshift()', 'A'),
(1, '以下哪个不是 JavaScript 的基本数据类型？', 'string', 'number', 'array', 'boolean', 'C'),
(1, '在 JavaScript 中，typeof null 的结果是什么？', 'null', 'object', 'undefined', 'string', 'B'),
(1, '以下哪个方法会改变原数组？', 'map()', 'filter()', 'splice()', 'concat()', 'C'),
(1, 'JavaScript 中 const 声明的变量具有什么特性？', '可以重新赋值', '块级作用域', '函数作用域', '全局作用域', 'B');

INSERT INTO questions (exam_id, question_text, option_a, option_b, option_c, option_d, correct_answer)
VALUES 
(2, 'React 中用于管理组件内部状态的 Hook 是？', 'useEffect', 'useState', 'useContext', 'useRef', 'B'),
(2, 'React 组件的渲染方法返回什么？', '字符串', 'DOM 元素', 'React 元素', '数字', 'C'),
(2, '以下哪个不是 React 的生命周期方法？', 'componentDidMount', 'componentWillUpdate', 'componentWillReceiveProps', 'componentDidRender', 'D'),
(2, 'React 中使用什么来创建组件间的上下文？', 'Props', 'State', 'Context API', 'Redux', 'C'),
(2, '以下关于 React Hook 的说法哪个是正确的？', '可以在条件语句中调用', '可以在普通函数中调用', '必须在函数组件的顶层调用', '只能在类组件中使用', 'C'),
(2, 'React 中哪个方法用于处理副作用？', 'useState', 'useEffect', 'useReducer', 'useCallback', 'B');
