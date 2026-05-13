import os
import shutil
from pathlib import Path
from log import logger


class DuplicateHandler:
    def __init__(self, strategy: str = "rename"):
        self.strategy = strategy
        self.valid_strategies = ["rename", "skip", "overwrite"]

    def handle(self, source: Path, dest: Path) -> Path:
        if not dest.exists():
            return dest

        strategy = self.strategy.lower()
        if strategy == "skip":
            logger.info(f"Skipping duplicate: {source.name}")
            return None
        elif strategy == "overwrite":
            logger.warning(f"Overwriting existing file: {dest.name}")
            return dest
        elif strategy == "rename":
            return self._generate_unique_path(dest)
        else:
            raise ValueError(f"Unknown duplicate strategy: {self.strategy}")

    def _generate_unique_path(self, dest: Path) -> Path:
        parent = dest.parent
        stem = dest.stem
        suffix = dest.suffix
        counter = 1

        while True:
            new_name = f"{stem} ({counter}){suffix}"
            new_path = parent / new_name
            if not new_path.exists():
                logger.info(f"Renaming duplicate to: {new_name}")
                return new_path
            counter += 1

    def _preserve_timestamps(self, source: Path, dest: Path) -> None:
        try:
            stat = source.stat()
            os.utime(str(dest), (stat.st_atime, stat.st_mtime))
            logger.debug(f"Preserved timestamps for: {dest.name}")
        except Exception as e:
            logger.warning(f"Failed to preserve timestamps for {source.name}: {e}")

    def move_file(self, source: Path, dest: Path) -> bool:
        if dest is None:
            return False

        try:
            dest.parent.mkdir(parents=True, exist_ok=True)

            source_stat = source.stat()
            try:
                dest_stat = dest.stat()
                if dest.exists():
                    dest.unlink()
            except FileNotFoundError:
                pass

            try:
                shutil.move(str(source), str(dest))
            except shutil.Error:
                shutil.copy2(str(source), str(dest))
                source.unlink()

            new_stat = dest.stat()
            if new_stat.st_mtime != source_stat.st_mtime:
                os.utime(str(dest), (source_stat.st_atime, source_stat.st_mtime))

            logger.info(f"Moved: {source.name} -> {dest.parent.name}/{dest.name}")
            return True
        except PermissionError as e:
            logger.error(f"Permission denied moving {source.name}: {e}")
            return False
        except OSError as e:
            logger.error(f"OS error moving {source.name}: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to move {source.name}: {e}")
            return False
