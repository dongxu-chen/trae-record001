import os
import argparse
from typing import List, Tuple
from id3_reader import ID3Reader
from pattern_resolver import PatternResolver
from conflict import ConflictResolver


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


def compute_changes(files: List[str], resolver: PatternResolver, conflict_resolver: ConflictResolver) -> List[Tuple[str, str, dict]]:
    changes = []
    for file_path in files:
        dir_name = os.path.dirname(file_path)
        ext = os.path.splitext(file_path)[1].lower()

        reader = ID3Reader(file_path)
        tags = reader.read()

        base_name = resolver.resolve(tags)
        new_filename = conflict_resolver.resolve(dir_name, base_name, ext)
        new_path = os.path.join(dir_name, new_filename)
        changes.append((file_path, new_path, tags))
    return changes


def format_size(width: int, text: str) -> str:
    if len(text) <= width:
        return text.ljust(width)
    return '...' + text[-(width - 3):]


def main():
    parser = argparse.ArgumentParser(
        description='预览音乐文件重命名变更（不实际执行）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='示例: python dry_run.py -d ./music -p "{artist} - {title}"'
    )
    parser.add_argument('-d', '--directory', required=True, help='音乐文件所在目录')
    parser.add_argument('-p', '--pattern', default='{artist} - {title}', help='命名模板（默认: {artist} - {title}）')
    parser.add_argument('-r', '--recursive', action='store_true', help='递归扫描子目录')
    parser.add_argument('-s', '--strategy', choices=ConflictResolver.get_strategies(), default='suffix',
                        help='重名冲突处理策略（默认: suffix）')
    parser.add_argument('-f', '--fallback', default='Unknown', help='标签缺失时的默认值（默认: Unknown）')
    parser.add_argument('--show-tags', action='store_true', help='显示从文件读取的 ID3 标签')
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

    to_rename = sum(1 for old, new, _ in changes if old != new)

    print(f'\n{"=" * 60}')
    print(f'  变更预览 ({to_rename}/{len(files)} 个文件将被重命名)')
    print(f'{"=" * 60}\n')

    for idx, (old, new, tags) in enumerate(changes, 1):
        old_name = os.path.basename(old)
        new_name = os.path.basename(new)
        changed = old != new

        print(f'[{idx}] {old_name}')
        print(f'    {"->" if changed else "=="} {new_name}')

        if args.show_tags and tags:
            print('    标签:')
            for key in ['artist', 'title', 'album', 'track', 'year', 'genre']:
                if key in tags and tags[key]:
                    print(f'      {key}: {tags[key]}')

        if changed:
            print()

    print(f'\n{"=" * 60}')
    print(f'  摘要')
    print(f'{"=" * 60}')
    print(f'  目录:         {args.directory}')
    print(f'  递归:         {"是" if args.recursive else "否"}')
    print(f'  命名模板:     {args.pattern}')
    print(f'  冲突策略:     {args.strategy}')
    print(f'  总文件数:     {len(files)}')
    print(f'  将重命名:     {to_rename}')
    print(f'  无变化:       {len(files) - to_rename}')
    print(f'\n使用 rename.py 执行实际重命名')


if __name__ == '__main__':
    main()
