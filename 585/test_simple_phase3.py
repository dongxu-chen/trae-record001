import sys
import os
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test1_action_recognition():
    print("Test 1: Action Recognition")
    from utils.action_recognition import ActionRecognizer, ACTION_LIST
    rec = ActionRecognizer(num_joints=24, sequence_length=10)
    pose = np.random.randn(24, 3)
    
    for i in range(15):
        result = rec.update_pose(0, pose + np.random.randn(24, 3) * 0.01)
        if result:
            print(f"  Frame {i}: {result.action_name} ({result.confidence:.2f})")
    
    print(f"  ACTION_LIST has {len(ACTION_LIST)} actions")
    rec.reset()
    print("  [PASS]\n")
    return True

def test2_avatar():
    print("Test 2: Avatar Driver")
    from utils.avatar import Avatar, RealTimeAvatarDriver
    avatar = Avatar(num_joints=24)
    driver = RealTimeAvatarDriver(num_joints=24)
    
    pose = np.random.randn(24, 3)
    for i in range(5):
        frame = driver.update(pose + np.random.randn(24, 3) * 0.01)
        print(f"  Frame {i}: action={frame.action_name}, root={frame.pose.root_translation[:2]}")
    
    driver.close()
    print(f"  Joint names: {avatar.JOINT_NAMES[:5]}...")
    print("  [PASS]\n")
    return True

def test3_pose_scoring():
    print("Test 3: Pose Scoring")
    from utils.pose_scoring import PoseScorer, compute_all_joint_angles
    
    scorer = PoseScorer()
    print(f"  Templates: {[t.name for t in scorer.templates]}")
    
    pose = np.zeros((24, 3))
    pose[0] = [0, 0.8, 0]
    pose[1] = [0.15, 0.6, 0]; pose[2] = [-0.15, 0.6, 0]
    pose[3] = [0, 1.1, 0]; pose[4] = [0.15, 0.3, 0]; pose[5] = [-0.15, 0.3, 0]
    pose[6] = [0, 1.4, 0]; pose[7] = [0.15, 0.0, 0]; pose[8] = [-0.15, 0.0, 0]
    pose[9] = [0, 1.7, 0]; pose[10] = [0.15, -0.05, 0.1]; pose[11] = [-0.15, -0.05, 0.1]
    pose[12] = [0, 1.9, 0]; pose[13] = [0.1, 1.75, 0]; pose[14] = [-0.1, 1.75, 0]
    pose[15] = [0, 2.0, 0]; pose[16] = [0.2, 1.7, 0]; pose[17] = [-0.2, 1.7, 0]
    pose[18] = [0.4, 1.5, 0]; pose[19] = [-0.4, 1.5, 0]
    pose[20] = [0.5, 1.35, 0]; pose[21] = [-0.5, 1.35, 0]
    pose[22] = [0.52, 1.32, 0.03]; pose[23] = [-0.52, 1.32, 0.03]
    
    angles = compute_all_joint_angles(pose)
    print(f"  Computed {len(angles)} joint angles")
    for k, v in list(angles.items())[:5]:
        print(f"    {k}: {v:.1f}°")
    
    for i in range(5):
        score = scorer.score_pose(pose, action_name="深蹲")
        if i == 0:
            print(f"  Score: {score.overall_score:.1f} ({score.get_level().value})")
            print(f"  Feedback: {score.feedback[:2]}")
    
    scorer.reset()
    print("  [PASS]\n")
    return True

def test4_pipeline():
    print("Test 4: Pipeline Integration")
    from pipeline.estimator import PersonResult, FrameResult
    
    joints = np.random.randn(24, 3)
    result = PersonResult(
        track_id=0,
        joints_3d=joints,
        betas=np.zeros(10),
        pose=np.zeros(72),
        camera=np.zeros(3),
        reprojection_error=0.0,
        bbox=(0, 0, 100, 100)
    )
    
    print(f"  PersonResult fields: track_id={result.track_id}, joints shape={result.joints_3d.shape}")
    print(f"  Has new fields: action_result={result.action_result}, avatar_frame={result.avatar_frame}, pose_score={result.pose_score}")
    print("  [PASS]\n")
    return True

def main():
    print("="*60)
    print("Phase 3 Simple Unit Tests")
    print("="*60 + "\n")
    
    all_pass = True
    for test in [test1_action_recognition, test2_avatar, test3_pose_scoring, test4_pipeline]:
        try:
            if not test():
                all_pass = False
        except Exception as e:
            print(f"  [FAIL] {e}\n")
            import traceback
            traceback.print_exc()
            all_pass = False
    
    print("="*60)
    if all_pass:
        print("ALL TESTS PASSED!")
    else:
        print("SOME TESTS FAILED!")
    print("="*60)
    
    return 0 if all_pass else 1

if __name__ == "__main__":
    sys.exit(main())
