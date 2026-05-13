import os
import json
import argparse
from datetime import datetime
from typing import List, Tuple, Dict, Any
from id3_reader import ID3Reader
from pattern_resolver import PatternResolver
from conflict import ConflictResolver

HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.rename_history.json')


def load_history() -> List[Dict[str, Any]]:
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_history(history_entry: Dict[str, Any]):
    history = load_history()
    history.append(history_entry)
    if len(history) > 20:
        history = history[-20:]
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"警告: 无法保存重命名历史 - {e}")


def find_music_files(directory: str, recursive: bool = False) -> List[str]:
    files = []
    if recursive:
        for root, _, filenames in os.walk(directory):
            for filename in filenames:
                filepath = os.path.join(root, filename)
                if ID3Reader.is_supported(filepath):
                    files.append(filepath)
    else:
        for filename in os.listdir(directory):
            filepath = os.path.join(directory, filename)
            if os.path.isfile(filepath) and ID3Reader.is_supported(filepath):
                files.append(filepath)
    return files


def compute_changes(files: List[str], resolver: PatternResolver, conflict_resolver: ConflictResolver) -> List[Tuple[str, str]]:
    changes = []
    for file_path in files:
        dir_name = os.path.dirname(file_path)
        ext = os.path.splitext(file_path)[1].lower()

        reader = ID3Reader(file_path)
        tags = reader.read()

        base_name = resolver.resolve(tags)
        new_filename = conflict_resolver.resolve(dir_name, base_name, ext)
        new_path = os.path.join(dir_name, new_filename)
        changes.append((file_path, new_path))
    return changes


def main():
    parser = argparse.ArgumentParser(
        description='批量重命名音乐文件（根据 ID3 标签）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='示例: python rename.py -d ./music -p "{artist} - {title}" --preview'
    )
    parser.add_argument('-d', '--directory', required=True, help='音乐文件所在目录')
    parser.add_argument('-p', '--pattern', default='{artist} - {title}', help='命名模板（默认: {artist} - {title}）')
    parser.add_argument('-r', '--recursive', action='store_true', help='递归扫描子目录')
    parser.add_argument('-s', '--strategy', choices=ConflictResolver.get_strategies(), default='suffix',
                        help='重名冲突处理策略（默认: suffix）')
    parser.add_argument('-f', '--fallback', default='Unknown', help='标签缺失时的默认值（默认: Unknown）')
    parser.add_argument('--preview', action='store_true', help='仅预览不执行重命名')
    parser.add_argument('--list-placeholders', action='store_true', help='列出所有可用的占位符')

    args = parser.parse_args()

    if args.list_placeholders:
        print('可用的占位符:')
        for ph in PatternResolver.list_placeholders():
            print(f'  - {{{ph}}}')
        return

    if not os.path.isdir(args.directory):
        print(f'错误: 目录不存在 - {args.directory}')
        return

    resolver = PatternResolver(args.pattern, fallback=args.fallback)
    conflict_resolver = ConflictResolver(strategy=args.strategy)

    print(f'扫描目录: {args.directory}')
    files = find_music_files(args.directory, args.recursive)
    print(f'找到 {len(files)} 个音乐文件')

    if not files:
        return

    for f in files:
        conflict_resolver.register(f)

    changes = compute_changes(files, resolver, conflict_resolver)

    if args.preview:
        print('\n=== 预览 ===')
        for old, new in changes:
            status = ' -> ' if old != new else ' (不变) '
            print(f'{os.path.basename(old)}{status}{os.path.basename(new)}')
        return

    print('\n执行重命名...')
    renamed = 0
    rename_list = []
    for old, new in changes:
        if old != new:
            print(f'{os.path.basename(old)} -> {os.path.basename(new)}')
            os.rename(old, new)
            rename_list.append({'old': old, 'new': new})
            renamed += 1

    if rename_list:
        history_entry = {
            'timestamp': datetime.now().isoformat(),
            'directory': args.directory,
            'pattern': args.pattern,
            'recursive': args.recursive,
            'renames': rename_list
        }
        save_history(history_entry)
        print(f'\n完成！已重命名 {renamed} 个文件，历史记录已保存')
    else:
        print(f'\n完成！没有文件需要重命名')


if __name__ == '__main__':
    main()
