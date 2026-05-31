import numpy as np
import pandas as pd
from typing import Tuple, Optional, Dict, List


SKILL_GROUPS = {
    'novice': {'name': '新手', 'range': (0.1, 0.35), 'color': '#3b82f6'},
    'intermediate': {'name': '普通', 'range': (0.35, 0.65), 'color': '#22c55e'},
    'expert': {'name': '高手', 'range': (0.65, 1.0), 'color': '#f97316'},
}

SKILL_GROUP_ORDER = ['novice', 'intermediate', 'expert']


def generate_level_design_params(n_levels: int = 200, random_state: int = 42) -> pd.DataFrame:
    np.random.seed(random_state)
    
    level_ids = [f"Level_{i+1:03d}" for i in range(n_levels)]
    
    obstacle_density = np.random.uniform(0.05, 0.45, n_levels)
    time_limit = np.random.randint(30, 180, n_levels)
    enemy_count = np.random.randint(0, 15, n_levels)
    platform_gap = np.random.uniform(0.5, 3.0, n_levels)
    moving_obstacle_ratio = np.random.uniform(0.0, 0.8, n_levels)
    powerup_count = np.random.randint(0, 5, n_levels)
    checkpoint_count = np.random.randint(0, 4, n_levels)
    level_length = np.random.randint(50, 300, n_levels)
    
    df = pd.DataFrame({
        'level_id': level_ids,
        'obstacle_density': obstacle_density,
        'time_limit': time_limit,
        'enemy_count': enemy_count,
        'platform_gap': platform_gap,
        'moving_obstacle_ratio': moving_obstacle_ratio,
        'powerup_count': powerup_count,
        'checkpoint_count': checkpoint_count,
        'level_length': level_length
    })
    
    return df


def calculate_difficulty_metrics_by_group(df: pd.DataFrame, random_state: int = 42) -> pd.DataFrame:
    np.random.seed(random_state)
    n_levels = len(df)
    
    base_completion_rate = 0.8
    base_attempts = 2.0
    base_avg_time = df['time_limit'] * 0.6
    
    obstacle_effect = df['obstacle_density'] * 1.2
    time_pressure_effect = (180 - df['time_limit']) / 180 * 0.8
    enemy_effect = df['enemy_count'] / 15 * 0.9
    gap_effect = (df['platform_gap'] - 0.5) / 2.5 * 0.5
    moving_effect = df['moving_obstacle_ratio'] * 0.7
    powerup_help = df['powerup_count'] / 5 * 0.3
    checkpoint_help = df['checkpoint_count'] / 4 * 0.25
    length_effect = (df['level_length'] - 50) / 250 * 0.4
    
    base_difficulty = (
        obstacle_effect +
        time_pressure_effect +
        enemy_effect +
        gap_effect +
        moving_effect +
        length_effect -
        powerup_help -
        checkpoint_help
    ) / 7.0
    base_difficulty = np.clip(base_difficulty, 0, 1)
    
    df_result = df.copy()
    df_result['base_difficulty_score'] = base_difficulty
    
    group_multipliers = {
        'novice': {'difficulty': 1.8, 'attempts': 2.0, 'time': 1.5},
        'intermediate': {'difficulty': 1.0, 'attempts': 1.0, 'time': 1.0},
        'expert': {'difficulty': 0.6, 'attempts': 0.5, 'time': 0.7},
    }
    
    for group, mult in group_multipliers.items():
        group_difficulty = np.clip(base_difficulty * mult['difficulty'], 0, 1)
        
        completion_rate = base_completion_rate - group_difficulty * 0.75
        completion_rate = np.clip(completion_rate + np.random.normal(0, 0.05, n_levels), 0.05, 0.98)
        
        avg_attempts = base_attempts + group_difficulty * 8.0 * mult['attempts']
        avg_attempts = np.clip(avg_attempts + np.random.normal(0, 0.5, n_levels), 1.0, 20.0)
        
        avg_completion_time = base_avg_time * (1 + group_difficulty * 0.3) * mult['time']
        avg_completion_time = np.clip(avg_completion_time + np.random.normal(0, 5, n_levels), 10, df['time_limit'])
        
        quit_rate = group_difficulty * 0.6
        quit_rate = np.clip(quit_rate + np.random.normal(0, 0.03, n_levels), 0.01, 0.85)
        
        perfect_clear_rate = (1 - group_difficulty) * 0.4 / mult['difficulty']
        perfect_clear_rate = np.clip(perfect_clear_rate + np.random.normal(0, 0.02, n_levels), 0, 0.8)
        
        df_result[f'{group}_completion_rate'] = completion_rate
        df_result[f'{group}_avg_attempts'] = avg_attempts
        df_result[f'{group}_avg_time'] = avg_completion_time
        df_result[f'{group}_quit_rate'] = quit_rate
        df_result[f'{group}_perfect_rate'] = perfect_clear_rate
    
    return df_result


