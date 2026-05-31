import os
import time
import threading
import torch
from .config import TrainConfig


class CheckpointManager:
    def __init__(self, config: TrainConfig, max_keep: int = 5, expire_seconds: float = 86400.0):
        self.config = config
        self.checkpoint_dir = config.checkpoint_dir
        self.max_keep = max_keep
        self.expire_seconds = expire_seconds
        os.makedirs(self.checkpoint_dir, exist_ok=True)
        self._window = []
        self._lock = threading.Lock()
        self._cleanup_timer = None
        self._start_periodic_cleanup(interval_seconds=3600)

    def _start_periodic_cleanup(self, interval_seconds: float = 3600):
        def _timer_loop():
            while True:
                time.sleep(interval_seconds)
                self._cleanup_expired()

        self._cleanup_timer = threading.Thread(target=_timer_loop, daemon=True)
        self._cleanup_timer.start()

    def _cleanup_expired(self):
        now = time.time()
        with self._lock:
            if not os.path.exists(self.checkpoint_dir):
                return
            for f in os.listdir(self.checkpoint_dir):
                if f.startswith("checkpoint_step_") and f.endswith(".pt"):
                    fpath = os.path.join(self.checkpoint_dir, f)
                    try:
                        mtime = os.path.getmtime(fpath)
                        if (now - mtime) > self.expire_seconds:
                            if f not in [os.path.basename(p) for p in self._window]:
                                os.remove(fpath)
                    except OSError:
                        pass

    def _sliding_window_save(self, new_path: str):
        with self._lock:
            self._window.append(new_path)
            while len(self._window) > self.max_keep:
                oldest = self._window.pop(0)
                if os.path.exists(oldest):
                    try:
                        os.remove(oldest)
                    except OSError:
                        pass

    def save(
        self,
        epoch: int,
        step: int,
        g_state: dict,
        d_state: dict,
        g_opt_state: dict,
        d_opt_state: dict,
        is_best: bool = False,
        ema_g_state: dict = None,
        scaler_state: dict = None,
    ):
        checkpoint = {
            "epoch": epoch,
            "step": step,
            "architecture": self.config.architecture,
            "g_state_dict": g_state,
            "d_state_dict": d_state,
            "g_optimizer_state_dict": g_opt_state,
            "d_optimizer_state_dict": d_opt_state,
            "config": self.config.__dict__,
            "timestamp": time.time(),
        }
        if ema_g_state is not None:
            checkpoint["ema_g_state_dict"] = ema_g_state
        if scaler_state is not None:
            checkpoint["scaler_state_dict"] = scaler_state

        path = os.path.join(self.checkpoint_dir, f"checkpoint_step_{step}.pt")
        torch.save(checkpoint, path)
        self._sliding_window_save(path)

        latest_path = os.path.join(self.checkpoint_dir, "latest.pt")
        torch.save(checkpoint, latest_path)

        if is_best:
            best_path = os.path.join(self.checkpoint_dir, "best.pt")
            torch.save(checkpoint, best_path)

    def load(self, path: str = None, load_best: bool = False):
        if path is None:
            if load_best:
                path = os.path.join(self.checkpoint_dir, "best.pt")
            else:
                path = os.path.join(self.checkpoint_dir, "latest.pt")

        if not os.path.exists(path):
            return None

        checkpoint = torch.load(path, map_location="cpu", weights_only=False)
        return checkpoint

    def cleanup_old(self, max_keep: int = None):
        keep = max_keep if max_keep is not None else self.max_keep
        checkpoints = []
        for f in os.listdir(self.checkpoint_dir):
            if f.startswith("checkpoint_step_") and f.endswith(".pt"):
                step = int(f.split("_")[-1].split(".")[0])
                checkpoints.append((step, f))

        checkpoints.sort(key=lambda x: x[0])

        if len(checkpoints) > keep:
            for _, fname in checkpoints[:-keep]:
                fpath = os.path.join(self.checkpoint_dir, fname)
                try:
                    os.remove(fpath)
                except OSError:
                    pass

        with self._lock:
            self._window = [
                p for p in self._window if os.path.exists(p)
            ]

    def stop_cleanup(self):
        pass
