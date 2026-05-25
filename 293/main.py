#!/usr/bin/env python3
"""Dockerfile缓存分析工具 - 主入口"""

import argparse
import os
import sys
from pathlib import Path
from colorama import init, Fore, Style

from dockerfile_parser import DockerfileParser
from cache_analyzer import CacheAnalyzer
from optimizer import Optimizer, OptimizationSeverity
from size_analyzer import SizeAnalyzer
from build_time_predictor import BuildTimePredictor
from auto_optimizer import DockerfileAutoOptimizer
from ci_checker import CIChecker, CIProvider

init(autoreset=True)


def print_banner():
    banner = f"""
{Fore.CYAN}{Style.BRIGHT}
╔══════════════════════════════════════════════════════════════╗
║           Docker 镜像构建层缓存分析工具 v1.0                ║
║  Docker Layer Cache Analyzer & Optimization Tool           ║
╚══════════════════════════════════════════════════════════════╝
{Style.RESET_ALL}"""
    print(banner)


def analyze_dockerfile(dockerfile_path: str, context_path: str = None,
                       show_cache: bool = True, show_size: bool = True,
                       show_optimizations: bool = True, show_time: bool = True,
                       output_format: str = "text",
                       auto_optimize: bool = False,
                       optimize_output: str = None,
                       ci_mode: str = None):
    """分析Dockerfile"""
    if not os.path.exists(dockerfile_path):
        print(f"{Fore.RED}错误: Dockerfile 文件不存在: {dockerfile_path}")
        sys.exit(1)

    if ci_mode:
        return run_ci_check(dockerfile_path, context_path, ci_mode)

    print(f"{Fore.CYAN}📂 正在分析: {dockerfile_path}")
    if context_path:
        print(f"{Fore.CYAN}📂 上下文路径: {context_path}")

    parser = DockerfileParser(dockerfile_path, context_path)
    parser.analyze_stage_dependencies()

    print(f"\n{Fore.GREEN}✅ 解析完成:")
    print(f"   - 阶段数: {len(parser.stages)}")
    print(f"   - 总层数: {len(parser.get_all_layers())}")

    cross_copies = parser.get_cross_stage_copies()
    if cross_copies:
        print(f"   - 跨阶段COPY: {len(cross_copies)} 处")

    for i, stage in enumerate(parser.stages):
        stage_name = stage.name or f"stage-{i}"
        dep_info = ""
        if stage.dependent_stages:
            dep_names = [parser.stages[idx].name or f"stage-{idx}"
                         for idx in stage.dependent_stages]
            dep_info = f" [依赖: {', '.join(dep_names)}]"
        print(f"     阶段 {i}: {stage_name} ({len(stage.layers)} 层, 基础镜像: {stage.base_image}){dep_info}")

    high_churn = parser.get_high_churn_files()
    if high_churn:
        print(f"\n{Fore.YELLOW}📄 高修改频率文件 ({len(high_churn)} 个):")
        for file, freq in high_churn:
            print(f"   - {file}: 修改频率 {freq:.1f}")

    analyzer = CacheAnalyzer(parser, context_path)
    optimizer = Optimizer(parser, analyzer)
    size_analyzer = SizeAnalyzer(parser)
    time_predictor = BuildTimePredictor(parser, optimizer)

    if output_format == "json":
        output_json(parser, analyzer, optimizer, size_analyzer, time_predictor)
        return

    if show_cache:
        analyzer.print_analysis_report()

    if show_size:
        size_analyzer.print_size_report()

    if show_time:
        time_predictor.print_time_report()

    if show_optimizations:
        optimizer.print_optimization_report()

    print_summary(parser, analyzer, optimizer, size_analyzer, time_predictor)

    if auto_optimize:
        auto_optimizer = DockerfileAutoOptimizer(dockerfile_path, parser, optimizer)
        auto_optimizer.apply_optimizations()
        auto_optimizer.print_summary()

        if optimize_output or auto_optimizer.applied_optimizations:
            output_path = auto_optimizer.save_optimized(optimize_output)
            print(f"\n{Fore.GREEN}✅ 优化后的Dockerfile已保存至: {output_path}")
            print(f"{Fore.CYAN}💡 差异预览:")
            print(auto_optimizer.get_diff())


