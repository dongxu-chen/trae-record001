import os
import urllib.request
import argparse
from typing import Dict

MODEL_URLS = {
    "starry_night": "https://cs.stanford.edu/people/jcjohns/fast-neural-style/models/starry_night.pth",
    "mosaic": "https://cs.stanford.edu/people/jcjohns/fast-neural-style/models/mosaic.pth",
    "candy": "https://cs.stanford.edu/people/jcjohns/fast-neural-style/models/candy.pth",
    "the_scream": "https://cs.stanford.edu/people/jcjohns/fast-neural-style/models/the_scream.pth",
    "udnie": "https://cs.stanford.edu/people/jcjohns/fast-neural-style/models/udnie.pth",
}

def download_model(style_name: str, save_dir: str = "models") -> bool:
    if style_name not in MODEL_URLS:
        print(f"Unknown style: {style_name}")
        print(f"Available styles: {', '.join(MODEL_URLS.keys())}")
        return False

    os.makedirs(save_dir, exist_ok=True)
    url = MODEL_URLS[style_name]
    save_path = os.path.join(save_dir, f"{style_name}.pth")

    if os.path.exists(save_path):
        print(f"Model already exists: {save_path}")
        return True

    print(f"Downloading {style_name} model...")
    try:
        def progress_hook(block_num, block_size, total_size):
            downloaded = block_num * block_size
            percent = downloaded * 100 / total_size
            print(f"\rProgress: {percent:.1f}% ({downloaded}/{total_size} bytes)", end="")

        urllib.request.urlretrieve(url, save_path, reporthook=progress_hook)
        print(f"\nSuccessfully downloaded to: {save_path}")
        return True
    except Exception as e:
        print(f"\nDownload failed: {e}")
        if os.path.exists(save_path):
            os.remove(save_path)
        return False

def download_all(save_dir: str = "models"):
    print(f"Downloading all {len(MODEL_URLS)} models...")
    success_count = 0
    for style in MODEL_URLS:
        if download_model(style, save_dir):
            success_count += 1
    print(f"\nDownloaded {success_count}/{len(MODEL_URLS)} models")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download pre-trained style transfer models")
    parser.add_argument(
        "--style",
        type=str,
        default=None,
        help=f"Style name to download. Available: {', '.join(MODEL_URLS.keys())}"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Download all available models"
    )
    parser.add_argument(
        "--save-dir",
        type=str,
        default="models",
        help="Directory to save models"
    )
    args = parser.parse_args()

    if args.all:
        download_all(args.save_dir)
    elif args.style:
        download_model(args.style, args.save_dir)
    else:
        print("Please specify --style <name> or --all")
        print(f"Available styles: {', '.join(MODEL_URLS.keys())}")
