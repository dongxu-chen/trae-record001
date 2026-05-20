import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from config import Config
from data_preprocessing import AirQualityDataProcessor
from model import AirQualitySeq2Seq
from health_advice import HealthAdvisor
from source_apportionment import SourceApportionment
from regional_prediction import RegionalPrediction
from historical_analysis import HistoricalAnalysis


class AirQualityPredictor:
    def __init__(self, model_path=None, city=None):
        self.config = Config()
        self.processor = AirQualityDataProcessor()
        self.advisor = HealthAdvisor()
        self.source_analyzer = SourceApportionment()
        self.regional_predictor = RegionalPrediction()
        self.historical_analyzer = HistoricalAnalysis()
        self.model = None
        self.model_path = model_path or 'models/aqi_seq2seq.h5'
        self.city = city or self.config.DEFAULT_CITY
        self.city_data = {}

    def train(self, data_path, model_path=None):
        model_path = model_path or self.model_path
        print(f"正在加载数据: {data_path}")
        df = self.processor.load_data(data_path)
        print(f"数据加载完成，共 {len(df)} 条记录")

        print("正在预处理数据...")
        data = self.processor.preprocess(df)
        X_train, y_train = data['X_train'], data['y_train']
        X_val, y_val = data['X_val'], data['y_val']
        X_test, y_test = data['X_test'], data['y_test']

        print(f"训练集: {X_train.shape}, 验证集: {X_val.shape}, 测试集: {X_test.shape}")

        input_shape = (X_train.shape[1], X_train.shape[2])
        output_shape = (y_train.shape[1], y_train.shape[2])

        print(f"输入形状: {input_shape}, 输出形状: {output_shape}")

        print("正在构建Seq2Seq模型...")
        self.model = AirQualitySeq2Seq(input_shape, output_shape)
        self.model.model.summary()

        print("开始训练模型...")
        history = self.model.train(X_train, y_train, X_val, y_val, model_path)
        print("模型训练完成")

        print("正在评估模型...")
        loss, mae = self.model.evaluate(X_test, y_test)
        print(f"测试集 - Loss: {loss:.4f}, MAE: {mae:.4f}")

        return {
            'history': history,
            'test_loss': loss,
            'test_mae': mae,
            'data': data
        }

    def load_model(self, model_path=None):
        model_path = model_path or self.model_path
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"模型文件不存在: {model_path}")
        self.model = AirQualitySeq2Seq.load(model_path)
        print(f"模型已加载: {model_path}")
        return self.model

    def predict_next_24h(self, data_path, start_time=None):
        if self.model is None:
            if os.path.exists(self.model_path):
                self.load_model()
            else:
                raise ValueError("请先训练模型或指定已训练的模型路径")

        df = self.processor.load_data(data_path)
        df = self.processor.handle_missing_data(df)
        df['AQI'] = df.apply(self.processor.calculate_aqi, axis=1)

        data = self.processor.preprocess(df)
        X_pred = self.processor.prepare_prediction_data(df)

        predictions_scaled = self.model.predict(X_pred)
        predictions_scaled = predictions_scaled[0]

        predictions = data['target_scaler'].inverse_transform(predictions_scaled)

        if start_time is None:
            start_time = df['timestamp'].iloc[-1] + timedelta(hours=1)

        timestamps = [start_time + timedelta(hours=i) for i in range(self.config.PREDICTION_LENGTH)]

        predictions_df = pd.DataFrame(
            predictions,
            columns=self.config.TARGET_COLS,
            index=timestamps
        )
        predictions_df.index.name = 'timestamp'
        predictions_df.reset_index(inplace=True)

        predictions_df['AQI'] = predictions_df.apply(self.processor.calculate_aqi, axis=1)

        for col in ['PM2.5', 'PM10', 'SO2', 'NO2', 'O3']:
            predictions_df[col] = predictions_df[col].clip(lower=0)

        return predictions_df

    def predict_with_advice(self, data_path, start_time=None):
        predictions_df = self.predict_next_24h(data_path, start_time)
        hourly_advice = self.advisor.generate_hourly_advice(predictions_df)
        summary = self.advisor.generate_summary(predictions_df)

        return {
            'predictions': predictions_df,
            'hourly_advice': hourly_advice,
            'summary': summary
        }

    def print_prediction_report(self, result):
        predictions_df = result['predictions']
        summary = result['summary']
        hourly_advice = result['hourly_advice']

        print("\n" + "=" * 100)
        print(" " * 30 + "城市空气质量24小时预测报告")
        print("=" * 100)

        print(f"\n预测时间范围: {predictions_df['timestamp'].iloc[0]} ~ {predictions_df['timestamp'].iloc[-1]}")

        print("\n" + "-" * 100)
        print("📊 总体概况")
        print("-" * 100)
        print(f"  平均AQI: {summary['avg_aqi']} ({summary['avg_level']})")
        print(f"  最高AQI: {summary['max_aqi']} ({summary['max_level']})")
        print(f"  最低AQI: {summary['min_aqi']}")

        print("\n📅 空气质量时段分布:")
        for period in summary['time_periods']:
            print(f"    {period['start'].strftime('%m-%d %H:00')} - {period['end'].strftime('%m-%d %H:00')}: {period['level']}")

        advice = summary['overall_advice']
        print(f"\n📝 总体评价: {advice.get('summary', '')}")
        print(f"   {advice.get('general', '')}")

        print("\n" + "-" * 100)
        print("🌡️  综合健康建议")
        print("-" * 100)

        advice_categories = [
            ('🏃', '户外运动', 'outdoor_activity'),
            ('⚽', '体育锻炼', 'exercise'),
            ('🚗', '出行建议', 'travel'),
            ('🪟', '开窗通风', 'window'),
            ('😷', '口罩佩戴', 'mask'),
            ('👶', '儿童防护', 'children'),
            ('👴', '老人防护', 'elderly'),
            ('🫁', '呼吸道疾病患者', 'respiratory_patients'),
            ('❤️', '心脏病患者', 'heart_patients'),
            ('🤰', '孕妇防护', 'pregnant_women'),
            ('💼', '办公建议', 'office_workers'),
            ('🍽️', '用餐建议', 'dining'),
            ('👕', '着装建议', 'clothing'),
            ('🚲', '交通方式', 'transportation'),
            ('🌬️', '室内空气', 'home_air'),
            ('🌿', '绿植养护', 'plants'),
            ('😊', '情绪调节', 'emotion')
        ]

        for icon, label, key in advice_categories:
            if key in advice:
                print(f"  {icon} {label}: {advice[key]}")

        print("\n" + "-" * 100)
        print("⏰ 分时段详细预测")
        print("-" * 100)
        print(f"{'时间':<16} {'AQI':<8} {'等级':<10} {'PM2.5':<8} {'PM10':<8} {'SO2':<8} {'NO2':<8} {'O3':<8}")
        print("-" * 100)

        for item in hourly_advice:
            time_str = item['time'].strftime('%m-%d %H:00')
            print(f"{time_str:<16} {item['aqi']:<8} {item['level']:<10} {item['pm25']:<8} {item['pm10']:<8} {item['so2']:<8} {item['no2']:<8} {item['o3']:<8}")

        print("\n" + "=" * 100)
        print("💡 温馨提示: 请根据实时空气质量调整活动安排，保护好自己和家人的健康！")
        print("=" * 100)

    def save_predictions(self, result, output_path='predictions/aqi_predictions.csv'):
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        predictions_df = result['predictions']
        predictions_df.to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f"预测结果已保存到: {output_path}")

    def load_multi_city_data(self, data_dir='data'):
        print(f"正在加载多城市数据...")
        for city in self.config.CITIES:
            file_path = os.path.join(data_dir, f'air_quality_{city}.csv')
            if os.path.exists(file_path):
                df = self.processor.load_data(file_path)
                self.city_data[city] = df
                print(f"  已加载 {city}: {len(df)} 条记录")
            else:
                print(f"  未找到 {city} 的数据文件")
        return self.city_data

    def analyze_sources(self, df=None):
        if df is None:
            data_path = 'data/air_quality_data.csv'
            if os.path.exists(data_path):
                df = self.processor.load_data(data_path)
            else:
                raise FileNotFoundError("请提供数据或确保数据文件存在")

        print("正在进行污染源解析...")
        contribution_df = self.source_analyzer.calculate_source_contributions(df)
        source_report = self.source_analyzer.generate_source_report(df, contribution_df)
        self.source_analyzer.print_source_report(source_report)

        return {
            'contribution_df': contribution_df,
            'source_report': source_report
        }

    def predict_with_regional(self, data_path=None, target_city=None, start_time=None):
        target_city = target_city or self.city

        if not self.city_data:
            self.load_multi_city_data()

        if target_city not in self.city_data:
            raise ValueError(f"未找到城市 {target_city} 的数据")

        result = self.predict_with_advice(data_path, start_time)
        base_predictions = result['predictions']

        print(f"\n正在进行区域联动预测分析 ({target_city})...")
        adjusted_predictions, regional_contributions = self.regional_predictor.generate_regional_prediction(
            target_city, self.city_data, base_predictions
        )

        adjusted_predictions['AQI'] = adjusted_predictions.apply(self.processor.calculate_aqi, axis=1)

        self.regional_predictor.print_regional_report(target_city, regional_contributions, adjusted_predictions)

        result['base_predictions'] = base_predictions
        result['adjusted_predictions'] = adjusted_predictions
        result['regional_contributions'] = regional_contributions

        return result

    def analyze_history(self, df=None, target_date=None, years_back=3):
        if df is None:
            data_path = 'data/air_quality_data.csv'
            if os.path.exists(data_path):
                df = self.processor.load_data(data_path)
            else:
                raise FileNotFoundError("请提供数据或确保数据文件存在")

        if target_date is None:
            target_date = df['timestamp'].iloc[-1] - timedelta(days=30)

        print(f"正在进行历史重演分析 (目标日期: {target_date.date()})...")
        comparison_result = self.historical_analyzer.compare_with_history(
            df, target_date, target_period_hours=24, years_back=years_back
        )
        self.historical_analyzer.print_historical_report(comparison_result)

        print("\n正在进行长期趋势分析...")
        trend_data, trends = self.historical_analyzer.analyze_trend(df, period='M')
        self.historical_analyzer.print_trend_report(trend_data, trends)

        return {
            'comparison_result': comparison_result,
            'trend_data': trend_data,
            'trends': trends
        }

    def full_analysis(self, data_path=None, city=None):
        city = city or self.city
        print("=" * 100)
        print(" " * 35 + "城市空气质量综合分析报告")
        print("=" * 100)
        print(f"\n分析城市: {city}")
        print(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        result = {}

        print("\n" + "-" * 100)
        result['source_analysis'] = self.analyze_sources()

        print("\n" + "-" * 100)
        result['prediction'] = self.predict_with_regional(data_path, city)

        print("\n" + "-" * 100)
        result['historical_analysis'] = self.analyze_history()

        self.print_prediction_report(result['prediction'])

        return result
