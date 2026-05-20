import os
import argparse
import sys
from predict import AirQualityPredictor


def main():
    parser = argparse.ArgumentParser(description='城市空气质量预测系统')
    parser.add_argument('--mode', type=str, default='predict',
                        choices=['generate_data', 'train', 'predict', 'full',
                                 'source_analysis', 'regional_predict', 'historical_analysis', 'full_analysis'],
                        help='运行模式')
    parser.add_argument('--data_path', type=str, default='data/air_quality_data.csv',
                        help='数据文件路径')
    parser.add_argument('--model_path', type=str, default='models/aqi_seq2seq.h5',
                        help='模型文件路径')
    parser.add_argument('--output_path', type=str, default='predictions/aqi_predictions.csv',
                        help='预测结果输出路径')
    parser.add_argument('--city', type=str, default=None,
                        help='目标城市名称')
    parser.add_argument('--years_back', type=int, default=3,
                        help='历史分析回溯年数')

    args = parser.parse_args()

    predictor = AirQualityPredictor(model_path=args.model_path, city=args.city)

    if args.mode == 'generate_data':
        print("=== 生成多城市示例数据 ===")
        from generate_sample_data import main as generate_data
        generate_data()

    elif args.mode == 'train':
        print("=== 训练Seq2Seq模型 ===")
        if not os.path.exists(args.data_path):
            print(f"数据文件不存在: {args.data_path}")
            print("请先运行 --mode generate_data 生成示例数据")
            sys.exit(1)
        predictor.train(args.data_path, args.model_path)

    elif args.mode == 'predict':
        print("=== 进行24小时空气质量预测 ===")
        if not os.path.exists(args.model_path):
            print(f"模型文件不存在: {args.model_path}")
            print("请先运行 --mode train 训练模型")
            sys.exit(1)
        predictor.load_model(args.model_path)
        result = predictor.predict_with_advice(args.data_path)
        predictor.print_prediction_report(result)
        predictor.save_predictions(result, args.output_path)

    elif args.mode == 'full':
        print("=== 完整流程：生成数据 -> 训练模型 -> 预测 ===")
        from generate_sample_data import main as generate_data
        generate_data()
        print("\n" + "=" * 80 + "\n")
        predictor.train(args.data_path, args.model_path)
        print("\n" + "=" * 80 + "\n")
        result = predictor.predict_with_advice(args.data_path)
        predictor.print_prediction_report(result)
        predictor.save_predictions(result, args.output_path)

    elif args.mode == 'source_analysis':
        print("=== 污染源解析分析 ===")
        predictor.analyze_sources()

    elif args.mode == 'regional_predict':
        print("=== 区域联动预测 ===")
        if not os.path.exists(args.model_path):
            print(f"模型文件不存在: {args.model_path}")
            print("请先运行 --mode train 训练模型")
            sys.exit(1)
        predictor.load_model(args.model_path)
        predictor.predict_with_regional(args.data_path, args.city)

    elif args.mode == 'historical_analysis':
        print("=== 历史重演分析 ===")
        predictor.analyze_history(years_back=args.years_back)

    elif args.mode == 'full_analysis':
        print("=== 综合分析：源解析 + 区域预测 + 历史分析 ===")
        if not os.path.exists(args.model_path):
            print(f"模型文件不存在: {args.model_path}")
            print("请先运行 --mode train 训练模型")
            sys.exit(1)
        predictor.load_model(args.model_path)
        predictor.full_analysis(args.data_path, args.city)


if __name__ == '__main__':
    main()
