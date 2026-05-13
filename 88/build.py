#!/usr/bin/env python3
"""
Docker 镜像构建自动化脚本 - 支持多阶段构建和多架构构建（buildx）
"""
import argparse
import os
import sys
from pathlib import Path

from dockerfile_gen import DockerfileGenerator
from cache import CacheManager
from push import ImagePusher


class DockerBuilder:
    """Docker 镜像构建器"""

    def __init__(self, config_path: str = "build_config.json"):
        """
        初始化构建器

        Args:
            config_path: 配置文件路径
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.dockerfile_gen = DockerfileGenerator(self.config)
        self.cache_manager = CacheManager(self.config)
        self.image_pusher = ImagePusher(self.config)
        self.buildx_config = self.config.get("buildx", {})
        self.use_buildx = self.buildx_config.get("enabled", False)
        self.builder_name = self.buildx_config.get("builder_name", "multiarch-builder")
        self.default_platforms = self.buildx_config.get("platforms", ["linux/amd64"])

    def _load_config(self) -> dict:
        """加载配置文件"""
        import json

        if not self.config_path.exists():
            print(f"错误: 配置文件 {self.config_path} 不存在")
            sys.exit(1)

        with open(self.config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _run_command(self, command: list, max_retries: int = 3, retry_delay: int = 5) -> bool:
        """
        运行系统命令（支持网络重试）

        Args:
            command: 命令列表
            max_retries: 最大重试次数
            retry_delay: 重试间隔（秒）

        Returns:
            是否成功
        """
        import subprocess
        import time

        print(f"执行命令: {' '.join(command)}")

        network_error_patterns = [
            "timeout",
            "timed out",
            "connection reset",
            "connection refused",
            "network is unreachable",
            "no route to host",
            "i/o timeout",
            "tls handshake timeout",
        ]

        last_error = None
        for attempt in range(1, max_retries + 1):
            try:
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    shell=False,
                )

                if result.returncode == 0:
                    if result.stdout:
                        sys.stdout.write(result.stdout)
                    if result.stderr:
                        sys.stderr.write(result.stderr)
                    return True

                combined_output = (result.stdout + result.stderr).lower()
                is_network_error = any(
                    pattern in combined_output for pattern in network_error_patterns
                )

                if result.stdout:
                    sys.stdout.write(result.stdout)
                if result.stderr:
                    sys.stderr.write(result.stderr)

                if is_network_error and attempt < max_retries:
                    print(f"\n检测到网络错误，{retry_delay}秒后进行第 {attempt + 1}/{max_retries} 次重试...")
                    time.sleep(retry_delay)
                    continue

                last_error = f"命令返回错误码 {result.returncode}"
                break

            except Exception as e:
                last_error = str(e)
                print(f"命令执行异常: {e}")
                if attempt < max_retries:
                    print(f"{retry_delay}秒后进行第 {attempt + 1}/{max_retries} 次重试...")
                    time.sleep(retry_delay)
                    continue
                break

        if last_error:
            print(f"命令执行失败（已重试 {max_retries} 次）: {last_error}")
        return False

    def _run_command_capture(self, command: list, max_retries: int = 1) -> tuple[bool, str, str]:
        """
        运行系统命令并捕获输出

        Args:
            command: 命令列表
            max_retries: 最大重试次数

        Returns:
            (是否成功, stdout, stderr)
        """
        import subprocess
        import time

        network_error_patterns = [
            "timeout",
            "timed out",
            "connection reset",
            "connection refused",
            "network is unreachable",
            "no route to host",
            "i/o timeout",
            "tls handshake timeout",
        ]

        for attempt in range(1, max_retries + 1):
            try:
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    shell=False,
                )

                if result.returncode == 0:
                    return True, result.stdout.strip(), result.stderr.strip()

                combined_output = (result.stdout + result.stderr).lower()
                is_network_error = any(
                    pattern in combined_output for pattern in network_error_patterns
                )

                if is_network_error and attempt < max_retries:
                    time.sleep(2)
                    continue

                return False, result.stdout.strip(), result.stderr.strip()

            except Exception as e:
                if attempt < max_retries:
                    time.sleep(2)
                    continue
                return False, "", str(e)

        return False, "", ""

    def _ensure_buildx_builder(self) -> bool:
        """
        确保 buildx builder 存在并处于可用状态

        Returns:
            是否成功
        """
        if not self.use_buildx:
            return True

        print(f"\n检查 buildx builder: {self.builder_name}")

        success, stdout, _ = self._run_command_capture(
            ["docker", "buildx", "ls"]
        )
        if not success:
            print("错误: docker buildx 不可用，请先安装 Docker Buildx")
            return False

        if self.builder_name in stdout:
            print(f"builder {self.builder_name} 已存在")
            success_inspect, _, _ = self._run_command_capture(
                ["docker", "buildx", "inspect", self.builder_name]
            )
            if success_inspect:
                return True

        print(f"创建 builder: {self.builder_name}")
        success_create, _, stderr = self._run_command_capture(
            ["docker", "buildx", "create", "--name", self.builder_name, "--use"]
        )
        if not success_create:
            print(f"创建 builder 失败: {stderr}")
            return False

        print(f"使用 builder: {self.builder_name}")
        self._run_command_capture(["docker", "buildx", "use", self.builder_name])

        success_bootstrap, _, _ = self._run_command_capture(
            ["docker", "buildx", "inspect", "--bootstrap"]
        )
        if not success_bootstrap:
            print("警告: builder bootstrap 失败，但尝试继续")

        return True

    def generate_dockerfile(self, stage: str = "all") -> str:
        """
        生成 Dockerfile

        Args:
            stage: 构建阶段名称，'all' 表示生成完整 Dockerfile

        Returns:
            生成的 Dockerfile 路径
        """
        output_path = Path(self.config.get("dockerfile_output", "Dockerfile"))
        self.dockerfile_gen.generate(output_path=str(output_path), stage=stage)
        return str(output_path)

    def build(
        self,
        image_name: str,
        tag: str = "latest",
        stage: str = None,
        use_cache: bool = True,
        push: bool = False,
        platforms: list = None,
        load: bool = False,
        output_type: str = None,
    ) -> bool:
        """
        构建 Docker 镜像（支持 buildx 多架构）

        Args:
            image_name: 镜像名称
            tag: 镜像标签
            stage: 构建阶段（用于多阶段构建）
            use_cache: 是否使用缓存
            push: 构建后是否推送（buildx 模式下 build --push）
            load: 是否加载到本地 Docker 镜像（仅 buildx，与 push 互斥）
            platforms: 目标架构列表，如 ["linux/amd64", "linux/arm64"]
            output_type: 输出类型 ("image", "registry", "local", "tar")

        Returns:
            构建是否成功
        """
        print(f"\n{'='*60}")
        print(f"开始构建镜像: {image_name}:{tag}")
        if stage:
            print(f"构建阶段: {stage}")
        if platforms:
            print(f"目标架构: {', '.join(platforms)}")
        print(f"{'='*60}\n")

        dockerfile_path = self.generate_dockerfile(stage or "all")

        build_params = {"stage": stage, "platforms": platforms}

        if self.use_buildx:
            if not self._ensure_buildx_builder():
                return False
            return self._buildx_build(
                image_name=image_name,
                tag=tag,
                dockerfile_path=dockerfile_path,
                stage=stage,
                use_cache=use_cache,
                push=push,
                load=load,
                platforms=platforms or self.default_platforms,
                output_type=output_type,
                build_params=build_params,
            )
        else:
            return self._classic_build(
                image_name=image_name,
                tag=tag,
                dockerfile_path=dockerfile_path,
                stage=stage,
                use_cache=use_cache,
                push=push,
                build_params=build_params,
            )

    def _classic_build(
        self,
        image_name: str,
        tag: str,
        dockerfile_path: str,
        stage: str,
        use_cache: bool,
        push: bool,
        build_params: dict,
    ) -> bool:
        """传统 docker build"""
        build_command = ["docker", "build", "-t", f"{image_name}:{tag}", "-f", dockerfile_path]

        if stage:
            build_command.extend(["--target", stage])

        if use_cache:
            cache_from = self.cache_manager.get_cache_from(image_name, tag, build_params)
            if cache_from:
                build_command.extend(["--cache-from", cache_from])

        build_context = self.config.get("build_context", ".")
        build_command.append(build_context)

        if not self._run_command(build_command):
            print("镜像构建失败")
            return False

        print(f"\n镜像构建成功: {image_name}:{tag}")

        if use_cache:
            self.cache_manager.save_cache(image_name, tag, build_params)

        if push:
            return self.image_pusher.push(image_name, tag)

        return True

    def _buildx_build(
        self,
        image_name: str,
        tag: str,
        dockerfile_path: str,
        stage: str,
        use_cache: bool,
        push: bool,
        load: bool,
        platforms: list,
        output_type: str,
        build_params: dict,
    ) -> bool:
        """buildx 多架构构建"""
        build_command = ["docker", "buildx", "build"]

        tag_list = [f"{image_name}:{tag}"]
        for t in tag_list:
            build_command.extend(["-t", t])

        build_command.extend(["-f", dockerfile_path])

        if stage:
            build_command.extend(["--target", stage])

        platform_str = ",".join(platforms)
        build_command.extend(["--platform", platform_str])

        if use_cache:
            cache_from = self.cache_manager.get_cache_from(image_name, tag, build_params)
            if cache_from:
                build_command.extend(["--cache-from", f"type=registry,ref={cache_from}"])

            cache_to_registry = self.cache_manager.remote_cache_registry
            if cache_to_registry and self.cache_manager.use_remote_cache:
                cache_ref = f"{cache_to_registry}/{image_name}:{tag}-buildcache"
                build_command.extend(["--cache-to", f"type=registry,ref={cache_ref},mode=max"])

        if push:
            build_command.append("--push")
        elif load:
            build_command.append("--load")
        elif output_type:
            if output_type == "local":
                output_dir = f"./build-output/{image_name}-{tag}"
                Path(output_dir).mkdir(parents=True, exist_ok=True)
                build_command.extend(["--output", f"type=local,dest={output_dir}"])
            elif output_type == "tar":
                tar_path = f"./build-output/{image_name}-{tag}.tar"
                Path("./build-output").mkdir(parents=True, exist_ok=True)
                build_command.extend(["--output", f"type=tar,dest={tar_path}"])
            elif output_type == "oci":
                oci_path = f"./build-output/{image_name}-{tag}"
                Path("./build-output").mkdir(parents=True, exist_ok=True)
                build_command.extend(["--output", f"type=oci,dest={oci_path}"])
            elif output_type == "docker":
                tar_path = f"./build-output/{image_name}-{tag}.docker.tar"
                Path("./build-output").mkdir(parents=True, exist_ok=True)
                build_command.extend(["--output", f"type=docker,dest={tar_path}"])

        build_context = self.config.get("build_context", ".")
        build_command.append(build_context)

        print(f"构建架构: {platform_str}")

        if not self._run_command(build_command):
            print("镜像构建失败")
            return False

        print(f"\n镜像构建成功: {image_name}:{tag}")

        if use_cache and not push:
            self.cache_manager.save_cache(image_name, tag, build_params)

        return True

    def build_all_stages(
        self,
        image_name: str,
        tag: str = "latest",
        use_cache: bool = True,
        push: bool = False,
        platforms: list = None,
    ) -> bool:
        """
        构建所有阶段（用于多阶段构建的调试或中间镜像）

        Args:
            image_name: 基础镜像名称
            tag: 基础标签
            use_cache: 是否使用缓存
            push: 构建后是否推送
            platforms: 目标架构列表

        Returns:
            是否全部成功
        """
        stages = self.config.get("stages", [])
        if not stages:
            print("未配置构建阶段，执行默认构建")
            return self.build(
                image_name,
                tag,
                use_cache=use_cache,
                push=push,
                platforms=platforms,
            )

        all_success = True
        for stage in stages:
            stage_name = stage.get("name")
            stage_tag = f"{tag}-{stage_name}" if stage_name else tag
            if not self.build(
                image_name=f"{image_name}-{stage_name}" if stage_name else image_name,
                tag=stage_tag,
                stage=stage_name,
                use_cache=use_cache,
                push=False,
                platforms=platforms,
                load=True,
            ):
                all_success = False

        if all_success and push:
            if self.use_buildx:
                return self.build(
                    image_name,
                    tag,
                    use_cache=use_cache,
                    push=True,
                    platforms=platforms,
                )
            else:
                self.image_pusher.push(image_name, tag)

        return all_success


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="Docker 镜像构建自动化工具")

    parser.add_argument(
        "-c",
        "--config",
        default="build_config.json",
        help="配置文件路径 (默认: build_config.json)",
    )

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
        help="镜像标签 (默认: latest)",
    )

    parser.add_argument(
        "-s",
        "--stage",
        help="构建指定阶段 (多阶段构建)",
    )

    parser.add_argument(
        "--all-stages",
        action="store_true",
        help="构建所有阶段",
    )

    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="不使用缓存",
    )

    parser.add_argument(
        "--push",
        action="store_true",
        help="构建后推送到仓库 (buildx 模式下使用 --push)",
    )

    parser.add_argument(
        "--load",
        action="store_true",
        help="(buildx) 构建后加载到本地 Docker 镜像",
    )

    parser.add_argument(
        "--platforms",
        nargs="*",
        help="目标架构列表 (如: linux/amd64 linux/arm64 linux/arm/v7)",
    )

    parser.add_argument(
        "--output",
        choices=["image", "registry", "local", "tar", "oci", "docker"],
        help="输出类型",
    )

    parser.add_argument(
        "--buildx",
        action="store_true",
        help="强制使用 buildx 构建",
    )

    parser.add_argument(
        "--no-buildx",
        action="store_true",
        help="强制使用传统 docker build",
    )

    parser.add_argument(
        "--generate-only",
        action="store_true",
        help="仅生成 Dockerfile，不构建",
    )

    return parser.parse_args()


def main():
    """主函数"""
    args = parse_args()

    builder = DockerBuilder(config_path=args.config)

    if args.buildx:
        builder.use_buildx = True
    if args.no_buildx:
        builder.use_buildx = False

    if args.generate_only:
        dockerfile_path = builder.generate_dockerfile(args.stage or "all")
        print(f"Dockerfile 已生成: {dockerfile_path}")
        return 0

    platforms = args.platforms
    if not platforms and builder.use_buildx:
        platforms = builder.default_platforms

    if args.all_stages:
        success = builder.build_all_stages(
            image_name=args.name,
            tag=args.tag,
            use_cache=not args.no_cache,
            push=args.push,
            platforms=platforms,
        )
    else:
        success = builder.build(
            image_name=args.name,
            tag=args.tag,
            stage=args.stage,
            use_cache=not args.no_cache,
            push=args.push,
            platforms=platforms,
            load=args.load,
            output_type=args.output,
        )

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
