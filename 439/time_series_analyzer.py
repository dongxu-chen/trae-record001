import pandas as pd
import numpy as np
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.seasonal import seasonal_decompose
from sklearn.preprocessing import MinMaxScaler
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


def analyze_department_trends(monthly_df):
    dept_trends = monthly_df.groupby(['month', 'department']).agg({
        'late_rate': 'mean',
        'absent_rate': 'mean',
        'avg_total_emails': 'mean',
        'avg_completion_rate': 'mean',
        'avg_overtime_hours': 'mean',
        'overall_satisfaction': 'mean',
    }).reset_index()

    dept_trends['month'] = pd.to_datetime(dept_trends['month'])
    dept_trends = dept_trends.sort_values('month')

    return dept_trends


def analyze_company_trends(monthly_df):
    company_trends = monthly_df.groupby('month').agg({
        'late_rate': 'mean',
        'absent_rate': 'mean',
        'avg_total_emails': 'mean',
        'avg_completion_rate': 'mean',
        'avg_overtime_hours': 'mean',
        'overall_satisfaction': 'mean',
        'employee_id': 'count',
    }).reset_index()

    company_trends['month'] = pd.to_datetime(company_trends['month'])
    company_trends = company_trends.sort_values('month')

    attrition_counts = monthly_df[monthly_df['is_attrited'] == True].groupby('month')['employee_id'].nunique().reset_index()
    attrition_counts.columns = ['month', 'attrition_count']
    company_trends = company_trends.merge(attrition_counts, on='month', how='left')
    company_trends['attrition_count'] = company_trends['attrition_count'].fillna(0)

    return company_trends


def forecast_trend(series, periods=6):
    try:
        series_clean = series.dropna()
        if len(series_clean) < 4:
            return None, None

        model = ExponentialSmoothing(
            series_clean,
            trend='add',
            seasonal=None,
            damped_trend=True,
        )
        fitted = model.fit(optimized=True)
        forecast = fitted.forecast(periods)

        last_date = series_clean.index[-1]
        future_dates = pd.date_range(
            start=last_date + pd.DateOffset(months=1),
            periods=periods,
            freq='M'
        )
        forecast_series = pd.Series(forecast, index=future_dates)

        return series_clean, forecast_series
    except Exception as e:
        print(f"Forecast error: {e}")
        return None, None


def compute_risk_trend_score(monthly_df, employee_id):
    emp_data = monthly_df[monthly_df['employee_id'] == employee_id].copy()
    if len(emp_data) < 3:
        return None

    emp_data = emp_data.sort_values('month')
    emp_data['month_dt'] = pd.to_datetime(emp_data['month'])

    metrics = {}
    for col in ['late_rate', 'absent_rate', 'avg_total_emails', 'avg_completion_rate', 'overall_satisfaction']:
        if col in emp_data.columns:
            vals = emp_data[col].dropna()
            if len(vals) >= 3:
                x = np.arange(len(vals))
                slope = np.polyfit(x, vals.values, 1)[0]
                metrics[col] = {
                    'slope': slope,
                    'trend': '上升' if slope > 0.01 else ('下降' if slope < -0.01 else '稳定'),
                    'current': vals.values[-1],
                    'history': vals.values.tolist(),
                }

    risk_trend = 0
    if 'late_rate' in metrics:
        risk_trend += metrics['late_rate']['slope'] * 100
    if 'absent_rate' in metrics:
        risk_trend += metrics['absent_rate']['slope'] * 100
    if 'avg_total_emails' in metrics:
        risk_trend -= metrics['avg_total_emails']['slope'] * 0.1
    if 'avg_completion_rate' in metrics:
        risk_trend -= metrics['avg_completion_rate']['slope'] * 100
    if 'overall_satisfaction' in metrics:
        risk_trend -= metrics['overall_satisfaction']['slope'] * 20

    return {
        'employee_id': employee_id,
        'risk_trend_score': risk_trend,
        'risk_trend_label': '恶化' if risk_trend > 0.5 else ('改善' if risk_trend < -0.5 else '稳定'),
        'metrics': metrics,
    }


def detect_anomalies(monthly_df, metric_col, threshold=2):
    anomalies = []
    for emp_id in monthly_df['employee_id'].unique():
        emp_data = monthly_df[monthly_df['employee_id'] == emp_id].copy()
        emp_data = emp_data.sort_values('month')

        values = emp_data[metric_col].dropna()
        if len(values) < 5:
            continue

        mean_val = values.mean()
        std_val = values.std()
        if std_val == 0:
            continue

        for idx, val in values.items():
            z_score = (val - mean_val) / std_val
            if abs(z_score) > threshold:
                row = emp_data.loc[idx]
                anomalies.append({
                    'employee_id': emp_id,
                    'month': row['month'],
                    'metric': metric_col,
                    'value': val,
                    'z_score': z_score,
                    'anomaly_type': '偏高' if z_score > 0 else '偏低',
                })

    return pd.DataFrame(anomalies)


