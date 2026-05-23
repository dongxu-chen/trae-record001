import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, MinMaxScaler, OneHotEncoder, LabelEncoder
from sklearn.impute import SimpleImputer
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

class FeatureEngineering:
    def __init__(self, scaling_method='standard'):
        self.scaling_method = scaling_method
        self.scaler = StandardScaler() if scaling_method == 'standard' else MinMaxScaler()
        self.onehot_encoder = OneHotEncoder(sparse_output=False, drop='first', handle_unknown='ignore')
        self.label_encoders = {}
        self.preprocessor = None
        self.numerical_features = []
        self.categorical_features = []
        self.feature_names = []
        
    def fit_transform(self, df, target_col='Attrition'):
        df = df.copy()
        
        if 'EmployeeID' in df.columns:
            df = df.drop('EmployeeID', axis=1)
        
        X = df.drop(target_col, axis=1) if target_col in df.columns else df
        y = df[target_col] if target_col in df.columns else None
        
        self.numerical_features = X.select_dtypes(include=['int64', 'float64']).columns.tolist()
        self.categorical_features = X.select_dtypes(include=['object', 'category']).columns.tolist()
        
        print(f"数值特征 ({len(self.numerical_features)}): {self.numerical_features}")
        print(f"类别特征 ({len(self.categorical_features)}): {self.categorical_features}")
        
        numerical_transformer = Pipeline(steps=[
            ('imputer', SimpleImputer(strategy='median')),
            ('scaler', self.scaler)
        ])
        
        categorical_transformer = Pipeline(steps=[
            ('imputer', SimpleImputer(strategy='most_frequent')),
            ('onehot', self.onehot_encoder)
        ])
        
        self.preprocessor = ColumnTransformer(
            transformers=[
                ('num', numerical_transformer, self.numerical_features),
                ('cat', categorical_transformer, self.categorical_features)
            ])
        
        X_transformed = self.preprocessor.fit_transform(X)
        
        self._get_feature_names()
        
        X_transformed_df = pd.DataFrame(X_transformed, columns=self.feature_names)
        
        return X_transformed_df, y
    
    def transform(self, df, target_col='Attrition'):
        df = df.copy()
        
        if 'EmployeeID' in df.columns:
            df = df.drop('EmployeeID', axis=1)
        
        X = df.drop(target_col, axis=1) if target_col in df.columns else df
        y = df[target_col] if target_col in df.columns else None
        
        X_transformed = self.preprocessor.transform(X)
        X_transformed_df = pd.DataFrame(X_transformed, columns=self.feature_names)
        
        return X_transformed_df, y
    
    def _get_feature_names(self):
        num_features = self.numerical_features
        cat_features = self.preprocessor.named_transformers_['cat']['onehot'].get_feature_names_out(self.categorical_features)
        self.feature_names = list(num_features) + list(cat_features)
    
    def get_feature_names(self):
        return self.feature_names
    
    def create_additional_features(self, df):
        df = df.copy()
        
        df['TotalSatisfaction'] = df['JobSatisfaction'] + df['EnvironmentSatisfaction'] + df['RelationshipSatisfaction']
        
        df['YearsPerRole'] = df['YearsAtCompany'] / (df['YearsInCurrentRole'] + 1)
        
        df['IncomePerYear'] = df['MonthlyIncome'] / (df['YearsAtCompany'] + 1)
        
        df['PromotionFrequency'] = df['NumPromotions'] / (df['YearsAtCompany'] + 1)
        
        df['OvertimeRisk'] = (df['OverTime'] == 'Yes').astype(int) * (df['AverageMonthlyHours'] > 180).astype(int)
        
        df['LowSatisfactionFlag'] = (df['JobSatisfaction'] <= 2).astype(int)
        
        df['CareerStagnation'] = (df['YearsSinceLastPromotion'] >= 4).astype(int)
        
        return df


if __name__ == "__main__":
    from data_generator import generate_hr_data
    
    df = generate_hr_data(num_samples=1000)
    
    fe = FeatureEngineering(scaling_method='standard')
    
    df_enhanced = fe.create_additional_features(df)
    
    X_processed, y = fe.fit_transform(df_enhanced)
    
    print(f"\n处理后特征形状: {X_processed.shape}")
    print(f"\n特征名称: {fe.get_feature_names()}")
    print(f"\n处理后数据前5行:")
    print(X_processed.head())
