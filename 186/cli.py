import os
import sys
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import init_database
from modules.audit_service import DramaAuditService


class MockFile:
    def __init__(self, file_path):
        self.file_path = file_path
    
    def save(self, path):
        import shutil
        shutil.copy2(self.file_path, path)


audit_service = DramaAuditService()


def cmd_init_db(args):
    print("正在初始化数据库...")
    try:
        init_database()
        print("数据库初始化成功！")
    except Exception as e:
        print(f"数据库初始化失败: {e}")
        sys.exit(1)


def cmd_upload(args):
    print(f"上传视频: {args.file}")
    try:
        if not os.path.exists(args.file):
            print(f"错误: 文件不存在: {args.file}")
            sys.exit(1)
        
        mock_file = MockFile(args.file)
        result = audit_service.upload_video(mock_file, os.path.basename(args.file))
        print(f"上传成功！视频ID: {result['video_id']}")
        print(f"文件名: {result['filename']}")
        print(f"文件大小: {result['file_size']} bytes")
    except Exception as e:
        print(f"上传失败: {e}")
        sys.exit(1)


def cmd_audit(args):
    print(f"开始审核视频ID: {args.video_id}")
    try:
        result = audit_service.audit_video(args.video_id, frame_interval=args.interval)
        print(f"\n审核完成！")
        print(f"审核结果: {'违规' if result['audit_result'] == 'violated' else '通过'}")
        print(f"违规数量: {result['violation_count']}")
        
        if result['violations']:
            print("\n违规详情:")
            for v in result['violations']:
                from modules import format_time
                print(f"  [{format_time(v['timestamp'])} - {v['violation_type_name']} (置信度: {v['confidence']:.2f})")
                print(f"    描述: {v['description']}")
                
    except Exception as e:
        print(f"审核失败: {e}")
        sys.exit(1)


def cmd_result(args):
    print(f"获取视频审核结果: {args.video_id}")
    try:
        result = audit_service.get_audit_result(args.video_id)
        print(f"视频: {result['video']['original_name']}")
        print(f"状态: {result['video']['status']}")
        print(f"审核结果: {result['video']['audit_result']}")
        print(f"违规数量: {result['violation_count']}")
        
        if result['violations']:
            from modules import format_time
            print("\n违规列表:")
            for v in result['violations']:
                print(f"  [{format_time(v['timestamp'])} - {v['violation_type_name']}")
                if v.get('description'):
                    print(f"    描述: {v['description']}")
    except Exception as e:
        print(f"获取结果失败: {e}")
        sys.exit(1)


def cmd_list(args):
    print("视频列表:")
    try:
        result = audit_service.list_videos(status=args.status, page=args.page, page_size=args.page_size)
        print(f"共 {result['total']} 个视频")
        print(f"第 {result['page']}/{result['total_pages']} 页\n")
        
        for v in result['videos']:
            print(f"ID: {v['id']}")
            print(f"  名称: {v['original_name']}")
            print(f"  时长: {v['duration']} 秒")
            print(f"  状态: {v['status']}")
            print(f"  审核结果: {v['audit_result']}")
            print(f"  违规数: {v['violation_count']}")
            print()
    except Exception as e:
        print(f"获取列表失败: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description='短剧内容审核系统 - 命令行工具')
    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    parser_init = subparsers.add_parser('init-db', help='初始化数据库')
    parser_init.set_defaults(func=cmd_init)

    parser_upload = subparsers.add_parser('upload', help='上传视频')
    parser_upload.add_argument('file', help='视频文件路径')
    parser_upload.set_defaults(func=cmd_upload)

    parser_audit = subparsers.add_parser('audit', help='审核视频')
    parser_audit.add_argument('video_id', type=int, help='视频ID')
    parser_audit.add_argument('--interval', type=float, default=None, help='帧抽取间隔（秒）')
    parser_audit.set_defaults(func=cmd_audit)

    parser_result = subparsers.add_parser('result', help='查看审核结果')
    parser_result.add_argument('video_id', type=int, help='视频ID')
    parser_result.set_defaults(func=cmd_result)

    parser_list = subparsers.add_parser('list', help='列出视频')
    parser_list.add_argument('--status', default=None, help='按状态筛选')
    parser_list.add_argument('--page', type=int, default=1)
    parser_list.add_argument('--page-size', type=int, default=20)
    parser_list.set_defaults(func=cmd_list)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == '__main__':
    main()
