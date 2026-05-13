#!/usr/bin/env python3
"""
Docker 镜像检查工具 - 查看镜像层大小和元数据
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


def format_size(size_bytes: int) -> str:
    """
    格式化字节大小

    Args:
        size_bytes: 字节数

    Returns:
        格式化的字符串
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


class ImageInspector:
    """Docker 镜像检查器"""

    def __init__(self):
        """初始化检查器"""
        pass

    def _run_docker_command(self, args: List[str]) -> tuple[bool, str, str]:
        """
        运行 Docker 命令

        Args:
            args: 命令参数列表

        Returns:
            (是否成功, stdout, stderr)
        """
        try:
            result = subprocess.run(
                ["docker"] + args,
                capture_output=True,
                text=True,
                shell=False,
            )
            return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
        except FileNotFoundError:
            return False, "", "Docker 命令未找到"
        except Exception as e:
            return False, "", str(e)

    def image_exists(self, image_name: str) -> bool:
        """
        检查镜像是否存在

        Args:
            image_name: 镜像名称

        Returns:
            是否存在
        """
        success, stdout, _ = self._run_docker_command(["images", "-q", image_name])
        return success and bool(stdout.strip())

    def get_image_info(self, image_name: str) -> Optional[Dict[str, Any]]:
        """
        获取镜像基本信息

        Args:
            image_name: 镜像名称

        Returns:
            镜像信息字典
        """
        success, stdout, stderr = self._run_docker_command(
            ["inspect", "--format", "{{json .}}", image_name]
        )
        if not success:
            print(f"获取镜像信息失败: {stderr}")
            return None

        try:
            return json.loads(stdout)
        except json.JSONDecodeError:
            return None

    def get_image_history(self, image_name: str) -> Optional[List[Dict[str, Any]]]:
        """
        获取镜像历史（层信息）

        Args:
            image_name: 镜像名称

        Returns:
            层信息列表
        """
        success, stdout, stderr = self._run_docker_command(
            ["history", "--format", "{{json .}}", "--no-trunc", image_name]
        )
        if not success:
            print(f"获取镜像历史失败: {stderr}")
            return None

        layers = []
        for line in stdout.strip().split("\n"):
            if line:
                try:
                    layer_info = json.loads(line)
                    layers.append(layer_info)
                except json.JSONDecodeError:
                    pass

        return layers

    def get_layer_size(self, image_name: str) -> Optional[List[Dict[str, Any]]]:
        """
        获取各层的详细大小

        Args:
            image_name: 镜像名称

        Returns:
            层大小信息列表
        """
        history = self.get_image_history(image_name)
        if not history:
            return None

        layers_with_size = []
        for layer in history:
            size_str = layer.get("Size", "0B")
            size_bytes = self._parse_size_to_bytes(size_str)

            layers_with_size.append({
                "id": layer.get("ID", "")[:12] if layer.get("ID") else "",
                "created_by": layer.get("CreatedBy", ""),
                "size": size_str,
                "size_bytes": size_bytes,
                "created_at": layer.get("CreatedAt", ""),
                "comment": layer.get("Comment", ""),
            })

        return layers_with_size

    def _parse_size_to_bytes(self, size_str: str) -> int:
        """
        解析大小字符串为字节数

        Args:
            size_str: 大小字符串，如 "1.2MB", "500kB"

        Returns:
            字节数
        """
        size_str = size_str.strip()
        if size_str == "0B" or size_str == "0":
            return 0

        units = {
            "B": 1,
            "KB": 1024,
            "kB": 1024,
            "MB": 1024 * 1024,
            "GB": 1024 * 1024 * 1024,
        }

        for unit, multiplier in units.items():
            if size_str.endswith(unit):
                try:
                    value = float(size_str[:-len(unit)])
                    return int(value * multiplier)
                except ValueError:
                    pass

        return 0

    def inspect(
        self,
        image_name: str,
        show_layers: bool = True,
        show_details: bool = False,
        max_layers: int = 50,
        sort_by_size: bool = False,
        output_format: str = "table",
        output_file: Optional[str] = None,
    ) -> bool:
        """
        检查镜像

        Args:
            image_name: 镜像名称
            show_layers: 是否显示层信息
            show_details: 是否显示详细信息
            max_layers: 显示的最大层数
            sort_by_size: 是否按大小排序
            output_format: 输出格式 (table, json)
            output_file: 输出文件

        Returns:
            是否成功
        """
        print(f"\n{'='*70}")
        print(f"检查镜像: {image_name}")
        print(f"{'='*70}\n")

        if not self.image_exists(image_name):
            print(f"错误: 镜像 {image_name} 不存在")
            return False

        image_info = self.get_image_info(image_name)
        if not image_info:
            return False

        layer_info = self.get_layer_size(image_name)

        report = self._build_report(image_name, image_info, layer_info)

        if output_format == "json":
            output = json.dumps(report, indent=2, ensure_ascii=False)
            if output_file:
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(output)
                print(f"JSON 报告已保存: {output_file}")
            else:
                print(output)
            return True

        self._print_table_report(report, show_layers, show_details, max_layers, sort_by_size)

        return True

    def _build_report(
        self,
        image_name: str,
        image_info: Dict[str, Any],
        layer_info: Optional[List[Dict[str, Any]]],
    ) -> Dict[str, Any]:
        """
        构建检查报告

        Args:
            image_name: 镜像名称
            image_info: 镜像信息
            layer_info: 层信息

        Returns:
            报告字典
        """
        config = image_info.get("Config", {})
        root_fs = image_info.get("RootFS", {})

        total_size = image_info.get("Size", 0)
        virtual_size = image_info.get("VirtualSize", total_size)

        layers = root_fs.get("Layers", [])
        layer_count = len(layers)

        if layer_info:
            for layer in layer_info:
                size = layer.get("size_bytes", 0)
                if size > 0:
                    pass

        return {
            "image_name": image_name,
            "id": image_info.get("Id", "").replace("sha256:", "")[:12],
            "digest": image_info.get("RepoDigests", [""])[0] if image_info.get("RepoDigests") else "",
            "created": image_info.get("Created", ""),
            "os": config.get("Os", ""),
            "architecture": config.get("Architecture", ""),
            "size": total_size,
            "size_formatted": format_size(total_size),
            "virtual_size": virtual_size,
            "virtual_size_formatted": format_size(virtual_size),
            "layer_count": layer_count,
            "entrypoint": config.get("Entrypoint", []),
            "cmd": config.get("Cmd", []),
            "env": config.get("Env", []),
            "exposed_ports": list(config.get("ExposedPorts", {}).keys()) if config.get("ExposedPorts") else [],
            "working_dir": config.get("WorkingDir", ""),
            "layers": layer_info or [],
        }

    def _print_table_report(
        self,
        report: Dict[str, Any],
        show_layers: bool,
        show_details: bool,
        max_layers: int,
        sort_by_size: bool,
    ) -> None:
        """
        打印表格格式的报告

        Args:
            report: 报告数据
            show_layers: 是否显示层
            show_details: 是否显示细节
            max_layers: 最大层数
            sort_by_size: 是否按大小排序
        """
        print("基本信息")
        print("-" * 70)
        print(f"  镜像 ID:      {report['id']}")
        print(f"  操作系统:     {report['os']}")
        print(f"  架构:         {report['architecture']}")
        print(f"  创建时间:     {report['created']}")
        print(f"  总大小:       {report['size_formatted']}")
        print(f"  虚拟大小:     {report['virtual_size_formatted']}")
        print(f"  层数:         {report['layer_count']}")

        if show_details:
            print("\n配置信息")
            print("-" * 70)
            if report["entrypoint"]:
                print(f"  Entrypoint:   {' '.join(report['entrypoint'])}")
            if report["cmd"]:
                print(f"  Cmd:          {' '.join(report['cmd'])}")
            if report["env"]:
                print(f"  环境变量:")
                for env in report["env"][:10]:
                    print(f"    {env}")
                if len(report["env"]) > 10:
                    print(f"    ... 还有 {len(report['env']) - 10} 个")
            if report["exposed_ports"]:
                print(f"  暴露端口:     {', '.join(report['exposed_ports'])}")
            if report["working_dir"]:
                print(f"  工作目录:     {report['working_dir']}")

        if show_layers and report["layers"]:
            layers = report["layers"]

            if sort_by_size:
                layers = [l for l in layers if l.get("size_bytes", 0) > 0]
                layers.sort(key=lambda x: x["size_bytes"], reverse=True)

            print(f"\n层信息 (显示前 {min(len(layers), max_layers)} 层)")
            print("-" * 70)
            print(f"{'大小':>12}  {'指令'}")
            print("-" * 70)

            for layer in layers[:max_layers]:
                size_str = layer.get("size", "0B")
                created_by = layer.get("created_by", "")

                cmd_short = created_by
                if len(cmd_short) > 50:
                    cmd_short = cmd_short[:47] + "..."

                print(f"{size_str:>12}  {cmd_short}")

            if len(layers) > max_layers:
                print(f"\n... 还有 {len(layers) - max_layers} 层未显示")

            non_empty_layers = [l for l in layers if l.get("size_bytes", 0) > 0]
            if non_empty_layers:
                largest = max(non_empty_layers, key=lambda x: x["size_bytes"])
                print(f"\n层大小统计")
                print("-" * 70)
                print(f"  非空层数:     {len(non_empty_layers)}")
                print(f"  最大层:       {largest['size']}")
                print(f"    指令:       {largest['created_by'][:60]}")


