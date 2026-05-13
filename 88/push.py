#!/usr/bin/env python3
"""
Docker 镜像推送器 - 支持多仓库推送
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


class RegistryConfig:
    """单个仓库配置"""

    def __init__(self, config: Dict[str, Any]):
        self.name = config.get("name", "default")
        self.url = config.get("url", "")
        self.username = config.get("username", "")
        self.password = config.get("password", "")
        self.password_file = config.get("password_file", "")
        self.use_tls = config.get("use_tls", True)
        self.insecure = config.get("insecure", False)
        self.enabled = config.get("enabled", True)


class ImagePusher:
    """Docker 镜像推送器（支持多仓库）"""

    def __init__(self, config: Dict):
        """
        初始化推送器

        Args:
            config: 配置字典
        """
        self.config = config
        self.registries = self._load_registries(config)

    def _load_registries(self, config: Dict) -> List[RegistryConfig]:
        """
        加载所有仓库配置

        Args:
            config: 主配置字典

        Returns:
            仓库配置列表
        """
        registries = []

        registry_list = config.get("registries", [])
        if registry_list:
            for reg_config in registry_list:
                registry = RegistryConfig(reg_config)
                if registry.enabled:
                    registries.append(registry)
        else:
            registry_config = config.get("registry", {})
            if registry_config.get("url"):
                registry = RegistryConfig(registry_config)
                if registry.enabled:
                    registries.append(registry)

        return registries

    def _load_password_from_file(self, password_file: str) -> Optional[str]:
        """
        从文件加载密码

        Args:
            password_file: 密码文件路径

        Returns:
            密码字符串
        """
        if not password_file:
            return None

        password_path = Path(password_file)
        if not password_path.exists():
            print(f"警告: 密码文件不存在: {password_file}")
            return None

        try:
            with open(password_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception as e:
            print(f"读取密码文件失败: {e}")
            return None

    def _get_password(self, registry: RegistryConfig) -> Optional[str]:
        """
        获取密码（优先使用环境变量）

        Args:
            registry: 仓库配置

        Returns:
            密码字符串
        """
        env_prefix = f"DOCKER_REGISTRY_{registry.name.upper()}_" if registry.name != "default" else "DOCKER_REGISTRY_"

        env_password = os.environ.get(f"{env_prefix}PASSWORD", "")
        if env_password:
            return env_password

        if registry.password:
            return registry.password

        return self._load_password_from_file(registry.password_file)

    def _run_docker_command(self, args: List[str]) -> bool:
        """
        运行 Docker 命令

        Args:
            args: 命令参数列表

        Returns:
            是否成功
        """
        print(f"执行命令: docker {' '.join(args)}")
        try:
            result = subprocess.run(
                ["docker"] + args,
                stdout=sys.stdout,
                stderr=sys.stderr,
                shell=False,
            )
            return result.returncode == 0
        except Exception as e:
            print(f"Docker 命令执行失败: {e}")
            return False

    def login(self, registry: RegistryConfig) -> bool:
        """
        登录到指定仓库

        Args:
            registry: 仓库配置

        Returns:
            是否成功
        """
        if not registry.url:
            print(f"[{registry.name}] 未配置仓库地址，跳过登录")
            return True

        env_prefix = f"DOCKER_REGISTRY_{registry.name.upper()}_" if registry.name != "default" else "DOCKER_REGISTRY_"
        username = registry.username or os.environ.get(f"{env_prefix}USERNAME", "")
        password = self._get_password(registry)

        if not username or not password:
            print(f"[{registry.name}] 警告: 未提供用户名或密码，尝试跳过登录")
            return True

        print(f"[{registry.name}] 登录到仓库: {registry.url}")

        login_args = ["login", registry.url, "-u", username, "--password-stdin"]

        try:
            result = subprocess.run(
                ["docker"] + login_args,
                input=password.encode("utf-8"),
                stdout=sys.stdout,
                stderr=sys.stderr,
                shell=False,
            )
            if result.returncode == 0:
                print(f"[{registry.name}] 登录成功")
                return True
            else:
                print(f"[{registry.name}] 登录失败")
                return False
        except Exception as e:
            print(f"[{registry.name}] 登录过程中出错: {e}")
            return False

    def logout(self, registry: RegistryConfig) -> bool:
        """
        登出指定仓库

        Args:
            registry: 仓库配置

        Returns:
            是否成功
        """
        if not registry.url:
            return True

        print(f"[{registry.name}] 登出仓库: {registry.url}")
        return self._run_docker_command(["logout", registry.url])

    def get_full_image_name(
        self,
        image_name: str,
        tag: str = "latest",
        registry: Optional[RegistryConfig] = None,
    ) -> str:
        """
        获取完整的镜像名称（包含仓库地址）

        Args:
            image_name: 镜像名称
            tag: 镜像标签
            registry: 仓库配置（None 表示不包含仓库）

        Returns:
            完整镜像名称
        """
        if registry and registry.url:
            return f"{registry.url}/{image_name}:{tag}"
        return f"{image_name}:{tag}"

    def tag_image(self, source_image: str, target_image: str) -> bool:
        """
        给镜像打标签

        Args:
            source_image: 源镜像
            target_image: 目标镜像

        Returns:
            是否成功
        """
        print(f"打标签: {source_image} -> {target_image}")
        return self._run_docker_command(["tag", source_image, target_image])

    def push_image(self, full_image_name: str) -> bool:
        """
        推送镜像

        Args:
            full_image_name: 完整镜像名称（含仓库地址和标签）

        Returns:
            是否成功
        """
        print(f"推送镜像: {full_image_name}")
        return self._run_docker_command(["push", full_image_name])

    def push_to_registry(
        self,
        registry: RegistryConfig,
        image_name: str,
        tag: str = "latest",
        additional_tags: List[str] = None,
        source_image: Optional[str] = None,
    ) -> bool:
        """
        推送镜像到指定仓库

        Args:
            registry: 目标仓库配置
            image_name: 镜像名称
            tag: 主标签
            additional_tags: 额外标签列表
            source_image: 源镜像名称（如果不指定则使用 image_name:tag）

        Returns:
            是否成功
        """
        if not registry.enabled:
            print(f"[{registry.name}] 仓库已禁用，跳过")
            return True

        print(f"\n{'='*60}")
        print(f"[{registry.name}] 开始推送到: {registry.url}")
        print(f"{'='*60}\n")

        if not self.login(registry):
            return False

        source = source_image or f"{image_name}:{tag}"
        target_main = self.get_full_image_name(image_name, tag, registry)

        if source != target_main:
            if not self.tag_image(source, target_main):
                print(f"[{registry.name}] 打标签失败")
                self.logout(registry)
                return False

        if not self.push_image(target_main):
            print(f"[{registry.name}] 推送主标签失败")
            self.logout(registry)
            return False

        if additional_tags:
            for extra_tag in additional_tags:
                extra_target = self.get_full_image_name(image_name, extra_tag, registry)
                print(f"\n[{registry.name}] 推送额外标签: {extra_tag}")

                if self.tag_image(source, extra_target) and self.push_image(extra_target):
                    print(f"[{registry.name}] 额外标签 {extra_tag} 推送成功")
                else:
                    print(f"[{registry.name}] 额外标签 {extra_tag} 推送失败")

        self.logout(registry)

        print(f"\n{'='*60}")
        print(f"[{registry.name}] 镜像推送完成: {target_main}")
        print(f"{'='*60}\n")

        return True

    def push(
        self,
        image_name: str,
        tag: str = "latest",
        additional_tags: List[str] = None,
        registry_names: Optional[List[str]] = None,
    ) -> bool:
        """
        推送镜像到所有配置的仓库

        Args:
            image_name: 镜像名称
            tag: 主标签
            additional_tags: 额外标签列表
            registry_names: 指定仓库名称列表，None 表示推送到所有启用的仓库

        Returns:
            是否全部成功
        """
        if registry_names:
            target_registries = [r for r in self.registries if r.name in registry_names]
            if not target_registries:
                print(f"错误: 未找到指定的仓库: {registry_names}")
                return False
        else:
            target_registries = [r for r in self.registries if r.enabled]
            if not target_registries:
                print("警告: 未配置任何启用的仓库，跳过推送")
                return True

        all_success = True
        for registry in target_registries:
            if not self.push_to_registry(
                registry=registry,
                image_name=image_name,
                tag=tag,
                additional_tags=additional_tags,
            ):
                all_success = False

        return all_success

    def push_multiple(
        self,
        images: List[Dict],
        registry_names: Optional[List[str]] = None,
    ) -> bool:
        """
        批量推送多个镜像

        Args:
            images: 镜像列表，每个元素为 {"name": "...", "tag": "...", "additional_tags": [...]}
            registry_names: 指定仓库名称列表

        Returns:
            是否全部成功
        """
        if registry_names:
            target_registries = [r for r in self.registries if r.name in registry_names]
        else:
            target_registries = [r for r in self.registries if r.enabled]

        if not target_registries:
            print("警告: 未配置任何启用的仓库，跳过推送")
            return True

        all_success = True
        for registry in target_registries:
            for image_info in images:
                name = image_info.get("name", "")
                tag = image_info.get("tag", "latest")
                additional_tags = image_info.get("additional_tags", [])

                if not name:
                    continue

                if not self.push_to_registry(
                    registry=registry,
                    image_name=name,
                    tag=tag,
                    additional_tags=additional_tags,
                ):
                    all_success = False

        return all_success

    def list_registries(self) -> List[Dict]:
        """
        列出所有配置的仓库

        Returns:
            仓库信息列表
        """
        result = []
        for registry in self.registries:
            result.append({
                "name": registry.name,
                "url": registry.url,
                "username": registry.username,
                "enabled": registry.enabled,
                "insecure": registry.insecure,
            })
        return result


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="Docker 镜像推送工具（支持多仓库）")

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
        "--additional-tags",
        nargs="*",
        default=[],
        help="额外标签列表",
    )

    parser.add_argument(
        "--registries",
        nargs="*",
        help="指定推送的仓库名称列表 (不指定则推送到所有启用的仓库)",
    )

    parser.add_argument(
        "--list-registries",
        action="store_true",
        help="列出所有配置的仓库",
    )

    return parser.parse_args()


def main():
    """主函数"""
    args = parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"错误: 配置文件 {config_path} 不存在")
        sys.exit(1)

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    pusher = ImagePusher(config)

    if args.list_registries:
        registries = pusher.list_registries()
        if not registries:
            print("未配置任何仓库")
        else:
            print("\n配置的仓库列表:")
            print("-" * 60)
            for reg in registries:
                status = "启用" if reg["enabled"] else "禁用"
                secure = "HTTP" if reg["insecure"] else "HTTPS"
                print(f"  名称: {reg['name']}")
                print(f"    地址: {reg['url']}")
                print(f"    用户: {reg['username'] or '(未配置)'}")
                print(f"    状态: {status} | {secure}")
                print()
        return 0

    success = pusher.push(
        image_name=args.name,
        tag=args.tag,
        additional_tags=args.additional_tags,
        registry_names=args.registries,
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
