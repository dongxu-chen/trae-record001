import sys
import os
import numpy as np
import cv2
from typing import List, Dict, Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.action_recognition import ActionRecognizer, ACTION_LIST
from utils.avatar import Avatar, AvatarVisualizer, RealTimeAvatarDriver
from utils.pose_scoring import PoseScorer, PoseScoreResult, compute_all_joint_angles
from models.smpl import SMPL


def generate_synthetic_pose_sequence(num_frames: int = 100, num_joints: int = 24) -> np.ndarray:
    sequence = []
    
    base_pose = np.zeros((num_joints, 3))
    
    base_pose[0] = [0, 0, 0]
    base_pose[1] = [0.3, -0.3, 0]
    base_pose[2] = [-0.3, -0.3, 0]
    base_pose[3] = [0, 0.5, 0]
    base_pose[4] = [0.3, -0.7, 0]
    base_pose[5] = [-0.3, -0.7, 0]
    base_pose[6] = [0, 0.9, 0]
    base_pose[7] = [0.3, -1.0, 0]
    base_pose[8] = [-0.3, -1.0, 0]
    base_pose[9] = [0, 1.3, 0]
    base_pose[10] = [0.3, -1.05, 0.1]
    base_pose[11] = [-0.3, -1.05, 0.1]
    base_pose[12] = [0, 1.6, 0]
    base_pose[13] = [0.2, 1.4, 0]
    base_pose[14] = [-0.2, 1.4, 0]
    base_pose[15] = [0, 1.75, 0]
    base_pose[16] = [0.3, 1.4, 0]
    base_pose[17] = [-0.3, 1.4, 0]
    base_pose[18] = [0.6, 1.2, 0]
    base_pose[19] = [-0.6, 1.2, 0]
    base_pose[20] = [0.8, 1.0, 0]
    base_pose[21] = [-0.8, 1.0, 0]
    base_pose[22] = [0.9, 0.95, 0.05]
    base_pose[23] = [-0.9, 0.95, 0.05]
    
    for i in range(num_frames):
        t = i / num_frames
        pose = base_pose.copy()
        
        angle = t * np.pi * 4
        pose[16, 1] = 1.4 + 0.3 * np.sin(angle)
        pose[18, 1] = 1.2 + 0.5 * np.sin(angle)
        pose[20, 1] = 1.0 + 0.6 * np.sin(angle)
        pose[22, 1] = 0.95 + 0.5 * np.sin(angle)
        
        pose[17, 1] = 1.4 + 0.3 * np.sin(angle + np.pi)
        pose[19, 1] = 1.2 + 0.5 * np.sin(angle + np.pi)
        pose[21, 1] = 1.0 + 0.6 * np.sin(angle + np.pi)
        pose[23, 1] = 0.95 + 0.5 * np.sin(angle + np.pi)
        
        noise = np.random.normal(0, 0.005, pose.shape)
        pose += noise
        
        sequence.append(pose)
    
    return np.array(sequence)


def generate_squat_sequence(num_frames: int = 60, num_joints: int = 24) -> np.ndarray:
    sequence = []
    
    for i in range(num_frames):
        t = i / (num_frames - 1)
        squat_depth = np.sin(t * np.pi)
        
        pose = np.zeros((num_joints, 3))
        
        hip_height = 0.8 - squat_depth * 0.4
        
        pose[0] = [0, hip_height, 0]
        pose[1] = [0.15, hip_height - 0.2, 0]
        pose[2] = [-0.15, hip_height - 0.2, 0]
        pose[3] = [0, hip_height + 0.3, 0]
        
        knee_bend = 40 + squat_depth * 50
        knee_y = hip_height - 0.2 - 0.4 * (1 - squat_depth)
        pose[4] = [0.15, knee_y, 0]
        pose[5] = [-0.15, knee_y, 0]
        
        pose[6] = [0, hip_height + 0.6, 0]
        pose[7] = [0.15, knee_y - 0.4, 0.05]
        pose[8] = [-0.15, knee_y - 0.4, 0.05]
        pose[9] = [0, hip_height + 0.9, 0]
        pose[10] = [0.15, knee_y - 0.42, 0.1]
        pose[11] = [-0.15, knee_y - 0.42, 0.1]
        pose[12] = [0, hip_height + 1.1, 0]
        pose[13] = [0.1, hip_height + 0.95, 0]
        pose[14] = [-0.1, hip_height + 0.95, 0]
        pose[15] = [0, hip_height + 1.2, 0]
        
        arm_forward = squat_depth * 0.3
        pose[16] = [0.2 + arm_forward, hip_height + 0.9, 0]
        pose[17] = [-0.2 - arm_forward, hip_height + 0.9, 0]
        pose[18] = [0.4 + arm_forward * 1.5, hip_height + 0.7, 0]
        pose[19] = [-0.4 - arm_forward * 1.5, hip_height + 0.7, 0]
        pose[20] = [0.5 + arm_forward * 2, hip_height + 0.55, 0]
        pose[21] = [-0.5 - arm_forward * 2, hip_height + 0.55, 0]
        pose[22] = [0.52 + arm_forward * 2, hip_height + 0.52, 0.03]
        pose[23] = [-0.52 - arm_forward * 2, hip_height + 0.52, 0.03]
        
        noise = np.random.normal(0, 0.008, pose.shape)
        pose += noise
        
        sequence.append(pose)
    
    return np.array(sequence)


