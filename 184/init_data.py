from data_generator import generate_comments, save_comments_to_csv
from data_processor import import_csv_to_db
from config import CSV_PATH
import os

def main():
    import sys
    force = '--force' in sys.argv or '-f' in sys.argv
    
    print('=' * 50)
    print('商品评论情感分析系统 - 数据初始化')
    print('=' * 50)
    
    if os.path.exists(CSV_PATH) and not force:
        print(f'发现已有数据文件: {CSV_PATH}')
        print('使用现有数据进行分析...')
        import_csv_to_db(analyze=True)
        print('数据初始化完成！')
        return
    
    print('\n正在生成模拟评论数据...')
    comments = generate_comments(1000)
    save_comments_to_csv(comments, CSV_PATH)
    
    print('\n正在进行情感分析并导入数据库...')
    import_csv_to_db(analyze=True)
    
    print('\n' + '=' * 50)
    print('数据初始化完成！')
    print('=' * 50)

if __name__ == '__main__':
    main()
