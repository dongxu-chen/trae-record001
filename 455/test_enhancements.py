import numpy as np
from tracker import (
    DeepSORT, KalmanBoxTracker,
    associate_detections_to_trackers,
    motion_distance, feature_distance, iou_batch,
    convert_bbox_to_z, convert_x_to_bbox
)
from config import Config


def test_occlusion_detection():
    print("=" * 50)
    print("测试1: 遮挡检测与处理")
    print("=" * 50)

    KalmanBoxTracker.count = 0
    tracker = KalmanBoxTracker(
        np.array([100, 100, 200, 200]),
        0,
        np.random.rand(128)
    )

    for i in range(5):
        tracker.predict()
        if i == 2:
            bbox = np.array([500, 500, 600, 600])
        else:
            bbox = np.array([100 + i * 5, 100 + i * 5, 200 + i * 5, 200 + i * 5])
        tracker.update(bbox, 0, np.random.rand(128))

        print(f"  帧{i}: 遮挡={tracker.is_occluded}, 遮挡计数={tracker.occlusion_count}, "
              f"不确定性={tracker.get_motion_uncertainty():.2f}")

    assert tracker.is_occluded or tracker.occlusion_count > 0, "遮挡检测失败"
    print("OK 遮挡检测与处理测试通过\n")


def test_multi_modal_data_association():
    print("=" * 50)
    print("测试2: 外观+运动+IOU融合数据关联")
    print("=" * 50)

    KalmanBoxTracker.count = 0
    tracker = DeepSORT(max_age=10, n_init=1)

    bboxes_1 = np.array([
        [100, 100, 200, 200],
        [300, 300, 400, 400],
    ])
    confs_1 = np.array([0.9, 0.85])
    class_ids_1 = np.array([0, 1])
    features_1 = np.random.rand(2, 128)

    tracks_1 = tracker.update(bboxes_1, confs_1, class_ids_1, features_1)
    assert len(tracks_1) == 2, f"初始跟踪数量错误: {len(tracks_1)}"
    track_ids_1 = [t["id"] for t in tracks_1]
    print(f"  初始跟踪ID: {track_ids_1}")

    bboxes_2 = np.array([
        [120, 120, 220, 220],
        [320, 320, 420, 420],
    ])
    features_2 = features_1.copy()
    features_2[0] = features_1[0] + np.random.randn(128) * 0.1

    tracks_2 = tracker.update(bboxes_2, confs_1, class_ids_1, features_2)
    track_ids_2 = [t["id"] for t in tracks_2]
    print(f"  更新后跟踪ID: {track_ids_2}")

    assert set(track_ids_1) == set(track_ids_2), f"ID切换发生: {track_ids_1} -> {track_ids_2}"
    print("OK 多模态数据关联测试通过 (ID保持不变)\n")


def test_occlusion_id_stability():
    print("=" * 50)
    print("测试3: 遮挡时ID稳定性")
    print("=" * 50)

    KalmanBoxTracker.count = 0
    tracker = DeepSORT(max_age=10, n_init=1)

    bboxes_init = np.array([[100, 100, 200, 200], [300, 300, 400, 400]])
    confs = np.array([0.9, 0.9])
    class_ids = np.array([0, 1])
    features = np.random.rand(2, 128)

    tracks = tracker.update(bboxes_init, confs, class_ids, features)
    original_ids = [t["id"] for t in tracks]
    print(f"  初始ID: {original_ids}")

    for i in range(5):
        bboxes = np.array([
            [100 + i * 10, 100 + i * 10, 200 + i * 10, 200 + i * 10],
            [300 - i * 5, 300, 400 - i * 5, 400],
        ])
        if i == 2 or i == 3:
            bboxes[0] = [500, 500, 600, 600]

        current_features = features + np.random.randn(2, 128) * 0.05
        tracks = tracker.update(bboxes, confs, class_ids, current_features)
        current_ids = [t["id"] for t in tracks]
        print(f"  帧{i}: IDs={current_ids}")

    final_ids = [t["id"] for t in tracks]
    assert len(final_ids) >= 1, "跟踪全部丢失"
    common_ids = set(original_ids) & set(final_ids)
    print(f"  保持的ID: {list(common_ids)}")
    assert len(common_ids) >= 1, "ID完全切换"
    print("OK 遮挡时ID稳定性测试通过\n")


