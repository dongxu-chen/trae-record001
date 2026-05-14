import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import os
import platform


def get_tesseract_cmd():
    system = platform.system()
    if system == "Windows":
        possible_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.join(os.path.expanduser("~"), "AppData", "Local", "Programs", "Tesseract-OCR", "tesseract.exe")
        ]
        for path in possible_paths:
            if os.path.exists(path):
                return path
    elif system == "Darwin":
        possible_paths = [
            "/opt/homebrew/bin/tesseract",
            "/usr/local/bin/tesseract"
        ]
        for path in possible_paths:
            if os.path.exists(path):
                return path
    else:
        possible_paths = [
            "/usr/bin/tesseract",
            "/usr/local/bin/tesseract"
        ]
        for path in possible_paths:
            if os.path.exists(path):
                return path
    return None


def configure_tesseract(tesseract_cmd=None):
    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
    else:
        default_cmd = get_tesseract_cmd()
        if default_cmd:
            pytesseract.pytesseract.tesseract_cmd = default_cmd


def get_languages():
    try:
        return pytesseract.get_languages()
    except Exception:
        return ["eng"]


def preprocess_image(image, upscale=True, denoise=True, enhance_contrast=True):
    if isinstance(image, str):
        if not os.path.exists(image):
            raise FileNotFoundError(f"图片文件不存在: {image}")
        image = Image.open(image)
    
    img = image.convert('RGB')
    
    if upscale:
        width, height = img.size
        if width < 600 or height < 400:
            scale_factor = max(600 / width, 400 / height)
            scale_factor = min(scale_factor, 3.0)
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)
            img = img.resize((new_width, new_height), Image.LANCZOS)
    
    img = img.convert('L')
    
    if enhance_contrast:
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.5)
        
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(1.2)
    
    if denoise:
        img = img.filter(ImageFilter.MedianFilter(size=1))
        img = img.filter(ImageFilter.SMOOTH)
    
    return img


def binarize_image(image, threshold=127):
    if isinstance(image, str):
        image = Image.open(image)
    if image.mode != 'L':
        image = image.convert('L')
    
    return image.point(lambda p: 255 if p > threshold else 0)


def adaptive_binarize(image):
    if isinstance(image, str):
        image = Image.open(image)
    if image.mode != 'L':
        image = image.convert('L')
    
    import numpy as np
    from PIL import Image
    
    img_array = np.array(image)
    
    from scipy import ndimage
    local_mean = ndimage.uniform_filter(img_array, size=15)
    
    binary_array = (img_array > local_mean).astype(np.uint8) * 255
    
    return Image.fromarray(binary_array)


def get_optimal_config(lang, mode="auto"):
    if mode == "block":
        return "--psm 6"
    elif mode == "line":
        return "--psm 7"
    elif mode == "word":
        return "--psm 8"
    elif mode == "sparse":
        return "--psm 11"
    else:
        if "chi" in lang or "jpn" in lang or "kor" in lang:
            return "--psm 6 -c preserve_interword_spaces=1"
        else:
            return "--psm 6"


def recognize_text(image, lang="chi_sim+eng", config=None, preprocess=True, mode="auto"):
    if config is None:
        config = get_optimal_config(lang, mode)
    
    if isinstance(image, str):
        if not os.path.exists(image):
            raise FileNotFoundError(f"图片文件不存在: {image}")
        image = Image.open(image)
    
    if preprocess:
        try:
            image = preprocess_image(image)
        except Exception:
            pass
    
    try:
        text = pytesseract.image_to_string(image, lang=lang, config=config)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return "\n".join(lines)
    except Exception as e:
        raise RuntimeError(f"OCR识别失败: {str(e)}")


def recognize_with_position(image, lang="chi_sim+eng", config=None, preprocess=True):
    if config is None:
        config = get_optimal_config(lang, "auto")
    
    if isinstance(image, str):
        if not os.path.exists(image):
            raise FileNotFoundError(f"图片文件不存在: {image}")
        image = Image.open(image)
    
    if preprocess:
        try:
            image = preprocess_image(image)
        except Exception:
            pass
    
    try:
        data = pytesseract.image_to_data(image, lang=lang, config=config, output_type=pytesseract.Output.DICT)
        results = []
        n_boxes = len(data['level'])
        for i in range(n_boxes):
            if int(data['conf'][i]) > 0 and data['text'][i].strip():
                results.append({
                    'text': data['text'][i].strip(),
                    'confidence': data['conf'][i],
                    'left': data['left'][i],
                    'top': data['top'][i],
                    'width': data['width'][i],
                    'height': data['height'][i]
                })
        return results
    except Exception as e:
        raise RuntimeError(f"OCR识别失败: {str(e)}")


