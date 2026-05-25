"""Dockerfile解析模块 - 解析Dockerfile并提取各层信息"""

import re
import os
import glob
import time
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple


@dataclass
class FileChurnInfo:
    file_pattern: str
    churn_frequency: float
    modification_count: int
    last_modified: float


@dataclass
class CrossStageDependency:
    from_stage_name: str
    from_stage_index: int
    source_path: str
    dest_path: str


@dataclass
class LayerInfo:
    layer_index: int
    instruction: str
    value: str
    original_line: str
    line_number: int
    stage_name: Optional[str] = None
    stage_index: int = 0
    is_cache_busting: bool = False
    cache_hit_probability: float = 1.0
    estimated_size: int = 0
    context_files: List[str] = field(default_factory=list)
    file_churn_info: List[FileChurnInfo] = field(default_factory=list)
    cross_stage_dependency: Optional[CrossStageDependency] = None
    is_shared_layer: bool = False


@dataclass
class StageInfo:
    stage_index: int
    name: Optional[str]
    base_image: str
    layers: List[LayerInfo] = field(default_factory=list)
    is_final: bool = False
    dependent_stages: List[int] = field(default_factory=list)


class DockerfileParser:
    def __init__(self, dockerfile_path: str, context_path: Optional[str] = None):
        self.dockerfile_path = dockerfile_path
        self.context_path = context_path or os.path.dirname(dockerfile_path)
        self.stages: List[StageInfo] = []
        self._parse()

    def _parse(self):
        with open(self.dockerfile_path, 'r', encoding='utf-8') as f:
            content = f.read()

        lines = content.split('\n')
        processed_lines = self._join_continuations(lines)

        current_stage = None
        stage_index = 0
        layer_index = 0

        for line_num, line in processed_lines:
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue

            instruction, value = self._parse_instruction(stripped)

            if instruction == 'FROM':
                if current_stage is not None:
                    self.stages.append(current_stage)

                stage_name = self._extract_stage_name(value)
                base_image = value.split(' AS ')[0].strip()
                current_stage = StageInfo(
                    stage_index=stage_index,
                    name=stage_name,
                    base_image=base_image
                )
                stage_index += 1
                layer_index = 0
                continue

            if current_stage is None:
                current_stage = StageInfo(
                    stage_index=0,
                    name=None,
                    base_image='scratch'
                )

            layer = LayerInfo(
                layer_index=layer_index,
                instruction=instruction,
                value=value,
                original_line=line,
                line_number=line_num,
                stage_name=current_stage.name,
                stage_index=current_stage.stage_index
            )

            self._enrich_layer_info(layer)
            current_stage.layers.append(layer)
            layer_index += 1

        if current_stage is not None:
            current_stage.is_final = True
            self.stages.append(current_stage)

    def _join_continuations(self, lines: List[str]) -> List[tuple]:
        """处理换行符连接的行"""
        result = []
        current_line = ''
        current_line_num = 0

        for i, line in enumerate(lines, 1):
            stripped = line.rstrip()
            if stripped.endswith('\\'):
                if not current_line:
                    current_line_num = i
                current_line += stripped[:-1] + ' '
            else:
                if current_line:
                    current_line += stripped
                    result.append((current_line_num, current_line))
                    current_line = ''
                else:
                    result.append((i, line))

        return result

    def _parse_instruction(self, line: str) -> tuple:
        """解析指令类型和值"""
        match = re.match(r'^(\w+)\s+(.*)$', line, re.DOTALL)
        if match:
            return match.group(1).upper(), match.group(2).strip()
        return line.upper(), ''

    def _extract_stage_name(self, from_value: str) -> Optional[str]:
        """提取阶段名称"""
        match = re.search(r'AS\s+(\w+)', from_value, re.IGNORECASE)
        if match:
            return match.group(1)
        return None

    def _enrich_layer_info(self, layer: LayerInfo):
        """丰富层信息"""
        layer.is_cache_busting = self._is_cache_busting(layer)
        layer.context_files = self._get_context_files(layer)
        layer.estimated_size = self._estimate_size(layer)
        layer.file_churn_info = self._analyze_file_churn(layer)
        layer.cross_stage_dependency = self._detect_cross_stage_dependency(layer)

    def _is_cache_busting(self, layer: LayerInfo) -> bool:
        """判断是否是缓存破坏指令"""
        cache_busting_patterns = [
            (r'COPY\s+--from=', True),
            (r'ADD\s+.*https?://', True),
            (r'RUN\s+.*apt-get\s+update', True),
            (r'RUN\s+.*yum\s+update', True),
            (r'RUN\s+.*pip\s+install.*--upgrade', True),
            (r'RUN\s+.*npm\s+install.*--force', True),
        ]

        for pattern, is_busting in cache_busting_patterns:
            if re.search(pattern, layer.original_line, re.IGNORECASE):
                return is_busting

        return False

    def _get_context_files(self, layer: LayerInfo) -> List[str]:
        """获取涉及的上下文文件"""
        files = []

        if layer.instruction in ['COPY', 'ADD']:
            parts = layer.value.split()
            if not parts:
                return files

            src_parts = parts[:-1]
            for src in src_parts:
                if src.startswith('--'):
                    continue
                src = src.strip('"').strip("'")
                if not src.startswith('--from='):
                    files.append(src)

        return files

    def _estimate_size(self, layer: LayerInfo) -> int:
        """估算层大小（字节）"""
        size_estimates = {
            'FROM': 100 * 1024 * 1024,
            'RUN': 50 * 1024 * 1024,
            'COPY': 10 * 1024 * 1024,
            'ADD': 10 * 1024 * 1024,
            'CMD': 0,
            'ENTRYPOINT': 0,
            'ENV': 0,
            'ARG': 0,
            'WORKDIR': 0,
            'EXPOSE': 0,
            'LABEL': 0,
            'USER': 0,
            'VOLUME': 0,
            'HEALTHCHECK': 0,
            'SHELL': 0,
            'STOPSIGNAL': 0,
        }

        base_size = size_estimates.get(layer.instruction, 1024 * 1024)

        if layer.instruction == 'RUN':
            if 'apt-get install' in layer.value or 'yum install' in layer.value:
                base_size = 100 * 1024 * 1024
            if 'pip install' in layer.value or 'npm install' in layer.value:
                base_size = 200 * 1024 * 1024

        return base_size

    def get_all_layers(self) -> List[LayerInfo]:
        """获取所有层"""
        all_layers = []
        for stage in self.stages:
            all_layers.extend(stage.layers)
        return all_layers

    def get_stage_by_name(self, name: str) -> Optional[StageInfo]:
        """按名称获取阶段"""
        for stage in self.stages:
            if stage.name == name:
                return stage
        return None

    def get_final_stage(self) -> Optional[StageInfo]:
        """获取最终阶段"""
        for stage in self.stages:
            if stage.is_final:
                return stage
        return None

    def _analyze_file_churn(self, layer: LayerInfo) -> List[FileChurnInfo]:
        """分析文件修改频率"""
        churn_info_list = []

        if not layer.context_files:
            return churn_info_list

        for file_pattern in layer.context_files:
            churn_info = self._calculate_file_churn(file_pattern)
            churn_info_list.append(churn_info)

        return churn_info_list

    def _calculate_file_churn(self, file_pattern: str) -> FileChurnInfo:
        """计算单个文件的修改频率"""
        full_pattern = os.path.join(self.context_path, file_pattern)
        matching_files = glob.glob(full_pattern, recursive=True)

        if not matching_files:
            return FileChurnInfo(
                file_pattern=file_pattern,
                churn_frequency=0.5,
                modification_count=0,
                last_modified=0
            )

        total_size = 0
        latest_mtime = 0
        modification_count = len(matching_files)

        for file_path in matching_files:
            try:
                stat = os.stat(file_path)
                total_size += stat.st_size
                latest_mtime = max(latest_mtime, stat.st_mtime)
            except (OSError, FileNotFoundError):
                continue

        current_time = time.time()
        days_since_modified = (current_time - latest_mtime) / (24 * 3600) if latest_mtime > 0 else 365

        churn_frequency = self._estimate_churn_frequency(file_pattern, matching_files, days_since_modified)

        return FileChurnInfo(
            file_pattern=file_pattern,
            churn_frequency=churn_frequency,
            modification_count=modification_count,
            last_modified=latest_mtime
        )

    def _estimate_churn_frequency(self, file_pattern: str, matching_files: List[str],
                                   days_since_modified: float) -> float:
        """估算文件修改频率（0-1，越高表示修改越频繁）"""
        high_churn_patterns = [
            r'\.js$', r'\.ts$', r'\.jsx$', r'\.tsx$',
            r'\.py$', r'\.java$', r'\.go$', r'\.rs$',
            r'src/', r'app/', r'lib/', r'components/',
            r'\.vue$', r'\.svelte$', r'\.css$', r'\.scss$',
        ]

        medium_churn_patterns = [
            r'package\.json', r'requirements\.txt', r'pom\.xml',
            r'build\.gradle', r'Cargo\.toml', r'go\.mod',
            r'Dockerfile', r'\.dockerignore',
            r'\.yaml$', r'\.yml$', r'\.json$',
        ]

        low_churn_patterns = [
            r'\.md$', r'README', r'LICENSE',
            r'\.png$', r'\.jpg$', r'\.jpeg$', r'\.gif$', r'\.svg$',
            r'\.lock$', r'yarn\.lock', r'Pipfile\.lock',
            r'vendor/', r'node_modules/', r'third_party/',
        ]

        pattern_lower = file_pattern.lower()

        for pattern in high_churn_patterns:
            if re.search(pattern, pattern_lower):
                return 0.8

        for pattern in medium_churn_patterns:
            if re.search(pattern, pattern_lower):
                return 0.5

        for pattern in low_churn_patterns:
            if re.search(pattern, pattern_lower):
                return 0.2

        if days_since_modified < 7:
            return 0.7
        elif days_since_modified < 30:
            return 0.4
        else:
            return 0.2

    def _detect_cross_stage_dependency(self, layer: LayerInfo) -> Optional[CrossStageDependency]:
        """检测COPY --from跨阶段依赖"""
        if layer.instruction not in ['COPY', 'ADD']:
            return None

        match = re.search(r'--from=([\w-]+)(?::\d+)?\s+(\S+)\s+(\S+)', layer.value)
        if match:
            from_stage = match.group(1)
            source_path = match.group(2)
            dest_path = match.group(3)

            stage_index = self._get_stage_index_by_name(from_stage)

            if stage_index is not None:
                return CrossStageDependency(
                    from_stage_name=from_stage,
                    from_stage_index=stage_index,
                    source_path=source_path,
                    dest_path=dest_path
                )

        match = re.search(r'--from=(\d+)\s+(\S+)\s+(\S+)', layer.value)
        if match:
            stage_index = int(match.group(1))
            source_path = match.group(2)
            dest_path = match.group(3)

            stage_name = None
            if stage_index < len(self.stages):
                stage_name = self.stages[stage_index].name

            return CrossStageDependency(
                from_stage_name=stage_name or f"stage-{stage_index}",
                from_stage_index=stage_index,
                source_path=source_path,
                dest_path=dest_path
            )

        return None

    def _get_stage_index_by_name(self, stage_name: str) -> Optional[int]:
        """根据阶段名称获取索引"""
        for i, stage in enumerate(self.stages):
            if stage.name == stage_name:
                return i
        return None

    def analyze_stage_dependencies(self):
        """分析阶段间的依赖关系"""
        for stage in self.stages:
            stage.dependent_stages = []
            for layer in stage.layers:
                if layer.cross_stage_dependency:
                    dep_stage_idx = layer.cross_stage_dependency.from_stage_index
                    if dep_stage_idx not in stage.dependent_stages:
                        stage.dependent_stages.append(dep_stage_idx)

    def get_high_churn_files(self, threshold: float = 0.6) -> List[Tuple[str, float]]:
        """获取高修改频率的文件"""
        high_churn = []
        for layer in self.get_all_layers():
            for churn_info in layer.file_churn_info:
                if churn_info.churn_frequency >= threshold:
                    high_churn.append((churn_info.file_pattern, churn_info.churn_frequency))
        return high_churn

    def get_cross_stage_copies(self) -> List[LayerInfo]:
        """获取所有跨阶段COPY层"""
        return [
            layer for layer in self.get_all_layers()
            if layer.cross_stage_dependency is not None
        ]
