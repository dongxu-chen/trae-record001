import numpy as np
import pandas as pd
from datetime import datetime, timedelta


np.random.seed(42)

NUM_EMPLOYEES = 200
START_DATE = datetime(2024, 1, 1)
END_DATE = datetime(2025, 12, 31)
DAYS = (END_DATE - START_DATE).days + 1

DEPARTMENTS = ['工程部', '销售部', '市场部', '人力资源部', '财务部', '产品部', '客服部']
ROLES = ['高级工程师', '中级工程师', '初级工程师', '销售经理', '销售代表',
         '市场专员', 'HR专员', '财务分析师', '产品经理', '客服代表']
LEVELS = ['P4', 'P5', 'P6', 'P7', 'M1', 'M2']

HOLIDAYS_2024 = [
    '2024-01-01', '2024-02-10', '2024-02-11', '2024-02-12', '2024-02-13', '2024-02-14',
    '2024-02-15', '2024-02-16', '2024-02-17', '2024-04-04', '2024-04-05', '2024-04-06',
    '2024-05-01', '2024-05-02', '2024-05-03', '2024-05-04', '2024-05-05',
    '2024-06-10', '2024-09-15', '2024-09-16', '2024-09-17',
    '2024-10-01', '2024-10-02', '2024-10-03', '2024-10-04', '2024-10-05',
    '2024-10-06', '2024-10-07',
]

HOLIDAYS_2025 = [
    '2025-01-01', '2025-01-28', '2025-01-29', '2025-01-30', '2025-01-31',
    '2025-02-01', '2025-02-02', '2025-02-03', '2025-02-04',
    '2025-04-04', '2025-04-05', '2025-04-06',
    '2025-05-01', '2025-05-02', '2025-05-03', '2025-05-04', '2025-05-05',
    '2025-05-31', '2025-06-01', '2025-06-02',
    '2025-10-01', '2025-10-02', '2025-10-03', '2025-10-04', '2025-10-05',
    '2025-10-06', '2025-10-07',
]

HOLIDAYS = set(HOLIDAYS_2024 + HOLIDAYS_2025)


def is_workday(date):
    date_str = date.strftime('%Y-%m-%d')
    return date.weekday() < 5 and date_str not in HOLIDAYS


def rnd(x, n=0):
    return np.round(x, n)


def generate_employee_base():
    data = []
    for i in range(NUM_EMPLOYEES):
        emp_id = f'EMP{str(i + 1).zfill(4)}'
        dept = np.random.choice(DEPARTMENTS)
        role = np.random.choice(ROLES)
        level = np.random.choice(LEVELS)
        age = int(np.random.normal(32, 6))
        age = max(22, min(55, age))
        tenure = float(rnd(np.random.exponential(2.5) + 0.3, 1))
        salary = int(rnd(np.random.lognormal(mean=11, sigma=0.4), -2))
        hire_date = START_DATE - timedelta(days=int(tenure * 365))

        commute_distance = float(rnd(max(0.5, np.random.lognormal(2.0, 0.8)), 1))

        attrition_base = float(np.random.beta(2, 2.5))
        if tenure < 1:
            attrition_base += 0.25
        if tenure > 5:
            attrition_base -= 0.05
        if dept in ['销售部', '客服部']:
            attrition_base += 0.2
        if level in ['P4', 'P5']:
            attrition_base += 0.15

        attrition_base = max(0.01, min(0.95, attrition_base))

        data.append({
            'employee_id': emp_id,
            'department': dept,
            'role': role,
            'level': level,
            'age': age,
            'tenure_years': tenure,
            'salary': salary,
            'commute_distance': commute_distance,
            'hire_date': hire_date,
            'attrition_base': attrition_base,
        })
    return pd.DataFrame(data)


def generate_attendance(df_employees):
    records = []
    max_commute = df_employees['commute_distance'].max()

    for _, emp in df_employees.iterrows():
        emp_id = emp['employee_id']
        base = emp['attrition_base']
        commute = emp['commute_distance']

        commute_factor = commute / max_commute
        commute_late_bonus = commute_factor * 0.12

        for day_offset in range(DAYS):
            date = START_DATE + timedelta(days=day_offset)
            if not is_workday(date):
                continue

            weather_effect = np.random.choice([0, 0.05, 0.1], p=[0.7, 0.2, 0.1])

            late_prob = 0.03 + base * 0.12 + commute_late_bonus + weather_effect
            absent_prob = 0.02 + base * 0.10
            overtime_prob = 0.15 + base * 0.1 * np.random.randn()
            overtime_prob = max(0.0, min(0.7, overtime_prob))

            status = '正常'
            if np.random.random() < absent_prob:
                status = '缺勤'
            elif np.random.random() < late_prob:
                status = '迟到'

            overtime_hours = 0.0
            if status == '正常' and np.random.random() < overtime_prob:
                overtime_hours = float(rnd(np.random.exponential(1.5), 1))

            work_hours = 8 + overtime_hours
            if status == '迟到':
                work_hours -= np.random.uniform(0.5, 2)

            records.append({
                'employee_id': emp_id,
                'date': date,
                'status': status,
                'overtime_hours': overtime_hours,
                'work_hours': float(rnd(max(0, work_hours), 1)),
            })
    return pd.DataFrame(records)