def check_training_data(lang="chi_sim"):
    available = get_languages()
    if lang in available:
        return True, None
    
    if "+" in lang:
        missing = []
        for l in lang.split("+"):
            if l not in available:
                missing.append(l)
        if missing:
            return False, f"缺少语言包: {', '.join(missing)}"
        return True, None
    
    return False, f"语言包未安装: {lang}。请安装对应语言包（如中文: tesseract-ocr-chi-sim）"


def get_tessdata_dir():
    tesseract_cmd = get_tesseract_cmd()
    if not tesseract_cmd:
        return None
    
    system = platform.system()
    if system == "Windows":
        base_dir = os.path.dirname(tesseract_cmd)
        tessdata_dir = os.path.join(base_dir, "tessdata")
        if os.path.exists(tessdata_dir):
            return tessdata_dir
    else:
        try:
            import subprocess
            result = subprocess.run([tesseract_cmd, "--list-langs"], capture_output=True, text=True)
            output = result.stdout
            for line in output.splitlines():
                if "Tessdata prefix:" in line:
                    return line.split(":", 1)[1].strip()
        except Exception:
            pass
    
    return None


_baidu_config = {
    "app_id": "",
    "app_key": "",
    "secret_key": "",
    "access_token": "",
    "token_expires": 0
}


def set_baidu_config(app_id, app_key, secret_key):
    global _baidu_config
    _baidu_config["app_id"] = app_id
    _baidu_config["app_key"] = app_key
    _baidu_config["secret_key"] = secret_key
    _baidu_config["access_token"] = ""
    _baidu_config["token_expires"] = 0


def get_baidu_access_token():
    import time
    global _baidu_config
    
    if _baidu_config["access_token"] and time.time() < _baidu_config["token_expires"]:
        return _baidu_config["access_token"]
    
    if not _baidu_config["app_key"] or not _baidu_config["secret_key"]:
        raise RuntimeError("请先配置百度翻译 API: set_baidu_config(app_id, app_key, secret_key)")
    
    try:
        import urllib.request
        import urllib.parse
        import json
        
        url = "https://aip.baidubce.com/oauth/2.0/token"
        params = {
            "grant_type": "client_credentials",
            "client_id": _baidu_config["app_key"],
            "client_secret": _baidu_config["secret_key"]
        }
        
        url_with_params = url + "?" + urllib.parse.urlencode(params)
        request = urllib.request.Request(url_with_params, method="POST")
        response = urllib.request.urlopen(request, timeout=10)
        result = json.loads(response.read().decode())
        
        if "access_token" in result:
            _baidu_config["access_token"] = result["access_token"]
            _baidu_config["token_expires"] = time.time() + result.get("expires_in", 2592000) - 600
            return _baidu_config["access_token"]
        else:
            raise RuntimeError(f"获取百度Token失败: {result}")
    except Exception as e:
        raise RuntimeError(f"获取百度Token失败: {str(e)}")


LANG_CODE_MAP = {
    "auto": "auto",
    "zh": "zh",
    "cn": "zh",
    "zh-cn": "zh",
    "en": "en",
    "jp": "jp",
    "ja": "jp",
    "jpn": "jp",
    "kor": "kor",
    "ko": "kor",
    "fra": "fra",
    "fr": "fra",
    "spa": "spa",
    "es": "spa",
    "de": "de",
    "deu": "de",
    "it": "it",
    "ita": "it",
    "ru": "ru",
    "rus": "ru",
    "pt": "pt",
    "pt-br": "pt",
    "ar": "ar",
    "ara": "ar",
    "th": "th",
    "tha": "th",
    "vi": "vie",
    "vie": "vie",
    "id": "id",
    "ind": "id",
    "ms": "may",
    "may": "may",
    "tr": "tr",
    "tur": "tr",
}


def normalize_lang_code(lang):
    lang = lang.lower().strip()
    return LANG_CODE_MAP.get(lang, lang)


