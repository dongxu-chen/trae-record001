import argparse
import sys
from gui import main as run_gui
from poisson_editing import test_poisson_editing


def run_cli_test():
    print("运行泊松编辑测试...")
    result = test_poisson_editing()
    print("测试完成!")
    return result


def main():
    parser = argparse.ArgumentParser(description="泊松图像编辑 - Poisson Image Editing")
    parser.add_argument("--mode", choices=["gui", "test"], default="gui",
                       help="运行模式: gui (默认) 或 test")
    
    args = parser.parse_args()
    
    if args.mode == "gui":
        print("启动GUI界面...")
        run_gui()
    elif args.mode == "test":
        run_cli_test()


if __name__ == "__main__":
    main()