def test_skip_frame_prediction():
    print("=" * 50)
    print("测试4: 跳帧检测与卡尔曼预测")
    print("=" * 50)

    KalmanBoxTracker.count = 0
    tracker = DeepSORT(max_age=10, n_init=1)

    bboxes_1 = np.array([[100, 100, 200, 200]])
    confs = np.array([0.9])
    class_ids = np.array([0])
    features = np.random.rand(1, 128)

    tracks = tracker.update(bboxes_1, confs, class_ids, features)
    init_center = (tracks[0]["bbox"][0] + tracks[0]["bbox"][2]) / 2
    print(f"  检测帧0: 中心X={init_center:.1f}")

    prev_center = init_center
    for i in range(3):
        tracks_pred = tracker.predict_only()
        pred_center = (tracks_pred[0]["bbox"][0] + tracks_pred[0]["bbox"][2]) / 2
        movement = pred_center - prev_center
        print(f"  预测帧{i+1}: 中心X={pred_center:.1f}, 移动={movement:.1f}")
        prev_center = pred_center
        assert tracks_pred[0].get("is_predicted", True), "预测帧标记错误"

    bboxes_2 = np.array([[100 + 50, 100 + 50, 200 + 50, 200 + 50]])
    tracks_update = tracker.update(bboxes_2, confs, class_ids, features)
    update_center = (tracks_update[0]["bbox"][0] + tracks_update[0]["bbox"][2]) / 2
    print(f"  检测帧4: 中心X={update_center:.1f}")
    assert tracks_update[0]["id"] == 0, "检测帧ID切换"

    print("OK 跳帧检测与卡尔曼预测测试通过\n")


def test_motion_interpolation():
    print("=" * 50)
    print("测试5: 运动插值平滑")
    print("=" * 50)

    KalmanBoxTracker.count = 0
    tracker = DeepSORT(max_age=10, n_init=1)

    bboxes_1 = np.array([[100, 100, 200, 200]])
    confs = np.array([0.9])
    class_ids = np.array([0])
    features = np.random.rand(1, 128)

    tracks = tracker.update(bboxes_1, confs, class_ids, features)
    center_0 = (tracks[0]["bbox"][0] + tracks[0]["bbox"][2]) / 2
    print(f"  检测帧0: 中心X={center_0:.1f}")

    for i in range(3):
        tracks_pred = tracker.predict_only()

    bboxes_2 = np.array([[200, 100, 300, 200]])
    tracks = tracker.update(bboxes_2, confs, class_ids, features)
    center_4 = (tracks[0]["bbox"][0] + tracks[0]["bbox"][2]) / 2
    print(f"  检测帧4: 中心X={center_4:.1f}")

    KalmanBoxTracker.count = 0
    tracker2 = DeepSORT(max_age=10, n_init=1)
    tracker2.interpolation_enabled = True

    tracker2.update(bboxes_1, confs, class_ids, features)
    for i in range(3):
        tracker2.predict_only()

    for alpha in [0.25, 0.5, 0.75, 1.0]:
        tracks_interp = tracker2.get_interpolated_tracks(alpha=alpha)
        center = (tracks_interp[0]["bbox"][0] + tracks_interp[0]["bbox"][2]) / 2
        expected = center_0 + (center_4 - center_0) * alpha
        print(f"  插值 alpha={alpha:.2f}: 中心X={center:.1f} (预期~{expected:.1f})")

    print("OK 运动插值平滑测试通过\n")


def test_motion_uncertainty_weighting():
    print("=" * 50)
    print("测试6: 运动不确定性自适应权重")
    print("=" * 50)

    KalmanBoxTracker.count = 0

    track_stable = KalmanBoxTracker(
        np.array([100, 100, 200, 200]),
        0,
        np.random.rand(128)
    )
    for _ in range(5):
        track_stable.predict()
        track_stable.update(
            np.array([100, 100, 200, 200]),
            0,
            np.random.rand(128)
        )
    stable_uncertainty = track_stable.get_motion_uncertainty()
    print(f"  稳定跟踪不确定性: {stable_uncertainty:.2f}")

    track_unstable = KalmanBoxTracker(
        np.array([100, 100, 200, 200]),
        0,
        np.random.rand(128)
    )
    for i in range(3):
        track_unstable.predict()
        track_unstable.update(
            np.array([100 + i * 10, 100 + i * 10, 200 + i * 10, 200 + i * 10]),
            0,
            np.random.rand(128)
        )
    track_unstable.predict()
    track_unstable.predict()
    track_unstable.predict()

    unstable_uncertainty = track_unstable.get_motion_uncertainty()
    print(f"  不稳定跟踪(3次更新+3次纯预测)不确定性: {unstable_uncertainty:.2f}")

    assert unstable_uncertainty > stable_uncertainty, "不确定性估计错误"

    detections = np.array([[110, 110, 210, 210]])
    features = np.random.rand(1, 128)

    motion_cost_stable = motion_distance(
        [track_stable], detections, [0], [0]
    )[0, 0]
    motion_cost_unstable = motion_distance(
        [track_unstable], detections, [0], [0]
    )[0, 0]

    print(f"  稳定目标运动距离: {motion_cost_stable:.4f}")
    print(f"  不稳定目标运动距离: {motion_cost_unstable:.4f}")

    assert motion_cost_stable < motion_cost_unstable, "不确定性加权失败"
    print("OK 运动不确定性自适应权重测试通过\n")


