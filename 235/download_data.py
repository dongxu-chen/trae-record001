import os
import urllib.request
import zipfile
import argparse
from tqdm import tqdm


class DownloadProgressBar(tqdm):
    def update_to(self, b=1, bsize=1, tsize=None):
        if tsize is not None:
            self.total = tsize
        self.update(b * bsize - self.n)


def download_url(url, output_path):
    print(f'Downloading {url}...')
    with DownloadProgressBar(unit='B', unit_scale=True, miniters=1, desc=os.path.basename(output_path)) as t:
        urllib.request.urlretrieve(url, filename=output_path, reporthook=t.update_to)


def extract_zip(zip_path, extract_dir):
    print(f'Extracting {zip_path}...')
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
    print('Extraction complete.')


def main():
    parser = argparse.ArgumentParser(description='Download DIV2K dataset')
    parser.add_argument('--data_dir', type=str, default='./data', help='Data directory')
    parser.add_argument('--download_train', action='store_true', help='Download training set')
    parser.add_argument('--download_valid', action='store_true', help='Download validation set')
    parser.add_argument('--download_all', action='store_true', help='Download all datasets')
    args = parser.parse_args()
    
    os.makedirs(args.data_dir, exist_ok=True)
    
    div2k_dir = os.path.join(args.data_dir, 'DIV2K')
    os.makedirs(div2k_dir, exist_ok=True)
    
    base_url = 'http://data.vision.ee.ethz.ch/cvl/DIV2K'
    
    datasets = []
    
    if args.download_all or args.download_train:
        datasets.append(('DIV2K_train_HR.zip', f'{base_url}/DIV2K_train_HR.zip'))
    
    if args.download_all or args.download_valid:
        datasets.append(('DIV2K_valid_HR.zip', f'{base_url}/DIV2K_valid_HR.zip'))
    
    if not datasets:
        print('Please specify --download_train, --download_valid, or --download_all')
        return
    
    for filename, url in datasets:
        zip_path = os.path.join(args.data_dir, filename)
        
        if not os.path.exists(zip_path):
            try:
                download_url(url, zip_path)
            except Exception as e:
                print(f'Failed to download {filename}: {e}')
                print(f'Please download manually from: {url}')
                continue
        else:
            print(f'{filename} already exists, skipping download.')
        
        extract_dir = div2k_dir
        extract_zip(zip_path, extract_dir)
    
    print('\nDataset download complete!')
    print(f'Training data: {os.path.join(div2k_dir, "DIV2K_train_HR")}')
    print(f'Validation data: {os.path.join(div2k_dir, "DIV2K_valid_HR")}')


if __name__ == '__main__':
    main()
