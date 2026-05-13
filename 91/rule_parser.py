from typing import Set, List, Tuple, Optional
import re


DEFAULT_NEIGHBORHOOD = [
    (-1, -1), (-1, 0), (-1, 1),
    (0, -1),          (0, 1),
    (1, -1),  (1, 0), (1, 1)
]

VON_NEUMANN_NEIGHBORHOOD = [
    (-1, 0), (0, -1), (0, 1), (1, 0)
]


class Rule:
    def __init__(
        self,
        born: Set[int],
        survive: Set[int],
        neighborhood: List[Tuple[int, int]] = None,
        name: str = "Custom"
    ) -> None:
        self.born = set(born)
        self.survive = set(survive)
        self.neighborhood = neighborhood if neighborhood is not None else list(DEFAULT_NEIGHBORHOOD)
        self.name = name

    def will_be_alive(self, is_alive_now: bool, live_neighbors: int) -> bool:
        if is_alive_now:
            return live_neighbors in self.survive
        else:
            return live_neighbors in self.born

    def to_string(self) -> str:
        b = "".join(str(n) for n in sorted(self.born))
        s = "".join(str(n) for n in sorted(self.survive))
        return f"B{b}/S{s}"

    def __repr__(self) -> str:
        return f"Rule(name={self.name}, {self.to_string()}, neighbors={len(self.neighborhood)})"


def parse_rule(rule_string: str, name: str = None) -> Rule:
    rule_string = rule_string.strip().upper()
    match = re.match(r'^B(\d*)/S(\d*)$', rule_string)
    if not match:
        match2 = re.match(r'^S(\d*)/B(\d*)$', rule_string)
        if match2:
            survive_str, born_str = match2.group(1), match2.group(2)
        else:
            raise ValueError(f"Invalid rule format: {rule_string}. Use Bx/Sy format.")
    else:
        born_str, survive_str = match.group(1), match.group(2)

    born = {int(c) for c in born_str}
    survive = {int(c) for c in survive_str}

    if name is None:
        name = rule_string

    return Rule(born, survive, name=name)


CONWAY = Rule(born={3}, survive={2, 3}, name="Conway's Life")

HIGH_LIFE = Rule(born={3, 6}, survive={2, 3}, name="HighLife")

DAY_AND_NIGHT = Rule(born={3, 6, 7, 8}, survive={3, 4, 6, 7, 8}, name="Day & Night")

REPLICATOR = Rule(born={1, 3, 5, 7}, survive={1, 3, 5, 7}, name="Replicator")

SEEDS = Rule(born={2}, survive=set(), name="Seeds")

LIFE_WITHOUT_DEATH = Rule(born={3}, survive={0, 1, 2, 3, 4, 5, 6, 7, 8}, name="Life without Death")

FREDKIN = Rule(born={1, 3, 5, 7}, survive={0, 2, 4, 6, 8}, name="Fredkin's Modulo 2")

DAN_DRUM = Rule(born={3, 5, 6, 7, 8}, survive={3, 5, 6, 7, 8}, name="Dan Drum")

WALLS = Rule(born={4, 5, 6, 7, 8}, survive={1, 2, 3, 4, 5, 6, 7, 8}, name="Walls")

GNARL = Rule(born={1}, survive={1}, name="Gnarl")

VON_NEUMANN = Rule(
    born={1, 3},
    survive={2, 3},
    neighborhood=VON_NEUMANN_NEIGHBORHOOD,
    name="Von Neumann (4-neighbors)"
)

BUILTIN_RULES = {
    "Conway's Life": CONWAY,
    "HighLife": HIGH_LIFE,
    "Day & Night": DAY_AND_NIGHT,
    "Replicator": REPLICATOR,
    "Seeds": SEEDS,
    "Life without Death": LIFE_WITHOUT_DEATH,
    "Fredkin's Modulo 2": FREDKIN,
    "Dan Drum": DAN_DRUM,
    "Walls": WALLS,
    "Gnarl": GNARL,
    "Von Neumann": VON_NEUMANN
}


def list_builtin_rules() -> List[str]:
    return list(BUILTIN_RULES.keys())


def get_builtin_rule(name: str) -> Rule:
    if name not in BUILTIN_RULES:
        raise ValueError(f"Unknown builtin rule: {name}")
    return BUILTIN_RULES[name]


def create_rule_from_string(rule_string: str) -> Rule:
    return parse_rule(rule_string)


def is_valid_rule_string(rule_string: str) -> bool:
    try:
        parse_rule(rule_string)
        return True
    except ValueError:
        return False
