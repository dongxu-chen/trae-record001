#!/usr/bin/env python3
import os
import sys
import argparse
import json
from datetime import datetime
from web import app
from config import REPORTS_DIR


def main():
    parser = argparse.ArgumentParser(description='API模糊测试工具')
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    web_parser = subparsers.add_parser('web', help='启动Web界面')
    web_parser.add_argument('--host', default='0.0.0.0', help='监听地址')
    web_parser.add_argument('--port', type=int, default=5000, help='监听端口')
    web_parser.add_argument('--debug', action='store_true', help='调试模式')
    
    test_parser = subparsers.add_parser('test', help='命令行测试')
    test_parser.add_argument('--config', required=True, help='测试配置文件(JSON)')
    test_parser.add_argument('--mode', choices=['single', 'workflow', 'security'], default='single', help='测试模式')
    test_parser.add_argument('--test-mode', choices=['single', 'exhaustive', 'targeted'], default='single', help='参数测试模式')
    test_parser.add_argument('--max-combinations', type=int, default=100, help='最大组合数')
    test_parser.add_argument('--report-format', choices=['json', 'html', 'both'], default='both', help='报告格式')
    test_parser.add_argument('--output-dir', default=REPORTS_DIR, help='报告输出目录')
    test_parser.add_argument('--enable-evolution', action='store_true', help='启用用例演化')
    test_parser.add_argument('--quick', action='store_true', help='快速测试模式')
    
    ci_parser = subparsers.add_parser('ci', help='CI模式运行测试')
    ci_parser.add_argument('--config', required=True, help='测试配置文件(JSON)')
    ci_parser.add_argument('--mode', choices=['single', 'workflow', 'security'], default='security', help='测试模式')
    ci_parser.add_argument('--severity-threshold', choices=['high', 'medium', 'low'], default='medium', help='失败阈值')
    ci_parser.add_argument('--output', choices=['json', 'text'], default='json', help='输出格式')
    ci_parser.add_argument('--enable-evolution', action='store_true', help='启用用例演化')
    
    report_parser = subparsers.add_parser('report', help='生成报告')
    report_parser.add_argument('--input', required=True, help='测试结果JSON文件')
    report_parser.add_argument('--output', help='输出HTML报告路径')
    report_parser.add_argument('--format', choices=['html'], default='html', help='报告格式')
    
    generate_parser = subparsers.add_parser('generate', help='生成测试参数')
    generate_parser.add_argument('--name', required=True, help='参数名')
    generate_parser.add_argument('--type', default='string', help='参数类型')
    generate_parser.add_argument('--no-edge-cases', action='store_true', help='不包含边界值')
    generate_parser.add_argument('--no-injections', action='store_true', help='不包含注入载荷')
    generate_parser.add_argument('--no-type-mismatch', action='store_true', help='不包含类型不匹配')
    generate_parser.add_argument('--max-values', type=int, default=50, help='最大生成数量')
    
    args = parser.parse_args()
    
    if args.command == 'web':
        os.makedirs(REPORTS_DIR, exist_ok=True)
        print(f"启动Web界面: http://{args.host}:{args.port}")
        app.run(host=args.host, port=args.port, debug=args.debug)
    
    elif args.command == 'test':
        from core import TestEngine
        
        if not os.path.exists(args.config):
            print(f"配置文件不存在: {args.config}")
            sys.exit(1)
        
        with open(args.config, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        os.makedirs(args.output_dir, exist_ok=True)
        
        with TestEngine() as engine:
            def progress(current, total, message):
                percent = (current / total * 100) if total > 0 else 0
                print(f"\r进度: {current}/{total} ({percent:.1f}%) - {message}", end='')
            
            engine.set_progress_callback(progress)
            
            print(f"开始{args.mode}测试...")
            
            if args.mode == 'workflow':
                result = engine.run_workflow_test(config)
            else:
                result = engine.run_test(config, args.test_mode, args.max_combinations)
            
            print(f"\n\n测试完成!")
            print(f"总测试数: {result.total_tests}")
            print(f"通过: {result.passed_tests}")
            print(f"异常: {result.failed_tests}")
            print(f"通过率: {result.summary.get('pass_rate', 0):.1f}%")
            
            if args.report_format in ['json', 'both']:
                path = engine.save_report(result, 'json')
                print(f"JSON报告已保存: {path}")
            
            if args.report_format in ['html', 'both']:
                path = engine.save_report(result, 'html')
                print(f"HTML报告已保存: {path}")
            
            if result.summary.get('recommendations'):
                print(f"\n修复建议:")
                for rec in result.summary['recommendations']:
                    print(f"  - {rec}")
    
    elif args.command == 'ci':
        from core import TestEngine
        
        if not os.path.exists(args.config):
            if args.output == 'json':
                print(json.dumps({'error': f'Config file not found: {args.config}', 'overall_risk': 'high'}, indent=2))
            else:
                print(f"配置文件不存在: {args.config}")
            sys.exit(1)
        
        with open(args.config, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        with TestEngine() as engine:
            if args.mode == 'security':
                result = engine.run_security_scan(config, quick=args.quick if hasattr(args, 'quick') else False)
            elif args.mode == 'workflow':
                result = engine.run_workflow_test(config)
            else:
                result = engine.run_test(config, 'single', 50)
            
            if args.enable_evolution and result.failed_tests > 0:
                evolved_results = engine.run_case_evolution(result)
                result.test_cases.extend(evolved_results.test_cases)
            
            security_report = engine.get_security_report()
            
            if args.output == 'json':
                output = {
                    'timestamp': datetime.now().isoformat(),
                    'test_mode': args.mode,
                    'total_tests': result.total_tests,
                    'passed_tests': result.passed_tests,
                    'failed_tests': result.failed_tests,
                    'anomalies_count': result.summary.get('anomalies_count', 0),
                    'security_report': security_report,
                    'evolution_summary': engine.get_evolution_summary() if args.enable_evolution else None,
                    'overall_risk': security_report.get('overall_risk', 'none')
                }
                print(json.dumps(output, indent=2, ensure_ascii=False))
            else:
                print(f"\n=== CI 测试结果 ===")
                print(f"总测试数: {result.total_tests}")
                print(f"通过: {result.passed_tests}")
                print(f"异常: {result.failed_tests}")
                print(f"整体风险等级: {security_report.get('overall_risk', 'none').upper()}")
            
            risk_level = security_report.get('overall_risk', 'none')
            threshold_order = {'high': 3, 'medium': 2, 'low': 1, 'none': 0}
            if threshold_order.get(risk_level, 0) >= threshold_order.get(args.severity_threshold, 0):
                sys.exit(1)
    
    elif args.command == 'report':
        from core import TestEngine
        
        if not os.path.exists(args.input):
            print(f"输入文件不存在: {args.input}")
            sys.exit(1)
        
        with open(args.input, 'r', encoding='utf-8') as f:
            test_data = json.load(f)
        
        output_path = args.output or args.input.replace('.json', '.html')
        TestEngine.generate_html_report_from_json(test_data, output_path)
        print(f"HTML报告已生成: {output_path}")
    
    elif args.command == 'generate':
        from core import ParameterGenerator
        
        generator = ParameterGenerator()
        values = generator.generate_values(
            param_name=args.name,
            param_type=args.type,
            include_edge_cases=not args.no_edge_cases,
            include_injections=not args.no_injections,
            include_type_mismatch=not args.no_type_mismatch,
            max_values=args.max_values
        )
        
        print(f"为参数 '{args.name}' (类型: {args.type}) 生成了 {len(values)} 个测试值:\n")
        
        for i, v in enumerate(values, 1):
            print(f"{i:3d}. [{v['type']:15s}] {repr(v['value']):50s} - {v['description']}")
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
