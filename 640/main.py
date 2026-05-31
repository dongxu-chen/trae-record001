import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def check_dependencies():
    missing = []
    try:
        import SimpleITK
    except ImportError:
        missing.append("SimpleITK")
    try:
        import numpy
    except ImportError:
        missing.append("numpy")
    try:
        import scipy
    except ImportError:
        missing.append("scipy")
    try:
        import PyQt5
    except ImportError:
        missing.append("PyQt5")
    if missing:
        print("Missing dependencies:", ", ".join(missing))
        print("Install with: pip install " + " ".join(missing))
        return False
    return True


def main():
    if not check_dependencies():
        sys.exit(1)
    from gui import main as gui_main

    gui_main()


if __name__ == "__main__":
    main()
