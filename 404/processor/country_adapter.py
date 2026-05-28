from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import json
import os


@dataclass
class CountrySignStandard:
    country_code: str
    country_name: str
    region: str
    speed_limit_units: str
    sign_colors: Dict[str, Tuple[int, int, int]]
    class_mapping: Dict[str, str]
    special_signs: List[str] = field(default_factory=list)


@dataclass
class AdaptedDetection:
    original_class: str
    adapted_class: str
    country_code: str
    confidence_adjustment: float
    color_verified: bool
    local_name: str


class CountryAdapter:
    def __init__(self, default_country: str = "CN"):
        self.default_country = default_country
        self.current_country = default_country
        self.country_standards = self._load_country_standards()
        self.class_mappings = self._build_class_mappings()

    def _load_country_standards(self) -> Dict[str, CountrySignStandard]:
        standards = {}

        standards["CN"] = CountrySignStandard(
            country_code="CN",
            country_name="China",
            region="Asia",
            speed_limit_units="km/h",
            sign_colors={
                "speed_limit": (0, 0, 255),
                "prohibitory": (0, 0, 255),
                "warning": (0, 255, 255),
                "indicative": (0, 255, 0)
            },
            class_mapping={},
            special_signs=[]
        )

        standards["US"] = CountrySignStandard(
            country_code="US",
            country_name="United States",
            region="North America",
            speed_limit_units="mph",
            sign_colors={
                "speed_limit": (255, 255, 255),
                "prohibitory": (0, 0, 255),
                "warning": (0, 165, 255),
                "indicative": (255, 255, 255)
            },
            class_mapping={
                "speed_limit_20": "speed_limit_US_25",
                "speed_limit_30": "speed_limit_US_35",
                "speed_limit_50": "speed_limit_US_55",
                "speed_limit_60": "speed_limit_US_65",
                "speed_limit_80": "speed_limit_US_75",
                "speed_limit_100": "speed_limit_US_100",
                "speed_limit_120": "speed_limit_US_120",
            },
            special_signs=["stop_sign_US", "yield_US", "school_zone"]
        )

        standards["EU"] = CountrySignStandard(
            country_code="EU",
            country_name="European Union",
            region="Europe",
            speed_limit_units="km/h",
            sign_colors={
                "speed_limit": (255, 255, 255),
                "prohibitory": (0, 0, 255),
                "warning": (0, 0, 255),
                "indicative": (0, 255, 0)
            },
            class_mapping={
                "road_construction": "road_works_EU",
                "no_parking": "no_parking_EU",
            },
            special_signs=["priority_road", "end_priority"]
        )

        standards["JP"] = CountrySignStandard(
            country_code="JP",
            country_name="Japan",
            region="Asia",
            speed_limit_units="km/h",
            sign_colors={
                "speed_limit": (0, 0, 255),
                "prohibitory": (0, 0, 255),
                "warning": (0, 255, 255),
                "indicative": (255, 0, 0)
            },
            class_mapping={
                "stop": "stop_JP",
                "pedestrian_crossing": "pedestrian_crossing_JP",
            },
            special_signs=[]
        )

        standards["GB"] = CountrySignStandard(
            country_code="GB",
            country_name="United Kingdom",
            region="Europe",
            speed_limit_units="mph",
            sign_colors={
                "speed_limit": (255, 255, 255),
                "prohibitory": (0, 0, 255),
                "warning": (0, 0, 255),
                "indicative": (0, 255, 0)
            },
            class_mapping={
                "speed_limit_30": "speed_limit_GB_30",
                "speed_limit_50": "speed_limit_GB_50",
                "speed_limit_60": "speed_limit_GB_60",
                "speed_limit_70": "speed_limit_GB_70",
                "speed_limit_80": "speed_limit_GB_80",
            },
            special_signs=["national_speed_limit"]
        )

        standards["DE"] = CountrySignStandard(
            country_code="DE",
            country_name="Germany",
            region="Europe",
            speed_limit_units="km/h",
            sign_colors={
                "speed_limit": (255, 255, 255),
                "prohibitory": (0, 0, 255),
                "warning": (0, 0, 255),
                "indicative": (0, 255, 0)
            },
            class_mapping={
                "no_overtaking_trucks": "no_overtaking_trucks_DE",
            },
            special_signs=["autobahn", "end_autobahn"]
        )

        standards["AU"] = CountrySignStandard(
            country_code="AU",
            country_name="Australia",
            region="Oceania",
            speed_limit_units="km/h",
            sign_colors={
                "speed_limit": (255, 255, 255),
                "prohibitory": (0, 0, 255),
                "warning": (255, 255, 0),
                "indicative": (0, 255, 0)
            },
            class_mapping={},
            special_signs=[]
        )

        standards["IN"] = CountrySignStandard(
            country_code="IN",
            country_name="India",
            region="Asia",
            speed_limit_units="km/h",
            sign_colors={
                "speed_limit": (255, 255, 255),
                "prohibitory": (0, 0, 255),
                "warning": (0, 0, 255),
                "indicative": (0, 255, 0)
            },
            class_mapping={},
            special_signs=["cow_crossing", "elephant_crossing"]
        )

        standards["BR"] = CountrySignStandard(
            country_code="BR",
            country_name="Brazil",
            region="South America",
            speed_limit_units="km/h",
            sign_colors={
                "speed_limit": (255, 255, 255),
                "prohibitory": (0, 0, 255),
                "warning": (0, 255, 255),
                "indicative": (0, 255, 0)
            },
            class_mapping={},
            special_signs=[]
        )

        standards["RU"] = CountrySignStandard(
            country_code="RU",
            country_name="Russia",
            region="Europe/Asia",
            speed_limit_units="km/h",
            sign_colors={
                "speed_limit": (255, 255, 255),
                "prohibitory": (0, 0, 255),
                "warning": (0, 0, 255),
                "indicative": (0, 255, 0)
            },
            class_mapping={},
            special_signs=[]
        )

        return standards

    def _build_class_mappings(self) -> Dict[str, Dict[str, str]]:
        mappings = {}
        for code, standard in self.country_standards.items():
            mappings[code] = standard.class_mapping
        return mappings

    def set_country(self, country_code: str) -> bool:
        if country_code in self.country_standards:
            self.current_country = country_code
            return True
        return False

    def get_current_standard(self) -> CountrySignStandard:
        return self.country_standards[self.current_country]

    def get_supported_countries(self) -> List[Dict]:
        return [
            {
                "code": code,
                "name": std.country_name,
                "region": std.region,
                "units": std.speed_limit_units
            }
            for code, std in self.country_standards.items()
        ]

    def adapt_class_name(self, class_name: str) -> AdaptedDetection:
        standard = self.country_standards[self.current_country]
        mapping = standard.class_mapping

        if class_name in mapping:
            adapted = mapping[class_name]
            confidence_adj = 0.9
        else:
            adapted = class_name
            confidence_adj = 1.0

        from config import CLASS_ZH_CN
        local_name = CLASS_ZH_CN.get(class_name, class_name)

        return AdaptedDetection(
            original_class=class_name,
            adapted_class=adapted,
            country_code=self.current_country,
            confidence_adjustment=confidence_adj,
            color_verified=True,
            local_name=local_name
        )

    def adapt_speed_limit(self, class_name: str) -> Tuple[str, Optional[float], str]:
        if not class_name.startswith("speed_limit_"):
            return class_name, None, ""

        try:
            speed = int(class_name.split("_")[-1])
        except:
            return class_name, None, ""

        standard = self.country_standards[self.current_country]

        if standard.speed_limit_units == "mph":
            speed_kmh = speed
            speed_mph = int(speed * 0.621371)
            return f"speed_limit_{speed_mph}", speed_mph, "mph"

        return class_name, speed, "km/h"

    def adapt_color(self, category: str) -> Tuple[int, int, int]:
        standard = self.country_standards[self.current_country]
        return standard.sign_colors.get(category, (255, 255, 255))

    def convert_speed(self, speed_value: float, from_unit: str, to_unit: str) -> float:
        if from_unit == to_unit:
            return speed_value

        if from_unit == "km/h" and to_unit == "mph":
            return speed_value * 0.621371
        elif from_unit == "mph" and to_unit == "km/h":
            return speed_value / 0.621371

        return speed_value

    def auto_detect_country(
        self,
        detections: List,
        image: Optional[np.ndarray] = None
    ) -> str:
        if not detections:
            return self.default_country

        score_map: Dict[str, float] = {code: 0.0 for code in self.country_standards.keys()}

        for det in detections:
            class_name = det.class_name

            if class_name.startswith("speed_limit_"):
                try:
                    speed = int(class_name.split("_")[-1])
                    if speed in [25, 35, 45, 55, 65, 75]:
                        score_map["US"] += 1.0
                        score_map["GB"] += 0.5
                    elif speed in [30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130]:
                        score_map["EU"] += 0.8
                        score_map["DE"] += 0.8
                        score_map["CN"] += 0.8
                        score_map["AU"] += 0.8
                except:
                    pass

            if "school" in class_name.lower():
                score_map["US"] += 1.0

            if "cow" in class_name.lower() or "elephant" in class_name.lower():
                score_map["IN"] += 1.5

            if "autobahn" in class_name.lower():
                score_map["DE"] += 2.0

        if image is not None:
            h, w = image.shape[:2]
            image_hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

            for code, standard in self.country_standards.items():
                for category, color in standard.sign_colors.items():
                    color_rgb = np.array([[color]], dtype=np.uint8)
                    color_hsv = cv2.cvtColor(color_rgb, cv2.COLOR_RGB2HSV)[0][0]

                    lower = np.array([max(0, color_hsv[0] - 20), 50, 50])
                    upper = np.array([min(179, color_hsv[0] + 20), 255, 255])
                    mask = cv2.inRange(image_hsv, lower, upper)
                    color_ratio = np.sum(mask > 0) / (h * w)

                    if color_ratio > 0.01:
                        score_map[code] += color_ratio * 10

        if max(score_map.values()) > 0:
            return max(score_map, key=score_map.get)
        return self.default_country

    def get_display_name(self, class_name: str) -> str:
        from config import CLASS_ZH_CN
        return CLASS_ZH_CN.get(class_name, class_name)

    def get_country_info(self, country_code: Optional[str] = None) -> Optional[Dict]:
        code = country_code or self.current_country
        if code in self.country_standards:
            std = self.country_standards[code]
            return {
                "code": std.country_code,
                "name": std.country_name,
                "region": std.region,
                "units": std.speed_limit_units,
                "special_signs": std.special_signs
            }
        return None

    def batch_adapt(self, detections: List) -> List[AdaptedDetection]:
        return [self.adapt_class_name(det.class_name) for det in detections]


import cv2
import numpy as np
