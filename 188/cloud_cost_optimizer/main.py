import argparse
import logging
from datetime import date, timedelta
import json

from .app import CloudCostOptimizer
from .config import Settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="多云费用分析优化工具")
    parser.add_argument(
        "--mode",
        choices=["dashboard", "fetch", "analyze", "anomaly", "optimize", "allocate", "full", "budget", "ri", "forecast"],
        default="dashboard",
        help="运行模式",
    )
    parser.add_argument("--days", type=int, default=30, help="分析天数")
    parser.add_argument("--output", type=str, help="输出结果到文件")
    parser.add_argument("--provider", type=str, help="指定云厂商 (AWS/阿里云/腾讯云)")

    args = parser.parse_args()

    settings = Settings.from_env()
    settings.aws.enabled = True
    settings.aliyun.enabled = True
    settings.tencent.enabled = True

    optimizer = CloudCostOptimizer(settings)

    if args.mode == "dashboard":
        import subprocess
        import sys
        subprocess.run([
            sys.executable, "-m", "streamlit", "run",
            "cloud_cost_optimizer/streamlit_app.py",
            "--server.port=8501",
            "--server.address=0.0.0.0",
        ])

    elif args.mode == "fetch":
        logger.info(f"获取最近 {args.days} 天的账单数据...")
        end_date = date.today() + timedelta(days=1)
        start_date = end_date - timedelta(days=args.days)
        results = optimizer.fetch_and_store_billing_data(start_date, end_date)
        print(json.dumps(results, indent=2, ensure_ascii=False, default=str))
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False, default=str)

    elif args.mode == "analyze":
        logger.info(f"分析最近 {args.days} 天的费用趋势...")
        results = optimizer.run_trend_analysis()
        print(json.dumps(results, indent=2, ensure_ascii=False, default=str))
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False, default=str)

    elif args.mode == "anomaly":
        logger.info(f"检测最近 {args.days} 天的费用异常...")
        results = optimizer.run_anomaly_detection()
        print(json.dumps(results, indent=2, ensure_ascii=False, default=str))
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False, default=str)

    elif args.mode == "optimize":
        logger.info(f"分析最近 {args.days} 天的优化机会...")
        results = optimizer.run_optimization_analysis()
        print(json.dumps(results, indent=2, ensure_ascii=False, default=str))
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False, default=str)

    elif args.mode == "allocate":
        logger.info("执行费用分摊...")
        results = optimizer.run_cost_allocation()
        print(json.dumps(results, indent=2, ensure_ascii=False, default=str))
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False, default=str)

    elif args.mode == "full":
        logger.info(f"执行完整分析流程 (最近 {args.days} 天)...")
        results = optimizer.run_full_analysis(start_days=args.days)
        print(json.dumps(results, indent=2, ensure_ascii=False, default=str))
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False, default=str)

    elif args.mode == "budget":
        logger.info("执行预算分析...")
        results = optimizer.run_budget_analysis()
        print(json.dumps(results, indent=2, ensure_ascii=False, default=str))
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False, default=str)

    elif args.mode == "ri":
        logger.info(f"执行RI购买分析 (最近 {args.days} 天)...")
        results = optimizer.run_ri_analysis(analysis_days=args.days)
        print(json.dumps(results, indent=2, ensure_ascii=False, default=str))
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False, default=str)

    elif args.mode == "forecast":
        logger.info("执行费用预测...")
        results = optimizer.run_cost_forecast()
        print(json.dumps(results, indent=2, ensure_ascii=False, default=str))
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False, default=str)


if __name__ == "__main__":
    main()
