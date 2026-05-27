import pandas as pd
import numpy as np
from lifetimes import GammaGammaFitter


class GammaGammaModel:
    def __init__(self, penalizer_coef=0.0):
        self.penalizer_coef = penalizer_coef
        self.model = GammaGammaFitter(penalizer_coef=penalizer_coef)
        self.is_fitted = False
        self.frequency_col = 'frequency'
        self.amount_col = 'avg_amount'
    
    def fit(self, data, frequency_col='frequency', amount_col='avg_amount'):
        self.frequency_col = frequency_col
        self.amount_col = amount_col
        
        self.model.fit(
            data[frequency_col],
            data[amount_col]
        )
        self.is_fitted = True
        return self
    
    def predict_expected_average_profit(self, data):
        if not self.is_fitted:
            raise ValueError("模型尚未训练，请先调用fit()方法")
        
        predictions = self.model.conditional_expected_average_profit(
            data[self.frequency_col],
            data[self.amount_col]
        )
        return predictions
    
    def predict_customer_lifetime_value(self, bg_nbd_model, data, future_months=12, 
                                        discount_rate=0.01, freq='D'):
        if not self.is_fitted:
            raise ValueError("模型尚未训练，请先调用fit()方法")
        
        clv = self.model.customer_lifetime_value(
            bg_nbd_model.model,
            data[bg_nbd_model.frequency_col],
            data[bg_nbd_model.recency_col],
            data[bg_nbd_model.age_col],
            data[self.amount_col],
            time=future_months,
            discount_rate=discount_rate,
            freq=freq
        )
        return clv
    
    def predict_expected_profit_with_ci(self, data, n_samples=1000):
        if not self.is_fitted:
            raise ValueError("模型尚未训练，请先调用fit()方法")
        
        mean_predictions = self.predict_expected_average_profit(data)
        
        p, q, v = self.model._unload_params()
        
        samples = []
        for _ in range(n_samples):
            p_sample = np.random.gamma(p, 1)
            q_sample = np.random.gamma(q, 1)
            v_sample = np.random.gamma(v, 1)
            
            temp_model = GammaGammaFitter()
            temp_model.params_ = {'p': p_sample, 'q': q_sample, 'v': v_sample}
            
            pred = temp_model.conditional_expected_average_profit(
                data[self.frequency_col],
                data[self.amount_col]
            )
            samples.append(pred)
        
        samples = np.array(samples)
        lower = np.percentile(samples, 5, axis=0)
        upper = np.percentile(samples, 95, axis=0)
        
        return pd.DataFrame({
            'predicted_avg_amount': mean_predictions,
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
    
    def calculate_expected_total_spend(self, data, purchase_counts):
        if not self.is_fitted:
            raise ValueError("模型尚未训练，请先调用fit()方法")
        
        avg_profit = self.predict_expected_average_profit(data)
        return avg_profit * purchase_counts


if __name__ == '__main__':
    from data_generator import generate_customer_profiles, generate_transaction_history, prepare_model_data
    from bg_nbd_model import BGNBDModel
    
    profiles = generate_customer_profiles(n_customers=500)
    transactions = generate_transaction_history(profiles)
    model_data = prepare_model_data(profiles, transactions, None)
    
    bg_nbd = BGNBDModel()
    bg_nbd.fit(model_data)
    
    gg = GammaGammaModel()
    gg.fit(model_data)
    
    print("Gamma-Gamma模型参数:", gg.get_params())
    print("\n模型摘要:")
    print(gg.get_model_summary())
    
    expected_avg_profit = gg.predict_expected_average_profit(model_data)
    print(f"\n预期平均客单价统计:")
    print(expected_avg_profit.describe())
    
    clv = gg.predict_customer_lifetime_value(bg_nbd, model_data, future_months=12)
    print(f"\n12个月客户生命周期价值统计:")
    print(clv.describe())
