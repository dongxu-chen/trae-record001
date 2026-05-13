import argparse
import json
import os
import fnmatch
import time
import threading
from datetime import datetime
from pathlib import Path
from collections import deque

try:
    import yaml
except ImportError:
    raise ImportError("PyYAML 未安装，请运行: pip install pyyaml")

from log import logger, setup_logger
from duplicate_handler import DuplicateHandler
from ml_classify import MLClassifier
from undo import UndoManager

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False


class PriorityClassifier:
    def __init__(self, config: dict, type_map: dict, ml_classifier: MLClassifier = None):
        self.config = config
        self.type_map = type_map
        self.ml_classifier = ml_classifier
        self.priority_rules = config.get("priority_rules", ["name_pattern", "ml_classify", "extension"])
        self.name_patterns = config.get("name_patterns", {})
        self.image_extensions = set()
        for ext in type_map.get("Images", []):
            self.image_extensions.add(ext.lower())

    def _match_name_pattern(self, file_name: str) -> str:
        file_lower = file_name.lower()
        for pattern, category in self.name_patterns.items():
            if fnmatch.fnmatch(file_lower, pattern.lower()):
                logger.debug(f"Name pattern matched: {file_name} -> {pattern} -> {category}")
                return category
        return None

    def _classify_by_ml(self, file_path: Path) -> str:
        if self.ml_classifier is None:
            return None

        ext = file_path.suffix.lower()
        if ext not in self.image_extensions:
            return None

        result = self.ml_classifier.classify(file_path)
        return result.get("category")

    def _classify_by_extension(self, ext: str) -> str:
        ext_lower = ext.lower()
        for category, extensions in self.type_map.items():
            if ext_lower in extensions:
                return category
        return "Others"

    def get_category(self, file_path: Path) -> str:
        for rule in self.priority_rules:
            if rule == "name_pattern":
                category = self._match_name_pattern(file_path.name)
                if category:
                    return category
            elif rule == "ml_classify":
                category = self._classify_by_ml(file_path)
                if category:
                    return category
            elif rule == "extension":
                category = self._classify_by_extension(file_path.suffix)
                if category:
                    return category

        return "Others"


class DownloadEventHandler(FileSystemEventHandler):
    def __init__(self, organizer, debounce_seconds: float = 2.0):
        self.organizer = organizer
        self.debounce_seconds = debounce_seconds
        self.pending_files = {}
        self._lock = threading.Lock()

    def _schedule_process(self, file_path: Path):
        with self._lock:
            self.pending_files[str(file_path)] = time.time()

        threading.Timer(self.debounce_seconds, self._process_pending).start()

    def _process_pending(self):
        now = time.time()
        files_to_process = []

        with self._lock:
            for file_path_str, timestamp in list(self.pending_files.items()):
                if now - timestamp >= self.debounce_seconds:
                    files_to_process.append(Path(file_path_str))
                    del self.pending_files[file_path_str]

        for file_path in files_to_process:
            self.organizer._organize_single_file(file_path, record_history=False)

    def on_created(self, event):
        if not event.is_directory:
            self._schedule_process(Path(event.src_path))

    def on_moved(self, event):
        if not event.is_directory:
            self._schedule_process(Path(event.dest_path))


