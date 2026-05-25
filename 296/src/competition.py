import pandas as pd
import numpy as np
from typing import Dict, List, Callable, Optional, Tuple
from datetime import datetime
import json
import os
import warnings
warnings.filterwarnings('ignore')


class TimeSeriesCompetition:
    def __init__(self, competition_name: str = "TimeSeries_Challenge"):
        self.competition_name = competition_name
        self.leaderboard = pd.DataFrame(columns=[
            'rank', 'team_name', 'model_name', 'rmse', 'mae', 'mape',
            'submission_time', 'description'
        ])
        self.submissions = []
        self.public_leaderboard = pd.DataFrame()
        self.private_leaderboard = pd.DataFrame()

    def evaluate_submission(self, y_true: pd.Series, y_pred: np.ndarray) -> Dict:
        from sklearn.metrics import mean_absolute_error, mean_squared_error, mean_absolute_percentage_error
        
        y_pred_aligned = y_pred[:len(y_true)]
        
        metrics = {
            'rmse': np.sqrt(mean_squared_error(y_true, y_pred_aligned)),
            'mae': mean_absolute_error(y_true, y_pred_aligned),
            'mape': mean_absolute_percentage_error(y_true, y_pred_aligned) * 100
        }
        return metrics

    def submit_model(self, team_name: str, model_name: str,
                     y_pred: np.ndarray, y_true: pd.Series,
                     description: str = "") -> Dict:
        metrics = self.evaluate_submission(y_true, y_pred)
        
        submission = {
            'team_name': team_name,
            'model_name': model_name,
            'rmse': metrics['rmse'],
            'mae': metrics['mae'],
            'mape': metrics['mape'],
            'submission_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'description': description,
            'predictions': y_pred.tolist()
        }
        
        self.submissions.append(submission)
        self._update_leaderboard()
        
        return {
            'status': 'success',
            'metrics': metrics,
            'current_rank': self._get_team_rank(team_name)
        }

    def _update_leaderboard(self):
        if not self.submissions:
            return
        
        best_submissions = {}
        for sub in self.submissions:
            team = sub['team_name']
            if team not in best_submissions or sub['rmse'] < best_submissions[team]['rmse']:
                best_submissions[team] = sub
        
        leaderboard_data = []
        for team, sub in best_submissions.items():
            leaderboard_data.append({
                'team_name': team,
                'model_name': sub['model_name'],
                'rmse': sub['rmse'],
                'mae': sub['mae'],
                'mape': sub['mape'],
                'submission_time': sub['submission_time'],
                'description': sub['description']
            })
        
        self.leaderboard = pd.DataFrame(leaderboard_data)
        self.leaderboard = self.leaderboard.sort_values('rmse').reset_index(drop=True)
        self.leaderboard.index = self.leaderboard.index + 1
        self.leaderboard.insert(0, 'rank', self.leaderboard.index)

    def _get_team_rank(self, team_name: str) -> int:
        if self.leaderboard.empty:
            return -1
        team_row = self.leaderboard[self.leaderboard['team_name'] == team_name]
        return team_row['rank'].values[0] if not team_row.empty else -1

    def get_leaderboard(self, top_n: int = None) -> pd.DataFrame:
        if top_n:
            return self.leaderboard.head(top_n)
        return self.leaderboard

    def get_team_submissions(self, team_name: str) -> List[Dict]:
        return [sub for sub in self.submissions if sub['team_name'] == team_name]

    def save_leaderboard(self, filepath: str):
        self.leaderboard.to_csv(filepath, index=False)
        
        submissions_file = os.path.splitext(filepath)[0] + '_submissions.json'
        with open(submissions_file, 'w', encoding='utf-8') as f:
            json.dump(self.submissions, f, ensure_ascii=False, indent=2)

    def load_leaderboard(self, filepath: str):
        if os.path.exists(filepath):
            self.leaderboard = pd.read_csv(filepath)
        
        submissions_file = os.path.splitext(filepath)[0] + '_submissions.json'
        if os.path.exists(submissions_file):
            with open(submissions_file, 'r', encoding='utf-8') as f:
                self.submissions = json.load(f)

    def get_competition_stats(self) -> Dict:
        if self.leaderboard.empty:
            return {}
        
        return {
            'total_teams': len(self.leaderboard),
            'total_submissions': len(self.submissions),
            'best_rmse': self.leaderboard['rmse'].min(),
            'mean_rmse': self.leaderboard['rmse'].mean(),
            'worst_rmse': self.leaderboard['rmse'].max(),
            'best_team': self.leaderboard.iloc[0]['team_name'] if len(self.leaderboard) > 0 else None
        }


class CustomModelSubmission:
    def __init__(self, model_func: Callable, model_name: str, team_name: str):
        self.model_func = model_func
        self.model_name = model_name
        self.team_name = team_name
        self.model = None

    def train_and_predict(self, y_train: pd.Series, X_train: pd.DataFrame,
                          horizon: int, X_test: pd.DataFrame = None) -> np.ndarray:
        self.model = self.model_func()
        self.model.fit(y_train, X_train)
        predictions = self.model.predict(horizon, X_test)
        return predictions
