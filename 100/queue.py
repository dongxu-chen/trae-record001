from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass
from typing import Any, Callable, Optional, Set


@dataclass
class TaskResult:
    success: bool
    input_path: str
    output_path: Optional[str] = None
    error: Optional[str] = None


class ConversionQueue:
    def __init__(self, max_workers: int = 4, task_timeout: float = 7200.0):
        self.max_workers = max_workers
        self.task_timeout = task_timeout
        self.tasks: list[tuple[Callable, tuple, dict]] = []

    def add_task(self, func: Callable, *args: Any, **kwargs: Any) -> None:
        self.tasks.append((func, args, kwargs))

    def run(self, progress_callback: Optional[Callable[[int, int, TaskResult], None]] = None) -> list[TaskResult]:
        results: list[TaskResult] = []
        total = len(self.tasks)
        completed = 0

        if total == 0:
            return results

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            task_info: dict[Any, tuple[Callable, tuple, dict]] = {}
            pending: Set[Any] = set()

            for func, args, kwargs in self.tasks:
                future = executor.submit(func, *args, **kwargs)
                task_info[future] = (func, args, kwargs)
                pending.add(future)

            while pending:
                done, pending = wait(pending, timeout=60, return_when=FIRST_COMPLETED)

                for future in done:
                    func, args, _ = task_info[future]
                    input_path = args[0] if args else 'unknown'

                    try:
                        if future.cancelled():
                            result = TaskResult(
                                success=False,
                                input_path=input_path,
                                error='Task was cancelled'
                            )
                        else:
                            result = future.result(timeout=self.task_timeout)
                            result = self._normalize_result(result, input_path)
                    except Exception as e:
                        result = TaskResult(
                            success=False,
                            input_path=input_path,
                            error=str(e)
                        )

                    results.append(result)
                    completed += 1

                    if progress_callback:
                        try:
                            progress_callback(completed, total, result)
                        except Exception:
                            pass

                    del task_info[future]

        return results

    def _normalize_result(self, result: Any, input_path: str) -> TaskResult:
        if isinstance(result, TaskResult):
            return result

        if isinstance(result, tuple) and len(result) == 3:
            success, path, output_or_error = result
            if success:
                return TaskResult(success=True, input_path=path, output_path=output_or_error)
            else:
                return TaskResult(success=False, input_path=path, error=output_or_error)

        return TaskResult(success=True, input_path=input_path, output_path=str(result))

    def clear(self) -> None:
        self.tasks.clear()

    def __len__(self) -> int:
        return len(self.tasks)