def test_action_recognition():
    print("\n" + "="*60)
    print("测试1: 动作识别模块")
    print("="*60)
    
    recognizer = ActionRecognizer(
        num_joints=24,
        num_classes=15,
        sequence_length=30,
        overlap=15,
        device='cpu'
    )
    
    print(f"\n支持的动作类别 ({len(ACTION_LIST)} 种):")
    for i, action in enumerate(ACTION_LIST):
        print(f"  [{i}] {action}")
    
    print("\n生成合成姿态序列...")
    sequence = generate_synthetic_pose_sequence(num_frames=100, num_joints=24)
    print(f"序列长度: {len(sequence)} 帧")
    
    print("\n实时识别中...")
    results = []
    for i, pose in enumerate(sequence):
        result = recognizer.update_pose(track_id=0, joints_3d=pose)
        if result is not None:
            results.append(result)
            if len(results) <= 5 or i % 20 == 0:
                print(f"  帧 {i}: 动作={result.action_name} (置信度={result.confidence:.3f})")
    
    if len(results) > 0:
        print(f"\n识别结果统计:")
        action_counts = {}
        for r in results:
            action_counts[r.action_name] = action_counts.get(r.action_name, 0) + 1
        for action, count in sorted(action_counts.items(), key=lambda x: -x[1]):
            print(f"  {action}: {count} 次")
    
    recognizer.reset()
    print("\n[OK] 动作识别模块测试通过!")
    return True


def test_avatar_driver():
    print("\n" + "="*60)
    print("测试2: Avatar驱动模块")
    print("="*60)
    
    avatar = Avatar(name="TestAvatar", num_joints=24)
    print(f"\nAvatar名称: {avatar.name}")
    print(f"关节数量: {avatar.num_joints}")
    print(f"骨骼数量: {len(avatar.SMPL_SKELETON)}")
    
    print("\n关节名称:")
    for i, name in enumerate(avatar.JOINT_NAMES):
        print(f"  [{i}] {name}")
    
    visualizer = AvatarVisualizer()
    
    print("\n生成合成姿态序列...")
    sequence = generate_synthetic_pose_sequence(num_frames=30, num_joints=24)
    
    print("\n驱动Avatar...")
    frames = []
    for i, pose in enumerate(sequence):
        frame = avatar.update_pose(pose)
        frames.append(frame)
        
        if i == 0 or i == 14 or i == 29:
            print(f"  帧 {i}:")
            print(f"    根关节位置: {frame.pose.root_translation}")
            print(f"    骨骼数量: {len(frame.pose.bones)}")
            print(f"    旋转矩阵数量: {len(frame.pose.rotation_matrices)}")
            
            head_rot = avatar.get_joint_rotation('Head')
            if head_rot is not None:
                print(f"    头部旋转矩阵:\n{head_rot}")
    
    print(f"\n动画历史长度: {len(avatar.animation_history)}")
    
    driver = RealTimeAvatarDriver(num_joints=24, device='cpu')
    print("\n实时驱动测试:")
    for i, pose in enumerate(sequence[:5]):
        frame = driver.update(pose)
        print(f"  帧 {i}: 动作={frame.action_name}, 根位置={frame.pose.root_translation[:2]}")
    
    try:
        print("\n渲染Avatar...")
        img = driver.render(frames[0])
        print(f"  渲染图像尺寸: {img.shape}")
        
        output_path = "test_avatar_render.png"
        cv2.imwrite(output_path, img)
        print(f"  渲染图像已保存: {output_path}")
    except Exception as e:
        print(f"  渲染跳过 (需要显示环境): {e}")
    
    driver.close()
    print("\n[OK] Avatar驱动模块测试通过!")
    return True