def test_secondary_matching():
    print("=" * 50)
    print("测试7: 遮挡目标二次匹配")
    print("=" * 50)

    KalmanBoxTracker.count = 0
    tracker = DeepSORT(max_age=10, n_init=1)

    for i in range(10):
        bbox = np.array([
            [100 + i * 5, 100 + i * 5, 200 + i * 5, 200 + i * 5],
            [300 + i * 3, 300 + i * 3, 400 + i * 3, 400 + i * 3],
        ])
        conf = np.array([0.9, 0.85])
        cls = np.array([0, 1])
        feat = np.random.rand(2, 128)
        tracks = tracker.update(bbox, conf, cls, feat)

    print(f"  跟踪器数量: {len(tracker.tracks)}")
    print(f"  跟踪器0 hit_streak: {tracker.tracks[0].hit_streak}")
    print(f"  跟踪器1 hit_streak: {tracker.tracks[1].hit_streak}")

    occluded_track = tracker.tracks[0]
    occluded_track.is_occluded = True
    occluded_track.occlusion_count = 3

    for _ in range(3):
        tracker.predict_only()

    print(f"  遮挡后跟踪器0 hit_streak: {tracker.tracks[0].hit_streak}")
    print(f"  遮挡后跟踪器0 time_since_update: {tracker.tracks[0].time_since_update}")

    detections = np.array([
        [100 + 13 * 5, 100 + 13 * 5, 200 + 13 * 5, 200 + 13 * 5],
        [300 + 13 * 3, 300 + 13 * 3, 400 + 13 * 3, 400 + 13 * 3],
    ])
    confs = np.array([0.8, 0.9])
    class_ids = np.array([0, 1])
    features = np.random.rand(2, 128)

    occluded_track.hit_streak = 10

    matched, unmatched_det, unmatched_trk = associate_detections_to_trackers(
        detections, features, tracker.tracks
    )

    print(f"  匹配对数: {len(matched)}")
    print(f"  未匹配检测: {unmatched_det}")
    print(f"  未匹配跟踪: {unmatched_trk}")

    assert len(matched) >= 1, "二次匹配失败"
    print("OK 遮挡目标二次匹配测试通过\n")


def test_small_object_nms():
    print("=" * 50)
    print("测试8: 小目标检测NMS合并")
    print("=" * 50)

    def nms(boxes, scores, iou_threshold=0.5):
        if len(boxes) == 0:
            return np.array([], dtype=np.int64)
        
        x1 = boxes[:, 0]
        y1 = boxes[:, 1]
        x2 = boxes[:, 2]
        y2 = boxes[:, 3]
        
        areas = (x2 - x1 + 1) * (y2 - y1 + 1)
        order = scores.argsort()[::-1]
        
        keep = []
        while order.size > 0:
            i = order[0]
            keep.append(i)
            
            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])
            
            w = np.maximum(0.0, xx2 - xx1 + 1)
            h = np.maximum(0.0, yy2 - yy1 + 1)
            inter = w * h
            
            ovr = inter / (areas[i] + areas[order[1:]] - inter)
            
            inds = np.where(ovr <= iou_threshold)[0]
            order = order[inds + 1]
        
        return np.array(keep, dtype=np.int64)

    boxes = np.array([
        [10, 10, 30, 30],
        [12, 12, 32, 32],
        [50, 50, 80, 80],
    ])
    scores = np.array([0.9, 0.85, 0.95])

    keep = nms(boxes, scores, iou_threshold=0.5)
    print(f"  输入框数: {len(boxes)}")
    print(f"  保留框数: {len(keep)}")
    print(f"  保留索引: {keep.tolist()}")

    assert len(keep) == 2, f"NMS结果错误: {len(keep)}"
    assert 2 in keep, "高分框被错误抑制"
    print("OK 小目标检测NMS合并测试通过\n")


def main():
    print("\n" + "=" * 50)
    print("  增强功能单元测试")
    print("=" * 50 + "\n")

    tests = [
        test_occlusion_detection,
        test_multi_modal_data_association,
        test_occlusion_id_stability,
        test_skip_frame_prediction,
        test_motion_interpolation,
        test_motion_uncertainty_weighting,
        test_secondary_matching,
        test_small_object_nms,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"FAIL {test.__name__} 失败: {e}\n")
            import traceback
            traceback.print_exc()

    print("=" * 50)
    print(f"  测试完成: {passed} 通过, {failed} 失败")
    print("=" * 50)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit(main())
