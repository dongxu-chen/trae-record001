from typing import Dict, Set, Tuple


GLIDER = {(1, 0), (2, 1), (0, 2), (1, 2), (2, 2)}

BLINKER = {(0, 0), (1, 0), (2, 0)}

TOAD = {(1, 0), (2, 0), (3, 0), (0, 1), (1, 1), (2, 1)}

BEACON = {
    (0, 0), (1, 0),
    (0, 1), (1, 1),
    (2, 2), (3, 2),
    (2, 3), (3, 3)
}

PULSAR = {
    (2, 0), (3, 0), (4, 0),
    (8, 0), (9, 0), (10, 0),
    (0, 2), (5, 2), (7, 2), (12, 2),
    (0, 3), (5, 3), (7, 3), (12, 3),
    (0, 4), (5, 4), (7, 4), (12, 4),
    (2, 5), (3, 5), (4, 5),
    (8, 5), (9, 5), (10, 5),
    (2, 7), (3, 7), (4, 7),
    (8, 7), (9, 7), (10, 7),
    (0, 8), (5, 8), (7, 8), (12, 8),
    (0, 9), (5, 9), (7, 9), (12, 9),
    (0, 10), (5, 10), (7, 10), (12, 10),
    (2, 12), (3, 12), (4, 12),
    (8, 12), (9, 12), (10, 12)
}

GLIDER_GUN = {
    (24, 0),
    (22, 1), (24, 1),
    (12, 2), (13, 2), (20, 2), (21, 2), (34, 2), (35, 2),
    (11, 3), (15, 3), (20, 3), (21, 3), (34, 3), (35, 3),
    (0, 4), (1, 4), (10, 4), (16, 4), (20, 4), (21, 4),
    (0, 5), (1, 5), (10, 5), (14, 5), (16, 5), (17, 5), (22, 5), (24, 5),
    (10, 6), (16, 6), (24, 6),
    (11, 7), (15, 7),
    (12, 8), (13, 8)
}

BLOCK = {(0, 0), (1, 0), (0, 1), (1, 1)}

BOAT = {(0, 0), (1, 0), (0, 1), (2, 1), (1, 2)}

SHIP = {(0, 0), (1, 0), (2, 1), (0, 1), (1, 2), (2, 2)}

LIGHTWEIGHT_SPACESHIP = {
    (1, 0), (2, 0), (3, 0), (4, 0),
    (0, 1), (4, 1),
    (4, 2),
    (0, 3), (3, 3)
}

PENTOMINO = {(1, 0), (2, 0), (0, 1), (1, 1), (1, 2)}

R_PENTOMINO = {(1, 0), (2, 0), (0, 1), (1, 1), (1, 2)}

PIE_HEXOMINO = {
    (0, 0), (1, 0), (2, 0),
    (0, 1), (1, 1), (0, 2)
}

ACORN = {
    (0, 1),
    (1, 3),
    (2, 0), (2, 1), (2, 4), (2, 5), (2, 6)
}

SWITCH_ENGINE = {
    (2, 0),
    (0, 1), (2, 1),
    (0, 2), (1, 2),
    (4, 4),
    (3, 5), (4, 5), (5, 5),
    (3, 6), (4, 6), (5, 6),
    (3, 7), (4, 7), (5, 7)
}

PATTERNS: Dict[str, Set[Tuple[int, int]]] = {
    "glider": GLIDER,
    "blinker": BLINKER,
    "toad": TOAD,
    "beacon": BEACON,
    "pulsar": PULSAR,
    "glider_gun": GLIDER_GUN,
    "block": BLOCK,
    "boat": BOAT,
    "ship": SHIP,
    "lightweight_spaceship": LIGHTWEIGHT_SPACESHIP,
    "pentomino": PENTOMINO,
    "r_pentomino": R_PENTOMINO,
    "pie_hexomino": PIE_HEXOMINO,
    "acorn": ACORN,
    "switch_engine": SWITCH_ENGINE
}


def get_pattern(name: str) -> Set[Tuple[int, int]]:
    if name not in PATTERNS:
        raise ValueError(f"Unknown pattern: {name}")
    return PATTERNS[name]


def list_patterns() -> list:
    return list(PATTERNS.keys())


def center_pattern(pattern: Set[Tuple[int, int]], center_x: int, center_y: int) -> Set[Tuple[int, int]]:
    xs = [x for x, y in pattern]
    ys = [y for x, y in pattern]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    pattern_center_x = (min_x + max_x) // 2
    pattern_center_y = (min_y + max_y) // 2
    offset_x = center_x - pattern_center_x
    offset_y = center_y - pattern_center_y
    return {(x + offset_x, y + offset_y) for x, y in pattern}
