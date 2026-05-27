import pandas as pd
import numpy as np
from lifetimes import BetaGeoFitter
from lifetimes.utils import calibration_and_holdout_data
from lifetimes.plotting import plot_period_transactions, plot_calibration_purchases_vs_holdout_purchases
import matplotlib.pyplot as plt


class BGNBDModel:
    def __init__(self, penalizer_coef=0.0):
        self.penalizer_coef = penalizer_coef
        self.model = BetaGeoFitter(penalizer_coef=penalizer_coef)
        self.is_fitted = False
        self.frequency_col = 'frequency'
        self.recency_col = 'recency'
        self.age_col = 'T'
    
    def fit(self, data, frequency_col='frequency', recency_col='recency', age_col='T'):
        self.frequency_col = frequency_col
        self.recency_col = recency_col
        self.age_col = age_col
        
        self.model.fit(
            data[frequency_col],
            data[recency_col],
            data[age_col]
        )
        self.is_fitted = True
        return self
    
    def predict_purchases(self, data, future_months=12):
        if not self.is_fitted:
            raise ValueError("模型尚未训练，请先调用fit()方法")
        
        days = future_months * 30
        predictions = self.model.predict(
            days,
            data[self.frequency_col],
            data[self.recency_col],
            data[self.age_col]
        )
        return predictions
    
    def predict_purchases_with_ci(self, data, future_months=12, n_samples=1000):
        if not self.is_fitted:
            raise ValueError("模型尚未训练，请先调用fit()方法")
        
        days = future_months * 30
        mean_predictions = self.predict_purchases(data, future_months)
        
        samples = []
        param_samples = self.model._unload_params()
        
        r, alpha, a, b = param_samples
        
        for _ in range(n_samples):
            r_sample = np.random.gamma(r, 1)
            alpha_sample = np.random.gamma(alpha, 1)
            a_sample = np.random.gamma(a, 1)
            b_sample = np.random.gamma(b, 1)
            
            temp_model = BetaGeoFitter()
            temp_model.params_ = {'r': r_sample, 'alpha': alpha_sample, 'a': a_sample, 'b': b_sample}
            
            pred = temp_model.predict(
                days,
                data[self.frequency_col],
                data[self.recency_col],
                data[self.age_col]
            )
            samples.append(pred)
        
        samples = np.array(samples)
        lower = np.percentile(samples, 5, axis=0)
        upper = np.percentile(samples, 95, axis=0)
        
        return pd.DataFrame({
            'predicted_purchases': mean_predictions,
            'lower_ci': lower,
            'upper_ci': upper
        }, index=data.index)
    
    def get_model_summary(self):
        if not self.is_fitted:
            raise ValueError("模型尚未训练，请先调用fit()方法")
        
        return self.model.summary
    
    def get_params(self):
        if not self.is_fitted:
            raise ValueError("模型尚未训练，请先调用fit()方法")
        return self.model.params_
    
    def plot_period_transactions(self, ax=None):
        if not self.is_fitted:
            raise ValueError("模型尚未训练，请先调用fit()方法")
        return plot_period_transactions(self.model, ax=ax)
    
    def evaluate_holdout(self, data, calibration_period_months=9, holdout_period_months=3):
        from lifetimes.utils import calibration_and_holdout_data
        
        if 'customer_id' not in data.columns:
            data = data.reset_index()
        
        calibration_end = data[self.age_col].max() - holdout_period_months * 30
        
        summary_cal_holdout = calibration_and_holdout_data(
            data,
            customer_id_col='customer_id',
            datetime_col='transaction_date',
            observation_period_end=data['transaction_date'].max() if 'transaction_date' in data.columns else None,
            calibration_period_end=pd.Timestamp.now() - pd.DateOffset(months=holdout_period_months),
            duration=holdout_period_months * 30
        )
        
        return summary_cal_holdout
    
    def calculate_probability_alive(self, data):
        if not self.is_fitted:
            raise ValueError("模型尚未训练，请先调用fit()方法")
        
        return self.model.conditional_probability_alive(
            data[self.frequency_col],
            data[self.recency_col],
            data[self.age_col]
        )
    
    def predict_expected_purchases_up_to_time(self, data, t):
        if not self.is_fitted:
            raise ValueError("模型尚未训练，请先调用fit()方法")
        
        return self.model.predict(
            t,
            data[self.frequency_col],
            data[self.recency_col],
            data[self.age_col]
        )
    
    def calculate_reactivation_probability(self, data, future_months=12, churn_threshold=0.3):
        if not self.is_fitted:
            raise ValueError("模型尚未训练，请先调用fit()方法")
        
        prob_alive = self.calculate_probability_alive(data)
        is_churned = prob_alive < churn_threshold
        
        days = future_months * 30
        future_purchases = self.predict_purchases(data, future_months)
        
        reactivation_prob = np.zeros(len(data))
        
        for i in range(len(data)):
            if is_churned.iloc[i]:
                freq = data[self.frequency_col].iloc[i]
                rec = data[self.recency_col].iloc[i]
                T = data[self.age_col].iloc[i]
                
                if freq > 0:
                    expected_purchases_if_alive = self.model.predict(
                        days, freq, rec, T
                    )
                    
                    purchase_rate = self.model.params_['r'] / self.model.params_['alpha']
                    base_reactivation = 1 - np.exp(-purchase_rate * days / 30)
                    
                    historical_activity = min(freq / (T / 30), 5) if T > 30 else 0
                    
                    reactivation_prob[i] = min(
                        base_reactivation * (0.5 + 0.1 * historical_activity),
                        0.9
                    )
                else:
                    reactivation_prob[i] = 0.05
            else:
                reactivation_prob[i] = 1.0
        
        return pd.Series(reactivation_prob, index=data.index, name='reactivation_prob')
    
    def identify_churned_customers(self, data, churn_threshold=0.3):
        if not self.is_fitted:
            raise ValueError("模型尚未训练，请先调用fit()方法")
        
        prob_alive = self.calculate_probability_alive(data)
        is_churned = prob_alive < churn_threshold
        
        churn_info = pd.DataFrame({
            'customer_id': data['customer_id'].values if 'customer_id' in data.columns else data.index,
            'probability_alive': prob_alive.values,
            'is_churned': is_churned.values,
            'churn_days': data[self.recency_col].values
        }, index=data.index)
        
        return churn_info
    
    def predict_reactivated_purchases(self, data, future_months=12, churn_threshold=0.3):
        if not self.is_fitted:
            raise ValueError("模型尚未训练，请先调用fit()方法")
        
        reactivation_prob = self.calculate_reactivation_probability(
            data, future_months, churn_threshold
        )
        base_predictions = self.predict_purchases(data, future_months)
        
        churn_info = self.identify_churned_customers(data, churn_threshold)
        
        adjusted_predictions = base_predictions.copy()
        for i in range(len(data)):
            if churn_info['is_churned'].iloc[i]:
                adjusted_predictions.iloc[i] = base_predictions.iloc[i] * reactivation_prob.iloc[i]
        
        return pd.DataFrame({
            'base_purchases': base_predictions,
            'reactivation_prob': reactivation_prob,
            'is_churned': churn_info['is_churned'].values,
            'adjusted_purchases': adjusted_predictions
        }, index=data.index)


if __name__ == '__main__':
    from data_generator import generate_customer_profiles, generate_transaction_history, prepare_model_data
    
    profiles = generate_customer_profiles(n_customers=500)
    transactions = generate_transaction_history(profiles)
    model_data = prepare_model_data(profiles, transactions, None)
    
    bg_nbd = BGNBDModel()
    bg_nbd.fit(model_data)
    
    print("模型参数:", bg_nbd.get_params())
    print("\n模型摘要:")
    print(bg_nbd.get_model_summary())
    
    predictions = bg_nbd.predict_purchases(model_data, future_months=6)
    print(f"\n未来6个月预测购买次数统计:")
    print(predictions.describe())
    
    prob_alive = bg_nbd.calculate_probability_alive(model_data)
    print(f"\n客户活跃度统计:")
    print(prob_alive.describe())
