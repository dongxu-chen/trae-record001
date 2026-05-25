import os
import urllib.request
import tarfile
import argparse


def download_bsds500(output_dir='.'):
    url = "http://www.eecs.berkeley.edu/Research/Projects/CS/vision/bsds/BSDS500.tgz"
    tgz_path = os.path.join(output_dir, "BSDS500.tgz")
    
    os.makedirs(output_dir, exist_ok=True)
    
    if os.path.exists(os.path.join(output_dir, "BSDS500")):
        print("BSDS500数据集似乎已存在")
        return True
    
    print("正在下载BSDS500数据集...")
    print(f"URL: {url}")
    print(f"大小: ~70 MB")
    
    def progress_hook(block_num, block_size, total_size):
        downloaded = block_num * block_size
        percent = 100.0 * downloaded / total_size
        print(f"\r下载进度: {percent:.1f}% ({downloaded / 1024 / 1024:.1f} MB / {total_size / 1024 / 1024:.1f} MB)", end='')
    
    try:
        urllib.request.urlretrieve(url, tgz_path, reporthook=progress_hook)
        print("\n下载完成!")
    except Exception as e:
        print(f"\n下载失败: {e}")
        print("请手动下载:")
        print(f"  {url}")
        print("然后解压到当前目录")
        return False
    
    print("正在解压...")
    try:
        with tarfile.open(tgz_path, 'r:gz') as tar:
            tar.extractall(output_dir)
        print("解压完成!")
    except Exception as e:
        print(f"解压失败: {e}")
        return False
    
    print("清理下载文件...")
    os.remove(tgz_path)
    
    print(f"\nBSDS500数据集已成功下载到: {os.path.join(output_dir, 'BSDS500')}")
    return True


def main():
    parser = argparse.ArgumentParser(description='下载BSDS500数据集')
    parser.add_argument('--output', '-o', default='.', help='输出目录')
    args = parser.parse_args()
    
    success = download_bsds500(args.output)
    
    if not success:
        print("\n使用合成数据集作为替代:")
        print("  运行 python main.py 将自动创建合成BSDS风格数据集")


if __name__ == "__main__":
    main()
