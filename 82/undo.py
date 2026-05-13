import os
import json
import argparse
from datetime import datetime
from typing import List, Dict, Any

HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.rename_history.json')


def load_history() -> List[Dict[str, Any]]:
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_history(history: List[Dict[str, Any]]):
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"警告: 无法更新重命名历史 - {e}")


def format_timestamp(iso_str: str) -> str:
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        return iso_str


def list_history():
    history = load_history()
    if not history:
        print('没有找到重命名历史记录')
        return

    print(f'\n{"=" * 70}')
    print(f'  重命名历史记录 (最近 {len(history)} 次)')
    print(f'{"=" * 70}\n')

    for idx, entry in enumerate(reversed(history), 1):
        num = len(history) - idx
        print(f'[{num}] {format_timestamp(entry["timestamp"])}')
        print(f'    目录: {entry["directory"]}')
        print(f'    模板: {entry["pattern"]}')
        print(f'    重命名文件数: {len(entry["renames"])}')
        print()


def show_entry(entry_idx: int):
    history = load_history()
    if entry_idx < 0 or entry_idx >= len(history):
        print(f'错误: 历史记录索引 {entry_idx} 不存在')
        return

    entry = history[entry_idx]
    print(f'\n{"=" * 70}')
    print(f'  历史记录详情 #{entry_idx}')
    print(f'{"=" * 70}')
    print(f'  时间:     {format_timestamp(entry["timestamp"])}')
    print(f'  目录:     {entry["directory"]}')
    print(f'  模板:     {entry["pattern"]}')
    print(f'  递归:     {"是" if entry.get("recursive") else "否"}')
    print(f'  文件数:   {len(entry["renames"])}')
    print(f'\n  重命名列表:')

    for item in entry['renames']:
        old = item['old']
        new = item['new']
        print(f'    {os.path.basename(new)} <- {os.path.basename(old)}')

    print()


def execute_undo(entry_idx: int, dry_run: bool = False):
    history = load_history()
    if entry_idx < 0 or entry_idx >= len(history):
        print(f'错误: 历史记录索引 {entry_idx} 不存在')
        return

    entry = history[entry_idx]

    print(f'\n{"=" * 70}')
    print(f'  撤销历史记录 #{entry_idx}')
    print(f'  时间: {format_timestamp(entry["timestamp"])}')
    print(f'  文件数: {len(entry["renames"])}')
    print(f'{"=" * 70}\n')

    success_count = 0
    fail_count = 0

    for item in reversed(entry['renames']):
        old_path = item['old']
        new_path = item['new']

        current_filename = os.path.basename(new_path)
        target_filename = os.path.basename(old_path)
        current_dir = os.path.dirname(new_path)

        current_path = os.path.join(current_dir, current_filename)
        target_path = os.path.join(current_dir, target_filename)

        if not os.path.exists(current_path):
            print(f'[跳过] {current_filename} (文件不存在)')
            fail_count += 1
            continue

        if dry_run:
            print(f'[预览] {current_filename} -> {target_filename}')
            success_count += 1
        else:
            try:
                os.rename(current_path, target_path)
                print(f'[成功] {current_filename} -> {target_filename}')
                success_count += 1
            except Exception as e:
                print(f'[失败] {current_filename}: {e}')
                fail_count += 1

    if not dry_run and success_count > 0 and fail_count == 0:
        history.pop(entry_idx)
        save_history(history)
        print(f'\n完成！已撤销 {success_count} 个文件的重命名，历史记录已移除')
    elif not dry_run:
        print(f'\n完成！成功: {success_count}, 失败: {fail_count}')
    else:
        print(f'\n预览完成！将撤销 {success_count} 个文件的重命名')


def main():
    parser = argparse.ArgumentParser(
        description='撤销音乐文件重命名操作',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='示例:\n'
               '  python undo.py --list              # 列出历史记录\n'
               '  python undo.py --show 0             # 查看历史记录详情\n'
               '  python undo.py --undo 0 --dry-run   # 预览撤销操作\n'
               '  python undo.py --undo 0             # 执行撤销'
    )
    parser.add_argument('--list', action='store_true', help='列出所有重命名历史记录')
    parser.add_argument('--show', type=int, metavar='INDEX', help='显示指定历史记录的详情')
    parser.add_argument('--undo', type=int, metavar='INDEX', help='撤销指定的历史记录')
    parser.add_argument('--dry-run', action='store_true', help='预览撤销操作，不实际执行')

    args = parser.parse_args()

    if args.list:
        list_history()
    elif args.show is not None:
        show_entry(args.show)
    elif args.undo is not None:
        execute_undo(args.undo, dry_run=args.dry_run)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