def compare_images(image_names: List[str], inspector: ImageInspector) -> bool:
    """
    比较多个镜像

    Args:
        image_names: 镜像名称列表
        inspector: 检查器实例

    Returns:
        是否成功
    """
    if len(image_names) < 2:
        print("错误: 请至少提供 2 个镜像进行比较")
        return False

    print(f"\n{'='*70}")
    print("镜像比较")
    print(f"{'='*70}\n")

    reports = []
    for name in image_names:
        if not inspector.image_exists(name):
            print(f"错误: 镜像 {name} 不存在")
            return False

        info = inspector.get_image_info(name)
        layers = inspector.get_layer_size(name)
        if info and layers:
            reports.append(inspector._build_report(name, info, layers))

    print(f"{'镜像':<30} {'大小':>12} {'层数':>8} {'OS':<12} {'架构':<12}")
    print("-" * 80)
    for report in reports:
        print(
            f"{report['image_name']:<30} "
            f"{report['size_formatted']:>12} "
            f"{report['layer_count']:>8} "
            f"{report['os']:<12} "
            f"{report['architecture']:<12}"
        )

    return True


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="Docker 镜像检查工具 - 查看层大小和元数据")

    parser.add_argument(
        "-n",
        "--name",
        required=True,
        help="镜像名称",
    )

    parser.add_argument(
        "-t",
        "--tag",
        default="latest",
        help="镜像标签",
    )

    parser.add_argument(
        "--no-layers",
        action="store_true",
        help="不显示层信息",
    )

    parser.add_argument(
        "--details",
        action="store_true",
        help="显示详细配置信息",
    )

    parser.add_argument(
        "--max-layers",
        type=int,
        default=50,
        help="显示的最大层数",
    )

    parser.add_argument(
        "--sort-by-size",
        action="store_true",
        help="按层大小排序显示",
    )

    parser.add_argument(
        "--format",
        choices=["table", "json"],
        default="table",
        help="输出格式",
    )

    parser.add_argument(
        "--output",
        help="输出文件路径",
    )

    parser.add_argument(
        "--compare",
        nargs="+",
        help="与其他镜像比较 (提供镜像名称列表)",
    )

    return parser.parse_args()


def main():
    """主函数"""
    args = parse_args()

    inspector = ImageInspector()

    if args.compare:
        all_images = [f"{args.name}:{args.tag}"] + args.compare
        return 0 if compare_images(all_images, inspector) else 1

    image_full = f"{args.name}:{args.tag}"

    success = inspector.inspect(
        image_name=image_full,
        show_layers=not args.no_layers,
        show_details=args.details,
        max_layers=args.max_layers,
        sort_by_size=args.sort_by_size,
        output_format=args.format,
        output_file=args.output,
    )

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
