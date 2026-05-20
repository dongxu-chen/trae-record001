#!/usr/bin/env python3
import os
import re
import sys
import json
import logging
import argparse
import datetime
import yaml
import docker
import schedule
import time
import socket
from tabulate import tabulate
from pathlib import Path
from dateutil import parser as date_parser
from fnmatch import fnmatch
from collections import deque


class DockerImageCleaner:
    def __init__(self, config_path="config.yaml"):
        self.config = self._load_config(config_path)
        self._setup_logging()
        self.client = self._connect_docker()
        self.whitelist = self._build_whitelist()
        self.days_unused = self.config["cleanup"]["days_unused"]
        self.dry_run = self.config["cleanup"]["dry_run"]
        self.dockerfile_paths = self.config.get("dependency", {}).get("dockerfile_paths", ["./"])
        self.dependent_images = set()
        self.hostname = socket.gethostname()
        self.history_data = self._load_disk_history()
        self.audit_logger = self._setup_audit_logger()

    def _load_config(self, config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            sys.exit(1)

    def _setup_logging(self):
        log_config = self.config.get("logging", {})
        log_level = getattr(logging, log_config.get("level", "INFO").upper())
        log_file = log_config.get("log_file", "./logs/docker_cleaner.log")
        
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(log_file, encoding="utf-8"),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)

    def _setup_audit_logger(self):
        audit_config = self.config.get("audit", {})
        if not audit_config.get("enable", True):
            return None
        
        audit_logger = logging.getLogger("audit")
        audit_logger.setLevel(logging.INFO)
        audit_logger.propagate = False
        
        audit_file = audit_config.get("log_file", "./logs/audit.log")
        os.makedirs(os.path.dirname(audit_file), exist_ok=True)
        
        file_handler = logging.FileHandler(audit_file, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter("%(message)s"))
        audit_logger.addHandler(file_handler)
        
        elk_config = audit_config.get("elk", {})
        if elk_config.get("enable", False):
            try:
                from logging.handlers import HTTPHandler
                elk_host = elk_config.get("host", "localhost")
                elk_port = elk_config.get("port", 9200)
                elk_index = elk_config.get("index", "docker-cleaner-audit")
                
                class ELKHandler(logging.Handler):
                    def __init__(self, host, port, index):
                        super().__init__()
                        self.host = host
                        self.port = port
                        self.index = index
                        self.url = f"http://{host}:{port}/{index}/_doc"
                    
                    def emit(self, record):
                        try:
                            import urllib.request
                            log_entry = json.loads(record.getMessage())
                            data = json.dumps(log_entry).encode("utf-8")
                            req = urllib.request.Request(
                                self.url,
                                data=data,
                                headers={"Content-Type": "application/json"},
                                method="POST"
                            )
                            urllib.request.urlopen(req, timeout=5)
                        except Exception as e:
                            pass
                
                elk_handler = ELKHandler(elk_host, elk_port, elk_index)
                audit_logger.addHandler(elk_handler)
                self.logger.info(f"ELK审计日志已启用: {elk_host}:{elk_port}/{elk_index}")
            except Exception as e:
                self.logger.warning(f"ELK审计日志初始化失败: {e}")
        
        return audit_logger

    def _connect_docker(self):
        try:
            client = docker.from_env()
            client.ping()
            self.logger.info("成功连接到Docker守护进程")
            return client
        except Exception as e:
            self.logger.error(f"连接Docker失败: {e}")
            sys.exit(1)

    def _build_whitelist(self):
        wl_config = self.config.get("whitelist", {})
        whitelist = {
            "repositories": wl_config.get("repositories", []),
            "tags": wl_config.get("tags", []),
            "images": wl_config.get("images", [])
        }
        self.logger.info(f"白名单已加载: {len(whitelist['repositories'])} 个仓库, "
                        f"{len(whitelist['tags'])} 个标签, "
                        f"{len(whitelist['images'])} 个镜像")
        return whitelist

    def _match_pattern(self, pattern, text):
        if "*" in pattern or "?" in pattern:
            return fnmatch(text, pattern)
        return pattern == text

    def _is_whitelisted(self, image):
        if not image.tags:
            return False
        
        for tag in image.tags:
            for pattern in self.whitelist["images"]:
                if self._match_pattern(pattern, tag):
                    return True
            
            if ":" in tag:
                repo, tag_name = tag.rsplit(":", 1)
                for pattern in self.whitelist["repositories"]:
                    if self._match_pattern(pattern, repo):
                        return True
                for pattern in self.whitelist["tags"]:
                    if self._match_pattern(pattern, tag_name):
                        return True
        return False

    def _parse_dockerfile(self, dockerfile_path):
        base_images = []
        try:
            with open(dockerfile_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            from_pattern = re.compile(
                r'^\s*FROM\s+(?:--platform=\S+\s+)?([^\s]+)',
                re.IGNORECASE | re.MULTILINE
            )
            
            matches = from_pattern.findall(content)
            for match in matches:
                match = match.strip()
                if match and not match.startswith("${"):
                    base_images.append(match)
                    
        except Exception as e:
            self.logger.debug(f"解析Dockerfile失败 {dockerfile_path}: {e}")
        
        return base_images

    def _scan_dockerfiles(self):
        self.logger.info("扫描Dockerfile分析镜像依赖...")
        all_base_images = set()
        
        for base_path in self.dockerfile_paths:
            path = Path(base_path)
            if not path.exists():
                self.logger.warning(f"路径不存在: {base_path}")
                continue
            
            if path.is_file():
                dockerfiles = [path]
            else:
                dockerfiles = list(path.rglob("Dockerfile")) + list(path.rglob("Dockerfile.*"))
            
            for dockerfile in dockerfiles:
                base_images = self._parse_dockerfile(str(dockerfile))
                if base_images:
                    self.logger.debug(f"发现 {dockerfile} 依赖: {base_images}")
                    all_base_images.update(base_images)
        
        self.dependent_images = all_base_images
        self.logger.info(f"扫描完成，发现 {len(all_base_images)} 个被依赖的基础镜像")
        return all_base_images

    def _is_dependent(self, image):
        if not image.tags or not self.dependent_images:
            return False
        
        for tag in image.tags:
            if tag in self.dependent_images:
                return True
            
            if ":" in tag:
                repo, tag_name = tag.rsplit(":", 1)
                for dep in self.dependent_images:
                    if ":" in dep:
                        dep_repo, dep_tag = dep.rsplit(":", 1)
                        if repo == dep_repo and (tag_name == dep_tag or dep_tag == "latest"):
                            return True
                    else:
                        if repo == dep:
                            return True
        return False

    def _get_image_usage_count(self, image_id):
        count = 0
        try:
            for container in self.client.containers.list(all=True):
                if container.image.id == image_id:
                    count += 1
        except Exception as e:
            self.logger.warning(f"获取容器信息失败: {e}")
        return count

    def _get_last_used_time(self, image_id):
        latest_time = None
        try:
            for container in self.client.containers.list(all=True):
                if container.image.id == image_id:
                    try:
                        state = container.attrs.get("State", {})
                        finished_at = state.get("FinishedAt")
                        started_at = state.get("StartedAt")
                        
                        times = []
                        if finished_at and finished_at != "0001-01-01T00:00:00Z":
                            times.append(date_parser.parse(finished_at))
                        if started_at and started_at != "0001-01-01T00:00:00Z":
                            times.append(date_parser.parse(started_at))
                        
                        if times:
                            container_latest = max(times)
                            if latest_time is None or container_latest > latest_time:
                                latest_time = container_latest
                    except Exception as e:
                        self.logger.debug(f"解析容器时间失败: {e}")
        except Exception as e:
            self.logger.warning(f"获取容器状态失败: {e}")
        
        return latest_time

    def _format_size(self, size_bytes):
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"

    def _get_disk_usage(self):
        try:
            docker_root = self.client.info().get("DockerRootDir", "/var/lib/docker")
            if not os.path.exists(docker_root):
                docker_root = "/"
            
            stat = os.statvfs(docker_root)
            total = stat.f_frsize * stat.f_blocks
            free = stat.f_frsize * stat.f_bavail
            used = total - free
            usage_percent = (used / total) * 100 if total > 0 else 0
            
            return {
                "path": docker_root,
                "total": total,
                "used": used,
                "free": free,
                "usage_percent": usage_percent,
                "total_human": self._format_size(total),
                "used_human": self._format_size(used),
                "free_human": self._format_size(free)
            }
        except Exception as e:
            self.logger.warning(f"获取磁盘使用情况失败: {e}")
            return None

    def _load_disk_history(self):
        history_file = self.config.get("disk", {}).get("history_file", "./data/disk_history.json")
        os.makedirs(os.path.dirname(history_file), exist_ok=True)
        
        try:
            if os.path.exists(history_file):
                with open(history_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return deque(data, maxlen=100)
        except Exception as e:
            self.logger.warning(f"加载磁盘历史数据失败: {e}")
        
        return deque(maxlen=100)

    def _save_disk_history(self):
        history_file = self.config.get("disk", {}).get("history_file", "./data/disk_history.json")
        try:
            with open(history_file, "w", encoding="utf-8") as f:
                json.dump(list(self.history_data), f, indent=2)
        except Exception as e:
            self.logger.warning(f"保存磁盘历史数据失败: {e}")

    def _record_disk_usage(self, disk_info):
        if not disk_info:
            return
        
        record = {
            "timestamp": datetime.datetime.now().isoformat(),
            "used": disk_info["used"],
            "total": disk_info["total"],
            "usage_percent": disk_info["usage_percent"]
        }
        self.history_data.append(record)
        self._save_disk_history()

    def _predict_disk_full(self, disk_info):
        if not disk_info or len(self.history_data) < 2:
            return None
        
        try:
            history = list(self.history_data)
            first = history[0]
            last = history[-1]
            
            first_time = date_parser.parse(first["timestamp"])
            last_time = date_parser.parse(last["timestamp"])
            days_between = (last_time - first_time).total_seconds() / 86400
            
            if days_between < 1:
                return None
            
            used_increase = last["used"] - first["used"]
            daily_growth = used_increase / days_between
            
            if daily_growth <= 0:
                return {
                    "days_until_full": "无限",
                    "daily_growth": 0,
                    "daily_growth_human": "0 B",
                    "trend": "稳定或下降"
                }
            
            remaining = disk_info["total"] - disk_info["used"]
            days_until_full = remaining / daily_growth
            
            return {
                "days_until_full": round(days_until_full, 1),
                "daily_growth": daily_growth,
                "daily_growth_human": self._format_size(daily_growth),
                "trend": "增长"
            }
        except Exception as e:
            self.logger.warning(f"磁盘空间预测失败: {e}")
            return None

    def _check_auto_cleanup_trigger(self, disk_info):
        auto_config = self.config.get("auto_cleanup", {})
        if not auto_config.get("enable", True):
            return False, None
        
        threshold = auto_config.get("disk_usage_threshold", 80)
        if disk_info and disk_info["usage_percent"] >= threshold:
            reason = f"磁盘使用率 {disk_info['usage_percent']:.1f}% 超过阈值 {threshold}%"
            return True, reason
        
        return False, None

    def _simulate_delete(self, image_id, tags):
        try:
            for container in self.client.containers.list(all=True):
                if container.image.id == image_id:
                    status = container.status
                    if status == "running":
                        return False, "有运行中的容器使用此镜像"
                    else:
                        return False, f"有已停止的容器({container.id[:8]})使用此镜像"
            
            for image in self.client.images.list(all=True):
                if image.id == image_id:
                    continue
                try:
                    history = image.history()
                    if history and len(history) > 0:
                        for layer in history:
                            if layer.get("Id") and image_id in layer.get("Id", ""):
                                return False, "被其他镜像作为父镜像引用"
                except:
                    pass
            
            return True, None
        except Exception as e:
            return False, str(e)

    def scan_images(self):
        self.logger.info("开始扫描Docker镜像...")
        
        if self.config.get("dependency", {}).get("enable", True):
            self._scan_dockerfiles()
        
        images_data = []
        
        try:
            images = self.client.images.list(all=True)
            self.logger.info(f"发现 {len(images)} 个镜像")
            
            for image in images:
                try:
                    created_at = datetime.datetime.fromtimestamp(
                        image.attrs.get("Created", 0),
                        tz=datetime.timezone.utc
                    )
                    last_used = self._get_last_used_time(image.id)
                    usage_count = self._get_image_usage_count(image.id)
                    
                    now = datetime.datetime.now(datetime.timezone.utc)
                    days_since_created = (now - created_at).days
                    
                    if last_used:
                        days_unused = (now - last_used).days
                    else:
                        days_unused = days_since_created
                    
                    is_whitelisted = self._is_whitelisted(image)
                    is_dangling = len(image.tags) == 0
                    is_dependent = self._is_dependent(image)
                    
                    needs_cleanup = (
                        days_unused >= self.days_unused and 
                        not is_whitelisted and 
                        not is_dependent and
                        usage_count == 0
                    )
                    
                    if is_dangling and self.config["cleanup"].get("remove_dangling", True):
                        needs_cleanup = True
                    
                    images_data.append({
                        "id": image.id[:12],
                        "full_id": image.id,
                        "tags": ", ".join(image.tags) if image.tags else "<none>",
                        "tag_list": image.tags,
                        "size": image.attrs.get("Size", 0),
                        "size_human": self._format_size(image.attrs.get("Size", 0)),
                        "created_at": created_at.strftime("%Y-%m-%d %H:%M:%S"),
                        "days_since_created": days_since_created,
                        "last_used": last_used.strftime("%Y-%m-%d %H:%M:%S") if last_used else "从未使用",
                        "days_unused": days_unused,
                        "usage_count": usage_count,
                        "is_whitelisted": is_whitelisted,
                        "is_dangling": is_dangling,
                        "is_dependent": is_dependent,
                        "needs_cleanup": needs_cleanup,
                        "simulate_result": None,
                        "simulate_error": None
                    })
                except Exception as e:
                    self.logger.warning(f"处理镜像 {image.id} 失败: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"扫描镜像失败: {e}")
        
        return images_data

    def simulate_deletion(self, images_data):
        if not self.dry_run:
            return images_data
        
        self.logger.info("开始模拟删除验证...")
        images_to_cleanup = [img for img in images_data if img["needs_cleanup"]]
        
        for img in images_to_cleanup:
            can_delete, error = self._simulate_delete(img["full_id"], img["tag_list"])
            img["simulate_result"] = can_delete
            img["simulate_error"] = error
            
            if not can_delete:
                img["needs_cleanup"] = False
                self.logger.info(f"模拟删除失败: {img['tags']} - {error}")
            else:
                self.logger.debug(f"模拟删除成功: {img['tags']}")
        
        self.logger.info("模拟删除验证完成")
        return images_data

    def _write_audit_log(self, event_type, data):
        if not self.audit_logger:
            return
        
        audit_entry = {
            "@timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "event": event_type,
            "host": self.hostname,
            "dry_run": self.dry_run,
            **data
        }
        
        self.audit_logger.info(json.dumps(audit_entry, ensure_ascii=False))

    def generate_report(self, images_data, disk_info=None, prediction=None, auto_trigger=None):
        self.logger.info("生成清理报告...")
        
        images_to_cleanup = [img for img in images_data if img["needs_cleanup"]]
        whitelisted_images = [img for img in images_data if img["is_whitelisted"]]
        dangling_images = [img for img in images_data if img["is_dangling"]]
        dependent_images = [img for img in images_data if img["is_dependent"]]
        
        total_size = sum(img["size"] for img in images_data)
        cleanup_size = sum(img["size"] for img in images_to_cleanup)
        
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("DOCKER 镜像清理巡检报告")
        report_lines.append("=" * 80)
        report_lines.append(f"生成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"清理阈值: {self.days_unused} 天未使用")
        report_lines.append(f"干跑模式: {'启用' if self.dry_run else '禁用'}")
        if self.dry_run:
            report_lines.append("模拟删除: 已执行")
        report_lines.append("")
        
        if disk_info:
            report_lines.append("-" * 80)
            report_lines.append("磁盘使用情况")
            report_lines.append("-" * 80)
            disk_data = [
                ["磁盘路径", disk_info["path"]],
                ["总容量", disk_info["total_human"]],
                ["已使用", disk_info["used_human"]],
                ["可用空间", disk_info["free_human"]],
                ["使用率", f"{disk_info['usage_percent']:.1f}%"]
            ]
            if prediction:
                if prediction["days_until_full"] == "无限":
                    disk_data.append(["预计满盘时间", "磁盘空间充足，无增长趋势"])
                else:
                    disk_data.append(["日增长量", prediction["daily_growth_human"]])
                    disk_data.append(["预计满盘天数", f"{prediction['days_until_full']} 天"])
                    disk_data.append(["增长趋势", prediction["trend"]])
            report_lines.append(tabulate(disk_data, tablefmt="simple"))
            
            if auto_trigger and auto_trigger[0]:
                report_lines.append(f"\n⚠️  自动清理触发: {auto_trigger[1]}")
            report_lines.append("")
        
        report_lines.append("-" * 80)
        report_lines.append("统计概览")
        report_lines.append("-" * 80)
        stats_data = [
            ["镜像总数", len(images_data)],
            ["总大小", self._format_size(total_size)],
            ["待清理镜像数", len(images_to_cleanup)],
            ["可释放空间", self._format_size(cleanup_size)],
            ["白名单镜像数", len(whitelisted_images)],
            ["被依赖镜像数", len(dependent_images)],
            ["悬空镜像数", len(dangling_images)],
        ]
        report_lines.append(tabulate(stats_data, tablefmt="simple"))
        report_lines.append("")
        
        if self.dry_run:
            failed_sim = [img for img in images_data if img["simulate_result"] is False]
            if failed_sim:
                report_lines.append("-" * 80)
                report_lines.append(f"模拟删除失败列表 ({len(failed_sim)} 个)")
                report_lines.append("-" * 80)
                fail_table = []
                for img in failed_sim:
                    fail_table.append([
                        img["id"],
                        img["tags"],
                        img["simulate_error"] or "未知错误"
                    ])
                report_lines.append(tabulate(
                    fail_table,
                    headers=["ID", "标签", "失败原因"],
                    tablefmt="grid"
                ))
                report_lines.append("")
        
        report_lines.append("-" * 80)
        report_lines.append(f"最终待清理镜像列表 ({len(images_to_cleanup)} 个)")
        report_lines.append("-" * 80)
        
        if images_to_cleanup:
            cleanup_table = []
            for img in sorted(images_to_cleanup, key=lambda x: x["size"], reverse=True):
                sim_status = "可删除" if img["simulate_result"] else "未验证" if img["simulate_result"] is None else "不可删除"
                cleanup_table.append([
                    img["id"],
                    img["tags"],
                    img["size_human"],
                    img["created_at"],
                    img["days_unused"],
                    "是" if img["is_dangling"] else "否",
                    sim_status
                ])
            report_lines.append(tabulate(
                cleanup_table,
                headers=["ID", "标签", "大小", "创建时间", "未使用天数", "悬空镜像", "模拟状态"],
                tablefmt="grid"
            ))
        else:
            report_lines.append("没有需要清理的镜像")
        report_lines.append("")
        
        report_lines.append("-" * 80)
        report_lines.append(f"白名单镜像列表 ({len(whitelisted_images)} 个)")
        report_lines.append("-" * 80)
        
        if whitelisted_images:
            wl_table = []
            for img in whitelisted_images:
                wl_table.append([
                    img["id"],
                    img["tags"],
                    img["size_human"],
                    img["usage_count"]
                ])
            report_lines.append(tabulate(
                wl_table,
                headers=["ID", "标签", "大小", "使用次数"],
                tablefmt="grid"
            ))
        report_lines.append("")
        
        if dependent_images:
            report_lines.append("-" * 80)
            report_lines.append(f"Dockerfile依赖镜像列表 ({len(dependent_images)} 个)")
            report_lines.append("-" * 80)
            dep_table = []
            for img in dependent_images:
                dep_table.append([
                    img["id"],
                    img["tags"],
                    img["size_human"],
                    img["usage_count"]
                ])
            report_lines.append(tabulate(
                dep_table,
                headers=["ID", "标签", "大小", "使用次数"],
                tablefmt="grid"
            ))
            report_lines.append("")
        
        report_lines.append("-" * 80)
        report_lines.append("所有镜像详情")
        report_lines.append("-" * 80)
        all_table = []
        for img in sorted(images_data, key=lambda x: x["days_unused"], reverse=True):
            all_table.append([
                img["id"],
                img["tags"][:40],
                img["size_human"],
                img["days_since_created"],
                img["days_unused"],
                img["usage_count"],
                "是" if img["is_whitelisted"] else "否",
                "是" if img["is_dependent"] else "否",
                "是" if img["needs_cleanup"] else "否"
            ])
        report_lines.append(tabulate(
            all_table,
            headers=["ID", "标签", "大小", "创建天数", "未使用天数", "使用次数", "白名单", "被依赖", "待清理"],
            tablefmt="grid"
        ))
        
        report_content = "\n".join(report_lines)
        
        report_dir = self.config["report"].get("output_dir", "./reports")
        os.makedirs(report_dir, exist_ok=True)
        report_file = os.path.join(
            report_dir,
            f"cleanup_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report_content)
        
        self.logger.info(f"报告已保存到: {report_file}")
        
        print(report_content)
        
        return report_content, images_to_cleanup

    def cleanup_images(self, images_to_cleanup, trigger_reason=None):
        if not images_to_cleanup:
            self.logger.info("没有需要清理的镜像")
            return 0, 0
        
        self.logger.info(f"开始清理 {len(images_to_cleanup)} 个镜像...")
        
        deleted_images = []
        failed_images = []
        total_freed = 0
        
        if self.dry_run:
            self.logger.info("=" * 60)
            self.logger.info("干跑模式 - 最终清理计划")
            self.logger.info("=" * 60)
            self.logger.info(f"将删除以下 {len(images_to_cleanup)} 个镜像:")
            for img in sorted(images_to_cleanup, key=lambda x: x["size"], reverse=True):
                self.logger.info(f"  - {img['tags']} ({img['size_human']})")
                deleted_images.append({
                    "id": img["id"],
                    "tags": img["tags"],
                    "size": img["size"],
                    "size_human": img["size_human"]
                })
                total_freed += img["size"]
            self.logger.info(f"预计释放空间: {self._format_size(total_freed)}")
            self.logger.info("=" * 60)
            self.logger.info("干跑模式已启用，跳过实际删除操作")
            
            self._write_audit_log("cleanup", {
                "trigger_reason": trigger_reason or "scheduled",
                "total_images": len(images_to_cleanup),
                "deleted_count": len(deleted_images),
                "failed_count": 0,
                "total_freed_bytes": total_freed,
                "total_freed_human": self._format_size(total_freed),
                "deleted_images": deleted_images,
                "failed_images": failed_images
            })
            
            return len(deleted_images), total_freed
        
        deleted_count = 0
        failed_count = 0
        
        for img in images_to_cleanup:
            try:
                self.logger.info(f"删除镜像: {img['tags']} ({img['id']})")
                self.client.images.remove(img["full_id"], force=True)
                deleted_count += 1
                total_freed += img["size"]
                deleted_images.append({
                    "id": img["id"],
                    "tags": img["tags"],
                    "size": img["size"],
                    "size_human": img["size_human"]
                })
            except Exception as e:
                self.logger.error(f"删除镜像 {img['id']} 失败: {e}")
                failed_count += 1
                failed_images.append({
                    "id": img["id"],
                    "tags": img["tags"],
                    "error": str(e)
                })
        
        self.logger.info(f"清理完成: 成功删除 {deleted_count} 个, 失败 {failed_count} 个, 释放空间 {self._format_size(total_freed)}")
        
        self._write_audit_log("cleanup", {
            "trigger_reason": trigger_reason or "scheduled",
            "total_images": len(images_to_cleanup),
            "deleted_count": deleted_count,
            "failed_count": failed_count,
            "total_freed_bytes": total_freed,
            "total_freed_human": self._format_size(total_freed),
            "deleted_images": deleted_images,
            "failed_images": failed_images
        })
        
        return deleted_count, total_freed

    def run(self):
        self.logger.info("=" * 60)
        self.logger.info("开始执行Docker镜像清理巡检")
        self.logger.info("=" * 60)
        
        disk_info = self._get_disk_usage()
        if disk_info:
            self._record_disk_usage(disk_info)
            self.logger.info(f"磁盘使用情况: {disk_info['usage_percent']:.1f}% ({disk_info['used_human']}/{disk_info['total_human']})")
        
        prediction = self._predict_disk_full(disk_info)
        if prediction:
            if prediction["days_until_full"] == "无限":
                self.logger.info("磁盘空间趋势: 稳定或下降")
            else:
                self.logger.info(f"磁盘预测: 日增长 {prediction['daily_growth_human']}, 预计 {prediction['days_until_full']} 天后满盘")
        
        auto_trigger = self._check_auto_cleanup_trigger(disk_info)
        if auto_trigger[0]:
            self.logger.warning(f"自动清理触发: {auto_trigger[1]}")
            original_dry_run = self.dry_run
            auto_config = self.config.get("auto_cleanup", {})
            if auto_config.get("force_clean", False):
                self.dry_run = False
                self.logger.info("自动清理模式: 强制执行清理")
        
        images_data = self.scan_images()
        
        if self.dry_run:
            images_data = self.simulate_deletion(images_data)
        
        _, images_to_cleanup = self.generate_report(images_data, disk_info, prediction, auto_trigger)
        
        trigger_reason = auto_trigger[1] if auto_trigger[0] else None
        self.cleanup_images(images_to_cleanup, trigger_reason)
        
        if auto_trigger[0]:
            self.dry_run = original_dry_run
        
        self.logger.info("巡检任务完成")

    def run_scheduled(self):
        schedule_time = self.config["cleanup"].get("schedule", "02:00")
        self.logger.info(f"定时任务已启动，每天 {schedule_time} 执行清理巡检")
        
        schedule.every().day.at(schedule_time).do(self.run)
        
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)
            except KeyboardInterrupt:
                self.logger.info("收到中断信号，退出程序")
                break
            except Exception as e:
                self.logger.error(f"调度器运行出错: {e}")
                time.sleep(60)


def parse_args():
    parser = argparse.ArgumentParser(description="Docker镜像清理巡检工具")
    parser.add_argument(
        "-c", "--config",
        default="config.yaml",
        help="配置文件路径 (默认: config.yaml)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="干跑模式，不实际删除镜像"
    )
    parser.add_argument(
        "--schedule",
        action="store_true",
        help="以定时任务模式运行"
    )
    parser.add_argument(
        "--days",
        type=int,
        help="覆盖配置中的未使用天数阈值"
    )
    parser.add_argument(
        "--no-simulate",
        action="store_true",
        help="干跑模式下跳过模拟删除验证"
    )
    parser.add_argument(
        "--force-clean",
        action="store_true",
        help="强制执行清理（忽略dry_run设置）"
    )
    return parser.parse_args()


def main():
    args = parse_args()
    
    cleaner = DockerImageCleaner(args.config)
    
    if args.dry_run:
        cleaner.dry_run = True
        cleaner.logger.info("命令行参数: 启用干跑模式")
    
    if args.force_clean:
        cleaner.dry_run = False
        cleaner.logger.info("命令行参数: 强制执行清理")
    
    if args.no_simulate:
        cleaner.config["cleanup"]["skip_simulate"] = True
        cleaner.logger.info("命令行参数: 跳过模拟删除验证")
    
    if args.days:
        cleaner.days_unused = args.days
        cleaner.logger.info(f"命令行参数: 覆盖未使用天数阈值为 {args.days} 天")
    
    if args.schedule:
        cleaner.run_scheduled()
    else:
        cleaner.run()


if __name__ == "__main__":
    main()
