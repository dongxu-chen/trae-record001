import os
import subprocess
import shutil
import tempfile
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

from git_scanner import LargeFileInfo, GitHistoryScanner
from file_analyzer import FileTypeAnalyzer


def format_size(size_bytes: int) -> str:
    size = float(size_bytes)
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    unit_index = 0
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    return f"{size:.2f} {units[unit_index]}"


COMPRESSION_FACTORS = {
    'image': 0.98,
    'image_raw': 0.99,
    'video': 0.99,
    'audio': 0.98,
    'archive': 0.99,
    'document': 0.85,
    'database': 0.70,
    'executable': 0.90,
    'font': 0.92,
    'log': 0.30,
    'backup': 0.90,
    'data': 0.55,
    'model': 0.88,
    'other': 0.65,
}


class BFGCleanerAdvisor:
    def __init__(self, large_files: Dict[str, LargeFileInfo], repo_path: str):
        self.large_files = large_files
        self.repo_path = os.path.abspath(repo_path)

    def generate_bfg_commands(self, dry_run: bool = False) -> List[str]:
        commands = []

        files_by_pattern = self._group_files_by_pattern()

        for file_type, files in files_by_pattern.items():
            if len(files) > 0:
                commands.append(self._generate_delete_command(file_type, files, dry_run))

        commands.extend(self._generate_size_based_commands(dry_run))

        return commands

    def _group_files_by_pattern(self) -> Dict[str, List[str]]:
        pattern_groups = defaultdict(list)

        for file_path, info in self.large_files.items():
            file_type = info.file_type

            if file_type in ['archive', 'video', 'audio', 'image']:
                ext = FileTypeAnalyzer.get_file_extension(file_path)
                if ext:
                    pattern_groups[f"{file_type}_files"].append(file_path)
            else:
                filename = os.path.basename(file_path)
                if filename not in pattern_groups:
                    pattern_groups[filename] = []
                pattern_groups[filename].append(file_path)

        return dict(pattern_groups)

    def _generate_delete_command(self, pattern_name: str, files: List[str], dry_run: bool = False) -> str:
        dry_flag = " --no-commit" if dry_run else ""
        if len(files) == 1:
            file_path = files[0]
            filename = os.path.basename(file_path)
            return f"java -jar bfg.jar --delete-files '{filename}'{dry_flag} {self.repo_path}"
        else:
            exts = set()
            for f in files:
                ext = FileTypeAnalyzer.get_file_extension(f)
                if ext:
                    exts.add(ext.lstrip('.'))
            if exts:
                ext_pattern = '{' + ','.join(exts) + '}'
                return f"java -jar bfg.jar --delete-files '*.{ext_pattern}'{dry_flag} {self.repo_path}"
            else:
                return f"java -jar bfg.jar --delete-files '{pattern_name}'{dry_flag} {self.repo_path}"

    def _generate_size_based_commands(self, dry_run: bool = False) -> List[str]:
        commands = []
        dry_flag = " --no-commit" if dry_run else ""
        large_files_sorted = sorted(
            self.large_files.values(),
            key=lambda x: x.max_size,
            reverse=True
        )

        if large_files_sorted:
            median_size = large_files_sorted[len(large_files_sorted) // 2].max_size
            size_mb = int(median_size / (1024 * 1024))
            if size_mb >= 1:
                commands.append(
                    f"java -jar bfg.jar --strip-blobs-bigger-than {size_mb}M{dry_flag} {self.repo_path}"
                )

        return commands

    def generate_cleanup_steps(self, dry_run: bool = False) -> List[str]:
        mode_label = "【预演模式 - 仅查看，不实际修改】" if dry_run else "【正式执行模式】"
        steps = [
            f"=== Git 仓库清理步骤 (BFG Repo-Cleaner) === {mode_label}",
            "",
            "前置准备:",
            "  1. 下载 BFG Repo-Cleaner: https://rtyley.github.io/bfg-repo-cleaner/",
            "  2. 将 bfg.jar 放在仓库目录或系统路径中",
            "  3. 确保有 Java 运行环境 (JRE 8+)",
            "  4. 克隆一个裸仓库副本进行清理（推荐）:",
            f"     git clone --mirror {self.repo_path} clean_repo.git",
            "",
        ]

        if dry_run:
            steps.extend([
                "⚠  预演模式说明:",
                "  - 以下命令添加了 --no-commit 参数",
                "  - BFG 将分析并报告将要删除的对象，但不实际写入",
                "  - 请先在预演模式下确认无误后再正式执行",
                "",
            ])

        steps.append("清理命令:")
        for cmd in self.generate_bfg_commands(dry_run=dry_run):
            steps.append(f"  {cmd}")

        if dry_run:
            steps.extend([
                "",
                "验证步骤:",
                "  1. 检查 BFG 输出，确认将要删除的文件列表正确",
                "  2. 确认没有误删重要文件",
                "  3. 确认无误后，去掉 --no-commit 参数重新执行正式命令",
                "",
                "正式执行命令（去掉预演参数）:"
            ])
            for cmd in self.generate_bfg_commands(dry_run=False):
                steps.append(f"  {cmd}")
        else:
            steps.extend([
                "",
                "正式执行后操作:"
            ])

        steps.extend([
            "",
            "清理后执行:",
            "  1. 进入仓库目录",
            "  2. 执行垃圾回收:",
            "     cd clean_repo.git",
            "     git reflog expire --expire=now --all",
            "     git gc --prune=now --aggressive",
            "",
            "  3. 验证清理结果:",
            "     git count-objects -vH",
            "",
            "  4. 推送到远程仓库:",
            "     git push --force",
            "",
            "  5. 所有协作者需要重新克隆仓库或执行:",
            "     git fetch --all --prune",
            "     git rebase",
            "",
            "注意事项:",
            "  - 清理操作会修改 Git 历史，所有 commit hash 会改变",
            "  - 操作前务必备份仓库",
            "  - 确保所有分支和标签都已推送到远程",
            "  - 大文件清理后应配置 .gitignore 防止再次提交"
        ])

        return steps

    def verify_dry_run(self) -> dict:
        result = {
            'bfg_available': False,
            'java_available': False,
            'backup_created': False,
            'commands': [],
            'warnings': []
        }

        java_path = shutil.which('java')
        if java_path:
            result['java_available'] = True
            try:
                proc = subprocess.run(
                    ['java', '-version'],
                    capture_output=True, text=True, timeout=10
                )
                if proc.returncode == 0:
                    version_line = proc.stderr.split('\n')[0] if proc.stderr else ''
                    result['java_version'] = version_line
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass
        else:
            result['warnings'].append("未找到 Java 运行环境，BFG 需要 JRE 8+")

        bfg_path = shutil.which('bfg') or os.path.exists('bfg.jar')
        if bfg_path:
            result['bfg_available'] = True
        else:
            result['warnings'].append("未找到 bfg.jar，请下载: https://rtyley.github.io/bfg-repo-cleaner/")

        repo_git_dir = os.path.join(self.repo_path, '.git')
        if os.path.isdir(repo_git_dir):
            result['repo_valid'] = True
        else:
            result['repo_valid'] = False
            result['warnings'].append(f"路径 {self.repo_path} 不是有效的 Git 仓库")

        result['commands'] = self.generate_bfg_commands(dry_run=True)

        total_affected = len(self.large_files)
        result['affected_files'] = total_affected
        if total_affected > 50:
            result['warnings'].append(
                f"将影响 {total_affected} 个文件路径，建议分批清理"
            )

        return result


class SizeEstimator:
    def __init__(self, scanner: GitHistoryScanner):
        self.scanner = scanner
        self.large_files = scanner.large_files

    def _measure_git_compression(self) -> float:
        total_loose_size = 0
        total_pack_size = 0
        objects_dir = os.path.join(self.scanner.repo_path, '.git', 'objects')

        loose_dir = os.path.join(objects_dir, 'pack')
        for dirpath, dirnames, filenames in os.walk(objects_dir):
            if 'pack' in dirpath:
                continue
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                total_loose_size += os.path.getsize(filepath)

        pack_dir = os.path.join(objects_dir, 'pack')
        if os.path.isdir(pack_dir):
            for filename in os.listdir(pack_dir):
                if filename.endswith('.pack'):
                    filepath = os.path.join(pack_dir, filename)
                    total_pack_size += os.path.getsize(filepath)

        idx_path = os.path.join(pack_dir, '') if os.path.isdir(pack_dir) else ''
        idx_size = 0
        if os.path.isdir(pack_dir):
            for filename in os.listdir(pack_dir):
                if filename.endswith('.idx'):
                    idx_size += os.path.getsize(os.path.join(pack_dir, filename))

        try:
            count_output = self.scanner.repo.git.count_objects('-v')
            count_info = {}
            for line in count_output.split('\n'):
                if ':' in line:
                    key, val = line.split(':', 1)
                    count_info[key.strip()] = int(val.strip())

            in_pack = count_info.get('in-pack', 0)
            size = count_info.get('size', 0)
            pack_size_kb = count_info.get('pack-size', 0)
            pack_size_bytes = pack_size_kb * 1024

            if in_pack > 0 and pack_size_bytes > 0:
                count_output2 = self.scanner.repo.git.count_objects('-v')
                return pack_size_bytes / max(size * 1024 + pack_size_bytes, 1)
        except Exception:
            pass

        total_stored = total_loose_size + total_pack_size
        if total_pack_size > 0 and total_loose_size > 0:
            return total_pack_size / (total_loose_size + total_pack_size)

        return 0.65

    def _estimate_per_type_compression(self) -> Dict[str, float]:
        git_compression = self._measure_git_compression()

        type_compression = {}
        for file_path, info in self.large_files.items():
            file_type = info.file_type
            if '/' in file_type:
                primary_type = file_type.split('/')[0]
            else:
                primary_type = file_type

            base_factor = COMPRESSION_FACTORS.get(primary_type, COMPRESSION_FACTORS['other'])
            effective = base_factor * git_compression
            effective = max(0.1, min(effective, 1.0))

            if file_type not in type_compression:
                type_compression[file_type] = effective

        return type_compression

    def estimate_savings(self) -> dict:
        total_repo_size = self.scanner.get_repo_size()
        total_large_size = self.scanner.get_total_large_size()
        unique_blobs = set()
        blob_sizes = {}

        for info in self.large_files.values():
            for blob_id in info.blob_ids:
                unique_blobs.add(blob_id)
                blob_sizes[blob_id] = self.scanner.all_blobs.get(blob_id, 0)

        unique_blob_count = len(unique_blobs)
        total_unique_size = sum(blob_sizes.values())

        git_compression = self._measure_git_compression()
        type_compression = self._estimate_per_type_compression()

        blob_type_map: Dict[str, str] = {}
        for file_path, info in self.large_files.items():
            for blob_id in info.blob_ids:
                blob_type_map[blob_id] = info.file_type

        estimated_pack_size = 0
        for blob_id, raw_size in blob_sizes.items():
            file_type = blob_type_map.get(blob_id, 'other')
            factor = type_compression.get(file_type, git_compression)
            estimated_pack_size += int(raw_size * factor)

        actual_savings = min(estimated_pack_size, total_repo_size)

        savings_low = int(actual_savings * 0.8)
        savings_high = int(actual_savings * 1.2)

        return {
            'total_repo_size': total_repo_size,
            'total_large_files_size': total_large_size,
            'unique_large_blobs': unique_blob_count,
            'unique_blobs_size': total_unique_size,
            'estimated_savings': actual_savings,
            'estimated_savings_low': savings_low,
            'estimated_savings_high': savings_high,
            'estimated_reduction_percent': (
                (actual_savings / total_repo_size * 100) if total_repo_size > 0 else 0
            ),
            'estimated_reduction_low': (
                (savings_low / total_repo_size * 100) if total_repo_size > 0 else 0
            ),
            'estimated_reduction_high': (
                (savings_high / total_repo_size * 100) if total_repo_size > 0 else 0
            ),
            'git_compression_factor': git_compression,
            'type_compression_factors': type_compression
        }

    def generate_savings_report(self) -> List[str]:
        savings = self.estimate_savings()

        report = [
            "=== 仓库瘦身预估报告 ===",
            "",
            f"当前仓库大小 (.git/objects): {format_size(savings['total_repo_size'])}",
            f"大文件总大小 (所有版本): {format_size(savings['total_large_files_size'])}",
            f"唯一大文件 blob 数量: {savings['unique_large_blobs']}",
            f"唯一大文件总大小: {format_size(savings['unique_blobs_size'])}",
            "",
            f"Git 压缩率因子: {savings['git_compression_factor']:.3f}",
            "",
            "各类型文件压缩率因子:"
        ]

        for ftype, factor in savings['type_compression_factors'].items():
            report.append(f"  {ftype:20s} -> {factor:.3f}")

        report.extend([
            "",
            "预估瘦身效果:",
            f"  预计可节省空间: {format_size(savings['estimated_savings'])}",
            f"  预计缩减比例: {savings['estimated_reduction_percent']:.1f}%",
            "",
            f"  保守估计节省: {format_size(savings['estimated_savings_low'])} ({savings['estimated_reduction_low']:.1f}%)",
            f"  乐观估计节省: {format_size(savings['estimated_savings_high'])} ({savings['estimated_reduction_high']:.1f}%)",
            "",
            "说明:",
            "  - 压缩率因子基于实际 Git pack 文件与 loose 对象比值计算",
            "  - 不同文件类型有独立的压缩率（如图片/视频几乎不可压缩，日志/文本压缩率高）",
            "  - 实际节省空间取决于 Git 对象压缩率，以保守估计为准",
            "  - 清理后需运行 git gc --prune=now --aggressive 才能真正释放空间",
            "  - 如有多个分支引用相同 blob，节省空间可能更多"
        ])

        return report
