import pandas as pd
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')


def generate_chinese_holidays(start_year=2020, end_year=2030):
    holidays = []
    
    for year in range(start_year, end_year + 1):
        new_year_start = datetime(year, 1, 1)
        for i in range(3):
            holidays.append({
                'holiday': '元旦',
                'ds': new_year_start + timedelta(days=i),
                'lower_window': 0,
                'upper_window': 1
            })
        
        spring_festival_date = get_spring_festival_date(year)
        if spring_festival_date:
            for i in range(-3, 7):
                holidays.append({
                    'holiday': '春节',
                    'ds': spring_festival_date + timedelta(days=i),
                    'lower_window': 3,
                    'upper_window': 7
                })
        
        qingming_date = datetime(year, 4, 5)
        for i in range(3):
            holidays.append({
                'holiday': '清明节',
                'ds': qingming_date + timedelta(days=i),
                'lower_window': 0,
                'upper_window': 1
            })
        
        labor_start = datetime(year, 5, 1)
        for i in range(5):
            holidays.append({
                'holiday': '劳动节',
                'ds': labor_start + timedelta(days=i),
                'lower_window': 0,
                'upper_window': 2
            })
        
        dragon_boat_date = get_dragon_boat_date(year)
        if dragon_boat_date:
            for i in range(3):
                holidays.append({
                    'holiday': '端午节',
                    'ds': dragon_boat_date + timedelta(days=i),
                    'lower_window': 0,
                    'upper_window': 1
                })
        
        mid_autumn_date = get_mid_autumn_date(year)
        if mid_autumn_date:
            for i in range(3):
                holidays.append({
                    'holiday': '中秋节',
                    'ds': mid_autumn_date + timedelta(days=i),
                    'lower_window': 0,
                    'upper_window': 1
                })
        
        national_start = datetime(year, 10, 1)
        for i in range(-1, 8):
            holidays.append({
                'holiday': '国庆节',
                'ds': national_start + timedelta(days=i),
                'lower_window': 1,
                'upper_window': 7
            })
    
    holidays_df = pd.DataFrame(holidays)
    holidays_df = holidays_df.drop_duplicates(subset=['holiday', 'ds'])
    holidays_df = holidays_df.sort_values('ds').reset_index(drop=True)
    
    return holidays_df


def get_spring_festival_date(year):
    spring_festival_dates = {
        2020: datetime(2020, 1, 25),
        2021: datetime(2021, 2, 12),
        2022: datetime(2022, 2, 1),
        2023: datetime(2023, 1, 22),
        2024: datetime(2024, 2, 10),
        2025: datetime(2025, 1, 29),
        2026: datetime(2026, 2, 17),
        2027: datetime(2027, 2, 6),
        2028: datetime(2028, 1, 26),
        2029: datetime(2029, 2, 13),
        2030: datetime(2030, 2, 3)
    }
    return spring_festival_dates.get(year)


def get_dragon_boat_date(year):
    dragon_boat_dates = {
        2020: datetime(2020, 6, 25),
        2021: datetime(2021, 6, 14),
        2022: datetime(2022, 6, 3),
        2023: datetime(2023, 6, 22),
        2024: datetime(2024, 6, 10),
        2025: datetime(2025, 5, 31),
        2026: datetime(2026, 6, 19),
        2027: datetime(2027, 6, 9),
        2028: datetime(2028, 5, 28),
        2029: datetime(2029, 6, 16),
        2030: datetime(2030, 6, 5)
    }
    return dragon_boat_dates.get(year)


def get_mid_autumn_date(year):
    mid_autumn_dates = {
        2020: datetime(2020, 10, 1),
        2021: datetime(2021, 9, 21),
        2022: datetime(2022, 9, 10),
        2023: datetime(2023, 9, 29),
        2024: datetime(2024, 9, 17),
        2025: datetime(2025, 10, 6),
        2026: datetime(2026, 9, 25),
        2027: datetime(2027, 9, 15),
        2028: datetime(2028, 10, 3),
        2029: datetime(2029, 9, 22),
        2030: datetime(2030, 9, 12)
    }
    return mid_autumn_dates.get(year)


def get_prophet_holidays(start_year=2020, end_year=2030):
    holidays_df = generate_chinese_holidays(start_year, end_year)
    prophet_holidays = pd.DataFrame({
        'holiday': holidays_df['holiday'],
        'ds': pd.to_datetime(holidays_df['ds']),
        'lower_window': holidays_df['lower_window'],
        'upper_window': holidays_df['upper_window']
    })
    return prophet_holidays


if __name__ == "__main__":
    holidays = get_prophet_holidays(2024, 2025)
    print("中国节假日数据预览:")
    print(holidays.head(20))
    print(f"\n总节假日数量: {len(holidays)}")