def translate_text_baidu(text, from_lang="auto", to_lang="zh"):
    if not text or not text.strip():
        return ""
        
    try:
        import urllib.request
        import urllib.parse
        import json
        import hashlib
        import random
        import time
        
        access_token = get_baidu_access_token()
        
        url = "https://aip.baidubce.com/rpc/2.0/mt/texttrans/v1"
        
        from_lang = normalize_lang_code(from_lang)
        to_lang = normalize_lang_code(to_lang)
        
        request_data = {
            "from": from_lang,
            "to": to_lang,
            "q": text
        }
        
        request_body = json.dumps(request_data, ensure_ascii=False).encode('utf-8')
        
        full_url = f"{url}?access_token={access_token}"
        request = urllib.request.Request(
            full_url,
            data=request_body,
            headers={'Content-Type': 'application/json'}
        )
        
        response = urllib.request.urlopen(request, timeout=15)
        response_data = json.loads(response.read().decode('utf-8'))
        
        if "result" in response_data and "trans_result" in response_data["result"]:
            translations = []
            for item in response_data["result"]["trans_result"]:
                translations.append(item["dst"])
            return "\n".join(translations)
        elif "error_code" in response_data:
            raise RuntimeError(f"百度翻译错误: {response_data.get('error_msg', response_data)}")
        else:
            raise RuntimeError(f"百度翻译返回格式异常: {response_data}")
            
    except Exception as e:
        raise RuntimeError(f"翻译失败: {str(e)}")


def translate_text_free(text, from_lang="auto", to_lang="zh"):
    if not text or not text.strip():
        return ""
        
    try:
        import urllib.request
        import urllib.parse
        import json
        
        text = text.strip()
        text_encoded = urllib.parse.quote(text)
        from_lang = normalize_lang_code(from_lang)
        to_lang = normalize_lang_code(to_lang)
        
        url = f"https://api.mymemory.translated.net/get?q={text_encoded}&langpair={from_lang}|{to_lang}"
        
        request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib.request.urlopen(request, timeout=15)
        result = json.loads(response.read().decode())
        
        if "responseStatus" in result and result["responseStatus"] == 200:
            return result["responseData"]["translatedText"]
        else:
            raise RuntimeError(f"免费翻译API错误: {result}")
            
    except Exception as e:
        raise RuntimeError(f"免费翻译失败: {str(e)}")


def translate_text(text, from_lang="auto", to_lang="zh", use_baidu=False):
    if use_baidu:
        try:
            return translate_text_baidu(text, from_lang, to_lang)
        except Exception as e:
            try:
                return translate_text_free(text, from_lang, to_lang)
            except:
                raise e
    else:
        return translate_text_free(text, from_lang, to_lang)


def ocr_and_translate(image, ocr_lang="chi_sim+eng", to_lang="zh", use_baidu=False):
    text = recognize_text(image, lang=ocr_lang)
    
    if not text:
        return text, ""
    
    from_lang = "auto"
    if "chi" in ocr_lang or "zh" in ocr_lang:
        if "eng" not in ocr_lang:
            from_lang = "zh"
    elif "eng" in ocr_lang:
        from_lang = "en"
    elif "jpn" in ocr_lang:
        from_lang = "jp"
    elif "kor" in ocr_lang:
        from_lang = "kor"
    
    translated = translate_text(text, from_lang=from_lang, to_lang=to_lang, use_baidu=use_baidu)
    return text, translated


def is_baidu_configured():
    return bool(_baidu_config["app_key"] and _baidu_config["secret_key"])


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python ocr.py <image_path> [lang]")
        print("  python ocr.py translate <text> [from_lang] [to_lang]")
        print("  python ocr.py ocr-trans <image_path> [to_lang]")
        sys.exit(1)
    
    if sys.argv[1] == "translate" and len(sys.argv) >= 3:
        text = sys.argv[2]
        from_lang = sys.argv[3] if len(sys.argv) > 3 else "auto"
        to_lang = sys.argv[4] if len(sys.argv) > 4 else "zh"
        
        try:
            result = translate_text(text, from_lang, to_lang, use_baidu=is_baidu_configured())
            print(f"原文: {text}")
            print(f"翻译: {result}")
        except Exception as e:
            print(f"错误: {e}")
        sys.exit(0)
        
    if sys.argv[1] == "ocr-trans" and len(sys.argv) >= 3:
        image_path = sys.argv[2]
        to_lang = sys.argv[3] if len(sys.argv) > 3 else "zh"
        
        configure_tesseract()
        
        try:
            original, translated = ocr_and_translate(image_path, to_lang=to_lang, use_baidu=is_baidu_configured())
            print("=" * 50)
            print("识别结果:")
            print(original)
            print("=" * 50)
            print("翻译结果:")
            print(translated)
        except Exception as e:
            print(f"错误: {e}")
        sys.exit(0)
    
    image_path = sys.argv[1]
    lang = sys.argv[2] if len(sys.argv) > 2 else "chi_sim+eng"
    
    configure_tesseract()
    
    print(f"识别语言: {lang}")
    print(f"可用语言: {get_languages()}")
    print("-" * 50)
    
    try:
        text = recognize_text(image_path, lang=lang)
        print("识别结果:")
        print(text)
    except Exception as e:
        print(f"错误: {e}")