def run_ci_check(dockerfile_path: str, context_path: str, ci_mode: str) -> int:
    """运行CI检查"""
    checker = CIChecker(dockerfile_path, context_path)

    if ci_mode == "github":
        return checker.print_github_output()
    elif ci_mode == "gitlab":
        return checker.print_gitlab_output()
    else:
        return checker.print_console_report()


def print_summary(parser: DockerfileParser, analyzer: CacheAnalyzer,
                  optimizer: Optimizer, size_analyzer: SizeAnalyzer,
                  time_predictor: BuildTimePredictor = None):
    """打印总结"""
    print("\n" + "=" * 80)
    print(f"{Fore.CYAN}{Style.BRIGHT}📊 分析总结")
    print("=" * 80)

    overall_cache_score = analyzer.get_overall_cache_score()
    cache_breakers = len(analyzer.get_cache_breakers())
    total_suggestions = len(optimizer.suggestions)
    critical_count = len(optimizer.get_suggestions_by_severity(OptimizationSeverity.CRITICAL))
    high_count = len(optimizer.get_suggestions_by_severity(OptimizationSeverity.HIGH))
    total_size = size_analyzer.get_total_size()
    estimated_savings = optimizer.get_total_estimated_savings()
    incremental_savings = optimizer.get_total_incremental_savings()

    cache_score_color = Fore.GREEN if overall_cache_score >= 0.7 else (
        Fore.YELLOW if overall_cache_score >= 0.3 else Fore.RED)

    print(f"\n{Fore.WHITE}缓存性能:")
    print(f"  整体缓存得分: {cache_score_color}{overall_cache_score:.1%}")
    print(f"  高风险缓存破坏点: {Fore.RED if cache_breakers > 0 else Fore.GREEN}{cache_breakers} 个")

    print(f"\n{Fore.WHITE}优化建议:")
    print(f"  总计优化建议: {total_suggestions} 条")
    print(f"  🔴 严重: {critical_count} 条")
    print(f"  🟠 高优先级: {high_count} 条")

    print(f"\n{Fore.WHITE}镜像大小:")
    print(f"  预估总大小: {SizeAnalyzer.format_size(total_size)}")
    if estimated_savings > 0:
        print(f"  预估可节省: {Fore.GREEN}{SizeAnalyzer.format_size(estimated_savings)}")
        print(f"  增量实际节省: {Fore.GREEN}{SizeAnalyzer.format_size(incremental_savings)} (扣除共享层)")

    if time_predictor:
        print(f"\n{Fore.WHITE}构建时间:")
        orig = time_predictor.original_prediction
        if orig:
            print(f"  无缓存构建: {BuildTimePredictor.format_time(orig.total_estimated_seconds)}")
            print(f"  全缓存构建: {BuildTimePredictor.format_time(orig.total_cached_seconds)}")

            speedup = time_predictor.get_speedup_percentage()
            if speedup > 0:
                print(f"  优化后预计加速: {Fore.GREEN}+{speedup:.1f}%")

    print("\n" + "=" * 80)

    if overall_cache_score >= 0.7 and total_suggestions == 0:
        print(f"{Fore.GREEN}🎉 Dockerfile 状态良好！")
    elif overall_cache_score < 0.3 or critical_count > 0:
        print(f"{Fore.RED}⚠️  建议优先处理严重级别的优化建议")
    else:
        print(f"{Fore.YELLOW}💡 建议查看优化建议以提升构建性能")
        print(f"{Fore.CYAN}💡 使用 --auto-optimize 一键应用优化建议")

    print("=" * 80)


