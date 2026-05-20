import numpy as np
import struct
import os
from typing import Tuple, Dict, List, Optional, Iterator, BinaryIO
from dataclasses import dataclass


@dataclass
class XTCHeader:
    magic: int
    n_atoms: int
    step: int
    time: float
    box: np.ndarray
    precision: float


class XTCParser:
    XTC_MAGIC = 1995
    
    def __init__(self, filename: str):
        self.filename = filename
        self.file = None
        self._n_atoms = None
        self._n_frames = None
        self._frame_offsets = []
        self._precision = None
        
    def open(self) -> None:
        self.file = open(self.filename, 'rb')
        self._scan_file()
    
    def close(self) -> None:
        if self.file:
            self.file.close()
            self.file = None
    
    def __enter__(self):
        self.open()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def _scan_file(self) -> None:
        self.file.seek(0)
        self._frame_offsets = []
        
        while True:
            offset = self.file.tell()
            try:
                header = self._read_header(skip_coords=True)
                self._frame_offsets.append(offset)
                if self._n_atoms is None:
                    self._n_atoms = header.n_atoms
                    self._precision = header.precision
            except EOFError:
                break
        
        self._n_frames = len(self._frame_offsets)
    
    def _read_header(self, skip_coords: bool = False) -> XTCHeader:
        data = self.file.read(4)
        if not data:
            raise EOFError("End of file reached")
        
        magic = struct.unpack('>i', data)[0]
        if magic != self.XTC_MAGIC:
            raise ValueError(f"Invalid XTC magic number: {magic}")
        
        n_atoms = struct.unpack('>i', self.file.read(4))[0]
        step = struct.unpack('>i', self.file.read(4))[0]
        time = struct.unpack('>f', self.file.read(4))[0]
        
        box = np.zeros((3, 3), dtype=np.float32)
        for i in range(3):
            for j in range(3):
                box[i, j] = struct.unpack('>f', self.file.read(4))[0]
        
        precision = struct.unpack('>f', self.file.read(4))[0]
        
        if skip_coords:
            min_bytes = (n_atoms * 3 + 2) // 3 * 4
            self.file.seek(min_bytes, 1)
        
        return XTCHeader(magic=magic, n_atoms=n_atoms, step=step, 
                        time=time, box=box, precision=precision)
    
    def _decompress_coords(self, n_atoms: int, precision: float) -> np.ndarray:
        buf = np.fromfile(self.file, dtype=np.uint32, count=(n_atoms * 3 + 2) // 3)
        
        coords = np.zeros(n_atoms * 3, dtype=np.float32)
        
        mask = 0x00000FFF
        idx = 0
        
        for i in range(0, len(buf)):
            val = int(buf[i])
            
            if idx < n_atoms * 3:
                coords[idx] = val & mask
                idx += 1
            if idx < n_atoms * 3:
                coords[idx] = (val >> 12) & mask
                idx += 1
            if idx < n_atoms * 3:
                coords[idx] = (val >> 24) & mask
                idx += 1
        
        coords = coords.reshape((n_atoms, 3)) / precision
        
        return coords
    
    def read_frame(self, frame_idx: int) -> Tuple[int, float, np.ndarray, np.ndarray]:
        if frame_idx < 0 or frame_idx >= self._n_frames:
            raise ValueError(f"Frame index out of range: {frame_idx}")
        
        self.file.seek(self._frame_offsets[frame_idx])
        header = self._read_header()
        coords = self._decompress_coords(header.n_atoms, header.precision)
        
        return header.step, header.time, coords, header.box
    
    def iterate_frames(self, 
                      start: int = 0, 
                      stop: Optional[int] = None, 
                      step: int = 1) -> Iterator[Tuple[int, float, np.ndarray, np.ndarray]]:
        if stop is None:
            stop = self._n_frames
        
        for i in range(start, stop, step):
            yield self.read_frame(i)
    
    def get_precision_info(self) -> Dict:
        return {
            "precision": self._precision,
            "n_frames": self._n_frames,
            "n_atoms": self._n_atoms,
            "file_size_mb": os.path.getsize(self.filename) / (1024 * 1024)
        }
    
    def estimate_memory_usage(self, n_frames: Optional[int] = None) -> Dict:
        if n_frames is None:
            n_frames = self._n_frames
        
        coords_memory = n_frames * self._n_atoms * 3 * 4  # float32
        box_memory = n_frames * 9 * 4
        
        return {
            "coords_mb": coords_memory / (1024 * 1024),
            "box_mb": box_memory / (1024 * 1024),
            "total_mb": (coords_memory + box_memory) / (1024 * 1024)
        }
    
    @property
    def n_frames(self) -> int:
        return self._n_frames
    
    @property
    def n_atoms(self) -> int:
        return self._n_atoms


class PrecisionConverter:
    @staticmethod
    def compress_coords(coords: np.ndarray, precision: float = 1000.0) -> np.ndarray:
        coords_int = np.round(coords * precision).astype(np.int32)
        coords_int = np.clip(coords_int, 0, 4095)
        return coords_int
    
    @staticmethod
    def estimate_compression_ratio(n_atoms: int, precision: float = 1000.0) -> float:
        uncompressed = n_atoms * 3 * 4  # float32
        compressed = (n_atoms * 3 + 2) // 3 * 4
        return uncompressed / compressed
    
    @staticmethod
    def get_precision_levels() -> Dict[str, float]:
        return {
            "low": 100.0,      # 0.01 Å precision
            "medium": 1000.0,  # 0.001 Å precision (standard)
            "high": 10000.0,   # 0.0001 Å precision
            "ultra": 100000.0  # 0.00001 Å precision
        }


class StreamingAnalyzer:
    def __init__(self, xtc_file: str):
        self.parser = XTCParser(xtc_file)
    
    def analyze_rmsd_streaming(self, 
                              ref_coords: np.ndarray,
                              start: int = 0,
                              stop: Optional[int] = None,
                              step: int = 1,
                              selection_mask: Optional[np.ndarray] = None) -> Tuple[np.ndarray, np.ndarray]:
        if selection_mask is not None:
            ref_selected = ref_coords[selection_mask]
        else:
            ref_selected = ref_coords
        
        ref_center = np.mean(ref_selected, axis=0)
        ref_centered = ref_selected - ref_center
        
        times = []
        rmsd_values = []
        
        with self.parser:
            for _, time, coords, _ in self.parser.iterate_frames(start, stop, step):
                if selection_mask is not None:
                    mob_coords = coords[selection_mask]
                else:
                    mob_coords = coords
                
                mob_center = np.mean(mob_coords, axis=0)
                mob_centered = mob_coords - mob_center
                
                H = mob_centered.T @ ref_centered
                U, S, Vt = np.linalg.svd(H)
                
                if np.linalg.det(Vt.T @ U.T) < 0:
                    Vt[-1, :] *= -1
                
                R = Vt.T @ U.T
                mob_aligned = (R @ mob_centered.T).T
                
                diff = mob_aligned - ref_centered
                rmsd = np.sqrt(np.mean(np.sum(diff ** 2, axis=1)))
                
                times.append(time)
                rmsd_values.append(rmsd)
        
        return np.array(times), np.array(rmsd_values)