def generate_email_data(df_employees):
    records = []
    for _, emp in df_employees.iterrows():
        emp_id = emp['employee_id']
        base = emp['attrition_base']

        internal_base = max(1, int(np.random.normal(12, 4) - base * 8))
        external_base = max(0, int(np.random.normal(5, 2) - base * 3))

        for day_offset in range(DAYS):
            date = START_DATE + timedelta(days=day_offset)
            if not is_workday(date):
                continue

            is_week_before_holiday = False
            for i in range(1, min(5, DAYS - day_offset)):
                future_date = START_DATE + timedelta(days=day_offset + i)
                if not is_workday(future_date):
                    is_week_before_holiday = True
                    break

            holiday_factor = 0.7 if is_week_before_holiday else 1.0

            internal = max(0, int(np.random.normal(internal_base * holiday_factor, 3)))
            external = max(0, int(np.random.normal(external_base * holiday_factor, 2)))
            total = internal + external

            response_base = 0.5 + base * 1.0
            if is_week_before_holiday:
                response_base += 0.5

            response_hours = float(rnd(np.random.lognormal(response_base, 0.6), 1))

            records.append({
                'employee_id': emp_id,
                'date': date,
                'internal_emails': internal,
                'external_emails': external,
                'total_emails': total,
                'avg_response_hours': response_hours,
                'is_pre_holiday': is_week_before_holiday,
            })
    return pd.DataFrame(records)


def generate_task_data(df_employees):
    records = []
    for _, emp in df_employees.iterrows():
        emp_id = emp['employee_id']
        base = emp['attrition_base']
        dept = emp['department']

        tasks_per_week = {
            '工程部': 8, '销售部': 10, '市场部': 7, '人力资源部': 6,
            '财务部': 5, '产品部': 9, '客服部': 15
        }.get(dept, 7)

        weeks = DAYS // 7
        for week in range(weeks):
            week_start = START_DATE + timedelta(days=week * 7)
            week_end = week_start + timedelta(days=6)

            num_tasks = max(1, int(np.random.normal(tasks_per_week, 2)))
            completed = max(0, int(num_tasks * (0.85 - base * 0.35 + np.random.normal(0, 0.05))))
            completed = min(num_tasks, completed)

            on_time = max(0, int(completed * (0.9 - base * 0.25 + np.random.normal(0, 0.05))))
            on_time = min(completed, on_time)

            avg_hours = float(rnd(np.random.normal(6 + base * 2, 1), 1))

            records.append({
                'employee_id': emp_id,
                'week_start': week_start,
                'week_end': week_end,
                'total_tasks': num_tasks,
                'completed_tasks': completed,
                'on_time_tasks': on_time,
                'completion_rate': float(rnd(completed / num_tasks, 3)),
                'on_time_rate': float(rnd(on_time / max(1, completed), 3)),
                'avg_task_hours': max(0.5, avg_hours),
            })
    return pd.DataFrame(records)


def generate_satisfaction_surveys(df_employees):
    records = []
    survey_dates = [
        datetime(2024, 3, 1), datetime(2024, 6, 1),
        datetime(2024, 9, 1), datetime(2024, 12, 1),
        datetime(2025, 3, 1), datetime(2025, 6, 1),
        datetime(2025, 9, 1), datetime(2025, 12, 1),
    ]

    for _, emp in df_employees.iterrows():
        emp_id = emp['employee_id']
        base = emp['attrition_base']

        for sdate in survey_dates:
            if sdate < emp['hire_date']:
                continue

            time_factor = (sdate - START_DATE).days / DAYS
            drift = base * time_factor * 0.3

            s1 = int(np.clip(np.round(np.random.normal(4.0 - base * 1.5 - drift, 0.7)), 1, 5))
            s2 = int(np.clip(np.round(np.random.normal(3.8 - base * 1.2 - drift, 0.8)), 1, 5))
            s3 = int(np.clip(np.round(np.random.normal(3.6 - base * 1.0 - drift, 0.9)), 1, 5))
            s4 = int(np.clip(np.round(np.random.normal(3.5 - base * 1.3 - drift, 0.9)), 1, 5))
            s5 = int(np.clip(np.round(np.random.normal(3.3 - base * 1.1 - drift, 0.8)), 1, 5))

            overall = float(rnd(np.mean([s1, s2, s3, s4, s5]), 2))

            records.append({
                'employee_id': emp_id,
                'survey_date': sdate,
                'satisfaction': s1,
                'work_life_balance': s2,
                'leadership': s3,
                'career_growth': s4,
                'compensation': s5,
                'overall_score': overall,
            })
    return pd.DataFrame(records)


