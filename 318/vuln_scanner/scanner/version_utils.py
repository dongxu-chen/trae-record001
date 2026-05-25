"""
版本比较工具
"""
import re
from typing import Tuple, List, Optional


def parse_version(version: str) -> Tuple[int, ...]:
    """解析版本号为元组"""
    if not version:
        return (0, 0, 0)

    version = str(version).strip()

    version = re.sub(r'[^\d.]', '', version.split('+')[0].split('-')[0])

    if not version:
        return (0, 0, 0)

    parts = version.split('.')
    try:
        return tuple(int(p) if p else 0 for p in parts)
    except ValueError:
        return (0, 0, 0)


def parse_version_full(version: str) -> Tuple[List[int], str, str]:
    """完整解析版本，包括预发布和构建信息"""
    if not version:
        return ([0, 0, 0], "", "")

    version = str(version).strip()

    build = ""
    if "+" in version:
        parts = version.split("+", 1)
        version = parts[0]
        build = parts[1]

    pre_release = ""
    if "-" in version:
        parts = version.split("-", 1)
        version = parts[0]
        pre_release = parts[1]

    version = re.sub(r'[^\d.]', '', version)
    parts = version.split('.')
    try:
        nums = [int(p) if p else 0 for p in parts]
    except ValueError:
        nums = [0, 0, 0]

    while len(nums) < 3:
        nums.append(0)

    return (nums, pre_release, build)


def compare_versions(v1: str, v2: str) -> int:
    """比较两个版本号"""
    ver1 = parse_version(v1)
    ver2 = parse_version(v2)

    max_len = max(len(ver1), len(ver2))
    ver1 = ver1 + (0,) * (max_len - len(ver1))
    ver2 = ver2 + (0,) * (max_len - len(ver2))

    if ver1 < ver2:
        return -1
    elif ver1 > ver2:
        return 1
    return 0


def version_greater(v1: str, v2: str) -> bool:
    return compare_versions(v1, v2) > 0


def version_greater_or_equal(v1: str, v2: str) -> bool:
    return compare_versions(v1, v2) >= 0


def version_less(v1: str, v2: str) -> bool:
    return compare_versions(v1, v2) < 0


def version_less_or_equal(v1: str, v2: str) -> bool:
    return compare_versions(v1, v2) <= 0


def version_equal(v1: str, v2: str) -> bool:
    return compare_versions(v1, v2) == 0


def is_version_in_range(version: str, version_range: str) -> bool:
    """检查版本是否在指定范围内"""
    if not version_range or version_range == "*":
        return True

    version_range = version_range.strip()

    parts = [p.strip() for p in version_range.split(",")]

    if _is_safety_db_format(parts):
        return _check_safety_db_range(version, parts)

    for part in parts:
        part = part.strip()
        if not part:
            continue

        if part.startswith(">="):
            lower = part[2:].strip()
            if not version_greater_or_equal(version, lower):
                return False
        elif part.startswith("<="):
            upper = part[2:].strip()
            if not version_less_or_equal(version, upper):
                return False
        elif part.startswith(">"):
            lower = part[1:].strip()
            if not version_greater(version, lower):
                return False
        elif part.startswith("<"):
            upper = part[1:].strip()
            if not version_less(version, upper):
                return False
        elif part.startswith("==") or part.startswith("="):
            target = part.lstrip("= ").strip()
            if not version_equal(version, target):
                return False
        elif part.startswith("!="):
            target = part[2:].strip()
            if version_equal(version, target):
                return False
        elif " - " in part:
            low, high = part.split(" - ", 1)
            low = low.strip()
            high = high.strip()
            if not (version_greater_or_equal(version, low) and version_less_or_equal(version, high)):
                return False
        else:
            if not version_equal(version, part):
                return False

    return True


def _is_safety_db_format(parts: List[str]) -> bool:
    """检查是否为 Safety DB 格式（成对的 < 和 >=，顺序任意）"""
    if len(parts) < 2 or len(parts) % 2 != 0:
        return False

    has_lt = any(p.startswith("<") and "=" not in p for p in parts)
    has_gte = any(p.startswith(">=") for p in parts)

    if not (has_lt and has_gte):
        return False

    for i in range(0, len(parts), 2):
        if i + 1 >= len(parts):
            return False
        pair = parts[i:i + 2]
        has_pair_lt = any(p.startswith("<") and "=" not in p for p in pair)
        has_pair_gte = any(p.startswith(">=") for p in pair)
        if not (has_pair_lt and has_pair_gte):
            return False

    return True


def _check_safety_db_range(version: str, parts: List[str]) -> bool:
    """检查 Safety DB 格式的版本范围（OR 多组范围）"""
    for i in range(0, len(parts), 2):
        if i + 1 >= len(parts):
            continue

        pair = parts[i:i + 2]
        lower = None
        upper = None

        for part in pair:
            if part.startswith(">="):
                lower = part[2:].strip()
            elif part.startswith("<") and "=" not in part:
                upper = part[1:].strip()

        if lower is not None and upper is not None:
            if version_greater_or_equal(version, lower) and version_less(version, upper):
                return True

    return False


def is_version_affected(version: str, affected_versions: List[str]) -> bool:
    """检查版本是否受影响"""
    if not affected_versions:
        return False

    for affected in affected_versions:
        if is_version_in_range(version, affected):
            return True

    return False


def get_version_type(current: str, target: str) -> str:
    """判断版本升级类型"""
    curr = parse_version(current)
    tgt = parse_version(target)

    max_len = max(len(curr), len(tgt), 3)
    curr = curr + (0,) * (max_len - len(curr))
    tgt = tgt + (0,) * (max_len - len(tgt))

    if tgt[0] > curr[0]:
        return "major"
    elif tgt[1] > curr[1]:
        return "minor"
    elif tgt[2] > curr[2] or compare_versions(target, current) > 0:
        return "patch"
    else:
        return "downgrade"


def has_breaking_changes(current: str, target: str) -> bool:
    """判断是否有破坏性变更"""
    curr = parse_version(current)
    tgt = parse_version(target)

    if curr[0] != tgt[0]:
        return True

    if curr[0] == 0 and curr[1] != tgt[1]:
        return True

    return False
