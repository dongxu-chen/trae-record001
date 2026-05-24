import numpy as np
import pandas as pd
from gaussian_plume import GaussianPlumeModel
from terrain import Terrain
from adaptive_smoothing import AdaptiveSmoother
from typing import List, Dict, Optional, Union, Tuple


class EmissionSource:
    def __init__(self, source_id: str, Q: float, x: float, y: float, h_s: float,
                 u: float = 5.0, stability_class: str = 'D',
                 v_s: float = 0.0, d: float = 0.0, T_s: float = 293.0, T_a: float = 293.0,
                 terrain: Optional[Terrain] = None,
                 use_advanced_plume_rise: bool = True,
                 use_streamline_deflection: bool = True,
                 pollutant: str = 'PM2.5',
                 source_type: str = 'point',
                 operational: bool = True,
                 emission_factor: Optional[Dict] = None,
                 **kwargs):
        self.source_id = source_id
        self.Q = Q
        self.x = x
        self.y = y
        self.h_s = h_s
        self.u = u
        self.stability_class = stability_class
        self.v_s = v_s
        self.d = d
        self.T_s = T_s
        self.T_a = T_a
        self.terrain = terrain
        self.use_advanced_plume_rise = use_advanced_plume_rise
        self.use_streamline_deflection = use_streamline_deflection
        self.pollutant = pollutant
        self.source_type = source_type
        self.operational = operational
        self.emission_factor = emission_factor or {}
        self.extra_params = kwargs

        self._model = None
        self._heat_source_params = None
        self._build_model()

    def _build_model(self):
        self._model = GaussianPlumeModel(
            Q=self.Q,
            u=self.u,
            stability_class=self.stability_class,
            h_s=self.h_s,
            terrain=self.terrain,
            use_advanced_plume_rise=self.use_advanced_plume_rise,
            use_streamline_deflection=self.use_streamline_deflection
        )

    def update_params(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                self.extra_params[key] = value
        self._build_model()

    def calculate_concentration(self, x: Union[float, np.ndarray],
                                y: Union[float, np.ndarray],
                                z: Union[float, np.ndarray] = 0.0,
                                apply_coordinate_transform: bool = True) -> Tuple[np.ndarray, Dict]:
        if not self.operational:
            x_arr = np.asarray(x, dtype=float)
            return np.zeros_like(x_arr), {}

        if apply_coordinate_transform:
            x_local = np.asarray(x, dtype=float) - self.x
            y_local = np.asarray(y, dtype=float) - self.y
        else:
            x_local = np.asarray(x, dtype=float)
            y_local = np.asarray(y, dtype=float)

        z_local = np.asarray(z, dtype=float)

        mask = x_local < 0
        x_local_safe = np.maximum(x_local, 1.0)

        result = self._model.calculate_concentration(
            x_local_safe, y_local, z_local,
            v_s=self.v_s, d=self.d, T_s=self.T_s, T_a=self.T_a
        )

        C, H_e, delta_h, sigma_y, sigma_z, extra = result

        C = np.where(mask, 0.0, C)

        extra_info = {
            'source_id': self.source_id,
            'x_global': x,
            'y_global': y,
            'x_local': x_local,
            'y_local': y_local,
            'H_e': H_e,
            'delta_h': delta_h,
            'sigma_y': sigma_y,
            'sigma_z': sigma_z,
            'pollutant': self.pollutant,
            'operational': self.operational
        }
        extra_info.update(extra)

        return C, extra_info

    def calculate_concentration_grid(self, x_range: Tuple[float, float],
                                     y_range: Tuple[float, float],
                                     z: float = 0.0,
                                     resolution: int = 100,
                                     apply_smoothing: bool = True,
                                     **kwargs) -> Dict:
        x = np.linspace(x_range[0], x_range[1], resolution)
        y = np.linspace(y_range[0], y_range[1], resolution)
        X, Y = np.meshgrid(x, y, indexing='ij')

        C, extra_info = self.calculate_concentration(X, Y, z)

        grid_data = {
            'X': X,
            'Y': Y,
            'C': C,
            'x': x,
            'y': y,
            'source_id': self.source_id,
            'pollutant': self.pollutant,
            'extra': extra_info,
            'smoothed': False
        }

        if apply_smoothing and self._model.adaptive_smoother is not None:
            smoother = self._model.adaptive_smoother
            grid_data = smoother.process_concentration_grid(
                grid_data, use_log=kwargs.get('use_log_for_smooth', True),
                interpolation_factor=kwargs.get('interpolation_factor', 1),
                smooth_method=kwargs.get('smooth_method', 'adaptive_gaussian')
            )

        return grid_data

    def get_info(self) -> Dict:
        return {
            'source_id': self.source_id,
            'Q': self.Q,
            'x': self.x,
            'y': self.y,
            'h_s': self.h_s,
            'u': self.u,
            'stability_class': self.stability_class,
            'v_s': self.v_s,
            'd': self.d,
            'T_s': self.T_s,
            'T_a': self.T_a,
            'pollutant': self.pollutant,
            'source_type': self.source_type,
            'operational': self.operational,
            'use_advanced_plume_rise': self.use_advanced_plume_rise,
            'use_streamline_deflection': self.use_streamline_deflection
        }

    def __repr__(self) -> str:
        return (f"EmissionSource(id='{self.source_id}', Q={self.Q} g/s, "
                f"pos=({self.x}, {self.y}, {self.h_s}), "
                f"pollutant='{self.pollutant}', operational={self.operational})")


class MultiSourcePlumeModel:
    def __init__(self, sources: Optional[List[EmissionSource]] = None,
                 terrain: Optional[Terrain] = None,
                 adaptive_smoother: Optional[AdaptiveSmoother] = None,
                 combine_method: str = 'linear'):
        self.sources: Dict[str, EmissionSource] = {}
        self.terrain = terrain
        self.adaptive_smoother = adaptive_smoother or AdaptiveSmoother(
            gradient_threshold=0.05, min_sigma=0.3, max_sigma=2.0
        )
        self.combine_method = combine_method
        self._last_calculation = None

        if sources:
            for source in sources:
                self.add_source(source)

    def add_source(self, source: Union[EmissionSource, Dict]) -> str:
        if isinstance(source, dict):
            source = EmissionSource(**source)

        if source.terrain is None and self.terrain is not None:
            source.terrain = self.terrain
            source._build_model()

        if source._model.adaptive_smoother is None:
            source._model.adaptive_smoother = self.adaptive_smoother

        self.sources[source.source_id] = source
        return source.source_id

    def remove_source(self, source_id: str) -> bool:
        if source_id in self.sources:
            del self.sources[source_id]
            return True
        return False

    def update_source(self, source_id: str, **kwargs) -> bool:
        if source_id in self.sources:
            self.sources[source_id].update_params(**kwargs)
            return True
        return False

    def get_source(self, source_id: str) -> Optional[EmissionSource]:
        return self.sources.get(source_id)

    def list_sources(self) -> pd.DataFrame:
        data = []
        for source_id, source in self.sources.items():
            info = source.get_info()
            data.append(info)
        return pd.DataFrame(data)

    def calculate_concentration(self, x: Union[float, np.ndarray],
                                y: Union[float, np.ndarray],
                                z: Union[float, np.ndarray] = 0.0,
                                source_ids: Optional[List[str]] = None,
                                return_source_contributions: bool = False) -> Union[np.ndarray, Tuple[np.ndarray, Dict]]:
        x_arr = np.asarray(x, dtype=float)
        y_arr = np.asarray(y, dtype=float)
        z_arr = np.asarray(z, dtype=float)

        if x_arr.shape != y_arr.shape:
            if x_arr.ndim == 0:
                x_arr = np.full_like(y_arr, float(x_arr))
            elif y_arr.ndim == 0:
                y_arr = np.full_like(x_arr, float(y_arr))

        if source_ids is None:
            active_sources = [s for s in self.sources.values() if s.operational]
        else:
            active_sources = [self.sources[sid] for sid in source_ids
                             if sid in self.sources and self.sources[sid].operational]

        total_C = np.zeros_like(x_arr, dtype=float)
        source_contributions = {}

        for source in active_sources:
            C, extra_info = source.calculate_concentration(x_arr, y_arr, z_arr)

            if self.combine_method == 'linear':
                total_C += C
            elif self.combine_method == 'log_sum':
                total_C = np.logaddexp(total_C, np.log(C + 1e-15))
            elif self.combine_method == 'maximum':
                total_C = np.maximum(total_C, C)
            else:
                total_C += C

            if return_source_contributions:
                source_contributions[source.source_id] = {
                    'C': C,
                    'extra': extra_info
                }

        self._last_calculation = {
            'x': x, 'y': y, 'z': z,
            'total_C': total_C,
            'source_contributions': source_contributions,
            'active_sources': [s.source_id for s in active_sources]
        }

        if return_source_contributions:
            return total_C, source_contributions
        else:
            return total_C

    def calculate_concentration_grid(self, x_range: Tuple[float, float],
                                     y_range: Tuple[float, float],
                                     z: float = 0.0,
                                     resolution: int = 100,
                                     source_ids: Optional[List[str]] = None,
                                     apply_smoothing: bool = True,
                                     return_source_contributions: bool = False,
                                     **kwargs) -> Dict:
        x = np.linspace(x_range[0], x_range[1], resolution)
        y = np.linspace(y_range[0], y_range[1], resolution)
        X, Y = np.meshgrid(x, y, indexing='ij')

        result = self.calculate_concentration(
            X, Y, z, source_ids=source_ids,
            return_source_contributions=return_source_contributions
        )

        if return_source_contributions:
            total_C, source_contributions = result
        else:
            total_C = result
            source_contributions = None

        grid_data = {
            'X': X,
            'Y': Y,
            'C': total_C,
            'x': x,
            'y': y,
            'source_contributions': source_contributions,
            'smoothed': False,
            'multi_source': True,
            'num_sources': len([s for s in self.sources.values() if s.operational])
        }

        if apply_smoothing and self.adaptive_smoother is not None:
            grid_data = self.adaptive_smoother.process_concentration_grid(
                grid_data, use_log=kwargs.get('use_log_for_smooth', True),
                interpolation_factor=kwargs.get('interpolation_factor', 1),
                smooth_method=kwargs.get('smooth_method', 'adaptive_gaussian')
            )

        return grid_data

    def calculate_source_contribution_map(self, x_range: Tuple[float, float],
                                          y_range: Tuple[float, float],
                                          z: float = 0.0,
                                          resolution: int = 50,
                                          source_ids: Optional[List[str]] = None) -> Dict:
        x = np.linspace(x_range[0], x_range[1], resolution)
        y = np.linspace(y_range[0], y_range[1], resolution)
        X, Y = np.meshgrid(x, y, indexing='ij')

        if source_ids is None:
            active_sources = [s for s in self.sources.values() if s.operational]
        else:
            active_sources = [self.sources[sid] for sid in source_ids
                             if sid in self.sources and self.sources[sid].operational]

        contribution_maps = {}
        for source in active_sources:
            C, _ = source.calculate_concentration(X, Y, z)
            contribution_maps[source.source_id] = C

        total_C = np.sum(list(contribution_maps.values()), axis=0)

        percentage_maps = {}
        for source_id, C in contribution_maps.items():
            percentage_maps[source_id] = np.where(total_C > 0, C / total_C * 100, 0)

        return {
            'X': X,
            'Y': Y,
            'x': x,
            'y': y,
            'total_C': total_C,
            'contribution_maps': contribution_maps,
            'percentage_maps': percentage_maps,
            'source_ids': [s.source_id for s in active_sources]
        }

    def find_max_contribution_source(self, x: float, y: float, z: float = 0.0) -> Tuple[Optional[str], float, Dict]:
        _, contributions = self.calculate_concentration(
            x, y, z, return_source_contributions=True
        )

        if not contributions:
            return None, 0.0, {}

        max_source_id = None
        max_C = 0.0
        for source_id, data in contributions.items():
            C = float(data['C'])
            if C > max_C:
                max_C = C
                max_source_id = source_id

        return max_source_id, max_C, contributions

    def calculate_total_emission_rate(self, source_ids: Optional[List[str]] = None,
                                       pollutant: Optional[str] = None) -> Dict:
        if source_ids is None:
            sources = [s for s in self.sources.values() if s.operational]
        else:
            sources = [self.sources[sid] for sid in source_ids
                      if sid in self.sources and self.sources[sid].operational]

        if pollutant is not None:
            sources = [s for s in sources if s.pollutant == pollutant]

        total_Q = sum(s.Q for s in sources)

        by_pollutant = {}
        for s in sources:
            if s.pollutant not in by_pollutant:
                by_pollutant[s.pollutant] = 0.0
            by_pollutant[s.pollutant] += s.Q

        return {
            'total_Q_g_per_s': total_Q,
            'total_Q_kg_per_h': total_Q * 3.6,
            'total_Q_ton_per_year': total_Q * 3.6 * 24 * 365 / 1000,
            'by_pollutant': by_pollutant,
            'num_sources': len(sources),
            'source_ids': [s.source_id for s in sources]
        }

    def get_combined_smoother(self) -> AdaptiveSmoother:
        return self.adaptive_smoother

    def __len__(self) -> int:
        return len([s for s in self.sources.values() if s.operational])

    def __iter__(self):
        return iter([s for s in self.sources.values() if s.operational])

    def __getitem__(self, source_id: str) -> EmissionSource:
        return self.sources[source_id]

    def __repr__(self) -> str:
        active_count = len([s for s in self.sources.values() if s.operational])
        total_count = len(self.sources)
        pollutants = set(s.pollutant for s in self.sources.values())
        return (f"MultiSourcePlumeModel(sources={active_count}/{total_count}, "
                f"pollutants={sorted(pollutants)}, "
                f"combine_method='{self.combine_method}')")


def create_example_multi_source_model(terrain: Optional[Terrain] = None,
                                       num_sources: int = 5) -> MultiSourcePlumeModel:
    sources = []

    pollutants = ['PM2.5', 'SO2', 'NOx', 'PM10', 'CO']
    source_types = ['point', 'area', 'fugitive']

    base_positions = [
        (1000, -500),
        (1500, 300),
        (2000, -200),
        (2500, 400),
        (3000, 0)
    ]

    for i in range(min(num_sources, 5)):
        x, y = base_positions[i]
        source = EmissionSource(
            source_id=f'factory_{i+1:02d}',
            Q=50.0 + np.random.uniform(20, 80),
            x=x,
            y=y,
            h_s=80.0 + np.random.uniform(20, 80),
            u=5.0,
            stability_class='C',
            v_s=12.0 + np.random.uniform(3, 10),
            d=2.0 + np.random.uniform(0.5, 2.0),
            T_s=380.0 + np.random.uniform(20, 60),
            T_a=293.0,
            pollutant=pollutants[i % len(pollutants)],
            source_type=source_types[i % len(source_types)],
            terrain=terrain,
            operational=True
        )
        sources.append(source)

    return MultiSourcePlumeModel(sources=sources, terrain=terrain)
