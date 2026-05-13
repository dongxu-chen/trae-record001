import json
import shutil
import argparse
from pathlib import Path
from datetime import datetime

try:
    import yaml
except ImportError:
    raise ImportError("PyYAML 未安装，请运行: pip install pyyaml")

from log import logger, setup_logger


class UndoManager:
    def __init__(self, config_path: str = "config.yaml"):
        self.config = self._load_config(config_path)
        self.download_folder = Path(self.config["download_folder"])
        self.history_file = Path(self.config.get("history_file", "organizer_history.json"))

        setup_logger(
            "undo_manager",
            self.config.get("log_level", "INFO"),
            self.config.get("log_file", "organizer.log"),
            self.config.get("log_rotation", {})
        )

    def _load_config(self, path: str) -> dict:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def load_history(self) -> list:
        if not self.history_file.exists():
            logger.warning(f"No history file found: {self.history_file}")
            return []

        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("operations", [])
        except Exception as e:
            logger.error(f"Failed to load history: {e}")
            return []

    def save_history(self, operations: list, timestamp: str = None):
        timestamp = timestamp or datetime.now().isoformat()
        data = {
            "timestamp": timestamp,
            "operations": operations
        }

        try:
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"History saved: {len(operations)} operations")
        except Exception as e:
            logger.error(f"Failed to save history: {e}")

    def _generate_unique_path(self, dest: Path) -> Path:
        if not dest.exists():
            return dest

        parent = dest.parent
        stem = dest.stem
        suffix = dest.suffix
        counter = 1

        while True:
            new_name = f"{stem} (restored {counter}){suffix}"
            new_path = parent / new_name
            if not new_path.exists():
                return new_path
            counter += 1

    def undo(self, dry_run: bool = False) -> dict:
        operations = self.load_history()
        if not operations:
            logger.info("Nothing to undo.")
            return {"restored": 0, "skipped": 0, "failed": 0}

        logger.info(f"Undoing {len(operations)} operations...")
        if dry_run:
            logger.info("DRY RUN mode - no files will be moved")

        stats = {"restored": 0, "skipped": 0, "failed": 0}
        failed_ops = []

        for op in reversed(operations):
            source = Path(op["destination"])
            target = Path(op["source"])

            if not source.exists():
                logger.warning(f"Source file not found, already moved or deleted: {source}")
                stats["skipped"] += 1
                failed_ops.append(op)
                continue

            if target.exists():
                target = self._generate_unique_path(target)
                logger.info(f"Target exists, using: {target.name}")

            target.parent.mkdir(parents=True, exist_ok=True)

            try:
                if dry_run:
                    logger.info(f"[DRY RUN] Would restore: {source.name} -> {target.name}")
                    stats["restored"] += 1
                else:
                    shutil.move(str(source), str(target))
                    logger.info(f"Restored: {source.name} -> {target.name}")
                    stats["restored"] += 1
            except PermissionError as e:
                logger.error(f"Permission denied restoring {source.name}: {e}")
                stats["failed"] += 1
                failed_ops.append(op)
            except Exception as e:
                logger.error(f"Failed to restore {source.name}: {e}")
                stats["failed"] += 1
                failed_ops.append(op)

        if not dry_run:
            if failed_ops:
                self.save_history(failed_ops)
                logger.info(f"Remaining {len(failed_ops)} operations saved for retry")
            else:
                if self.history_file.exists():
                    backup = self.history_file.with_suffix(".bak")
                    self.history_file.rename(backup)
                    logger.info(f"History file backed up to: {backup}")

        logger.info(f"Undo complete. Restored: {stats['restored']}, Skipped: {stats['skipped']}, Failed: {stats['failed']}")
        return stats

    def list_history(self):
        operations = self.load_history()
        if not operations:
            print("No history found.")
            return

        print(f"\n=== History ({len(operations)} operations) ===\n")
        for i, op in enumerate(operations, 1):
            print(f"{i}. {Path(op['source']).name}")
            print(f"   From: {op['source']}")
            print(f"   To:   {op['destination']}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Undo the last file organization")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without moving files")
    parser.add_argument("--list", action="store_true", help="List history without undoing")
    parser.add_argument("--config", default="config.yaml", help="Path to config file")

    args = parser.parse_args()

    undo_mgr = UndoManager(config_path=args.config)

    if args.list:
        undo_mgr.list_history()
    else:
        undo_mgr.undo(dry_run=args.dry_run)
