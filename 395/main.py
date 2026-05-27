import argparse
import os
import sys
import cv2
from panorama_stitcher import PanoramaStitcher
from panorama_gui import run_gui
from camera_calibration import CameraCalibrator
from equirectangular import Panorama360Stitcher
from video_stitcher import VideoPanoramaStitcher


def main():
    parser = argparse.ArgumentParser(
        description='全景图拼接工具 - Panorama Stitching Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例用法:
  启动GUI界面:      python main.py
  命令行拼接:        python main.py --images img1.jpg img2.jpg img3.jpg --output panorama.jpg
  柱面投影拼接:      python main.py --images *.jpg --projection cylindrical --blend multiband
  360度全景拼接:     python main.py --mode 360 --images *.jpg --fov 60
  视频拼接:          python main.py --mode video --video input.mp4 --output panorama.jpg
  相机标定:          python main.py --mode calibrate --calib-images calib/*.jpg
  视频转全景视频:    python main.py --mode video-to-video --video input.mp4 --output output.mp4
        '''
    )
    
    parser.add_argument('--mode', default='image',
                        choices=['image', '360', 'video', 'calibrate', 'video-to-video'],
                        help='运行模式: image(图像拼接), 360(360度全景), video(视频拼接), calibrate(相机标定)')
    parser.add_argument('--gui', action='store_true', default=True,
                        help='启动GUI界面 (默认)')
    parser.add_argument('--no-gui', action='store_true',
                        help='禁用GUI，使用命令行模式')
    
    parser.add_argument('--images', nargs='+',
                        help='输入图像文件路径列表')
    parser.add_argument('--output', default='panorama.jpg',
                        help='输出全景图文件路径 (默认: panorama.jpg)')
    
    parser.add_argument('--projection', default='plane',
                        choices=['plane', 'cylindrical', 'spherical', 'equirectangular'],
                        help='投影方式: plane(平面), cylindrical(柱面), spherical(球面), equirectangular(等距柱状)')
    parser.add_argument('--blend', default='multiband',
                        choices=['multiband', 'feather', 'simple'],
                        help='融合方式: multiband(多波段), feather(羽化), simple(简单)')
    parser.add_argument('--no-crop', action='store_true',
                        help='不自动裁剪黑边')
    parser.add_argument('--show', action='store_true',
                        help='拼接完成后显示结果')
    
    parser.add_argument('--block-stitching', action='store_true', default=True,
                        help='启用大图分块拼接 (默认)')
    parser.add_argument('--block-size', type=int, default=2000,
                        help='分块大小 (默认: 2000)')
    parser.add_argument('--block-overlap', type=int, default=200,
                        help='分块重叠区域大小 (默认: 200)')
    
    parser.add_argument('--fov', type=float, default=90,
                        help='360度模式的视场角 (默认: 90)')
    parser.add_argument('--output-width', type=int, default=4096,
                        help='360度全景输出宽度 (默认: 4096)')
    
    parser.add_argument('--video', type=str,
                        help='视频文件路径')
    parser.add_argument('--frame-interval', type=int, default=1,
                        help='视频帧提取间隔 (默认: 1)')
    parser.add_argument('--max-frames', type=int, default=None,
                        help='最大提取帧数')
    parser.add_argument('--stabilize', action='store_true', default=True,
                        help='启用视频帧稳定 (默认)')
    parser.add_argument('--window-size', type=int, default=30,
                        help='视频转视频的窗口大小 (默认: 30)')
    parser.add_argument('--step-size', type=int, default=15,
                        help='视频转视频的步长 (默认: 15)')
    
    parser.add_argument('--calib-images', nargs='+',
                        help='标定图像路径列表')
    parser.add_argument('--calib-video', type=str,
                        help='标定视频路径')
    parser.add_argument('--chessboard-size', type=int, nargs=2, default=[9, 6],
                        help='棋盘格尺寸 (默认: 9 6)')
    parser.add_argument('--square-size', type=float, default=1.0,
                        help='棋盘格方块尺寸 (默认: 1.0)')
    parser.add_argument('--save-calib', type=str,
                        help='保存标定参数的文件路径')
    parser.add_argument('--load-calib', type=str,
                        help='加载标定参数的文件路径')
    
    args = parser.parse_args()
    
    if not args.no_gui and not args.images and not args.video and not args.calib_images:
        run_gui()
        return
    
    if args.mode == 'image':
        run_image_mode(args)
    elif args.mode == '360':
        run_360_mode(args)
    elif args.mode == 'video':
        run_video_mode(args)
    elif args.mode == 'video-to-video':
        run_video_to_video_mode(args)
    elif args.mode == 'calibrate':
        run_calibration_mode(args)


def run_image_mode(args):
    if not args.images:
        print('错误: 图像模式需要指定 --images 参数')
        sys.exit(1)
    
    image_paths = []
    for path in args.images:
        if os.path.exists(path):
            image_paths.append(path)
        else:
            print(f'警告: 文件不存在 - {path}')
    
    if len(image_paths) < 2:
        print('错误: 至少需要2张有效图像')
        sys.exit(1)
    
    print(f'加载 {len(image_paths)} 张图像...')
    print(f'投影方式: {args.projection}')
    print(f'融合方式: {args.blend}')
    
    try:
        stitcher = PanoramaStitcher(
            projection_type=args.projection if args.projection != 'equirectangular' else 'cylindrical',
            blend_type=args.blend,
            use_block_stitching=args.block_stitching,
            block_size=args.block_size,
            block_overlap=args.block_overlap
        )
        
        print('正在拼接...')
        panorama = stitcher.stitch(image_paths=image_paths)
        
        if not args.no_crop:
            print('正在裁剪黑边...')
            panorama = stitcher.crop_black_borders(panorama)
        
        cv2.imwrite(args.output, panorama)
        print(f'完成! 结果已保存到: {args.output}')
        print(f'图像尺寸: {panorama.shape[1]} x {panorama.shape[0]}')
        
        if args.show:
            cv2.imshow('Panorama', panorama)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
        
    except Exception as e:
        print(f'错误: {str(e)}')
        import traceback
        traceback.print_exc()
        sys.exit(1)


def run_360_mode(args):
    if not args.images:
        print('错误: 360度模式需要指定 --images 参数')
        sys.exit(1)
    
    image_paths = []
    for path in args.images:
        if os.path.exists(path):
            image_paths.append(path)
        else:
            print(f'警告: 文件不存在 - {path}')
    
    if len(image_paths) == 0:
        print('错误: 没有有效图像')
        sys.exit(1)
    
    print(f'加载 {len(image_paths)} 张图像...')
    
    try:
        images = [cv2.imread(p) for p in image_paths]
        
        stitcher_360 = Panorama360Stitcher(output_width=args.output_width)
        
        if args.load_calib:
            calibrator = CameraCalibrator()
            calibrator.load_calibration(args.load_calib)
            stitcher_360.set_calibration(calibrator.camera_matrix, calibrator.dist_coeffs)
        else:
            calibrator = CameraCalibrator()
            calibrator.auto_calibrate_from_scene(images, verbose=True)
            stitcher_360.set_calibration(calibrator.camera_matrix, calibrator.dist_coeffs)
        
        angles = [i * 360.0 / len(images) for i in range(len(images))]
        
        print('正在生成360度全景...')
        panorama = stitcher_360.stitch_360(images, angles=angles, fov=args.fov)
        panorama = stitcher_360.blend_360_seams(panorama, num_views=len(images))
        
        cv2.imwrite(args.output, panorama)
        print(f'完成! 结果已保存到: {args.output}')
        print(f'图像尺寸: {panorama.shape[1]} x {panorama.shape[0]}')
        
        if args.show:
            preview = stitcher_360.generate_360_preview(panorama)
            cv2.imshow('360 Panorama', preview)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
        
    except Exception as e:
        print(f'错误: {str(e)}')
        import traceback
        traceback.print_exc()
        sys.exit(1)


def run_video_mode(args):
    if not args.video:
        print('错误: 视频模式需要指定 --video 参数')
        sys.exit(1)
    
    if not os.path.exists(args.video):
        print(f'错误: 视频文件不存在 - {args.video}')
        sys.exit(1)
    
    print(f'处理视频: {args.video}')
    
    try:
        video_stitcher = VideoPanoramaStitcher(
            projection_type=args.projection if args.projection != 'equirectangular' else 'cylindrical',
            blend_type=args.blend
        )
        
        info = video_stitcher.get_video_info(args.video)
        print(f'视频信息: {info["width"]}x{info["height"]}, {info["fps"]:.2f}fps, {info["duration"]:.1f}秒')
        
        print('提取帧...')
        frames = video_stitcher.extract_frames(
            args.video,
            max_frames=args.max_frames,
            frame_interval=args.frame_interval
        )
        
        print(f'提取了 {len(frames)} 帧')
        
        print('正在拼接...')
        panorama = video_stitcher.stitch_video_frames(
            frames,
            output_path=args.output,
            stabilize=args.stabilize
        )
        
        if not args.no_crop:
            print('正在裁剪黑边...')
            stitcher = PanoramaStitcher()
            panorama = stitcher.crop_black_borders(panorama)
            cv2.imwrite(args.output, panorama)
        
        print(f'完成! 结果已保存到: {args.output}')
        
        if args.show:
            cv2.imshow('Video Panorama', panorama)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
        
    except Exception as e:
        print(f'错误: {str(e)}')
        import traceback
        traceback.print_exc()
        sys.exit(1)


def run_video_to_video_mode(args):
    if not args.video:
        print('错误: 视频转视频模式需要指定 --video 参数')
        sys.exit(1)
    
    if not os.path.exists(args.video):
        print(f'错误: 视频文件不存在 - {args.video}')
        sys.exit(1)
    
    output_video = args.output if args.output.endswith('.mp4') else args.output.replace('.jpg', '.mp4')
    
    print(f'视频转全景视频: {args.video} -> {output_video}')
    
    try:
        video_stitcher = VideoPanoramaStitcher(
            projection_type=args.projection if args.projection != 'equirectangular' else 'cylindrical',
            blend_type=args.blend
        )
        
        video_stitcher.stitch_video_to_video(
            args.video,
            output_video,
            window_size=args.window_size,
            step_size=args.step_size
        )
        
        print(f'完成! 结果已保存到: {output_video}')
        
    except Exception as e:
        print(f'错误: {str(e)}')
        import traceback
        traceback.print_exc()
        sys.exit(1)


def run_calibration_mode(args):
    calibrator = CameraCalibrator(
        chessboard_size=tuple(args.chessboard_size),
        square_size=args.square_size
    )
    
    try:
        if args.calib_images:
            image_paths = [p for p in args.calib_images if os.path.exists(p)]
            
            if len(image_paths) < 3:
                print('错误: 至少需要3张标定图像')
                sys.exit(1)
            
            print(f'使用 {len(image_paths)} 张图像进行标定...')
            calibrator.calibrate_from_images(image_paths)
            
        elif args.calib_video:
            if not os.path.exists(args.calib_video):
                print(f'错误: 视频文件不存在 - {args.calib_video}')
                sys.exit(1)
            
            print(f'从视频进行标定: {args.calib_video}')
            calibrator.calibrate_from_chessboard_video(args.calib_video)
            
        else:
            print('错误: 标定模式需要指定 --calib-images 或 --calib-video 参数')
            sys.exit(1)
        
        if args.save_calib:
            calibrator.save_calibration(args.save_calib)
            print(f'标定参数已保存到: {args.save_calib}')
        
    except Exception as e:
        print(f'标定错误: {str(e)}')
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