def generate_behavioral_features(df_levels: pd.DataFrame, random_state: int = 42) -> pd.DataFrame:
    np.random.seed(random_state)
    n_levels = len(df_levels)
    
    df = df_levels.copy()
    
    for group in SKILL_GROUP_ORDER:
        difficulty_col = 'base_difficulty_score'
        
        death_zone_1 = df[difficulty_col] * df['obstacle_density'] * 0.3
        death_zone_1 += np.random.normal(0, 0.02, n_levels)
        death_zone_1 = np.clip(death_zone_1, 0, 0.8)
        
        death_zone_2 = df[difficulty_col] * df['enemy_count'] / 15 * 0.25
        death_zone_2 += np.random.normal(0, 0.02, n_levels)
        death_zone_2 = np.clip(death_zone_2, 0, 0.7)
        
        death_zone_3 = df[difficulty_col] * df['platform_gap'] / 3 * 0.2
        death_zone_3 += np.random.normal(0, 0.02, n_levels)
        death_zone_3 = np.clip(death_zone_3, 0, 0.6)
        
        death_zone_4 = df[difficulty_col] * (180 - df['time_limit']) / 180 * 0.15
        death_zone_4 += np.random.normal(0, 0.02, n_levels)
        death_zone_4 = np.clip(death_zone_4, 0, 0.5)
        
        death_zone_5 = df[difficulty_col] * df['moving_obstacle_ratio'] * 0.25
        death_zone_5 += np.random.normal(0, 0.02, n_levels)
        death_zone_5 = np.clip(death_zone_5, 0, 0.65)
        
        total_deaths = death_zone_1 + death_zone_2 + death_zone_3 + death_zone_4 + death_zone_5
        total_deaths = total_deaths / total_deaths.max() * 0.9
        
        frustration_points = (
            death_zone_1 * 1.2 +
            death_zone_2 * 1.5 +
            death_zone_3 * 1.3 +
            death_zone_4 * 1.8 +
            death_zone_5 * 1.4
        )
        frustration_points = np.clip(frustration_points + np.random.normal(0, 0.03, n_levels), 0, 1)
        
        consecutive_fail_rate = df[f'{group}_quit_rate'] * 0.7
        consecutive_fail_rate = np.clip(consecutive_fail_rate + np.random.normal(0, 0.02, n_levels), 0, 0.8)
        
        rage_quit_rate = df[f'{group}_quit_rate'] * frustration_points * 0.5
        rage_quit_rate = np.clip(rage_quit_rate + np.random.normal(0, 0.01, n_levels), 0, 0.5)
        
        checkpoint_utilization = 1 - df[f'{group}_quit_rate'] * 0.3
        checkpoint_utilization = np.clip(checkpoint_utilization + np.random.normal(0, 0.02, n_levels), 0.2, 1.0)
        
        avg_death_position = np.where(
            total_deaths > 0.1,
            0.3 + df['base_difficulty_score'] * 0.4,
            0.7
        )
        avg_death_position += np.random.normal(0, 0.05, n_levels)
        avg_death_position = np.clip(avg_death_position, 0.05, 0.95)
        
        death_concentration = np.max([death_zone_1, death_zone_2, death_zone_3, death_zone_4, death_zone_5], axis=0)
        death_concentration = death_concentration / (total_deaths + 0.001)
        death_concentration = np.clip(death_concentration, 0.1, 0.9)
        
        df[f'{group}_death_zone_1'] = death_zone_1
        df[f'{group}_death_zone_2'] = death_zone_2
        df[f'{group}_death_zone_3'] = death_zone_3
        df[f'{group}_death_zone_4'] = death_zone_4
        df[f'{group}_death_zone_5'] = death_zone_5
        df[f'{group}_total_death_density'] = total_deaths
        df[f'{group}_frustration_index'] = frustration_points
        df[f'{group}_consecutive_fail_rate'] = consecutive_fail_rate
        df[f'{group}_rage_quit_rate'] = rage_quit_rate
        df[f'{group}_checkpoint_utilization'] = checkpoint_utilization
        df[f'{group}_avg_death_position'] = avg_death_position
        df[f'{group}_death_concentration'] = death_concentration
    
    return df


