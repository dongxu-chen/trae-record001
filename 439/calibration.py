import numpy as np
import pandas as pd
from sklearn.metrics import (
    brier_score_loss,
    roc_auc_score,
    accuracy_score,
    confusion_matrix,
)

THRESHOLD = 0.5
RISK_BINS = [-0.01, 0.3, 0.5, 0.7, 1.01]
RISK_LABELS = ['低风险', '中低风险', '中高风险', '高风险']


def compute_calibration_metrics(y_true, y_pred_proba, n_bins=10):
    y_true = np.asarray(y_true, dtype=float)
    y_pred_proba = np.asarray(y_pred_proba, dtype=float)

    brier = float(brier_score_loss(y_true, y_pred_proba))

    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    bin_indices = np.digitize(y_pred_proba, bin_edges[1:-1], right=True)

    rows = []
    total = len(y_true)
    ece = 0.0
    for i in range(n_bins):
        mask = bin_indices == i
        count = int(mask.sum())
        if count == 0:
            rows.append({
                '区间': f'{bin_edges[i]:.2f}-{bin_edges[i+1]:.2f}',
                '平均预测概率': 0.0,
                '平均实际概率': 0.0,
                '样本数': 0,
            })
            continue
        mean_pred = float(y_pred_proba[mask].mean())
        mean_actual = float(y_true[mask].mean())
        ece += (count / total) * abs(mean_actual - mean_pred)
        rows.append({
            '区间': f'{bin_edges[i]:.2f}-{bin_edges[i+1]:.2f}',
            '平均预测概率': round(mean_pred, 4),
            '平均实际概率': round(mean_actual, 4),
            '样本数': count,
        })

    cal_df = pd.DataFrame(rows)

    has_both = len(np.unique(y_true)) > 1
    auc = float(roc_auc_score(y_true, y_pred_proba)) if has_both else float('nan')

    y_pred_label = (y_pred_proba >= THRESHOLD).astype(int)
    acc = float(accuracy_score(y_true, y_pred_label))

    return {
        'brier_score': round(brier, 6),
        'ece': round(ece, 6),
        'calibration_curve': cal_df,
        'auc_roc': round(auc, 6) if not np.isnan(auc) else None,
        'accuracy': round(acc, 6),
    }


def calibration_over_time(model, scaler, df_features, data):
    from model_trainer import FEATURE_COLS

    df_emp = data['employees'].copy()
    if 'hire_date' not in df_emp.columns:
        return pd.DataFrame()

    df_emp = df_emp.sort_values('hire_date')
    n = len(df_emp)
    cut1 = n // 3
    cut2 = 2 * n // 3

    periods = [
        ('早期入职', df_emp.iloc[:cut1]),
        ('中期入职', df_emp.iloc[cut1:cut2]),
        ('近期入职', df_emp.iloc[cut2:]),
    ]

    results = []
    for period_name, period_df in periods:
        emp_ids = period_df['employee_id'].tolist()
        feat_subset = df_features[df_features['employee_id'].isin(emp_ids)]

        if feat_subset.empty:
            results.append({
                '时期': period_name,
                '样本数': 0,
                'brier_score': None,
                'ece': None,
                'auc_roc': None,
                'accuracy': None,
            })
            continue

        X = feat_subset[FEATURE_COLS].copy()
        X_scaled = scaler.transform(X)

        y_true = feat_subset['target'].values
        y_pred_proba = model.predict_proba(X_scaled)[:, 1]

        metrics = compute_calibration_metrics(y_true, y_pred_proba)

        results.append({
            '时期': period_name,
            '样本数': len(feat_subset),
            'brier_score': metrics['brier_score'],
            'ece': metrics['ece'],
            'auc_roc': metrics['auc_roc'],
            'accuracy': metrics['accuracy'],
        })

    return pd.DataFrame(results)


def compare_actual_vs_predicted(risk_df, df_employees):
    merged = risk_df.merge(
        df_employees[['employee_id', 'is_attrited']],
        on='employee_id',
        how='left',
    )

    merged['risk_level'] = pd.Categorical(
        merged['risk_level'],
        categories=RISK_LABELS,
        ordered=True,
    )

    comparison_rows = []
    for level in RISK_LABELS:
        subset = merged[merged['risk_level'] == level]
        if subset.empty:
            comparison_rows.append({
                '风险等级': level,
                '员工数': 0,
                '实际离职数': 0,
                '预测离职数': 0,
                '实际离职率': 0.0,
                '预测离职率': 0.0,
            })
            continue

        actual_count = int(subset['is_attrited'].sum())
        predicted_count = int((subset['risk_score'] >= THRESHOLD).sum())
        total = len(subset)

        comparison_rows.append({
            '风险等级': level,
            '员工数': total,
            '实际离职数': actual_count,
            '预测离职数': predicted_count,
            '实际离职率': round(actual_count / total, 4),
            '预测离职率': round(predicted_count / total, 4),
        })

    comparison_df = pd.DataFrame(comparison_rows)

    y_true = merged['is_attrited'].astype(int).values
    y_pred = (merged['risk_score'] >= THRESHOLD).astype(int).values

    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    cm_df = pd.DataFrame(
        cm,
        index=['实际未离职', '实际已离职'],
        columns=['预测未离职', '预测已离职'],
    )

    accuracy_by_level = {}
    for level in RISK_LABELS:
        subset = merged[merged['risk_level'] == level]
        if subset.empty:
            accuracy_by_level[level] = None
            continue
        yt = subset['is_attrited'].astype(int).values
        yp = (subset['risk_score'] >= THRESHOLD).astype(int).values
        accuracy_by_level[level] = round(float(accuracy_score(yt, yp)), 4)

    return {
        'comparison_df': comparison_df,
        'confusion_matrix': cm_df,
        'accuracy_by_risk_level': accuracy_by_level,
    }


def suggest_calibration_adjustment(calibration_metrics):
    cal_df = calibration_metrics['calibration_curve']
    valid = cal_df[cal_df['样本数'] > 0]

    if valid.empty:
        return {
            'current_threshold': THRESHOLD,
            'suggested_threshold': THRESHOLD,
            'adjustment_direction': '无调整',
            'adjustment_reason': '无有效校准数据',
            'platt_scaling_recommended': False,
        }

    mean_pred = valid['平均预测概率'].values
    mean_actual = valid['平均实际概率'].values

    overall_pred = float(np.mean(mean_pred))
    overall_actual = float(np.mean(mean_actual))
    gap = overall_pred - overall_actual

    current = THRESHOLD

    if abs(gap) < 0.02:
        direction = '无调整'
        suggested = current
        reason = '模型预测与实际值偏差较小，校准良好，无需调整'
        platt = False
    elif gap > 0:
        direction = '降低阈值'
        shift = min(gap * 0.5, 0.1)
        suggested = round(max(0.1, current - shift), 2)
        reason = (
            f'模型过度预测离职概率（平均预测{overall_pred:.3f} > '
            f'平均实际{overall_actual:.3f}），建议降低分类阈值'
        )
        platt = True
    else:
        direction = '提高阈值'
        shift = min(abs(gap) * 0.5, 0.1)
        suggested = round(min(0.9, current + shift), 2)
        reason = (
            f'模型低估离职概率（平均预测{overall_pred:.3f} < '
            f'平均实际{overall_actual:.3f}），建议提高分类阈值'
        )
        platt = True

    return {
        'current_threshold': current,
        'suggested_threshold': suggested,
        'adjustment_direction': direction,
        'adjustment_reason': reason,
        'platt_scaling_recommended': platt,
    }
