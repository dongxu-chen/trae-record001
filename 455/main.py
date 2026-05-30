import os
import argparse
import cv2
import numpy as np
from typing import Optional

from config import Config
from detector import YOLODetector
from tracker import DeepSORT
from processor import VideoProcessor


def parse_args():
    parser = argparse.ArgumentParser(
        description="视频目标检测与跟踪系统 - YOLOv8 + DeepSORT"
    )

    parser.add_argument(
        "--source",
        type=str,
        default="0",
        help="输入源: 视频文件路径 或 摄像头索引 (默认: 0)"
    )

    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="输出视频文件路径 (可选)"
    )

    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="YOLOv8模型路径 (默认: models/yolov8n.pt)"
    )

    parser.add_argument(
        "--conf",
        type=float,
        default=None,
        help="检测置信度阈值 (默认: 0.25)"
    )

    parser.add_argument(
        "--imgsz",
        type=int,
        default=None,
        help="输入图像大小 (默认: 640)"
    )

    parser.add_argument(
        "--device",
        type=str,
        default=None,
        help="运行设备: cuda 或 cpu (默认: 自动检测)"
    )

    parser.add_argument(
        "--classes",
        type=int,
        nargs="+",
        default=None,
        help="只检测指定的类别ID, 例如: --classes 0 2 5 (默认: 所有类别)"
    )

    parser.add_argument(
        "--max-age",
        type=int,
        default=None,
        help="跟踪器最大存活帧数 (默认: 30)"
    )

    parser.add_argument(
        "--no-display",
        action="store_true",
        help="不显示处理窗口"
    )

    parser.add_argument(
        "--no-trails",
        action="store_true",
        help="不绘制轨迹线"
    )

    parser.add_argument(
        "--save-txt",
        action="store_true",
        help="保存检测结果到文本文件"
    )

    parser.add_argument(
        "--no-skip-frame",
        action="store_true",
        help="禁用跳帧检测，每帧都检测"
    )

    parser.add_argument(
        "--detect-interval",
        type=int,
        default=None,
        help="跳帧检测间隔，例如2表示每2帧检测1次 (默认: 2)"
    )

    parser.add_argument(
        "--no-interpolation",
        action="store_true",
        help="禁用运动插值"
    )

    parser.add_argument(
        "--no-high-res",
        action="store_true",
        help="禁用高分辨率小目标检测分支"
    )

    parser.add_argument(
        "--high-res-scale",
        type=float,
        default=None,
        help="高分辨率放大倍数 (默认: 2.0)"
    )

    parser.add_argument(
        "--small-object-area",
        type=int,
        default=None,
        help="小目标面积阈值，小于该值启用高分辨率检测 (默认: 1024)"
    )

    parser.add_argument(
        "--no-anomaly",
        action="store_true",
        help="禁用轨迹异常检测"
    )

    parser.add_argument(
        "--no-cross-camera",
        action="store_true",
        help="禁用跨摄像头接力跟踪"
    )

    parser.add_argument(
        "--no-metrics",
        action="store_true",
        help="禁用评估仪表板"
    )

    parser.add_argument(
        "--camera-id",
        type=str,
        default="cam_0",
        help="当前摄像头ID，用于跨摄像头跟踪 (默认: cam_0)"
    )

    return parser.parse_args()