class DownloadOrganizer:
    def __init__(self, config_path: str = "config.yaml", type_map_path: str = "file_type_map.json"):
        try:
            self.config = self._load_config(config_path)
            self.type_map = self._load_type_map(type_map_path)
            self.download_folder = Path(os.path.expandvars(self.config["download_folder"]))
            self.duplicate_handler = DuplicateHandler(self.config["duplicate_strategy"])
            self.undo_manager = UndoManager(config_path=config_path)
            self.history_operations = []

            setup_logger(
                "download_organizer",
                self.config["log_level"],
                self.config["log_file"],
                self.config.get("log_rotation", {})
            )

            self.ml_classifier = None
            ml_config = self.config.get("ml_classify", {})
            if ml_config.get("enabled", False):
                self.ml_classifier = MLClassifier(
                    model_name=ml_config.get("model", "resnet50"),
                    threshold=ml_config.get("threshold", 0.5),
                    category_map=ml_config.get("categories", {})
                )

            self.priority_classifier = PriorityClassifier(
                self.config,
                self.type_map,
                self.ml_classifier
            )

            self.observer = None
        except Exception as e:
            logger.error(f"Failed to initialize organizer: {e}")
            raise

    def _load_config(self, path: str) -> dict:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.error(f"Config file not found: {path}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML in config file: {e}")
            raise

    def _load_type_map(self, path: str) -> dict:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Type map file not found: {path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in type map: {e}")
            raise

    def _should_ignore(self, file_name: str) -> bool:
        patterns = self.config.get("ignore_patterns", [])
        for pattern in patterns:
            if fnmatch.fnmatch(file_name, pattern):
                return True
        return False

    def _wait_file_ready(self, file_path: Path, timeout: float = 10.0) -> bool:
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                with open(file_path, "rb"):
                    pass
                return True
            except (PermissionError, OSError):
                time.sleep(0.5)
        return False

    def _organize_single_file(self, file_path: Path, record_history: bool = True) -> bool:
        try:
            if not file_path.exists() or not file_path.is_file():
                return False

            if self._should_ignore(file_path.name):
                return False

            if not self._wait_file_ready(file_path):
                logger.warning(f"File still locked, skipping: {file_path.name}")
                return False

            category = self.priority_classifier.get_category(file_path)
            target_dir = self.download_folder / category
            target_path = target_dir / file_path.name

            final_path = self.duplicate_handler.handle(file_path, target_path)

            if final_path is None:
                return False

            dry_run = self.config.get("dry_run", False)

            if dry_run:
                logger.info(f"[DRY RUN] Would move: {file_path.name} -> {category}/{final_path.name}")
                return True

            source_str = str(file_path.resolve())
            dest_str = str(final_path.resolve())

            if self.duplicate_handler.move_file(file_path, final_path):
                if record_history and source_str != dest_str:
                    self.history_operations.append({
                        "source": source_str,
                        "destination": dest_str,
                        "category": category,
                        "timestamp": datetime.now().isoformat()
                    })
                return True
            return False

        except PermissionError as e:
            logger.warning(f"Permission denied for {file_path.name}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error processing {file_path.name}: {e}")
            return False

    def organize(self):
        if not self.download_folder.exists():
            logger.error(f"Download folder does not exist: {self.download_folder}")
            return

        dry_run = self.config.get("dry_run", False)
        logger.info(f"Starting organization of: {self.download_folder}")
        if dry_run:
            logger.info("DRY RUN mode - no files will be moved")

        self.history_operations = []
        stats = {"moved": 0, "skipped": 0, "failed": 0}

        try:
            items = list(self.download_folder.iterdir())
        except PermissionError as e:
            logger.error(f"Permission denied accessing download folder: {e}")
            return
        except Exception as e:
            logger.error(f"Failed to list download folder: {e}")
            return

        for item in items:
            try:
                if item.is_file() and not self._should_ignore(item.name):
                    if self._organize_single_file(item, record_history=True):
                        stats["moved"] += 1
                    else:
                        stats["failed"] += 1
            except Exception as e:
                logger.error(f"Unexpected error processing {item.name}: {e}")
                stats["failed"] += 1

        if not dry_run and self.history_operations:
            self.undo_manager.save_history(self.history_operations)

        logger.info(f"Organization complete. Moved: {stats['moved']}, Failed: {stats['failed']}")
        return stats

    def start_watchdog(self):
        if not WATCHDOG_AVAILABLE:
            logger.error("Watchdog not installed. Run: pip install watchdog")
            return False

        if not self.download_folder.exists():
            logger.error(f"Download folder does not exist: {self.download_folder}")
            return False

        watchdog_config = self.config.get("watchdog", {})
        recursive = watchdog_config.get("recursive", False)
        debounce = watchdog_config.get("debounce_seconds", 2.0)

        event_handler = DownloadEventHandler(self, debounce_seconds=debounce)
        self.observer = Observer()
        self.observer.schedule(event_handler, str(self.download_folder), recursive=recursive)
        self.observer.start()

        logger.info(f"Watchdog started. Monitoring: {self.download_folder}")
        logger.info("Press Ctrl+C to stop...")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Stopping watchdog...")
            self.observer.stop()

        self.observer.join()
        logger.info("Watchdog stopped.")
        return True


def main():
    parser = argparse.ArgumentParser(description="Download Folder Organizer")
    parser.add_argument("--config", default="config.yaml", help="Path to config file")
    parser.add_argument("--type-map", default="file_type_map.json", help="Path to file type map")
    parser.add_argument("--watch", action="store_true", help="Start watchdog mode for real-time monitoring")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without moving files")
    parser.add_argument("--undo", action="store_true", help="Undo the last organization")
    parser.add_argument("--list-history", action="store_true", help="List last organization history")

    args = parser.parse_args()

    if args.undo or args.list_history:
        undo_mgr = UndoManager(config_path=args.config)
        if args.list_history:
            undo_mgr.list_history()
        else:
            undo_mgr.undo(dry_run=args.dry_run)
        return

    organizer = DownloadOrganizer(config_path=args.config, type_map_path=args.type_map)

    if args.dry_run:
        organizer.config["dry_run"] = True

    if args.watch:
        organizer.start_watchdog()
    else:
        organizer.organize()


if __name__ == "__main__":
    main()
