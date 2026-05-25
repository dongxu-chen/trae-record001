import numpy as np
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass, field
import logging
from .acoustic_simulator import RoomGeometry, AbsorptionBand, STANDARD_OCTAVE_BANDS

logger = logging.getLogger(__name__)


@dataclass
class AbsorptionMaterial:
    name: str
    description: str
    absorption_coefficients: np.ndarray
    frequencies: np.ndarray
    cost_per_sqm: float = 0.0
    thickness_mm: float = 0.0
    category: str = "general"

    def __post_init__(self):
        self.absorption_coefficients = np.asarray(self.absorption_coefficients, dtype=np.float64)
        self.frequencies = np.asarray(self.frequencies, dtype=np.float64)
        self.absorption_coefficients = np.clip(self.absorption_coefficients, 0.0, 1.0)

    def get_absorption_at(self, freq: float) -> float:
        idx = np.argmin(np.abs(self.frequencies - freq))
        return float(self.absorption_coefficients[idx])

    def get_absorption_band(self) -> AbsorptionBand:
        return AbsorptionBand(self.frequencies, self.absorption_coefficients)


MATERIAL_DATABASE = {
    "acoustic_foam_50mm": AbsorptionMaterial(
        name="Acoustic Foam 50mm",
        description="标准50mm聚氨酯声学泡沫",
        absorption_coefficients=np.array([0.15, 0.35, 0.65, 0.85, 0.90, 0.95, 0.95]),
        frequencies=STANDARD_OCTAVE_BANDS,
        cost_per_sqm=80.0,
        thickness_mm=50.0,
        category="foam"
    ),
    "acoustic_foam_100mm": AbsorptionMaterial(
        name="Acoustic Foam 100mm",
        description="100mm厚高性能声学泡沫",
        absorption_coefficients=np.array([0.25, 0.50, 0.80, 0.95, 0.95, 0.95, 0.95]),
        frequencies=STANDARD_OCTAVE_BANDS,
        cost_per_sqm=150.0,
        thickness_mm=100.0,
        category="foam"
    ),
    "fiberglass_50mm": AbsorptionMaterial(
        name="Fiberglass Insulation 50mm",
        description="50mm玻璃棉隔音棉",
        absorption_coefficients=np.array([0.20, 0.45, 0.75, 0.90, 0.92, 0.95, 0.95]),
        frequencies=STANDARD_OCTAVE_BANDS,
        cost_per_sqm=60.0,
        thickness_mm=50.0,
        category="fiberglass"
    ),
    "fiberglass_100mm": AbsorptionMaterial(
        name="Fiberglass Insulation 100mm",
        description="100mm厚玻璃棉",
        absorption_coefficients=np.array([0.35, 0.65, 0.85, 0.95, 0.95, 0.95, 0.95]),
        frequencies=STANDARD_OCTAVE_BANDS,
        cost_per_sqm=100.0,
        thickness_mm=100.0,
        category="fiberglass"
    ),
    "wood_panel": AbsorptionMaterial(
        name="Perforated Wood Panel",
        description="穿孔木质吸声板",
        absorption_coefficients=np.array([0.40, 0.60, 0.50, 0.40, 0.30, 0.25, 0.20]),
        frequencies=STANDARD_OCTAVE_BANDS,
        cost_per_sqm=200.0,
        thickness_mm=15.0,
        category="panel"
    ),
    "bass_trap": AbsorptionMaterial(
        name="Bass Trap Corner",
        description="低频陷阱，专用于吸收低频",
        absorption_coefficients=np.array([0.60, 0.80, 0.75, 0.65, 0.55, 0.50, 0.45]),
        frequencies=STANDARD_OCTAVE_BANDS,
        cost_per_sqm=300.0,
        thickness_mm=300.0,
        category="bass_trap"
    ),
    "carpet_thick": AbsorptionMaterial(
        name="Thick Carpet with Underlay",
        description="厚地毯带垫层",
        absorption_coefficients=np.array([0.05, 0.10, 0.25, 0.45, 0.65, 0.75, 0.80]),
        frequencies=STANDARD_OCTAVE_BANDS,
        cost_per_sqm=120.0,
        thickness_mm=10.0,
        category="floor"
    ),
    "curtain_heavy": AbsorptionMaterial(
        name="Heavy Acoustic Curtain",
        description="重型声学窗帘",
        absorption_coefficients=np.array([0.10, 0.30, 0.55, 0.70, 0.75, 0.80, 0.85]),
        frequencies=STANDARD_OCTAVE_BANDS,
        cost_per_sqm=150.0,
        thickness_mm=5.0,
        category="curtain"
    ),
    "ceiling_tile": AbsorptionMaterial(
        name="Acoustic Ceiling Tile",
        description="矿棉吸声天花板",
        absorption_coefficients=np.array([0.15, 0.30, 0.55, 0.75, 0.80, 0.85, 0.85]),
        frequencies=STANDARD_OCTAVE_BANDS,
        cost_per_sqm=90.0,
        thickness_mm=15.0,
        category="ceiling"
    ),
    "diffuser_qrd": AbsorptionMaterial(
        name="QRD Diffuser",
        description="二次余数扩散体，主要扩散而非吸收",
        absorption_coefficients=np.array([0.05, 0.08, 0.12, 0.15, 0.18, 0.20, 0.22]),
        frequencies=STANDARD_OCTAVE_BANDS,
        cost_per_sqm=400.0,
        thickness_mm=50.0,
        category="diffuser"
    ),
}