def generate_attrition_labels(df_employees, df_attendance, df_emails, df_tasks, df_surveys):
    records = []
    max_commute = df_employees['commute_distance'].max()

    for _, emp in df_employees.iterrows():
        emp_id = emp['employee_id']
        base = emp['attrition_base']
        commute = emp['commute_distance']

        emp_att = df_attendance[df_attendance['employee_id'] == emp_id]
        late_rate_raw = len(emp_att[emp_att['status'] == '迟到']) / max(1, len(emp_att))
        absent_rate = len(emp_att[emp_att['status'] == '缺勤']) / max(1, len(emp_att))

        commute_factor = commute / max_commute if max_commute > 0 else 0
        late_rate_adjusted = max(0, late_rate_raw - commute_factor * 0.08)

        emp_email = df_emails[df_emails['employee_id'] == emp_id]
        emp_email_workday = emp_email[emp_email['is_pre_holiday'] == False] if 'is_pre_holiday' in emp_email.columns else emp_email

        avg_email = float(emp_email_workday['total_emails'].mean()) if len(emp_email_workday) > 0 else 5.0
        avg_response = float(emp_email_workday['avg_response_hours'].mean()) if len(emp_email_workday) > 0 else 3.0

        emp_task = df_tasks[df_tasks['employee_id'] == emp_id]
        avg_completion = float(emp_task['completion_rate'].mean()) if len(emp_task) > 0 else 0.85
        avg_ontime = float(emp_task['on_time_rate'].mean()) if len(emp_task) > 0 else 0.85

        emp_survey = df_surveys[df_surveys['employee_id'] == emp_id]
        avg_satisfaction = float(emp_survey['overall_score'].mean()) if len(emp_survey) > 0 else 3.5

        risk_score = (
            base * 0.35
            + late_rate_adjusted * 0.15
            + absent_rate * 0.12
            + (1.0 - min(avg_completion, 1.0)) * 0.12
            + (1.0 - min(avg_ontime, 1.0)) * 0.08
            + max(0, (3.5 - avg_satisfaction) / 3.5) * 0.10
            + (5.0 - min(avg_email, 15.0)) / 15.0 * 0.05
            + min(avg_response, 10.0) / 10.0 * 0.03
        )
        risk_score = max(0.0, min(1.0, risk_score))

        is_attrited = risk_score > 0.40 and np.random.random() < (risk_score - 0.25) * 1.8

        attrition_date = None
        if is_attrited:
            days_to_attr = int(np.random.exponential(180) + 60)
            days_to_attr = min(days_to_attr, DAYS - 30)
            attrition_date = START_DATE + timedelta(days=days_to_attr)

        records.append({
            'employee_id': emp_id,
            'risk_score': float(rnd(risk_score, 4)),
            'late_rate_raw': float(rnd(late_rate_raw, 4)),
            'late_rate_adjusted': float(rnd(late_rate_adjusted, 4)),
            'commute_factor': float(rnd(commute_factor, 4)),
            'is_attrited': bool(is_attrited),
            'attrition_date': attrition_date,
        })
    return pd.DataFrame(records)


def generate_all_data():
    print("正在生成员工基础数据...")
    df_employees = generate_employee_base()

    print("正在生成考勤数据...")
    df_attendance = generate_attendance(df_employees)

    print("正在生成邮件沟通数据...")
    df_emails = generate_email_data(df_employees)

    print("正在生成任务数据...")
    df_tasks = generate_task_data(df_employees)

    print("正在生成满意度调查数据...")
    df_surveys = generate_satisfaction_surveys(df_employees)

    print("正在计算离职标签...")
    df_attrition = generate_attrition_labels(
        df_employees, df_attendance, df_emails, df_tasks, df_surveys
    )

    df_employees_full = df_employees.merge(df_attrition, on='employee_id')
    df_employees_full = df_employees_full.drop(columns=['attrition_base'])

    print(f"数据生成完成！")
    print(f"  员工数: {len(df_employees_full)}")
    print(f"  考勤记录: {len(df_attendance)}")
    print(f"  邮件记录: {len(df_emails)}")
    print(f"  任务记录: {len(df_tasks)}")
    print(f"  满意度记录: {len(df_surveys)}")
    print(f"  离职率: {df_attrition['is_attrited'].mean():.2%}")
    print(f"  平均通勤距离: {df_employees['commute_distance'].mean():.1f} km")

    return {
        'employees': df_employees_full,
        'attendance': df_attendance,
        'emails': df_emails,
        'tasks': df_tasks,
        'surveys': df_surveys,
    }


if __name__ == '__main__':
    data = generate_all_data()
    for name, df in data.items():
        df.to_csv(f'{name}.csv', index=False)
        print(f"已保存: {name}.csv")