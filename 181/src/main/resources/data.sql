INSERT INTO skills (name, description) VALUES
('医生', '具备执业医师资格'),
('护士', '注册护士资格'),
('药师', '药学专业资格'),
('检验师', '医学检验资格'),
('影像师', '医学影像资格');

INSERT INTO shift_types (code, name, start_time, end_time, duration_hours, color, is_active) VALUES
('MORNING', '早班', '08:00:00', '16:00:00', 8, '#4CAF50', 1),
('AFTERNOON', '中班', '14:00:00', '22:00:00', 8, '#FF9800', 1),
('NIGHT', '夜班', '22:00:00', '06:00:00', 8, '#9C27B0', 1),
('DAY', '白班', '09:00:00', '17:00:00', 8, '#2196F3', 1);

INSERT INTO employees (name, employee_no, max_weekly_hours, max_daily_hours, min_weekly_hours, max_consecutive_days, is_active) VALUES
('张三', 'EMP001', 40, 8, 20, 5, 1),
('李四', 'EMP002', 40, 8, 20, 5, 1),
('王五', 'EMP003', 40, 8, 20, 5, 1),
('赵六', 'EMP004', 40, 8, 20, 5, 1),
('钱七', 'EMP005', 40, 8, 20, 5, 1),
('孙八', 'EMP006', 40, 8, 20, 5, 1),
('周九', 'EMP007', 40, 8, 20, 5, 1),
('吴十', 'EMP008', 40, 8, 20, 5, 1);

INSERT INTO employee_skills (employee_id, skill_id) VALUES
(1, 1), (1, 2),
(2, 2),
(3, 2), (3, 3),
(4, 2),
(5, 4),
(6, 2),
(7, 5),
(8, 2);

INSERT INTO employee_preferred_shifts (employee_id, shift_type) VALUES
(1, 'MORNING'), (1, 'DAY'),
(2, 'AFTERNOON'),
(3, 'MORNING'),
(4, 'NIGHT'),
(5, 'DAY'),
(6, 'AFTERNOON'),
(7, 'MORNING'),
(8, 'MORNING');

INSERT INTO employee_unwanted_shifts (employee_id, shift_type) VALUES
(1, 'NIGHT'),
(2, 'NIGHT'),
(4, 'MORNING'),
(6, 'NIGHT');