@dataclass
class OptimizationSuggestion:
    wall_name: str
    wall_index: int
    suggested_material: str
    area_sqm: float
    estimated_improvement: Dict[str, float]
    cost_estimate: float
    priority: int = 1
    notes: str = ""


@dataclass
class RoomAcousticAnalysis:
    rt60_current: np.ndarray
    rt60_target: np.ndarray
    rt60_deviation: np.ndarray
    problem_bands: List[float]
    problem_walls: List[int]
    overall_grade: str
    suggestions: List[OptimizationSuggestion] = field(default_factory=list)
    total_estimated_cost: float = 0.0


class RoomOptimizer:
    def __init__(self, room: RoomGeometry):
        self.room = room
        self.wall_names = self._get_wall_names()

    def _get_wall_names(self) -> List[str]:
        if self.room.ndim == 2:
            return ["Left Wall", "Right Wall", "Bottom Wall", "Top Wall"]
        elif self.room.ndim == 3:
            return ["Left Wall (-X)", "Right Wall (+X)", "Front Wall (-Y)", "Back Wall (+Y)", "Floor (-Z)", "Ceiling (+Z)"]
        return [f"Wall {i}" for i in range(2 * self.room.ndim)]

    def analyze_room(self,
                     target_rt60: Optional[Union[float, np.ndarray]] = None,
                     room_type: str = "general") -> RoomAcousticAnalysis:
        if target_rt60 is None:
            target_rt60 = self._get_target_rt60(room_type)

        if isinstance(target_rt60, (int, float)):
            target_rt60 = np.ones_like(self.room.frequencies) * float(target_rt60)

        rt60_current = self._calculate_current_rt60()
        rt60_deviation = rt60_current - target_rt60

        problem_bands = []
        for i, freq in enumerate(self.room.frequencies):
            deviation = rt60_deviation[i]
            if deviation > 0.3:
                problem_bands.append(float(freq))

        problem_walls = self._identify_problem_walls(rt60_deviation)

        overall_grade = self._calculate_grade(rt60_deviation)

        analysis = RoomAcousticAnalysis(
            rt60_current=rt60_current,
            rt60_target=target_rt60,
            rt60_deviation=rt60_deviation,
            problem_bands=problem_bands,
            problem_walls=problem_walls,
            overall_grade=overall_grade
        )

        analysis.suggestions = self._generate_suggestions(analysis)
        analysis.total_estimated_cost = sum(s.cost_estimate for s in analysis.suggestions)

        return analysis

    def _get_target_rt60(self, room_type: str) -> np.ndarray:
        volume = self.room.get_volume()
        freq = self.room.frequencies

        if room_type == "studio":
            base_rt60 = 0.2 + 0.0001 * volume
            rt60 = base_rt60 * np.array([1.2, 1.1, 1.0, 1.0, 0.9, 0.8, 0.7])
        elif room_type == "concert_hall":
            base_rt60 = 1.5 + 0.0002 * volume
            rt60 = base_rt60 * np.array([1.2, 1.15, 1.1, 1.0, 1.0, 0.95, 0.9])
        elif room_type == "home_theater":
            base_rt60 = 0.3 + 0.00015 * volume
            rt60 = base_rt60 * np.array([1.1, 1.05, 1.0, 1.0, 0.95, 0.9, 0.85])
        elif room_type == "office":
            base_rt60 = 0.4 + 0.0001 * volume
            rt60 = base_rt60 * np.ones_like(freq)
        elif room_type == "classroom":
            base_rt60 = 0.5 + 0.0001 * volume
            rt60 = base_rt60 * np.array([1.1, 1.05, 1.0, 1.0, 0.95, 0.9, 0.85])
        elif room_type == "recording_booth":
            base_rt60 = 0.15 + 0.00005 * volume
            rt60 = base_rt60 * np.array([1.3, 1.2, 1.1, 1.0, 0.9, 0.8, 0.7])
        else:
            base_rt60 = 0.5 + 0.0001 * volume
            rt60 = base_rt60 * np.ones_like(freq)

        return np.clip(rt60, 0.1, 5.0)

    def _calculate_current_rt60(self) -> np.ndarray:
        volume = self.room.get_volume()
        surface_areas = self.room.get_wall_surface_areas()
        total_surface = np.sum(surface_areas)

        rt60_bands = []
        for band_idx in range(self.room.n_bands):
            absorption_coeffs = self.room.absorption[:, band_idx]
            alpha_mean = np.sum(surface_areas * absorption_coeffs) / max(total_surface, 1e-10)

            if alpha_mean <= 0:
                rt60 = 10.0
            elif alpha_mean >= 1.0:
                rt60 = 0.01
            else:
                alpha_eyring = -np.log(1 - alpha_mean)
                rt60 = 0.161 * volume / (total_surface * alpha_eyring)

            rt60_bands.append(rt60)

        return np.array(rt60_bands, dtype=np.float64)

    def _identify_problem_walls(self, rt60_deviation: np.ndarray) -> List[int]:
        problem_walls = []
        surface_areas = self.room.get_wall_surface_areas()

        for wall_idx in range(2 * self.room.ndim):
            avg_absorption = np.mean(self.room.absorption[wall_idx, :])
            area = surface_areas[wall_idx]
            contribution = area * (1.0 - avg_absorption)

            if contribution > np.mean(surface_areas) * 0.5 and avg_absorption < 0.3:
                problem_walls.append(wall_idx)

        if len(problem_walls) == 0 and np.max(rt60_deviation) > 0.3:
            sorted_walls = np.argsort(surface_areas)[::-1]
            problem_walls = list(sorted_walls[:2])

        return problem_walls

    def _calculate_grade(self, rt60_deviation: np.ndarray) -> str:
        mean_deviation = np.mean(np.abs(rt60_deviation))
        max_deviation = np.max(np.abs(rt60_deviation))

        if mean_deviation < 0.1 and max_deviation < 0.2:
            return "A"
        elif mean_deviation < 0.2 and max_deviation < 0.4:
            return "B"
        elif mean_deviation < 0.3 and max_deviation < 0.6:
            return "C"
        elif mean_deviation < 0.5 and max_deviation < 1.0:
            return "D"
        else:
            return "F"

    def _generate_suggestions(self, analysis: RoomAcousticAnalysis) -> List[OptimizationSuggestion]:
        suggestions = []
        surface_areas = self.room.get_wall_surface_areas()

        problem_band_indices = []
        for freq in analysis.problem_bands:
            idx = np.argmin(np.abs(self.room.frequencies - freq))
            problem_band_indices.append(idx)

        primary_band_idx = problem_band_indices[0] if problem_band_indices else np.argmax(analysis.rt60_deviation)
        primary_freq = self.room.frequencies[primary_band_idx]

        suggested_material_key = self._select_material_key(primary_freq, analysis.rt60_deviation)
        suggested_material = MATERIAL_DATABASE[suggested_material_key]

        priority = 1
        for wall_idx in analysis.problem_walls:
            area = surface_areas[wall_idx]
            current_abs = self.room.absorption[wall_idx, primary_band_idx]
            target_abs = suggested_material.get_absorption_at(primary_freq)

            improvement_factor = min((target_abs - current_abs) / max(current_abs, 0.01), 5.0)
            estimated_improvement = {}
            for i, freq in enumerate(self.room.frequencies):
                new_abs = max(self.room.absorption[wall_idx, i], suggested_material.get_absorption_at(freq))
                estimated_improvement[f"{freq:.0f}Hz"] = analysis.rt60_deviation[i] * (1 - improvement_factor * 0.3)

            coverage_ratio = 0.8
            actual_area = area * coverage_ratio
            cost = actual_area * suggested_material.cost_per_sqm

            notes = self._generate_wall_notes(wall_idx, primary_freq, suggested_material)

            suggestion = OptimizationSuggestion(
                wall_name=self.wall_names[wall_idx],
                wall_index=wall_idx,
                suggested_material=suggested_material_key,
                area_sqm=float(actual_area),
                estimated_improvement=estimated_improvement,
                cost_estimate=float(cost),
                priority=priority,
                notes=notes
            )
            suggestions.append(suggestion)
            priority += 1

        if primary_freq <= 250 and len(suggestions) < 4:
            corner_suggestion = self._generate_bass_trap_suggestion(analysis)
            if corner_suggestion:
                suggestions.append(corner_suggestion)

        suggestions.sort(key=lambda x: x.priority)
        return suggestions

    def _select_material_key(self, problem_freq: float, rt60_deviation: np.ndarray) -> str:
        if problem_freq <= 250:
            return "bass_trap"
        elif problem_freq <= 500:
            return "fiberglass_100mm"
        elif problem_freq <= 2000:
            return "acoustic_foam_50mm"
        else:
            return "ceiling_tile"

    def _select_material(self, problem_freq: float, rt60_deviation: np.ndarray) -> AbsorptionMaterial:
        key = self._select_material_key(problem_freq, rt60_deviation)
        return MATERIAL_DATABASE[key]

    def _generate_wall_notes(self, wall_idx: int, problem_freq: float, material: AbsorptionMaterial) -> str:
        notes = []

        if problem_freq <= 250:
            notes.append("重点解决低频混响问题")
        elif problem_freq <= 500:
            notes.append("改善中低频清晰度")
        elif problem_freq <= 2000:
            notes.append("优化中高频响应")
        else:
            notes.append("减少高频空气声反射")

        if self.room.ndim == 3:
            if wall_idx == 4:
                notes.append("建议使用厚地毯或浮动地板")
            elif wall_idx == 5:
                notes.append("建议使用吸声吊顶")
            elif wall_idx in [0, 1]:
                notes.append("可考虑安装扩散体与吸声结合")

        notes.append(f"材料厚度: {material.thickness_mm}mm")
        return "; ".join(notes)

    def _generate_bass_trap_suggestion(self, analysis: RoomAcousticAnalysis) -> Optional[OptimizationSuggestion]:
        volume = self.room.get_volume()
        perimeter = 2 * (self.room.dimensions[0] + self.room.dimensions[1])
        trap_area = perimeter * 0.1

        material = MATERIAL_DATABASE["bass_trap"]
        estimated_improvement = {}
        for i, freq in enumerate(self.room.frequencies):
            if freq <= 250:
                estimated_improvement[f"{freq:.0f}Hz"] = analysis.rt60_deviation[i] * 0.4
            else:
                estimated_improvement[f"{freq:.0f}Hz"] = analysis.rt60_deviation[i] * 0.1

        cost = trap_area * material.cost_per_sqm

        return OptimizationSuggestion(
            wall_name="Room Corners (Bass Traps)",
            wall_index=-1,
            suggested_material="bass_trap",
            area_sqm=float(trap_area),
            estimated_improvement=estimated_improvement,
            cost_estimate=float(cost),
            priority=3,
            notes="在房间4个垂直角落安装低频陷阱，建议从地面到天花板"
        )

    def apply_suggestion(self, suggestion: OptimizationSuggestion) -> RoomGeometry:
        material = MATERIAL_DATABASE[suggestion.suggested_material]
        new_absorption = self.room.absorption.copy()

        if suggestion.wall_index >= 0:
            for band_idx in range(self.room.n_bands):
                freq = self.room.frequencies[band_idx]
                mat_abs = material.get_absorption_at(freq)
                new_absorption[suggestion.wall_index, band_idx] = mat_abs

        new_room = RoomGeometry(
            dimensions=self.room.dimensions.copy(),
            absorption=new_absorption,
            scattering=self.room.scattering.copy(),
            max_order=self.room.max_order,
            use_pra=self.room.use_pra,
            adaptive_order=self.room.adaptive_order,
            band_type=self.room.band_type,
            frequencies=self.room.frequencies.copy()
        )

        return new_room

    def simulate_optimization(self, suggestions: List[OptimizationSuggestion]) -> Dict:
        current_rt60 = self._calculate_current_rt60()

        simulated_room = self.room
        for suggestion in suggestions:
            simulated_room = self.apply_suggestion(suggestion)

        temp_optimizer = RoomOptimizer(simulated_room)
        optimized_rt60 = temp_optimizer._calculate_current_rt60()

        improvement = current_rt60 - optimized_rt60

        return {
            "current_rt60": current_rt60,
            "optimized_rt60": optimized_rt60,
            "improvement": improvement,
            "total_cost": sum(s.cost_estimate for s in suggestions),
            "total_area": sum(s.area_sqm for s in suggestions)
        }

    def print_analysis_report(self, analysis: RoomAcousticAnalysis) -> None:
        print("\n" + "=" * 70)
        print("ROOM ACOUSTIC ANALYSIS REPORT")
        print("=" * 70)

        print(f"\n房间尺寸: {self.room.dimensions} m")
        print(f"房间容积: {self.room.get_volume():.1f} m³")
        print(f"表面积: {self.room.get_surface_area():.1f} m²")
        print(f"整体评价等级: {analysis.overall_grade}")

        print("\n" + "-" * 70)
        print("RT60 混响时间分析:")
        print("-" * 70)
        print(f"{'频率(Hz)':>10} {'当前(s)':>10} {'目标(s)':>10} {'偏差(s)':>10} {'状态':>10}")
        print("-" * 55)

        for i, freq in enumerate(self.room.frequencies):
            status = "✓" if abs(analysis.rt60_deviation[i]) < 0.2 else "⚠"
            if analysis.rt60_deviation[i] > 0.3:
                status = "✗"
            print(f"{freq:>10.0f} {analysis.rt60_current[i]:>10.3f} {analysis.rt60_target[i]:>10.3f} "
                  f"{analysis.rt60_deviation[i]:>10.3f} {status:>10}")

        if analysis.problem_bands:
            print(f"\n问题频带: {[f'{f:.0f}Hz' for f in analysis.problem_bands]}")

        print("\n" + "-" * 70)
        print("优化建议:")
        print("-" * 70)

        for i, s in enumerate(analysis.suggestions, 1):
            print(f"\n建议 #{i} (优先级: {s.priority})")
            print(f"  墙面: {s.wall_name}")
            print(f"  建议材料: {s.suggested_material}")
            print(f"  面积: {s.area_sqm:.1f} m²")
            print(f"  预估费用: ¥{s.cost_estimate:.0f}")
            print(f"  说明: {s.notes}")
            print(f"  预估各频带改善:")
            for freq_band, improvement in s.estimated_improvement.items():
                print(f"    {freq_band}: {improvement:+.3f}s")

        print(f"\n总预估费用: ¥{analysis.total_estimated_cost:.0f}")
        print("=" * 70 + "\n")
