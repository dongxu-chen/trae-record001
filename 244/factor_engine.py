import pandas as pd
import numpy as np
from typing import Dict, Callable
from config import FACTOR_NORMALIZE


class FactorEngine:
    def __init__(self, factor_data: Dict[str, pd.DataFrame]):
        self.factor_data = factor_data
        self.custom_functions = self._register_custom_functions()

    def _register_custom_functions(self) -> Dict[str, Callable]:
        functions = {
            'rank': self._rank,
            'zscore': self._zscore,
            'log': np.log,
            'abs': np.abs,
            'sqrt': np.sqrt,
            'pow': np.power,
            'max': np.maximum,
            'min': np.minimum,
            'mean': self._rolling_mean,
            'std': self._rolling_std,
            'delta': self._delta,
            'pct_change': self._pct_change,
        }
        return functions

    def _rank(self, df: pd.DataFrame) -> pd.DataFrame:
        return df.rank(axis=1, pct=True)

    def _zscore(self, df: pd.DataFrame) -> pd.DataFrame:
        return (df - df.mean(axis=1).values.reshape(-1, 1)) / df.std(axis=1).values.reshape(-1, 1)

    def _rolling_mean(self, df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
        return df.rolling(window=window).mean()

    def _rolling_std(self, df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
        return df.rolling(window=window).std()

    def _delta(self, df: pd.DataFrame, period: int = 1) -> pd.DataFrame:
        return df.diff(period)

    def _pct_change(self, df: pd.DataFrame, period: int = 1) -> pd.DataFrame:
        return df.pct_change(period)

    def _parse_expression(self, expression: str) -> str:
        parsed_expr = expression
        
        for func_name in self.custom_functions.keys():
            if func_name in parsed_expr:
                parsed_expr = parsed_expr.replace(f'{func_name}(', f'self.custom_functions["{func_name}"](')
        
        factor_names = list(self.factor_data.keys())
        for name in sorted(factor_names, key=len, reverse=True):
            parsed_expr = parsed_expr.replace(name, f'self.factor_data["{name}"]')
        
        return parsed_expr

    def calculate_factor(self, expression: str) -> pd.DataFrame:
        try:
            parsed_expr = self._parse_expression(expression)
            factor_values = eval(parsed_expr)
            
            if isinstance(factor_values, pd.DataFrame):
                factor_values = factor_values.replace([np.inf, -np.inf], np.nan)
            
            if FACTOR_NORMALIZE:
                factor_values = self._normalize_factor(factor_values)
            
            return factor_values
            
        except Exception as e:
            raise ValueError(f"Error calculating factor expression '{expression}': {str(e)}")

    def _normalize_factor(self, factor_df: pd.DataFrame) -> pd.DataFrame:
        demeaned = factor_df.subtract(factor_df.mean(axis=1), axis=0)
        normalized = demeaned.divide(factor_df.std(axis=1), axis=0)
        return normalized

    def winsorize(self, factor_df: pd.DataFrame, 
                   lower: float = 0.01, 
                   upper: float = 0.99) -> pd.DataFrame:
        def _winsorize_row(row):
            lower_val = row.quantile(lower)
            upper_val = row.quantile(upper)
            return row.clip(lower_val, upper_val)
        
        return factor_df.apply(_winsorize_row, axis=1)

    def neutralize(self, factor_df: pd.DataFrame, 
                   neutralize_factors: list) -> pd.DataFrame:
        result = factor_df.copy()
        
        for date in factor_df.index:
            y = factor_df.loc[date].values
            X = np.ones((len(y), 1))
            
            for nf in neutralize_factors:
                if nf in self.factor_data:
                    nf_values = self.factor_data[nf].loc[date].values
                    X = np.column_stack([X, nf_values])
            
            valid_mask = ~np.isnan(y) & ~np.isnan(X).any(axis=1)
            
            if valid_mask.sum() > X.shape[1]:
                beta = np.linalg.lstsq(X[valid_mask], y[valid_mask], rcond=None)[0]
                y_pred = X @ beta
                result.loc[date] = y - y_pred
        
        return result

    def shift_factor(self, factor_df: pd.DataFrame, periods: int = 1) -> pd.DataFrame:
        return factor_df.shift(periods)


if __name__ == '__main__':
    from data_loader import DataLoader
    
    loader = DataLoader()
    _, factors, _, _ = loader.load_data()
    
    engine = FactorEngine(factors)
    
    test_expressions = [
        '1 / PE',
        'ROE',
        'rank(1 / PE)',
        'zscore(ROE)',
        'log(MKT_CAP)',
        'delta(ROE, 20)',
    ]
    
    for expr in test_expressions:
        try:
            factor = engine.calculate_factor(expr)
            print(f"Expression '{expr}' calculated successfully, shape: {factor.shape}")
            print(f"  Mean: {factor.mean().mean():.4f}, Std: {factor.stack().std():.4f}")
        except Exception as e:
            print(f"Expression '{expr}' failed: {str(e)}")
