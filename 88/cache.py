#!/usr/bin/env python3
"""
Docker 层缓存管理器
"""
import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional


class CacheManager:
    """Docker 层缓存管理器"""

    def __init__(self, config: Dict):
        """
        初始化缓存管理器

        Args:
            config: 配置字典
        """
        self.config = config
        self.cache_config = config.get("cache", {})
        self.cache_enabled = self.cache_config.get("enabled", True)
        self.cache_dir = Path(self.cache_config.get("dir", ".docker_cache"))
        self.cache_ttl_days = self.cache_config.get("ttl_days", 30)
        self.max_cache_images = self.cache_config.get("max_images", 10)
        self.use_remote_cache = self.cache_config.get("use_remote", False)
        self.remote_cache_registry = self.cache_config.get("remote_registry", "")

        if self.cache_enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _run_docker_command(self, args: List[str]) -> Optional[str]:
        """
        运行 Docker 命令

        Args:
            args: 命令参数列表

        Returns:
            命令输出（如果成功），否则 None
        """
        try:
            result = subprocess.run(
                ["docker"] + args,
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except Exception as e:
            print(f"Docker 命令执行失败: {e}")
            return None

    def _get_cache_index_path(self) -> Path:
        """
        获取缓存索引文件路径

        Returns:
            索引文件路径
        """
        return self.cache_dir / "cache_index.json"

    def _load_cache_index(self) -> Dict:
        """
        加载缓存索引

        Returns:
            缓存索引字典
        """
        index_path = self._get_cache_index_path()
        if index_path.exists():
            try:
                with open(index_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"images": {}}

    def _save_cache_index(self, index: Dict) -> None:
        """
        保存缓存索引

        Args:
            index: 缓存索引字典
        """
        index_path = self._get_cache_index_path()
        try:
            with open(index_path, "w", encoding="utf-8") as f:
                json.dump(index, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存缓存索引失败: {e}")

    def _get_image_id(self, image_name: str, tag: str) -> Optional[str]:
        """
        获取镜像 ID

        Args:
            image_name: 镜像名称
            tag: 镜像标签

        Returns:
            镜像 ID（如果存在）
        """
        full_name = f"{image_name}:{tag}"
        output = self._run_docker_command(["images", "-q", full_name])
        if output:
            return output.strip()
        return None

    def _compute_build_params_hash(self, build_params: Optional[Dict[str, Any]] = None) -> str:
        """
        计算构建参数的哈希值

        Args:
            build_params: 构建参数字典

        Returns:
            哈希字符串
        """
        if not build_params:
            build_params = {}

        params_for_hash = {
            "base_image": self.config.get("base_image"),
            "workdir": self.config.get("workdir"),
            "env": self.config.get("env", {}),
            "stages": self.config.get("stages", []),
            "copy": self.config.get("copy", []),
            "run": self.config.get("run", []),
            "expose": self.config.get("expose", []),
            "cmd": self.config.get("cmd", []),
            "entrypoint": self.config.get("entrypoint", []),
            "variables": self.config.get("variables", {}),
            "build_args": build_params.get("build_args", {}),
            "target_stage": build_params.get("stage"),
            "platform": build_params.get("platform"),
        }

        params_str = json.dumps(params_for_hash, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(params_str.encode("utf-8")).hexdigest()[:16]

    def get_cache_from(
        self,
        image_name: str,
        tag: str,
        build_params: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        获取用于构建的缓存源镜像（比较构建参数）

        Args:
            image_name: 镜像名称
            tag: 镜像标签
            build_params: 构建参数字典（用于比较缓存是否匹配）

        Returns:
            缓存镜像名称（如果找到匹配的）
        """
        if not self.cache_enabled:
            return None

        current_hash = self._compute_build_params_hash(build_params)

        if self.use_remote_cache and self.remote_cache_registry:
            remote_cache = f"{self.remote_cache_registry}/{image_name}:{tag}"
            print(f"尝试从远程仓库拉取缓存: {remote_cache}")
            if self._pull_cache_image(remote_cache):
                print("警告: 远程缓存不支持构建参数校验，使用时需谨慎")
                return remote_cache

        index = self._load_cache_index()
        images = index.get("images", {})

        cache_candidates = [
            (f"{image_name}:{tag}", tag),
            (f"{image_name}:latest", "latest"),
        ]

        for candidate, candidate_tag in cache_candidates:
            if candidate in images:
                cached_info = images[candidate]
                cached_hash = cached_info.get("build_params_hash")

                if cached_hash and cached_hash != current_hash:
                    print(f"缓存 {candidate} 的构建参数不匹配（当前: {current_hash[:8]}，缓存: {cached_hash[:8]}），跳过")
                    continue

                image_id = self._get_image_id(image_name, candidate_tag)
                if image_id:
                    if cached_hash:
                        print(f"找到本地缓存镜像: {candidate}（构建参数匹配: {cached_hash[:8]}）")
                    else:
                        print(f"找到本地缓存镜像: {candidate}（旧版本缓存，无参数校验）")
                    return candidate

        return None

    def _pull_cache_image(self, image_name: str) -> bool:
        """
        从远程仓库拉取缓存镜像

        Args:
            image_name: 完整的镜像名称（含仓库）

        Returns:
            是否成功
        """
        try:
            result = subprocess.run(
                ["docker", "pull", image_name],
                capture_output=True,
                text=True,
                check=False,
            )
            return result.returncode == 0
        except Exception:
            return False

    def save_cache(
        self,
        image_name: str,
        tag: str,
        build_params: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        保存镜像到缓存（包含构建参数哈希）

        Args:
            image_name: 镜像名称
            tag: 镜像标签
            build_params: 构建参数字典

        Returns:
            是否成功
        """
        if not self.cache_enabled:
            return False

        image_id = self._get_image_id(image_name, tag)
        if not image_id:
            print(f"警告: 未找到镜像 {image_name}:{tag}，无法保存缓存")
            return False

        build_params_hash = self._compute_build_params_hash(build_params)

        full_name = f"{image_name}:{tag}"
        print(f"保存镜像到缓存: {full_name}（构建参数哈希: {build_params_hash[:8]}）")

        index = self._load_cache_index()
        import time

        index["images"][full_name] = {
            "image_id": image_id,
            "created_at": time.time(),
            "name": image_name,
            "tag": tag,
            "build_params_hash": build_params_hash,
        }

        self._save_cache_index(index)

        if self.use_remote_cache and self.remote_cache_registry:
            self._push_to_remote_cache(image_name, tag)

        self._cleanup_old_cache()

        return True

    def _push_to_remote_cache(self, image_name: str, tag: str) -> bool:
        """
        推送镜像到远程缓存仓库

        Args:
            image_name: 镜像名称
            tag: 镜像标签

        Returns:
            是否成功
        """
        source_image = f"{image_name}:{tag}"
        target_image = f"{self.remote_cache_registry}/{image_name}:{tag}"

        print(f"推送到远程缓存: {target_image}")

        try:
            tag_result = subprocess.run(
                ["docker", "tag", source_image, target_image],
                capture_output=True,
                text=True,
                check=False,
            )
            if tag_result.returncode != 0:
                return False

            push_result = subprocess.run(
                ["docker", "push", target_image],
                capture_output=True,
                text=True,
                check=False,
            )
            return push_result.returncode == 0
        except Exception as e:
            print(f"推送到远程缓存失败: {e}")
            return False

    def _cleanup_old_cache(self) -> None:
        """清理旧的缓存"""
        index = self._load_cache_index()
        images = index.get("images", {})
        if not images:
            return

        import time

        current_time = time.time()
        ttl_seconds = self.cache_ttl_days * 24 * 60 * 60

        expired_images = []
        for full_name, info in images.items():
            created_at = info.get("created_at", 0)
            if current_time - created_at > ttl_seconds:
                expired_images.append(full_name)

        sorted_images = sorted(
            images.items(),
            key=lambda x: x[1].get("created_at", 0),
            reverse=True,
        )

        if len(sorted_images) > self.max_cache_images:
            images_to_remove = sorted_images[self.max_cache_images:]
            for full_name, _ in images_to_remove:
                if full_name not in expired_images:
                    expired_images.append(full_name)

        for full_name in expired_images:
            if full_name in images:
                print(f"清理过期缓存: {full_name}")
                del images[full_name]

                image_name = images[full_name].get("name", "") if full_name in images else ""
                tag = images[full_name].get("tag", "") if full_name in images else ""
                if image_name and tag:
                    self._run_docker_command(["rmi", "-f", f"{image_name}:{tag}"])

        self._save_cache_index(index)

    def list_cache(self) -> List[Dict]:
        """
        列出所有缓存的镜像

        Returns:
            缓存镜像列表
        """
        index = self._load_cache_index()
        images = index.get("images", {})

        result = []
        import time

        for full_name, info in images.items():
            created_at = info.get("created_at", 0)
            result.append({
                "name": full_name,
                "image_id": info.get("image_id", ""),
                "created_at": time.strftime(
                    "%Y-%m-%d %H:%M:%S",
                    time.localtime(created_at)
                ),
            })

        return sorted(result, key=lambda x: x["created_at"], reverse=True)

    def clear_cache(self, image_name: Optional[str] = None) -> bool:
        """
        清除缓存

        Args:
            image_name: 指定镜像名称清除，None 表示清除所有

        Returns:
            是否成功
        """
        index = self._load_cache_index()
        images = index.get("images", {})

        if image_name:
            keys_to_remove = [k for k in images.keys() if k.startswith(f"{image_name}:")]
            for key in keys_to_remove:
                print(f"清除缓存: {key}")
                del images[key]
        else:
            print("清除所有缓存")
            images.clear()

        self._save_cache_index(index)

        if image_name:
            self._run_docker_command(["rmi", "-f", image_name])
        else:
            print("提示: 运行 'docker system prune -f' 可清理 Docker 系统缓存")

        return True

    def get_cache_stats(self) -> Dict:
        """
        获取缓存统计信息

        Returns:
            统计信息字典
        """
        index = self._load_cache_index()
        images = index.get("images", {})

        return {
            "enabled": self.cache_enabled,
            "cache_dir": str(self.cache_dir),
            "total_images": len(images),
            "max_images": self.max_cache_images,
            "ttl_days": self.cache_ttl_days,
            "use_remote_cache": self.use_remote_cache,
            "remote_registry": self.remote_cache_registry,
        }
