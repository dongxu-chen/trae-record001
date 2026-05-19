import os
import sys
import cv2
import numpy as np
import argparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from video_processor import VideoProcessor, TrackedPlate
from plate_blacklist import PlateListManager
from confidence_heatmap import ConfidenceHeatmap
from license_plate_recognition import LicensePlateRecognition


def test_blacklist_manager():
    print("\n" + "="*70)
    print("测试 1: 黑白名单管理功能")
    print("="*70)
    
    manager = PlateListManager(data_file='test_plate_lists.json')
    
    if os.path.exists('test_plate_lists.json'):
        os.remove('test_plate_lists.json')
        manager = PlateListManager(data_file='test_plate_lists.json')
    
    print("\n📋 添加白名单测试:")
    result = manager.add_to_whitelist(
        '京A12345',
        owner='张三',
        vehicle_type='小型汽车',
        description='员工车辆'
    )
    status = "✅ 成功" if result['success'] else f"❌ 失败 - {result['message']}"
    print(f"  添加京A12345: {status}")
    
    result = manager.add_to_whitelist(
        '沪B67890',
        owner='李四',
        vehicle_type='新能源汽车'
    )
    status = "✅ 成功" if result['success'] else f"❌ 失败 - {result['message']}"
    print(f"  添加沪B67890: {status}")
    
    print("\n📋 添加黑名单测试:")
    result = manager.add_to_blacklist(
        '粤C11111',
        reason='欠费车辆',
        level='high',
        description='长期未缴停车费'
    )
    status = "✅ 成功" if result['success'] else f"❌ 失败 - {result['message']}"
    print(f"  添加粤C11111: {status}")
    
    result = manager.add_to_blacklist(
        '川D22222',
        reason='可疑车辆',
        level='medium'
    )
    status = "✅ 成功" if result['success'] else f"❌ 失败 - {result['message']}"
    print(f"  添加川D22222: {status}")
    
    print("\n🔍 车牌检查测试:")
    test_plates = ['京A12345', '沪B67890', '粤C11111', '川D22222', '未知车牌']
    for plate in test_plates:
        result = manager.check_plate(plate)
        status = []
        if result['is_whitelist']:
            status.append('白名单')
        if result['is_blacklist']:
            status.append('黑名单')
        if not status:
            status.append('无记录')
        print(f"  {plate}: {' / '.join(status)}")
    
    print("\n📊 黑白名单告警测试:")
    alert_triggered = []
    def on_alert(alert):
        alert_triggered.append(alert)
        print(f"  🚨 告警触发: {alert['plate_number']} - {alert['reason']} (级别: {alert['level']})")
    
    manager.set_callback('on_alert', on_alert)
    
    print("  检查黑名单车牌...")
    manager.check_and_alert('粤C11111', extra_info={'location': '入口A'})
    manager.check_and_alert('川D22222', extra_info={'location': '出口B'})
    
    print(f"\n📈 统计信息:")
    stats = manager.get_statistics()
    print(f"  白名单总数: {stats['whitelist_total']} (有效: {stats['whitelist_active']})")
    print(f"  黑名单总数: {stats['blacklist_total']} (有效: {stats['blacklist_active']})")
    print(f"  告警总数: {stats['alerts_total']} (未确认: {stats['alerts_unacknowledged']})")
    if stats['alerts_by_level']:
        print(f"  告警级别分布: {stats['alerts_by_level']}")
    
    print("\n📄 告警历史:")
    alerts = manager.get_alert_history(page_size=10)
    for alert in alerts['items']:
        print(f"  - {alert['plate_number']}: {alert['reason']} ({alert['level']}) at {alert['timestamp']}")
    
    print("\n✅ 黑白名单测试完成!")


