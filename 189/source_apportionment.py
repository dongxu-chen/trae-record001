import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.ensemble import RandomForestRegressor
from config import Config


class SourceApportionment:
    def __init__(self):
        self.config = Config()
        self.source_profiles = {
            '工业排放': {
                'PM2.5': 0.35,
                'PM10': 0.25,
                'SO2': 0.45,
                'NO2': 0.30,
                'O3': 0.10,
                'description': '以SO2和细颗粒物为特征，主要来自燃煤、工业生产过程'
            },
            '交通尾气': {
                'PM2.5': 0.40,
                'PM10': 0.20,
                'SO2': 0.10,
                'NO2': 0.55,
                'O3': 0.15,
                'description': '以NOx和碳氢化合物为特征，主要来自机动车尾气排放'
            },
            '扬尘污染': {
                'PM2.5': 0.25,
                'PM10': 0.60,
                'SO2': 0.05,
                'NO2': 0.10,
                'O3': 0.05,
                'description': '以粗颗粒物PM10为特征，主要来自建筑施工、道路扬尘'
            },
            '农业燃烧': {
                'PM2.5': 0.30,
                'PM10': 0.35,
                'SO2': 0.15,
                'NO2': 0.20,
                'O3': 0.25,
                'description': '以PM2.5和VOCs为特征，主要来自秸秆焚烧、农业活动'
            },
            '自然来源': {
                'PM2.5': 0.10,
                'PM10': 0.20,
                'SO2': 0.05,
                'NO2': 0.05,
                'O3': 0.70,
                'description': '以O3为特征，来自自然光化学反应、植被排放'
            },
            '二次生成': {
                'PM2.5': 0.55,
                'PM10': 0.30,
                'SO2': 0.20,
                'NO2': 0.35,
                'O3': 0.60,
                'description': '气态污染物在大气中经过化学反应生成的二次污染物'
            }
        }

    def calculate_source_contributions(self, df):
        pollutants = ['PM2.5', 'PM10', 'SO2', 'NO2', 'O3']
        results = []

        for idx, row in df.iterrows():
            concentrations = {p: max(row[p], 0) for p in pollutants}
            total_concentration = sum(concentrations.values())

            if total_concentration == 0:
                contributions = {source: 0 for source in self.source_profiles}
            else:
                contributions = {}
                for source_name, profile in self.source_profiles.items():
                    similarity = 0
                    for p in pollutants:
                        weight = profile[p]
                        obs_ratio = concentrations[p] / total_concentration if total_concentration > 0 else 0
                        similarity += weight * obs_ratio
                    contributions[source_name] = similarity

                total = sum(contributions.values())
                if total > 0:
                    contributions = {k: v / total * 100 for k, v in contributions.items()}

            contributions['timestamp'] = row['timestamp']
            contributions['AQI'] = row['AQI']
            results.append(contributions)

        contribution_df = pd.DataFrame(results)
        return contribution_df

    def identify_primary_sources(self, contribution_df, top_n=3):
        source_cols = [col for col in contribution_df.columns if col in self.source_profiles]
        avg_contributions = contribution_df[source_cols].mean()
        sorted_sources = avg_contributions.sort_values(ascending=False)
        return sorted_sources.head(top_n)

    def analyze_temporal_patterns(self, contribution_df):
        contribution_df = contribution_df.copy()
        contribution_df['hour'] = contribution_df['timestamp'].dt.hour
        contribution_df['month'] = contribution_df['timestamp'].dt.month
        contribution_df['weekday'] = contribution_df['timestamp'].dt.weekday

        source_cols = [col for col in contribution_df.columns if col in self.source_profiles]

        hourly_patterns = contribution_df.groupby('hour')[source_cols].mean()
        monthly_patterns = contribution_df.groupby('month')[source_cols].mean()
        weekday_patterns = contribution_df.groupby('weekday')[source_cols].mean()

        return {
            'hourly': hourly_patterns,
            'monthly': monthly_patterns,
            'weekday': weekday_patterns
        }

    def calculate_source_impact_on_aqi(self, df, contribution_df):
        merged = pd.merge(df[['timestamp', 'AQI']], contribution_df, on='timestamp')
        source_cols = [col for col in contribution_df.columns if col in self.source_profiles]

        correlations = {}
        for source in source_cols:
            corr = merged[source].corr(merged['AQI'])
            correlations[source] = corr

        sorted_correlations = sorted(correlations.items(), key=lambda x: abs(x[1]), reverse=True)
        return sorted_correlations

    def generate_source_report(self, df, contribution_df):
        primary_sources = self.identify_primary_sources(contribution_df)
        temporal_patterns = self.analyze_temporal_patterns(contribution_df)
        aqi_impacts = self.calculate_source_impact_on_aqi(df, contribution_df)

        report = {
            'summary': {},
            'primary_sources': primary_sources.to_dict(),
            'temporal_patterns': temporal_patterns,
            'aqi_impacts': dict(aqi_impacts),
            'source_details': {}
        }

        source_cols = [col for col in contribution_df.columns if col in self.source_profiles]
        for source in source_cols:
            avg_contrib = contribution_df[source].mean()
            max_contrib = contribution_df[source].max()
            report['source_details'][source] = {
                'average_contribution': round(avg_contrib, 2),
                'max_contribution': round(max_contrib, 2),
                'description': self.source_profiles[source]['description']
            }
            report['summary'][source] = round(avg_contrib, 2)

        return report

    def print_source_report(self, report):
        print("\n" + "=" * 80)
        print(" " * 25 + "污染源解析报告")
        print("=" * 80)

        print("\n📊 各污染源平均贡献比例:")
        for source, contrib in sorted(report['summary'].items(), key=lambda x: x[1], reverse=True):
            bar = '█' * int(contrib / 2)
            print(f"  {source:<10}: {contrib:>5.1f}% {bar}")

        print("\n🎯 主要污染源排名:")
        for i, (source, contrib) in enumerate(report['primary_sources'].items(), 1):
            print(f"  第{i}位: {source} - 平均贡献 {contrib:.1f}%")
            print(f"      {self.source_profiles[source]['description']}")

        print("\n📈 污染源对AQI的影响程度（相关系数）:")
        for source, corr in report['aqi_impacts'].items():
            impact = "强正相关" if corr > 0.6 else "中等正相关" if corr > 0.3 else "弱相关" if corr > 0 else "负相关"
            print(f"  {source:<10}: {corr:+.3f} ({impact})")

        print("\n🕐 交通尾气小时变化特征:")
        hourly = report['temporal_patterns']['hourly']
        peak_hours = hourly['交通尾气'].nlargest(3)
        print(f"  高峰时段: {', '.join([f'{h}:00' for h in peak_hours.index])}")
        low_hours = hourly['交通尾气'].nsmallest(3)
        print(f"  低谷时段: {', '.join([f'{h}:00' for h in low_hours.index])}")

        print("\n" + "=" * 80)

    def plot_source_contributions(self, contribution_df, save_path=None):
        try:
            import matplotlib.pyplot as plt
            import seaborn as sns

            source_cols = [col for col in contribution_df.columns if col in self.source_profiles]
            avg_contrib = contribution_df[source_cols].mean()

            fig, axes = plt.subplots(2, 2, figsize=(15, 12))

            colors = plt.cm.Set3(np.linspace(0, 1, len(source_cols)))
            axes[0, 0].pie(avg_contrib, labels=avg_contrib.index, autopct='%1.1f%%', colors=colors)
            axes[0, 0].set_title('各污染源平均贡献比例')

            avg_contrib.sort_values().plot(kind='barh', ax=axes[0, 1], color=colors)
            axes[0, 1].set_title('污染源贡献排序')
            axes[0, 1].set_xlabel('贡献比例 (%)')

            contribution_df['hour'] = contribution_df['timestamp'].dt.hour
            hourly = contribution_df.groupby('hour')[source_cols].mean()
            hourly.plot(kind='line', ax=axes[1, 0], marker='o')
            axes[1, 0].set_title('污染源日变化特征')
            axes[1, 0].set_xlabel('小时')
            axes[1, 0].set_ylabel('贡献比例 (%)')
            axes[1, 0].legend(bbox_to_anchor=(1.05, 1), loc='upper left')

            contribution_df['month'] = contribution_df['timestamp'].dt.month
            monthly = contribution_df.groupby('month')[source_cols].mean()
            monthly.plot(kind='area', stacked=True, ax=axes[1, 1], alpha=0.7)
            axes[1, 1].set_title('污染源季节变化特征')
            axes[1, 1].set_xlabel('月份')
            axes[1, 1].set_ylabel('贡献比例 (%)')
            axes[1, 1].legend(bbox_to_anchor=(1.05, 1), loc='upper left')

            plt.tight_layout()
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                print(f"图表已保存到: {save_path}")
            plt.close()

        except ImportError:
            print("需要安装matplotlib和seaborn才能绘图")