def test_pose_scoring():
    print("\n" + "="*60)
    print("测试3: 姿态评分模块")
    print("="*60)
    
    scorer = PoseScorer()
    print(f"\n可用模板数量: {len(scorer.templates)}")
    for template in scorer.templates:
        print(f"  - {template.name}: {template.description}")
        print(f"    定义的关节角度: {list(template.joint_angles.keys())}")
    
    print("\n生成深蹲动作序列...")
    sequence = generate_squat_sequence(num_frames=60, num_joints=24)
    print(f"序列长度: {len(sequence)} 帧")
    
    print("\n关节角度计算测试:")
    angles = compute_all_joint_angles(sequence[0])
    print("  第一帧关节角度:")
    for name, value in list(angles.items())[:8]:
        print(f"    {name}: {value:.1f}°")
    
    print("\n实时姿态评分...")
    scores = []
    for i, pose in enumerate(sequence):
        try:
            result = scorer.score_pose(pose, action_name="深蹲")
            scores.append(result)
            
            if i % 10 == 0 or i == len(sequence) - 1:
                print(f"\n  帧 {i}:")
                print(f"    总分: {result.overall_score:.1f} ({result.get_level().value})")
                print(f"    模板匹配: {result.template_match_score:.1f}")
                print(f"    时序评分: {result.temporal_score:.1f}")
                
                print(f"    关键角度:")
                for angle_name in ['Left_Knee_Angle', 'Right_Knee_Angle', 'Back_Lean_Angle']:
                    if angle_name in result.angle_scores:
                        a = result.angle_scores[angle_name]
                        target_str = f", 目标={a.target:.1f}" if a.target else ""
                        print(f"      {angle_name}: {a.value:.1f}°{target_str}, 得分={a.score:.1f}")
                
                print(f"    对称性评分:")
                for sym_name, sym in result.symmetry_scores.items():
                    print(f"      {sym_name}: {sym.score:.1f} (左 {sym.left_value:.1f}° / 右 {sym.right_value:.1f}°)")
                
                print(f"    反馈:")
                for fb in result.feedback[:3]:
                    print(f"      {fb}")
        except Exception as e:
            print(f"  帧 {i} 评分错误: {e}")
    
    if len(scores) > 0:
        print(f"\n评分统计:")
        avg_score = scorer.get_average_score()
        print(f"  平均总分: {avg_score:.1f}")
        
        all_scores = [s.overall_score for s in scores]
        print(f"  最高分: {max(all_scores):.1f}")
        print(f"  最低分: {min(all_scores):.1f}")
        print(f"  评分历史长度: {len(scorer.get_score_history())}")
        
        print("\nJSON输出示例:")
        print(scores[-1].to_json()[:500] + "...")
    
    scorer.reset()
    print("\n[OK] 姿态评分模块测试通过!")
    return True


def test_integration():
    print("\n" + "="*60)
    print("测试4: 三模块集成测试")
    print("="*60)
    
    recognizer = ActionRecognizer(num_joints=24, num_classes=15, sequence_length=20, overlap=10)
    avatar_driver = RealTimeAvatarDriver(num_joints=24)
    scorer = PoseScorer()
    
    print("\n生成测试序列...")
    sequence = generate_squat_sequence(num_frames=50, num_joints=24)
    
    print("\n集成处理...")
    for i, pose in enumerate(sequence):
        action_result = recognizer.update_pose(track_id=0, joints_3d=pose)
        
        action_name = action_result.action_name if action_result else None
        avatar_frame = avatar_driver.update(pose, action_name=action_name)
        
        try:
            score_result = scorer.score_pose(pose, action_name=action_name)
        except:
            score_result = None
        
        if i % 10 == 0:
            print(f"\n  帧 {i}:")
            print(f"    动作识别: {action_result.action_name if action_result else '等待...'} "
                  f"({action_result.confidence:.2f} if action_result else 'N/A')")
            print(f"    Avatar: {avatar_frame.action_name}")
            print(f"    姿态评分: {score_result.overall_score:.1f} ({score_result.get_level().value})" if score_result else "    姿态评分: N/A")
    
    recognizer.reset()
    avatar_driver.close()
    scorer.reset()
    
    print("\n[OK] 三模块集成测试通过!")
    return True


def main():
    print("\n" + "#"*60)
    print("#  第三阶段功能测试 - 动作识别 + Avatar驱动 + 姿态评分  #")
    print("#"*60)
    
    results = {}
    
    try:
        results['action_recognition'] = test_action_recognition()
    except Exception as e:
        print(f"\n[错误] 动作识别测试失败: {e}")
        import traceback
        traceback.print_exc()
        results['action_recognition'] = False
    
    try:
        results['avatar_driver'] = test_avatar_driver()
    except Exception as e:
        print(f"\n[错误] Avatar驱动测试失败: {e}")
        import traceback
        traceback.print_exc()
        results['avatar_driver'] = False
    
    try:
        results['pose_scoring'] = test_pose_scoring()
    except Exception as e:
        print(f"\n[错误] 姿态评分测试失败: {e}")
        import traceback
        traceback.print_exc()
        results['pose_scoring'] = False
    
    try:
        results['integration'] = test_integration()
    except Exception as e:
        print(f"\n[错误] 集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        results['integration'] = False
    
    print("\n" + "="*60)
    print("测试总结:")
    print("="*60)
    for test_name, passed in results.items():
        status = "[OK]" if passed else "[FAIL]"
        print(f"  {status} {test_name}")
    
    all_passed = all(results.values())
    if all_passed:
        print("\n🎉 所有测试通过!")
    else:
        print(f"\n⚠️  部分测试失败，请检查错误信息。")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
