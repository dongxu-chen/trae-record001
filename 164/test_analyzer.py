from sales_analyzer import SalesAnalyzer


def run_test():
    print("=" * 60)
    print("电商销量数据分析系统 - 功能测试")
    print("=" * 60)
    
    try:
        analyzer = SalesAnalyzer('test_sales_data.csv')
        analyzer.run_full_analysis()
        
        print("\n" + "=" * 60)
        print("测试完成！请检查：")
        print("1. logs/ 目录下的日志文件")
        print("2. sales_report.txt 分析报告")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n测试出错: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_test()