def run_detection(args):
    Config.ensure_dirs()

    if args.no_trails:
        Config.SHOW_TRAILS = False

    skip_frame_enable = not args.no_skip_frame
    interpolation_enable = not args.no_interpolation
    high_res_enable = not args.no_high_res
    anomaly_enable = not args.no_anomaly
    cross_camera_enable = not args.no_cross_camera
    metrics_enable = not args.no_metrics

    detector = YOLODetector(
        model_path=args.model,
        conf=args.conf,
        imgsz=args.imgsz,
        device=args.device,
        classes=args.classes,
        high_res_enable=high_res_enable,
        high_res_scale=args.high_res_scale,
        small_object_area=args.small_object_area,
    )

    tracker = DeepSORT(
        max_age=args.max_age,
    )

    processor = VideoProcessor(
        detector=detector,
        tracker=tracker,
        skip_frame_enable=skip_frame_enable,
        detect_interval=args.detect_interval,
        interpolation_enable=interpolation_enable,
        anomaly_enable=anomaly_enable,
        cross_camera_enable=cross_camera_enable,
        metrics_enable=metrics_enable,
        camera_id=args.camera_id,
    )

    source = args.source
    if source.isdigit():
        source = int(source)
        print(f"正在打开摄像头 {source}...")
        process_generator = processor.process_webcam(
            camera_index=source,
            output_path=args.output,
        )
        source_type = "webcam"
    else:
        if not os.path.exists(source):
            raise FileNotFoundError(f"视频文件不存在: {source}")
        print(f"正在处理视频: {source}")
        process_generator = processor.process_video(
            input_path=source,
            output_path=args.output,
        )
        source_type = "video"

    if args.save_txt and args.output:
        txt_path = os.path.splitext(args.output)[0] + ".txt"
        txt_file = open(txt_path, "w")
    else:
        txt_file = None

    frame_count = 0
    try:
        for annotated_frame, tracks in process_generator:
            frame_count += 1

            if txt_file:
                for track in tracks:
                    bbox = track["bbox"]
                    txt_file.write(
                        f"{frame_count},{track['id']},{bbox[0]:.2f},{bbox[1]:.2f},"
                        f"{bbox[2]-bbox[0]:.2f},{bbox[3]-bbox[1]:.2f},"
                        f"{track['confidence']:.4f},{track['class_id']},-1,-1\n"
                    )

            if not args.no_display:
                display_frame = annotated_frame.copy()
                info_text = f"Frame: {frame_count} | Objects: {len(tracks)}"
                cv2.putText(
                    display_frame,
                    info_text,
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 255, 0),
                    2,
                )

                for i, track in enumerate(tracks):
                    track_info = f"ID:{track['id']} {detector.get_class_name(track['class_id'])}"
                    cv2.putText(
                        display_frame,
                        track_info,
                        (10, 60 + i * 25),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        processor.color_generator.get_color(track["id"]),
                        2,
                    )

                cv2.imshow("YOLOv8 + DeepSORT 目标检测与跟踪", display_frame)

                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('p'):
                    cv2.waitKey(0)
                elif key == ord('r'):
                    processor.reset_tracker()
                    print("跟踪器已重置")
                elif key == ord('s'):
                    status = processor.toggle_skip_frame()
                    print(f"跳帧检测: {'开启' if status else '关闭'}")
                elif key == ord('h'):
                    status = processor.toggle_high_resolution()
                    print(f"高分辨率分支: {'开启' if status else '关闭'}")
                elif key == ord('1'):
                    processor.set_detect_interval(1)
                    print("检测间隔: 每帧检测")
                elif key == ord('2'):
                    processor.set_detect_interval(2)
                    print("检测间隔: 每2帧检测")
                elif key == ord('3'):
                    processor.set_detect_interval(3)
                    print("检测间隔: 每3帧检测")
                elif key == ord('4'):
                    processor.set_detect_interval(4)
                    print("检测间隔: 每4帧检测")
                elif key == ord('a'):
                    status = processor.toggle_anomaly()
                    print(f"异常检测: {'开启' if status else '关闭'}")
                elif key == ord('c'):
                    status = processor.toggle_cross_camera()
                    print(f"跨摄像头跟踪: {'开启' if status else '关闭'}")
                elif key == ord('m'):
                    status = processor.toggle_metrics()
                    print(f"评估仪表板: {'开启' if status else '关闭'}")

    except KeyboardInterrupt:
        print("\n用户中断，正在停止...")
    finally:
        if txt_file:
            txt_file.close()
            print(f"检测结果已保存到: {txt_path}")

        if args.output:
            print(f"输出视频已保存到: {args.output}")

        if not args.no_display:
            cv2.destroyAllWindows()

        print(f"处理完成，共处理 {frame_count} 帧")


def main():
    args = parse_args()

    print("=" * 60)
    print("  视频目标检测与跟踪系统 - YOLOv8 + DeepSORT")
    print("=" * 60)
    print(f"  输入源: {args.source}")
    print(f"  输出文件: {args.output or '不保存'}")
    print(f"  置信度阈值: {args.conf or Config.YOLO_CONF}")
    print(f"  设备: {args.device or '自动检测'}")
    print(f"  检测类别: {args.classes or '所有类别'}")
    print(f"  跳帧检测: {'关闭' if args.no_skip_frame else '开启 (每' + str(args.detect_interval or Config.DETECT_INTERVAL) + '帧)'}")
    print(f"  运动插值: {'关闭' if args.no_interpolation else '开启'}")
    print(f"  高分辨率分支: {'关闭' if args.no_high_res else '开启'}")
    print(f"  异常检测: {'关闭' if args.no_anomaly else '开启'}")
    print(f"  跨摄像头跟踪: {'关闭' if args.no_cross_camera else '开启'}")
    print(f"  评估仪表板: {'关闭' if args.no_metrics else '开启'}")
    print(f"  摄像头ID: {args.camera_id}")
    print("=" * 60)
    print("  操作说明:")
    print("    q - 退出")
    print("    p - 暂停")
    print("    r - 重置跟踪器")
    print("    s - 切换跳帧检测")
    print("    h - 切换高分辨率分支")
    print("    a - 切换异常检测")
    print("    c - 切换跨摄像头跟踪")
    print("    m - 切换评估仪表板")
    print("    1/2/3/4 - 设置检测间隔 (每1/2/3/4帧)")
    print("=" * 60)

    try:
        run_detection(args)
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