def test_heatmap_generator():
    print("\n" + "="*70)
    print("测试 2: 置信度热力图生成")
    print("="*70)
    
    heatmap_gen = ConfidenceHeatmap()
    
    print("\n🎨 创建测试图像...")
    test_dir = 'test_heatmap_output'
    os.makedirs(test_dir, exist_ok=True)
    
    test_image = np.ones((400, 600, 3), dtype=np.uint8) * 200
    
    test_plates = [
        {
            'bbox': (50, 50, 200, 60),
            'ocr_text': '京A12345',
            'ocr_confidence': 0.95,
            'detection_confidence': 90.0
        },
        {
            'bbox': (350, 150, 200, 60),
            'ocr_text': '沪B67890',
            'ocr_confidence': 0.65,
            'detection_confidence': 70.0
        },
        {
            'bbox': (150, 280, 200, 60),
            'ocr_text': '粤C11111',
            'ocr_confidence': 0.35,
            'detection_confidence': 45.0
        }
    ]
    
    for i, plate in enumerate(test_plates):
        x, y, w, h = plate['bbox']
        if plate['ocr_confidence'] > 0.8:
            color = (255, 255, 255)
        elif plate['ocr_confidence'] > 0.5:
            color = (180, 180, 180)
        else:
            color = (100, 100, 100)
        cv2.rectangle(test_image, (x, y), (x + w, y + h), color, -1)
        cv2.rectangle(test_image, (x, y), (x + w, y + h), (0, 0, 0), 2)
        cv2.putText(test_image, plate['ocr_text'], (x + 10, y + 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    
    original_path = os.path.join(test_dir, 'test_original.jpg')
    cv2.imwrite(original_path, test_image)
    print(f"  原始测试图: {original_path}")
    
    print("\n🔥 生成热力图...")
    heatmap_result = heatmap_gen.generate_full_image_heatmap(test_image, test_plates)
    
    heatmap_path = os.path.join(test_dir, 'test_heatmap.jpg')
    cv2.imwrite(heatmap_path, heatmap_result)
    print(f"  热力图结果: {heatmap_path}")
    
    print("\n📊 生成质量报告...")
    quality_report = heatmap_gen.generate_quality_report(test_image, test_plates)
    print(f"  平均质量分数: {quality_report['average_quality']:.2f}")
    print(f"  检测车牌数: {quality_report['plate_count']}")
    
    for plate_info in quality_report['plates']:
        print(f"\n  车牌: {plate_info['plate_text']}")
        print(f"    OCR置信度: {plate_info['ocr_confidence']:.2f}")
        print(f"    质量分数: {plate_info['quality_score']:.2f}")
        if plate_info['quality_analysis']:
            print(f"    整体质量: {plate_info['quality_analysis']['overall_quality']}")
            print(f"    问题: {', '.join(plate_info['quality_analysis']['issues'])}")
            if plate_info['quality_analysis']['recommendations']:
                print(f"    建议: {', '.join(plate_info['quality_analysis']['recommendations'])}")
    
    print("\n🎨 生成热力图图例...")
    legend = heatmap_gen.create_heatmap_legend()
    legend_path = os.path.join(test_dir, 'heatmap_legend.png')
    cv2.imwrite(legend_path, legend)
    print(f"  热力图图例: {legend_path}")
    
    print("\n✅ 热力图测试完成!")


def test_video_processor():
    print("\n" + "="*70)
    print("测试 3: 视频流处理与车牌追踪")
    print("="*70)
    
    test_dir = 'test_video_output'
    os.makedirs(test_dir, exist_ok=True)
    
    print("\n🎬 创建模拟测试视频...")
    video_path = os.path.join(test_dir, 'test_simulation.avi')
    
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    fps = 10
    width, height = 640, 480
    writer = cv2.VideoWriter(video_path, fourcc, fps, (width, height))
    
    for frame_id in range(50):
        frame = np.ones((height, width, 3), dtype=np.uint8) * 180
        
        x_base = 50 + frame_id * 10
        y_base = 200
        
        if x_base < width - 200:
            cv2.rectangle(frame, (x_base, y_base), (x_base + 200, y_base + 60), (255, 0, 0), -1)
            cv2.rectangle(frame, (x_base, y_base), (x_base + 200, y_base + 60), (0, 0, 0), 2)
            cv2.putText(frame, '京A12345', (x_base + 20, y_base + 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
        
        writer.write(frame)
    
    writer.release()
    print(f"  测试视频已创建: {video_path}")
    
    print("\n🚗 初始化视频处理器...")
    lpr = LicensePlateRecognition()
    
    video_config = {
        'frame_skip': 2,
        'track_timeout': 3.0,
        'iou_threshold': 0.3,
        'entry_zone': (50, 180, 50, 100),
        'exit_zone': (540, 180, 50, 100)
    }
    
    processor = VideoProcessor(lpr, video_config)
    
    detected_events = []
    def on_plate_detected(track):
        if track.plate_text:
            detected_events.append(('detected', track.plate_text, track.bbox))
    
    def on_entry(record):
        detected_events.append(('entry', record['plate_text'], record['timestamp']))
        print(f"  🚪 进场: {record['plate_text']} at {record['timestamp']}")
    
    def on_exit(record):
        detected_events.append(('exit', record['plate_text'], record['timestamp']))
        print(f"  🚪 出场: {record['plate_text']} at {record['timestamp']}")
    
    processor.set_callback('on_plate_detected', on_plate_detected)
    processor.set_callback('on_entry', on_entry)
    processor.set_callback('on_exit', on_exit)
    
    print("\n📹 处理视频...")
    try:
        frame_count = 0
        for fc, frame, tracks in processor.process_video(video_path, max_frames=50):
            frame_count = fc
            if tracks:
                track_ids = [t.track_id for t in tracks]
                plates = [t.plate_text for t in tracks if t.plate_text]
                if plates:
                    print(f"  帧 {fc}: 追踪 {len(tracks)} 个目标, 车牌: {', '.join(plates)}")
            
            output_frame = frame.copy()
            for track in tracks:
                output_frame = processor.draw_track(output_frame, track)
            
            output_path = os.path.join(test_dir, f'frame_{fc:04d}.jpg')
            if fc % 5 == 0:
                cv2.imwrite(output_path, output_frame)
    except Exception as e:
        print(f"  视频处理提示: {e}")
    finally:
        processor.stop()
    
    print(f"\n📊 处理统计:")
    stats = processor.get_statistics()
    print(f"  处理帧数: {stats['total_frames_processed']}")
    print(f"  活跃追踪: {stats['active_tracks']}")
    print(f"  进场记录: {stats['total_entries']}")
    print(f"  出场记录: {stats['total_exits']}")
    print(f"  唯一车牌: {stats['unique_plates']}")
    
    print(f"\n📄 进出场记录:")
    records = processor.get_entry_exit_records()
    for record in records:
        print(f"  {record['type'].upper()}: {record['plate_text']} at {record['timestamp']} (方向: {record['direction']})")
    
    print("\n✅ 视频流处理测试完成!")


def test_iou_calculation():
    print("\n" + "="*70)
    print("测试 4: IOU计算与车牌匹配")
    print("="*70)
    
    lpr = LicensePlateRecognition()
    processor = VideoProcessor(lpr)
    
    test_cases = [
        ((50, 50, 100, 50), (60, 55, 100, 50), "高重叠"),
        ((50, 50, 100, 50), (160, 50, 100, 50), "相邻"),
        ((50, 50, 100, 50), (50, 120, 100, 50), "上下分离"),
        ((50, 50, 100, 50), (75, 75, 100, 50), "部分重叠"),
    ]
    
    for bbox1, bbox2, desc in test_cases:
        iou = processor.calculate_iou(bbox1, bbox2)
        print(f"  {desc}: IOU = {iou:.3f}")
    
    print("\n✅ IOU计算测试完成!")


def test_full_integration():
    print("\n" + "="*70)
    print("测试 5: 完整功能集成测试")
    print("="*70)
    
    print("\n🚀 初始化完整系统...")
    lpr = LicensePlateRecognition()
    
    print("\n📋 设置黑白名单...")
    lpr.add_to_whitelist('京A12345', owner='测试用户', vehicle_type='测试车')
    lpr.add_to_blacklist('粤C11111', reason='测试黑名单', level='high')
    
    print("\n🖼️ 创建测试图像...")
    test_image = np.ones((400, 600, 3), dtype=np.uint8) * 200
    cv2.rectangle(test_image, (100, 150), (300, 210), (255, 0, 0), -1)
    cv2.rectangle(test_image, (100, 150), (300, 210), (0, 0, 0), 2)
    cv2.putText(test_image, '京A12345', (120, 190),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
    
    test_dir = 'test_integration'
    os.makedirs(test_dir, exist_ok=True)
    test_path = os.path.join(test_dir, 'integration_test.jpg')
    cv2.imwrite(test_path, test_image)
    
    print("\n🔍 执行完整识别（带热力图和黑白名单检查）...")
    result = lpr.recognize(
        image_data=cv2.imencode('.jpg', test_image)[1].tobytes(),
        save_images=True,
        generate_heatmap=True,
        check_blacklist=True
    )
    
    if 'error' in result:
        print(f"❌ 识别失败: {result['error']}")
    else:
        print(f"  识别成功: {result['success']}")
        print(f"  检测车牌数: {result['plate_count']}")
        
        for plate in result['results']:
            print(f"\n  车牌: {plate.get('ocr_text', '未识别')}")
            print(f"    OCR置信度: {plate.get('ocr_confidence', 0):.2f}")
            print(f"    黑白名单检查: {plate.get('blacklist_check', {}).get('match_type', 'none')}")
            
            if plate.get('blacklist_check', {}).get('is_whitelist'):
                print(f"    ✅ 在白名单中")
            if plate.get('blacklist_check', {}).get('is_blacklist'):
                print(f"    ❌ 在黑名单中")
        
        if result.get('heatmap_report'):
            print(f"\n🔥 热力图报告:")
            print(f"  平均质量: {result['heatmap_report']['average_quality']:.2f}")
            for plate_info in result['heatmap_report']['plates']:
                if plate_info.get('quality_analysis'):
                    print(f"  {plate_info['plate_text']}: {plate_info['quality_analysis']['overall_quality']}")
    
    print("\n📊 系统信息:")
    info = lpr.get_system_info()
    print(f"  可用模块: {[k for k, v in info['modules'].items() if v]}")
    print(f"  功能特性: {len(info['features'])} 项")
    
    print("\n✅ 完整功能集成测试完成!")


def main():
    parser = argparse.ArgumentParser(description='新功能综合测试')
    parser.add_argument('--test-blacklist', action='store_true', help='测试黑白名单功能')
    parser.add_argument('--test-heatmap', action='store_true', help='测试热力图功能')
    parser.add_argument('--test-video', action='store_true', help='测试视频流功能')
    parser.add_argument('--test-iou', action='store_true', help='测试IOU计算')
    parser.add_argument('--test-all', action='store_true', help='运行所有测试')
    
    args = parser.parse_args()
    
    print("🚗 车牌识别系统 - 新功能综合测试")
    print(f"⏰ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if args.test_all or args.test_blacklist:
        test_blacklist_manager()
    
    if args.test_all or args.test_heatmap:
        test_heatmap_generator()
    
    if args.test_all or args.test_video:
        test_video_processor()
    
    if args.test_all or args.test_iou:
        test_iou_calculation()
    
    if args.test_all:
        test_full_integration()
    
    if not any([args.test_blacklist, args.test_heatmap, args.test_video, args.test_iou, args.test_all]):
        print("\nℹ️  请指定要运行的测试:")
        print("   python test_new_features.py --test-blacklist")
        print("   python test_new_features.py --test-heatmap")
        print("   python test_new_features.py --test-video")
        print("   python test_new_features.py --test-iou")
        print("   python test_new_features.py --test-all")
    
    print("\n" + "="*70)
    print("🎉 所有测试完成!")
    print("="*70)


if __name__ == '__main__':
    main()
