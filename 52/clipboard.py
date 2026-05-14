import pyperclip
import platform
from PIL import Image
import io


def copy_text(text):
    try:
        pyperclip.copy(text)
        return True
    except Exception as e:
        raise RuntimeError(f"复制文本到剪贴板失败: {str(e)}")


def paste_text():
    try:
        return pyperclip.paste()
    except Exception as e:
        raise RuntimeError(f"从剪贴板粘贴文本失败: {str(e)}")


def copy_image(image):
    system = platform.system()
    
    if system == "Windows":
        try:
            import win32clipboard
            from io import BytesIO
            
            output = BytesIO()
            if isinstance(image, str):
                image = Image.open(image)
            image.convert("RGB").save(output, "BMP")
            data = output.getvalue()[14:]
            output.close()
            
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
            win32clipboard.CloseClipboard()
            return True
        except ImportError:
            raise RuntimeError("Windows系统需要安装pywin32库: pip install pywin32")
        except Exception as e:
            raise RuntimeError(f"复制图片到剪贴板失败: {str(e)}")
    elif system == "Darwin":
        try:
            import subprocess
            import tempfile
            import os
            
            temp_path = tempfile.mktemp(suffix=".png")
            if isinstance(image, str):
                image = Image.open(image)
            image.save(temp_path, "PNG")
            
            script = f'''
            set the clipboard to (read (POSIX file "{temp_path}") as JPEG picture)
            '''
            subprocess.run(["osascript", "-e", script], check=True)
            os.remove(temp_path)
            return True
        except Exception as e:
            raise RuntimeError(f"复制图片到剪贴板失败: {str(e)}")
    else:
        try:
            import subprocess
            import tempfile
            import os
            
            temp_path = tempfile.mktemp(suffix=".png")
            if isinstance(image, str):
                image = Image.open(image)
            image.save(temp_path, "PNG")
            
            try:
                subprocess.run(["xclip", "-selection", "clipboard", "-t", "image/png", "-i", temp_path], check=True)
                os.remove(temp_path)
                return True
            except FileNotFoundError:
                subprocess.run(["xsel", "--clipboard", "--input", temp_path], check=True)
                os.remove(temp_path)
                return True
        except ImportError:
            raise RuntimeError("Linux系统需要安装xclip或xsel")
        except Exception as e:
            raise RuntimeError(f"复制图片到剪贴板失败: {str(e)}")


def clear_clipboard():
    try:
        pyperclip.copy("")
        return True
    except Exception as e:
        raise RuntimeError(f"清空剪贴板失败: {str(e)}")


def has_text():
    try:
        text = pyperclip.paste()
        return text is not None and text != ""
    except Exception:
        return False


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python clipboard.py copy <text>")
        print("  python clipboard.py paste")
        print("  python clipboard.py clear")
        sys.exit(1)
    
    command = sys.argv[1]
    
    try:
        if command == "copy":
            if len(sys.argv) < 3:
                print("Usage: python clipboard.py copy <text>")
                sys.exit(1)
            text = " ".join(sys.argv[2:])
            copy_text(text)
            print(f"已复制到剪贴板: {text}")
        elif command == "paste":
            text = paste_text()
            print(f"剪贴板内容: {text}")
        elif command == "clear":
            clear_clipboard()
            print("剪贴板已清空")
        else:
            print(f"未知命令: {command}")
            sys.exit(1)
    except Exception as e:
        print(f"错误: {e}")