def compute_risk_index(monthly_df):
    monthly_df = monthly_df.copy()
    monthly_df['risk_index'] = 0.0

    if 'late_rate' in monthly_df.columns:
        monthly_df['risk_index'] += monthly_df['late_rate'].fillna(0) * 20
    if 'absent_rate' in monthly_df.columns:
        monthly_df['risk_index'] += monthly_df['absent_rate'].fillna(0) * 25
    if 'avg_overtime_hours' in monthly_df.columns:
        monthly_df['risk_index'] += (monthly_df['avg_overtime_hours'].fillna(0) / 10) * 15
    if 'avg_total_emails' in monthly_df.columns:
        monthly_df['risk_index'] += (1 - (monthly_df['avg_total_emails'].fillna(0) / 20).clip(0, 1)) * 10
    if 'avg_completion_rate' in monthly_df.columns:
        monthly_df['risk_index'] += (1 - monthly_df['avg_completion_rate'].fillna(0.85).clip(0, 1)) * 15
    if 'overall_satisfaction' in monthly_df.columns:
        monthly_df['risk_index'] += (1 - (monthly_df['overall_satisfaction'].fillna(3.5) / 5)) * 15

    monthly_df['risk_index'] = monthly_df['risk_index'].clip(0, 100)
    return monthly_df


def generate_trend_charts(company_trends, output_dir='.'):
    import os
    os.makedirs(output_dir, exist_ok=True)

    company_trends_plot = company_trends.set_index('month')

    fig, axes = plt.subplots(2, 3, figsize=(18, 12))

    metrics = [
        ('late_rate', '迟到率趋势', '%'),
        ('absent_rate', '缺勤率趋势', '%'),
        ('avg_overtime_hours', '平均加班时长', '小时'),
        ('avg_total_emails', '邮件沟通量', '封'),
        ('avg_completion_rate', '任务完成率', '%'),
        ('overall_satisfaction', '综合满意度', '分'),
    ]

    for idx, (col, title, unit) in enumerate(metrics):
        ax = axes[idx // 3, idx % 3]
        if col in company_trends_plot.columns:
            data = company_trends_plot[col].dropna()
            ax.plot(data.index, data.values, 'b-o', markersize=4, linewidth=2)

            hist, forecast = forecast_trend(data, periods=3)
            if hist is not None and forecast is not None:
                ax.plot(forecast.index, forecast.values, 'r--', linewidth=2, label='预测')
                ax.legend()

            ax.set_title(title, fontsize=12)
            ax.set_xlabel('月份')
            ax.set_ylabel(unit)
            ax.grid(True, alpha=0.3)
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

    plt.suptitle('公司整体趋势分析 (含预测)', fontsize=14, y=1.02)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'company_trends.png'), dpi=150, bbox_inches='tight')
    plt.close()

    if 'attrition_count' in company_trends_plot.columns:
        fig, ax = plt.subplots(figsize=(12, 6))
        attr_data = company_trends_plot['attrition_count'].dropna()
        ax.bar(attr_data.index, attr_data.values, color='#FF6B6B', alpha=0.7, width=20)
        ax.set_title('月度离职人数趋势', fontsize=14)
        ax.set_xlabel('月份')
        ax.set_ylabel('离职人数')
        ax.grid(True, alpha=0.3)
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'attrition_trend.png'), dpi=150)
        plt.close()

    return True


def generate_department_heatmap(dept_trends, output_dir='.'):
    import os
    os.makedirs(output_dir, exist_ok=True)

    dept_pivot = dept_trends.pivot_table(
        index='department',
        columns='month',
        values='overall_satisfaction',
        aggfunc='mean'
    )

    if dept_pivot.shape[0] > 0 and dept_pivot.shape[1] > 0:
        fig, ax = plt.subplots(figsize=(14, 8))
        im = ax.imshow(dept_pivot.values, aspect='auto', cmap='RdYlGn', vmin=1, vmax=5)

        ax.set_xticks(range(len(dept_pivot.columns)))
        ax.set_xticklabels([str(m) for m in dept_pivot.columns], rotation=45, ha='right')
        ax.set_yticks(range(len(dept_pivot.index)))
        ax.set_yticklabels(dept_pivot.index)

        for i in range(len(dept_pivot.index)):
            for j in range(len(dept_pivot.columns)):
                val = dept_pivot.values[i, j]
                if not np.isnan(val):
                    ax.text(j, i, f'{val:.1f}', ha='center', va='center',
                           fontsize=8, color='black')

        plt.colorbar(im, label='综合满意度')
        ax.set_title('各部门满意度热力图', fontsize=14)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'department_heatmap.png'), dpi=150)
        plt.close()

    return True


if __name__ == '__main__':
    from data_generator import generate_all_data
    from model_trainer import build_features, build_monthly_features

    print("生成数据...")
    data = generate_all_data()

    print("构建月度特征...")
    monthly_df = build_monthly_features(data)

    print("分析公司趋势...")
    company_trends = analyze_company_trends(monthly_df)

    print("分析部门趋势...")
    dept_trends = analyze_department_trends(monthly_df)

    print("计算风险指数...")
    monthly_df = compute_risk_index(monthly_df)

    print("生成图表...")
    generate_trend_charts(company_trends, output_dir='ts_output')
    generate_department_heatmap(dept_trends, output_dir='ts_output')

    print("\n趋势分析完成！")
    print(f"公司趋势数据点: {len(company_trends)}")
    print(f"部门趋势数据点: {len(dept_trends)}")