def output_json(parser: DockerfileParser, analyzer: CacheAnalyzer,
                optimizer: Optimizer, size_analyzer: SizeAnalyzer,
                time_predictor: BuildTimePredictor = None):
    """输出JSON格式结果"""
    import json

    result = {
        "summary": {
            "stage_count": len(parser.stages),
            "total_layers": len(parser.get_all_layers()),
            "overall_cache_score": analyzer.get_overall_cache_score(),
            "total_optimization_suggestions": len(optimizer.suggestions),
            "estimated_total_size": size_analyzer.get_total_size(),
            "estimated_savings": optimizer.get_total_estimated_savings(),
            "incremental_savings": optimizer.get_total_incremental_savings(),
        },
        "stages": [],
        "optimizations": []
    }

    if time_predictor and time_predictor.original_prediction:
        result["summary"]["estimated_build_time_seconds"] = time_predictor.original_prediction.total_estimated_seconds
        result["summary"]["estimated_cached_time_seconds"] = time_predictor.original_prediction.total_cached_seconds
        result["summary"]["estimated_speedup_percent"] = time_predictor.get_speedup_percentage()

    for stage in parser.stages:
        stage_data = {
            "index": stage.stage_index,
            "name": stage.name,
            "base_image": stage.base_image,
            "is_final": stage.is_final,
            "dependent_stages": stage.dependent_stages,
            "layers": []
        }

        for layer in stage.layers:
            cache_result = next(
                (r for r in analyzer.results if r.layer == layer),
                None
            )
            size_result = next(
                (r for r in size_analyzer.analysis_results if r.layer == layer),
                None
            )

            layer_data = {
                "index": layer.layer_index,
                "instruction": layer.instruction,
                "value": layer.value,
                "line_number": layer.line_number,
                "cache_hit_probability": cache_result.cache_hit_probability if cache_result else None,
                "risk_level": cache_result.risk_level if cache_result else None,
                "estimated_size": layer.estimated_size,
                "is_cache_busting": layer.is_cache_busting,
                "file_churn_frequency": [f.churn_frequency for f in layer.file_churn_info],
                "cross_stage_dependency": layer.cross_stage_dependency is not None,
            }
            stage_data["layers"].append(layer_data)

        result["stages"].append(stage_data)

    for suggestion in optimizer.suggestions:
        opt_data = {
            "title": suggestion.title,
            "description": suggestion.description,
            "severity": suggestion.severity.value,
            "stage_index": suggestion.stage_index,
            "affected_layers": suggestion.affected_layers,
            "estimated_savings_bytes": suggestion.estimated_savings,
            "incremental_savings_bytes": suggestion.incremental_savings,
            "cache_improvement": suggestion.cache_improvement,
            "before": suggestion.before_code,
            "after": suggestion.after_code,
        }
        result["optimizations"].append(opt_data)

    print(json.dumps(result, indent=2, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(
        description="Docker镜像构建层缓存分析工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py Dockerfile
  python main.py path/to/Dockerfile --context .
  python main.py Dockerfile --no-size
  python main.py Dockerfile --format json
  python main.py Dockerfile --auto-optimize
  python main.py Dockerfile --ci github
  python main.py Dockerfile --generate-ci github > .github/workflows/dockerfile-analysis.yml
        """
    )

    parser.add_argument(
        "dockerfile",
        help="Dockerfile文件路径"
    )

    parser.add_argument(
        "--context", "-c",
        help="构建上下文路径 (默认: Dockerfile所在目录)",
        default=None
    )

    parser.add_argument(
        "--no-cache",
        help="不显示缓存分析报告",
        action="store_true"
    )

    parser.add_argument(
        "--no-size",
        help="不显示大小分析报告",
        action="store_true"
    )

    parser.add_argument(
        "--no-time",
        help="不显示构建时间预测",
        action="store_true"
    )

    parser.add_argument(
        "--no-optimizations",
        help="不显示优化建议",
        action="store_true"
    )

    parser.add_argument(
        "--format", "-f",
        help="输出格式 (text/json)",
        choices=["text", "json"],
        default="text"
    )

    parser.add_argument(
        "--auto-optimize",
        help="一键自动应用优化建议",
        action="store_true"
    )

    parser.add_argument(
        "--output", "-o",
        help="优化后Dockerfile输出路径",
        default=None
    )

    parser.add_argument(
        "--ci",
        help="CI检查模式 (console/github/gitlab)",
        choices=["console", "github", "gitlab"],
        default=None
    )

    parser.add_argument(
        "--generate-ci",
        help="生成CI配置文件 (github/gitlab)",
        choices=["github", "gitlab"],
        default=None
    )

    args = parser.parse_args()

    if args.generate_ci:
        from ci_checker import CIChecker
        checker = CIChecker(args.dockerfile, args.context)
        if args.generate_ci == "github":
            print(checker.generate_github_workflow())
        elif args.generate_ci == "gitlab":
            print(checker.generate_gitlab_ci_config())
        return

    print_banner()

    exit_code = analyze_dockerfile(
        dockerfile_path=args.dockerfile,
        context_path=args.context,
        show_cache=not args.no_cache,
        show_size=not args.no_size,
        show_optimizations=not args.no_optimizations,
        show_time=not args.no_time,
        output_format=args.format,
        auto_optimize=args.auto_optimize,
        optimize_output=args.output,
        ci_mode=args.ci
    )

    if exit_code:
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
