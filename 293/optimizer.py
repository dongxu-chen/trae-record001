"""优化建议生成器 - 提供缓存优化和Dockerfile改进建议"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set
from enum import Enum
from dockerfile_parser import DockerfileParser, LayerInfo, StageInfo, CrossStageDependency
from cache_analyzer import CacheAnalyzer, CacheAnalysisResult


class OptimizationSeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class SharedLayerInfo:
    instruction_signature: str
    stages: List[int]
    total_size: int
    incremental_savings: int
    is_duplicated: bool


@dataclass
class OptimizationSuggestion:
    title: str
    description: str
    severity: OptimizationSeverity
    affected_layers: List[int]
    stage_index: int
    before_code: str = ""
    after_code: str = ""
    estimated_savings: Optional[int] = None
    incremental_savings: Optional[int] = None
    cache_improvement: Optional[float] = None
    shared_layers: List[SharedLayerInfo] = field(default_factory=list)


class Optimizer:
    def __init__(self, parser: DockerfileParser, analyzer: CacheAnalyzer):
        self.parser = parser
        self.analyzer = analyzer
        self.suggestions: List[OptimizationSuggestion] = []
        self.shared_layers_cache: Dict[str, SharedLayerInfo] = {}
        self._analyze_shared_layers()
        self._generate_suggestions()

    def _generate_suggestions(self):
        for stage in self.parser.stages:
            self._check_run_merging(stage)
            self._check_copy_ordering(stage)
            self._check_package_manager_cleanup(stage)
            self._check_apt_update_install(stage)
            self._check_high_churn_ordering(stage)
            self._check_cross_stage_copy_optimization(stage)
            self._check_duplicate_commands(stage)
            self._check_unnecessary_instruction(stage)

        self._check_multistage_opportunities()
        self._check_shared_layer_optimization()

    def _check_run_merging(self, stage: StageInfo):
        """检查可以合并的RUN命令"""
        run_layers = [layer for layer in stage.layers if layer.instruction == 'RUN']

        if len(run_layers) < 2:
            return

        consecutive_groups = []
        current_group = [run_layers[0]]

        for i in range(1, len(run_layers)):
            prev_idx = run_layers[i - 1].layer_index
            curr_idx = run_layers[i].layer_index

            if curr_idx - prev_idx == 1:
                current_group.append(run_layers[i])
            else:
                if len(current_group) >= 2:
                    consecutive_groups.append(current_group)
                current_group = [run_layers[i]]

        if len(current_group) >= 2:
            consecutive_groups.append(current_group)

        for group in consecutive_groups:
            if len(group) >= 2:
                before = '\n'.join([layer.original_line for layer in group])
                after = 'RUN ' + ' && \\\n    '.join([layer.value for layer in group])

                saving = (len(group) - 1) * 1024 * 1024

                self.suggestions.append(OptimizationSuggestion(
                    title="合并连续的RUN命令",
                    description=f"可以将 {len(group)} 个连续的RUN命令合并为一个，减少镜像层数并提高缓存利用效率",
                    severity=OptimizationSeverity.MEDIUM,
                    affected_layers=[layer.layer_index for layer in group],
                    stage_index=stage.stage_index,
                    before_code=before,
                    after_code=after,
                    estimated_savings=saving,
                    cache_improvement=0.1
                ))

    def _check_copy_ordering(self, stage: StageInfo):
        """检查COPY命令的顺序优化"""
        copy_layers = [layer for layer in stage.layers if layer.instruction in ['COPY', 'ADD']]

        if len(copy_layers) < 2:
            return

        package_file_patterns = [
            r'package\.json',
            r'requirements\.txt',
            r'pom\.xml',
            r'build\.gradle',
            r'Gemfile',
            r'go\.mod',
            r'Cargo\.toml',
            r'\.lock$',
            r'yarn\.lock',
            r'Pipfile\.lock',
        ]

        package_files = []
        other_files = []

        for layer in copy_layers:
            is_package_file = False
            for pattern in package_file_patterns:
                if re.search(pattern, layer.value, re.IGNORECASE):
                    is_package_file = True
                    break

            if is_package_file:
                package_files.append(layer)
            else:
                other_files.append(layer)

        if not package_files:
            return

        first_package_idx = min(l.layer_index for l in package_files)
        first_other_idx = min((l.layer_index for l in other_files), default=9999)

        if first_other_idx < first_package_idx:
            before_lines = [layer.original_line for layer in sorted(
                copy_layers, key=lambda l: l.layer_index
            )]
            after_lines = [layer.original_line for layer in sorted(
                copy_layers, key=lambda l: 0 if l in package_files else 1
            )]

            self.suggestions.append(OptimizationSuggestion(
                title="优化COPY命令顺序",
                description="将依赖描述文件（如package.json、requirements.txt）的COPY放在源代码之前，可以显著提高缓存命中率",
                severity=OptimizationSeverity.HIGH,
                affected_layers=[layer.layer_index for layer in copy_layers],
                stage_index=stage.stage_index,
                before_code='\n'.join(before_lines),
                after_code='\n'.join(after_lines),
                cache_improvement=0.25
            ))

    def _check_package_manager_cleanup(self, stage: StageInfo):
        """检查包管理器清理命令"""
        run_layers = [layer for layer in stage.layers if layer.instruction == 'RUN']

        for layer in run_layers:
            value = layer.value.lower()

            has_apt_install = 'apt-get install' in value or 'apt install' in value
            has_apt_clean = 'apt-get clean' in value or 'apt clean' in value or \
                           'rm -rf /var/lib/apt/lists' in value

            has_yum_install = 'yum install' in value or 'dnf install' in value
            has_yum_clean = 'yum clean' in value or 'dnf clean' in value

            if has_apt_install and not has_apt_clean:
                self.suggestions.append(OptimizationSuggestion(
                    title="添加apt包管理器清理命令",
                    description="在apt-get install后添加清理命令可以显著减少镜像大小",
                    severity=OptimizationSeverity.HIGH,
                    affected_layers=[layer.layer_index],
                    stage_index=stage.stage_index,
                    before_code=layer.original_line,
                    after_code=layer.original_line + ' && \\\n    rm -rf /var/lib/apt/lists/*',
                    estimated_savings=50 * 1024 * 1024
                ))

            if has_yum_install and not has_yum_clean:
                self.suggestions.append(OptimizationSuggestion(
                    title="添加yum包管理器清理命令",
                    description="在yum install后添加清理命令可以显著减少镜像大小",
                    severity=OptimizationSeverity.HIGH,
                    affected_layers=[layer.layer_index],
                    stage_index=stage.stage_index,
                    before_code=layer.original_line,
                    after_code=layer.original_line + ' && \\\n    yum clean all',
                    estimated_savings=50 * 1024 * 1024
                ))

    def _check_apt_update_install(self, stage: StageInfo):
        """检查apt-get update和install是否在同一层"""
        run_layers = [layer for layer in stage.layers if layer.instruction == 'RUN']

        update_layer = None
        install_layers = []

        for layer in run_layers:
            value = layer.value.lower()
            if 'apt-get update' in value and 'apt-get install' not in value:
                update_layer = layer
            elif 'apt-get install' in value and 'apt-get update' not in value:
                install_layers.append(layer)

        if update_layer and install_layers:
            combined_value = f"apt-get update && apt-get install -y {' '.join(self._extract_packages(install_layers[0].value))}"
            self.suggestions.append(OptimizationSuggestion(
                title="合并apt-get update和install",
                description="apt-get update和install应该在同一RUN命令中，避免缓存问题导致安装失败",
                severity=OptimizationSeverity.CRITICAL,
                affected_layers=[update_layer.layer_index] + [l.layer_index for l in install_layers[:1]],
                stage_index=stage.stage_index,
                before_code=f"{update_layer.original_line}\n{install_layers[0].original_line}",
                after_code=f"RUN {combined_value}",
                cache_improvement=0.3
            ))

    def _extract_packages(self, run_value: str) -> List[str]:
        """从RUN命令中提取包名"""
        match = re.search(r'apt-get install\s+(-y\s+)?([\w\s\-]+)', run_value, re.IGNORECASE)
        if match:
            packages = match.group(2).strip().split()
            return [p for p in packages if not p.startswith('-')]
        return []

    def _check_multistage_opportunities(self):
        """检查多阶段构建优化机会"""
        if len(self.parser.stages) <= 1:
            final_stage = self.parser.get_final_stage()
            if not final_stage:
                return

            has_build_tools = False
            has_compiled_code = False

            for layer in final_stage.layers:
                if layer.instruction == 'RUN':
                    value = layer.value.lower()
                    build_patterns = [
                        'pip install.*-e',
                        'python setup.py install',
                        'npm install',
                        'go build',
                        'cargo build',
                        'mvn install',
                        'gradle build',
                        'make',
                        'gcc',
                        'g\+\+',
                    ]
                    for pattern in build_patterns:
                        if re.search(pattern, value):
                            has_build_tools = True
                            break

            if has_build_tools:
                self.suggestions.append(OptimizationSuggestion(
                    title="使用多阶段构建",
                    description="当前镜像包含构建工具和依赖，可以使用多阶段构建将构建阶段和运行阶段分离，显著减小最终镜像大小",
                    severity=OptimizationSeverity.HIGH,
                    affected_layers=[l.layer_index for l in final_stage.layers],
                    stage_index=0,
                    estimated_savings=200 * 1024 * 1024
                ))

    def _check_duplicate_commands(self, stage: StageInfo):
        """检查重复的命令"""
        command_counts = {}

        for layer in stage.layers:
            if layer.instruction in ['RUN', 'ENV', 'ARG', 'LABEL']:
                key = f"{layer.instruction}:{layer.value[:50]}"
                command_counts[key] = command_counts.get(key, 0) + 1

        duplicates = [(k, v) for k, v in command_counts.items() if v > 1]

        if duplicates:
            for key, count in duplicates:
                self.suggestions.append(OptimizationSuggestion(
                    title=f"发现重复的{key.split(':')[0]}命令",
                    description=f"有 {count} 个相同或相似的命令可以合并",
                    severity=OptimizationSeverity.LOW,
                    affected_layers=[],
                    stage_index=stage.stage_index
                ))

    def _check_unnecessary_instruction(self, stage: StageInfo):
        """检查不必要的指令"""
        for layer in stage.layers:
            if layer.instruction == 'ADD':
                if not any(proto in layer.value for proto in ['http://', 'https://']) and \
                   not layer.value.endswith(('.tar', '.tar.gz', '.tgz', '.zip')):
                    self.suggestions.append(OptimizationSuggestion(
                        title="使用COPY代替ADD",
                        description="对于普通文件复制，使用COPY比ADD更安全且语义更清晰",
                        severity=OptimizationSeverity.LOW,
                        affected_layers=[layer.layer_index],
                        stage_index=stage.stage_index,
                        before_code=layer.original_line,
                        after_code=layer.original_line.replace('ADD', 'COPY', 1)
                    ))

    def _analyze_shared_layers(self):
        """分析可以共享的层"""
        layer_signatures: Dict[str, SharedLayerInfo] = {}

        for stage in self.parser.stages:
            for layer in stage.layers:
                if layer.instruction in ['FROM', 'RUN', 'COPY', 'ADD', 'ENV', 'WORKDIR']:
                    signature = self._get_layer_signature(layer)

                    if signature in layer_signatures:
                        layer_signatures[signature].stages.append(stage.stage_index)
                        layer_signatures[signature].total_size += layer.estimated_size
                    else:
                        layer_signatures[signature] = SharedLayerInfo(
                            instruction_signature=signature,
                            stages=[stage.stage_index],
                            total_size=layer.estimated_size,
                            incremental_savings=0,
                            is_duplicated=False
                        )

        for sig, info in layer_signatures.items():
            if len(info.stages) > 1:
                info.is_duplicated = True
                info.incremental_savings = (len(info.stages) - 1) * (info.total_size // len(info.stages))

        self.shared_layers_cache = {
            k: v for k, v in layer_signatures.items() if v.is_duplicated
        }

    def _get_layer_signature(self, layer: LayerInfo) -> str:
        """获取层的签名用于比较"""
        return f"{layer.instruction}:{self._normalize_value(layer.value)}"

    def _normalize_value(self, value: str) -> str:
        """标准化值用于比较"""
        value = re.sub(r'\s+', ' ', value.strip())
        value = re.sub(r'&&\s*', '&&', value)
        return value

    def _check_high_churn_ordering(self, stage: StageInfo):
        """检查高频文件是否正确排序"""
        copy_layers = [layer for layer in stage.layers
                       if layer.instruction in ['COPY', 'ADD'] and not layer.cross_stage_dependency]

        if len(copy_layers) < 2:
            return

        misplaced_layers = []
        for i in range(len(copy_layers) - 1):
            current = copy_layers[i]
            next_layer = copy_layers[i + 1]

            current_churn = max((info.churn_frequency for info in current.file_churn_info), default=0)
            next_churn = max((info.churn_frequency for info in next_layer.file_churn_info), default=0)

            if current_churn > next_churn + 0.2:
                misplaced_layers.append((current, next_layer, current_churn, next_churn))

        if misplaced_layers:
            before_lines = [layer.original_line for layer in copy_layers]
            sorted_layers = sorted(copy_layers,
                                   key=lambda l: max((info.churn_frequency for info in l.file_churn_info), default=0))
            after_lines = [layer.original_line for layer in sorted_layers]

            self.suggestions.append(OptimizationSuggestion(
                title="按文件修改频率优化COPY顺序",
                description=f"检测到 {len(misplaced_layers)} 处高频文件前置问题。低频文件应放在高频文件之前以最大化缓存利用",
                severity=OptimizationSeverity.HIGH,
                affected_layers=[layer.layer_index for layer in copy_layers],
                stage_index=stage.stage_index,
                before_code='\n'.join(before_lines),
                after_code='\n'.join(after_lines),
                cache_improvement=0.2
            ))

    def _check_cross_stage_copy_optimization(self, stage: StageInfo):
        """检查跨阶段COPY优化"""
        cross_copies = [layer for layer in stage.layers if layer.cross_stage_dependency]

        if len(cross_copies) >= 2:
            savings = (len(cross_copies) - 1) * 5 * 1024 * 1024

            self.suggestions.append(OptimizationSuggestion(
                title="合并多个COPY --from命令",
                description=f"可以将 {len(cross_copies)} 个跨阶段COPY命令合并，减少层数",
                severity=OptimizationSeverity.LOW,
                affected_layers=[layer.layer_index for layer in cross_copies],
                stage_index=stage.stage_index,
                estimated_savings=savings,
                incremental_savings=savings // 2
            ))

    def _check_shared_layer_optimization(self):
        """检查共享层优化机会"""
        shared_layers = [info for info in self.shared_layers_cache.values()
                         if len(info.stages) >= 2 and info.incremental_savings > 0]

        if shared_layers and len(self.parser.stages) >= 2:
            total_incremental_savings = sum(info.incremental_savings for info in shared_layers)

            suggestion = OptimizationSuggestion(
                title="使用共享基础镜像",
                description=f"检测到 {len(shared_layers)} 个重复层可以共享。建议创建共享基础镜像或使用外部基础镜像",
                severity=OptimizationSeverity.MEDIUM,
                affected_layers=[],
                stage_index=-1,
                estimated_savings=sum(info.total_size for info in shared_layers),
                incremental_savings=total_incremental_savings
            )
            suggestion.shared_layers = shared_layers
            self.suggestions.append(suggestion)

    def get_suggestions_by_severity(self, severity: OptimizationSeverity) -> List[OptimizationSuggestion]:
        """按严重程度获取建议"""
        return [s for s in self.suggestions if s.severity == severity]

    def get_total_estimated_savings(self) -> int:
        """获取预估总节省空间"""
        return sum(s.estimated_savings or 0 for s in self.suggestions)

    def get_total_incremental_savings(self) -> int:
        """获取增量节省空间（只计算实际能节省的部分）"""
        return sum(s.incremental_savings or (s.estimated_savings or 0) for s in self.suggestions)

    def get_shared_layers(self) -> List[SharedLayerInfo]:
        """获取所有共享层信息"""
        return list(self.shared_layers_cache.values())

    def print_optimization_report(self):
        """打印优化建议报告"""
        print("\n" + "=" * 80)
        print("Dockerfile 优化建议")
        print("=" * 80)

        shared_layers = self.get_shared_layers()
        if shared_layers:
            print(f"\n📊 共享层分析:")
            print("-" * 80)
            for info in shared_layers[:5]:
                stage_names = ', '.join([f"stage-{s}" for s in info.stages])
                inc_size = info.incremental_savings / (1024 * 1024)
                print(f"   · {info.instruction_signature[:50]}...")
                print(f"     出现在阶段: {stage_names}")
                print(f"     增量可节省: {inc_size:.1f} MB")
            if len(shared_layers) > 5:
                print(f"   ... 还有 {len(shared_layers) - 5} 个共享层")

        severity_order = [
            OptimizationSeverity.CRITICAL,
            OptimizationSeverity.HIGH,
            OptimizationSeverity.MEDIUM,
            OptimizationSeverity.LOW
        ]

        total_suggestions = len(self.suggestions)

        for severity in severity_order:
            suggestions = self.get_suggestions_by_severity(severity)
            if not suggestions:
                continue

            severity_icon = {
                OptimizationSeverity.CRITICAL: "🔴",
                OptimizationSeverity.HIGH: "🟠",
                OptimizationSeverity.MEDIUM: "🟡",
                OptimizationSeverity.LOW: "🟢"
            }[severity]

            print(f"\n{severity_icon} {severity.value.upper()} ({len(suggestions)} 项)")
            print("-" * 80)

            for i, suggestion in enumerate(suggestions, 1):
                print(f"\n{i}. {suggestion.title}")
                print(f"   描述: {suggestion.description}")
                if suggestion.stage_index >= 0:
                    print(f"   阶段: {suggestion.stage_index}")

                if suggestion.affected_layers:
                    print(f"   影响层: {suggestion.affected_layers}")

                if suggestion.incremental_savings:
                    size_mb = suggestion.incremental_savings / (1024 * 1024)
                    print(f"   增量节省: {size_mb:.1f} MB")
                elif suggestion.estimated_savings:
                    size_mb = suggestion.estimated_savings / (1024 * 1024)
                    print(f"   预估节省: {size_mb:.1f} MB")

                if suggestion.cache_improvement:
                    print(f"   缓存提升: +{suggestion.cache_improvement:.0%}")

                if suggestion.before_code and suggestion.after_code:
                    print(f"\n   优化前:")
                    for line in suggestion.before_code.split('\n'):
                        print(f"     {line}")
                    print(f"   优化后:")
                    for line in suggestion.after_code.split('\n'):
                        print(f"     {line}")

        print("\n" + "=" * 80)
        print(f"总计: {total_suggestions} 条优化建议")

        total_savings = self.get_total_estimated_savings()
        incremental_savings = self.get_total_incremental_savings()

        if total_savings > 0:
            size_mb = total_savings / (1024 * 1024)
            inc_size_mb = incremental_savings / (1024 * 1024)
            print(f"总预估节省: {size_mb:.1f} MB")
            print(f"增量实际节省: {inc_size_mb:.1f} MB (扣除共享层)")
        print("=" * 80)
