import sys
import numpy as np
import cv2
import os
import time

sys.stdout.reconfigure(encoding='utf-8')

print("=" * 60)
print("泊松图像编辑 - 简单功能测试")
print("=" * 60)

from poisson_editing import PoissonEditing, VideoPoissonEditor, HAS_CUDA

print(f"\n系统信息:")
print(f"  CUDA可用: {HAS_CUDA}")

os.makedirs("test_images", exist_ok=True)

print("\n[1/5] 创建测试图像...")
src1 = np.zeros((100, 100, 3), dtype=np.uint8)
cv2.circle(src1, (50, 50), 35, (255, 100, 50), -1)

src2 = np.zeros((100, 100, 3), dtype=np.uint8)
cv2.rectangle(src2, (20, 20), (80, 80), (50, 200, 100), -1)

dst = np.zeros((200, 300, 3), dtype=np.uint8)
for y in range(200):
    for x in range(300):
        dst[y, x] = [100 + int(50 * np.sin(y / 15)), 
                     150 + int(50 * np.cos(x / 20)), 
                     200]

mask = np.zeros((100, 100), dtype=np.uint8)
cv2.circle(mask, (50, 50), 40, 255, -1)
print("  ✓ 完成")

print("\n[2/5] 测试基本泊松融合 (多网格法)...")
poisson = PoissonEditing(use_gpu=False)
start = time.time()
result1 = poisson.seamless_clone(src1, dst, mask, (150, 100), mix_weight=1.0, feather=True)
elapsed = time.time() - start
cv2.imwrite("test_images/result_basic.png", result1)
print(f"  ✓ 完成, 耗时: {elapsed:.2f}秒")

print("\n[3/5] 测试混合梯度场...")
start = time.time()
offset = (50, 100)
result_mix = poisson.fuse_mixed_gradients(
    [src1, src2], dst, mask, 
    offsets=[offset, offset], 
    weights=[0.5, 0.5], 
    feather=True
)
elapsed = time.time() - start
cv2.imwrite("test_images/result_mixed.png", result_mix)
print(f"  ✓ 完成, 耗时: {elapsed:.2f}秒")

print("\n[4/5] 测试不同羽化半径...")
for r in [0, 5, 10]:
    poisson.feather_radius = r
    result = poisson.seamless_clone(src1, dst, mask, (150, 100), mix_weight=1.0, feather=True)
    cv2.imwrite(f"test_images/result_feather_{r}.png", result)
    print(f"  ✓ 羽化半径 {r}: 完成")

print("\n[5/5] 测试视频处理...")
video_path = "test_images/test_video.mp4"
output_path = "test_images/test_video_output.mp4"

frame_width, frame_height = 300, 200
fps = 10
num_frames = 20

fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(video_path, fourcc, fps, (frame_width, frame_height))

for i in range(num_frames):
    frame = dst.copy()
    cv2.putText(frame, f"Frame {i+1}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    out.write(frame)
out.release()
print(f"  ✓ 测试视频已创建: {video_path}")

video_editor = VideoPoissonEditor(use_gpu=False, temporal_smoothing=0.3)
offset = (frame_height // 2 - src1.shape[0] // 2, frame_width // 2 - src1.shape[1] // 2)

start = time.time()
success = video_editor.process_video(
    src_img=src1,
    video_path=video_path,
    output_path=output_path,
    mask=mask,
    offset=offset,
    mix_weight=1.0,
    start_frame=0,
    max_frames=num_frames
)
elapsed = time.time() - start

if success:
    print(f"  ✓ 视频处理完成, 耗时: {elapsed:.2f}秒, 输出: {output_path}")
else:
    print("  ✗ 视频处理失败")

print("\n" + "=" * 60)
print("所有测试完成!")
print("请查看 test_images/ 目录下的结果")
print("=" * 60)
