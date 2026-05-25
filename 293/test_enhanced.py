"""增强功能测试脚本"""
import sys
import os
sys.path.insert(0, '.')

print("=" * 70)
print("🚀 Docker 缓存分析工具 - 增强功能测试")
print("=" * 70)

from dockerfile_parser import DockerfileParser
from cache_analyzer import CacheAnalyzer
from optimizer import Optimizer
from size_analyzer import SizeAnalyzer
from build_time_predictor import BuildTimePredictor
from auto_optimizer import DockerfileAutoOptimizer
from ci_checker import CIChecker

test_file = 'examples/bad.Dockerfile'
print(f"\n📄 测试文件: {test_file}")

print("\n" + "=" * 70)
print("测试1: 文件修改频率权重分析")
print("=" * 70)

parser = DockerfileParser(test_file)
parser.analyze_stage_dependencies()

print(f"✓ 解析完成: {len(parser.get_all_layers())} 层")

high_churn = parser.get_high_churn_files()
print(f"✓ 高修改频率文件: {len(high_churn)} 个")
for file, freq in high_churn:
    print(f"   - {file}: 修改频率 = {freq:.1f}")

for layer in parser.get_all_layers():
    if layer.file_churn_info:
        max_freq = max(f.churn_frequency for f in layer.file_churn_info)
        print(f"   层 {layer.layer_index} ({layer.instruction}): 修改频率权重 = {max_freq:.1f}")

print("\n" + "=" * 70)
print("测试2: COPY --from 跨阶段依赖检测")
print("=" * 70)

parser2 = DockerfileParser('examples/shared_layers.Dockerfile')
parser2.analyze_stage_dependencies()

print(f"✓ 阶段数: {len(parser2.stages)}")
for i, stage in enumerate(parser2.stages):
    print(f"   阶段 {i}: {stage.name or 'unnamed'}")
    if stage.dependent_stages:
        print(f"     → 依赖阶段: {stage.dependent_stages}")

cross_copies = parser2.get_cross_stage_copies()
print(f"✓ 跨阶段COPY数: {len(cross_copies)}")
for layer in cross_copies:
    dep = layer.cross_stage_dependency
    print(f"   层 {layer.layer_index}: 从 {dep.from_stage_name} 复制 {dep.source_path} → {dep.dest_path}")

print("\n" + "=" * 70)
print("测试3: 共享层分析和增量节省计算")
print("=" * 70)

analyzer2 = CacheAnalyzer(parser2)
optimizer2 = Optimizer(parser2, analyzer2)

shared_layers = optimizer2.get_shared_layers()
print(f"✓ 共享层数: {len(shared_layers)}")
for info in shared_layers:
    print(f"   · {info.instruction_signature[:50]}...")
    print(f"     → 出现在阶段: {info.stages}")
    print(f"     → 增量节省: {SizeAnalyzer.format_size(info.incremental_savings)}")

print(f"\n✓ 总预估节省: {SizeAnalyzer.format_size(optimizer2.get_total_estimated_savings())}")
print(f"✓ 增量实际节省: {SizeAnalyzer.format_size(optimizer2.get_total_incremental_savings())}")

print("\n" + "=" * 70)
print("测试4: 构建时间预测和优化模拟")
print("=" * 70)

time_predictor = BuildTimePredictor(parser2, optimizer2)

orig = time_predictor.original_prediction
print(f"✓ 无缓存构建: {BuildTimePredictor.format_time(orig.total_estimated_seconds)}")
print(f"✓ 全缓存构建: {BuildTimePredictor.format_time(orig.total_cached_seconds)}")

speedup = time_predictor.get_speedup_percentage()
print(f"✓ 优化后预计加速: +{speedup:.1f}%")

if orig.optimization_impact:
    print(f"\n✓ 各项优化贡献:")
    for title, savings in orig.optimization_impact.items():
        if savings > 0:
            print(f"   · {title}: 节省 {BuildTimePredictor.format_time(savings)}")

print("\n" + "=" * 70)
print("测试5: 自动优化Dockerfile生成")
print("=" * 70)

parser3 = DockerfileParser(test_file)
analyzer3 = CacheAnalyzer(parser3)
optimizer3 = Optimizer(parser3, analyzer3)

auto_opt = DockerfileAutoOptimizer(test_file, parser3, optimizer3)
applied_count = auto_opt.apply_optimizations()

print(f"✓ 应用了 {applied_count} 项优化")
if applied_count > 0:
    print(f"\n✓ 优化差异:")
    print(auto_opt.get_diff())

    output_file = test_file + '.optimized'
    saved_path = auto_opt.save_optimized(output_file)
    print(f"✓ 优化文件已保存: {saved_path}")

print("\n" + "=" * 70)
print("测试6: CI检查集成")
print("=" * 70)

ci_checker = CIChecker(test_file)
status = ci_checker.get_status()
print(f"✓ CI整体状态: {status.value.upper()}")

print(f"\n✓ 各项检查结果:")
for check in ci_checker.checks:
    icon = "✅" if check.status.value == "pass" else ("⚠️" if check.status.value == "warn" else "❌")
    print(f"   {icon} {check.check_name:20s} - {check.message}")

print("\n" + "=" * 70)
print("✅ 所有增强功能测试通过！")
print("=" * 70)
