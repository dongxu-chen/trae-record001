"""直接运行测试"""
import sys
sys.path.insert(0, '.')

from dockerfile_parser import DockerfileParser
from cache_analyzer import CacheAnalyzer
from optimizer import Optimizer
from size_analyzer import SizeAnalyzer

print("Testing...")

parser = DockerfileParser('examples/shared_layers.Dockerfile')
parser.analyze_stage_dependencies()

print(f"Stages: {len(parser.stages)}")
for i, stage in enumerate(parser.stages):
    print(f"  Stage {i}: {stage.name} ({len(stage.layers)} layers)")
    if stage.dependent_stages:
        print(f"    Depends on: {stage.dependent_stages}")

cross_copies = parser.get_cross_stage_copies()
print(f"\nCross-stage copies: {len(cross_copies)}")
for layer in cross_copies:
    dep = layer.cross_stage_dependency
    print(f"  Layer {layer.layer_index}: {dep.from_stage_name} -> {dep.dest_path}")

analyzer = CacheAnalyzer(parser)
optimizer = Optimizer(parser, analyzer)

print(f"\nShared layers: {len(optimizer.get_shared_layers())}")
for info in optimizer.get_shared_layers():
    print(f"  {info.instruction_signature[:50]} -> stages {info.stages}")

print(f"\nTotal suggestions: {len(optimizer.suggestions)}")
for s in optimizer.suggestions:
    print(f"  - {s.title}")

print("\nDone!")
