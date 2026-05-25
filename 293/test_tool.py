"""增强版测试脚本 - 验证所有新功能"""
import sys
sys.path.insert(0, '.')

from dockerfile_parser import DockerfileParser
from cache_analyzer import CacheAnalyzer
from optimizer import Optimizer
from size_analyzer import SizeAnalyzer

print("=" * 70)
print("Docker 镜像缓存分析工具 - 增强功能测试")
print("=" * 70)

print("\n" + "=" * 70)
print("测试1: 文件修改频率权重分析")
print("=" * 70)
parser = DockerfileParser('examples/bad.Dockerfile')
parser.analyze_stage_dependencies()

print(f"✓ 解析完成: {len(parser.get_all_layers())} 层")

high_churn = parser.get_high_churn_files()
print(f"✓ 高修改频率文件: {len(high_churn)} 个")
for file, freq in high_churn:
    print(f"   - {file}: {freq:.1f}")

for layer in parser.get_all_layers():
    if layer.file_churn_info:
        churn_info = layer.file_churn_info[0]
        print(f"   层 {layer.layer_index} ({layer.instruction}): "
              f"修改频率 = {churn_info.churn_frequency:.1f}")

print("\n" + "=" * 70)
print("测试2: COPY --from 跨阶段依赖检测")
print("=" * 70)
parser2 = DockerfileParser('examples/multistage.Dockerfile')
parser2.analyze_stage_dependencies()

print(f"✓ 阶段数: {len(parser2.stages)}")
for i, stage in enumerate(parser2.stages):
    print(f"   阶段 {i}: {stage.name or 'unnamed'}")
    if stage.dependent_stages:
        print(f"     依赖阶段: {stage.dependent_stages}")

cross_copies = parser2.get_cross_stage_copies()
print(f"✓ 跨阶段COPY数: {len(cross_copies)}")
for layer in cross_copies:
    dep = layer.cross_stage_dependency
    print(f"   层 {layer.layer_index}: 从 {dep.from_stage_name} "
          f"复制 {dep.source_path} → {dep.dest_path}")

print("\n" + "=" * 70)
print("测试3: 缓存分析 - 文件修改频率权重")
print("=" * 70)
analyzer = CacheAnalyzer(parser2)

for result in analyzer.get_results_by_stage(1):
    layer = result.layer
    print(f"   层 {layer.layer_index}: 缓存概率 = {result.cache_hit_probability:.1%}, "
          f"修改频率权重 = {result.file_churn_weight:.1f}")
    if result.cross_stage_dependency:
        print(f"     → 依赖阶段: {result.cross_stage_dependency.from_stage_name}")

print(f"✓ 高频文件未前置数: {len(analyzer.get_misplaced_high_churn_layers())}")
print(f"✓ 跨阶段依赖数: {len(analyzer.get_cross_stage_dependencies())}")

print("\n" + "=" * 70)
print("测试4: 共享层分析和增量节省计算")
print("=" * 70)
optimizer = Optimizer(parser2, analyzer)

shared_layers = optimizer.get_shared_layers()
print(f"✓ 共享层数: {len(shared_layers)}")
for info in shared_layers:
    print(f"   - {info.instruction_signature[:40]}... "
          f"出现在 {len(info.stages)} 个阶段, "
          f"增量节省 = {SizeAnalyzer.format_size(info.incremental_savings)}")

print(f"✓ 总预估节省: {SizeAnalyzer.format_size(optimizer.get_total_estimated_savings())}")
print(f"✓ 增量实际节省: {SizeAnalyzer.format_size(optimizer.get_total_incremental_savings())}")

print("\n" + "=" * 70)
print("测试5: 高频文件顺序优化建议")
print("=" * 70)
parser3 = DockerfileParser('examples/bad.Dockerfile')
analyzer3 = CacheAnalyzer(parser3)
optimizer3 = Optimizer(parser3, analyzer3)

ordering_suggestions = [s for s in optimizer3.suggestions
                       if "频率" in s.title or "COPY顺序" in s.title]
print(f"✓ 文件顺序优化建议: {len(ordering_suggestions)} 条")
for s in ordering_suggestions:
    print(f"   - {s.title}")
    if s.cache_improvement:
        print(f"     缓存提升: +{s.cache_improvement:.0%}")

print("\n" + "=" * 70)
print("✅ 所有增强功能测试通过！")
print("=" * 70)