def assign_skill_group(skill_value: float) -> str:
    for group, info in SKILL_GROUPS.items():
        low, high = info['range']
        if low <= skill_value < high:
            return group
    return 'intermediate'


def generate_player_level_data(df_levels: pd.DataFrame, n_players: int = 1000, random_state: int = 42) -> pd.DataFrame:
    np.random.seed(random_state)
    
    player_ids = [f"Player_{i+1:04d}" for i in range(n_players)]
    skill_level = np.random.normal(0.5, 0.2, n_players)
    skill_level = np.clip(skill_level, 0.1, 1.0)
    skill_groups = [assign_skill_group(s) for s in skill_level]
    
    player_records = []
    
    for i, player_id in enumerate(player_ids):
        player_skill = skill_level[i]
        player_group = skill_groups[i]
        
        n_levels_played = np.random.randint(5, min(50, len(df_levels)))
        played_levels = np.random.choice(df_levels['level_id'], n_levels_played, replace=False)
        
        for level_id in played_levels:
            level_data = df_levels[df_levels['level_id'] == level_id].iloc[0]
            
            base_completion = level_data[f'{player_group}_completion_rate']
            base_attempts = level_data[f'{player_group}_avg_attempts']
            base_time = level_data[f'{player_group}_avg_time']
            
            skill_deviation = (player_skill - np.mean(SKILL_GROUPS[player_group]['range'])) / 0.25
            effective_completion = np.clip(base_completion + skill_deviation * 0.15, 0.05, 0.98)
            effective_attempts = np.clip(base_attempts * (1 - skill_deviation * 0.2), 1, 20)
            
            attempts = max(1, int(np.random.poisson(effective_attempts)))
            completed = np.random.random() < effective_completion
            completed = completed if attempts <= 20 else False
            
            if completed:
                completion_time = min(
                    level_data['time_limit'],
                    np.random.normal(base_time, base_time * 0.15)
                )
                perfect = np.random.random() < level_data[f'{player_group}_perfect_rate']
            else:
                completion_time = None
                perfect = False
            
            frustration = level_data[f'{player_group}_frustration_index']
            is_rage_quit = (not completed) and (attempts >= 5) and (np.random.random() < frustration * 0.5)
            
            death_positions = []
            if attempts > 1:
                n_deaths = min(attempts - 1, 10)
                death_positions = np.random.beta(2, 2, n_deaths).tolist()
                if level_data[f'{player_group}_death_concentration'] > 0.5:
                    hot_spot = level_data[f'{player_group}_avg_death_position']
                    death_positions = [hot_spot + np.random.normal(0, 0.1) for _ in death_positions]
                    death_positions = np.clip(death_positions, 0.05, 0.95).tolist()
            
            player_records.append({
                'player_id': player_id,
                'level_id': level_id,
                'player_skill': player_skill,
                'skill_group': player_group,
                'attempts': attempts,
                'completed': completed,
                'completion_time': completion_time,
                'perfect_clear': perfect,
                'is_rage_quit': is_rage_quit if not completed else False,
                'death_positions': death_positions,
                'num_deaths': attempts - 1 if completed else attempts,
                'play_date': pd.Timestamp.now() - pd.Timedelta(days=np.random.randint(0, 60))
            })
    
    return pd.DataFrame(player_records)


def aggregate_level_metrics(df_players: pd.DataFrame) -> pd.DataFrame:
    level_metrics = df_players.groupby('level_id').agg(
        total_plays=('player_id', 'count'),
        unique_players=('player_id', 'nunique'),
        actual_completion_rate=('completed', 'mean'),
        actual_avg_attempts=('attempts', 'mean'),
        actual_quit_rate=('attempts', lambda x: (x >= 10).mean()),
        actual_avg_time=('completion_time', lambda x: x.dropna().mean()),
        actual_perfect_rate=('perfect_clear', 'mean'),
        actual_rage_quit_rate=('is_rage_quit', 'mean'),
        avg_num_deaths=('num_deaths', lambda x: x[x > 0].mean() if len(x[x > 0]) > 0 else 0),
    ).reset_index()
    
    for group in SKILL_GROUP_ORDER:
        group_data = df_players[df_players['skill_group'] == group]
        group_agg = group_data.groupby('level_id').agg(
            **{
                f'actual_{group}_completion_rate': ('completed', 'mean'),
                f'actual_{group}_avg_attempts': ('attempts', 'mean'),
                f'actual_{group}_quit_rate': ('attempts', lambda x: (x >= 10).mean()),
                f'actual_{group}_rage_quit_rate': ('is_rage_quit', 'mean'),
                f'actual_{group}_avg_time': ('completion_time', lambda x: x.dropna().mean()),
            }
        ).reset_index()
        
        level_metrics = level_metrics.merge(group_agg, on='level_id', how='left')
    
    return level_metrics


def generate_full_dataset(n_levels: int = 200, n_players: int = 1000, 
                          random_state: int = 42) -> Tuple[pd.DataFrame, pd.DataFrame]:
    df_params = generate_level_design_params(n_levels, random_state)
    df_metrics = calculate_difficulty_metrics_by_group(df_params, random_state)
    df_behavior = generate_behavioral_features(df_metrics, random_state)
    df_players = generate_player_level_data(df_behavior, n_players, random_state)
    df_aggregated = aggregate_level_metrics(df_players)
    
    df_final = df_behavior.merge(df_aggregated, on='level_id', how='left')
    
    return df_final, df_players


def save_datasets(df_levels: pd.DataFrame, df_players: pd.DataFrame, 
                  data_dir: str = "data") -> None:
    import os
    os.makedirs(data_dir, exist_ok=True)
    
    df_levels.to_csv(f"{data_dir}/level_data.csv", index=False)
    df_players.to_csv(f"{data_dir}/player_data.csv", index=False)
    
    print(f"数据已保存到 {data_dir}/ 目录")
    print(f"关卡数据: {len(df_levels)} 条, {len(df_levels.columns)} 个特征")
    print(f"玩家数据: {len(df_players)} 条")
    print(f"玩家分群: {df_players['skill_group'].value_counts().to_dict()}")


def load_datasets(data_dir: str = "data") -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
    import os
    
    level_path = f"{data_dir}/level_data.csv"
    player_path = f"{data_dir}/player_data.csv"
    
    df_levels = pd.read_csv(level_path) if os.path.exists(level_path) else None
    df_players = pd.read_csv(player_path) if os.path.exists(player_path) else None
    
    return df_levels, df_players


def get_target_columns_by_group(use_actual: bool = True) -> Dict[str, List[str]]:
    targets = {}
    for group in SKILL_GROUP_ORDER:
        if use_actual:
            targets[group] = [
                f'actual_{group}_completion_rate',
                f'actual_{group}_avg_attempts'
            ]
        else:
            targets[group] = [
                f'{group}_completion_rate',
                f'{group}_avg_attempts'
            ]
    return targets


if __name__ == "__main__":
    print("正在生成游戏关卡数据（含玩家分群和行为特征）...")
    df_levels, df_players = generate_full_dataset(n_levels=100, n_players=500)
    save_datasets(df_levels, df_players)
    
    print("\n关卡数据预览:")
    print(f"特征列数: {len(df_levels.columns)}")
    print(df_levels[['level_id', 'base_difficulty_score']].head())
    
    print("\n各分群难度指标示例（第一关）:")
    for group in SKILL_GROUP_ORDER:
        print(f"\n  {SKILL_GROUPS[group]['name']}:")
        print(f"    通关率: {df_levels.iloc[0][f'{group}_completion_rate']:.1%}")
        print(f"    平均尝试: {df_levels.iloc[0][f'{group}_avg_attempts']:.1f}")
        print(f"    挫败指数: {df_levels.iloc[0][f'{group}_frustration_index']:.2f}")
        print(f"    愤怒流失率: {df_levels.iloc[0][f'{group}_rage_quit_rate']:.1%}")
    
    print("\n玩家数据预览:")
    print(df_players[['player_id', 'level_id', 'skill_group', 'attempts', 'completed']].head())
    
    print("\n玩家分群分布:")
    print(df_players['skill_group'].value_counts())
