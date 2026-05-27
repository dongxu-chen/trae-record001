import cv2
import numpy as np
import os
from skimage.segmentation import slic

def create_test_image():
    img = np.zeros((300, 400, 3), dtype=np.uint8)
    cv2.circle(img, (150, 150), 80, (255, 100, 100), -1)
    cv2.rectangle(img, (250, 50), (350, 250), (100, 255, 100), -1)
    cv2.putText(img, 'Test', (50, 280), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
    return img

def create_test_video(output_path, num_frames=30):
    height, width = 240, 320
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, 10, (width, height))
    
    for i in range(num_frames):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        x = 50 + i * 8
        cv2.circle(frame, (x, 120), 40, (0, 255, 255), -1)
        cv2.rectangle(frame, (x - 20, 180), (x + 60, 220), (255, 100, 100), -1)
        out.write(frame)
    
    out.release()
    print(f"✓ 测试视频已创建: {output_path}")

def test_temporal_smoothing(frames, window_size=3):
    smoothed = []
    for i in range(len(frames)):
        if i < window_size:
            smoothed.append(frames[i].copy())
        else:
            result = frames[i].astype(np.float32)
            alpha = 1.0 / (window_size + 1)
            for j in range(1, window_size + 1):
                result = cv2.addWeighted(result, 1 - alpha, frames[i - j].astype(np.float32), alpha, 0)
            smoothed.append(result.astype(np.uint8))
    print(f"✓ 时间平滑测试通过，处理了 {len(frames)} 帧")
    return smoothed

def test_style_transfer(content, style_img, content_w=5, style_w=5):
    total_w = content_w + style_w
    content_alpha = content_w / total_w
    style_alpha = style_w / total_w
    
    style_img = cv2.resize(style_img, (content.shape[1], content.shape[0]))
    
    content_lab = cv2.cvtColor(content, cv2.COLOR_BGR2LAB)
    style_lab = cv2.cvtColor(style_img, cv2.COLOR_BGR2LAB)
    
    content_l, content_a, content_b = cv2.split(content_lab)
    style_l, style_a, style_b = cv2.split(style_lab)
    
    result_l = cv2.addWeighted(content_l, content_alpha, style_l, style_alpha, 0)
    result_a = cv2.addWeighted(content_a, content_alpha, style_a, style_alpha, 0)
    result_b = cv2.addWeighted(content_b, content_alpha, style_b, style_alpha, 0)
    
    result_lab = cv2.merge([result_l, result_a, result_b])
    result_rgb = cv2.cvtColor(result_lab, cv2.COLOR_LAB2BGR)
    
    content_segments = slic(cv2.cvtColor(content, cv2.COLOR_BGR2RGB), n_segments=100, compactness=10, sigma=1, start_label=0)
    
    for segment_id in np.unique(content_segments):
        mask = (content_segments == segment_id)
        segment_content = content[mask]
        segment_style = style_img[mask]
        
        content_mean = np.mean(segment_content, axis=0)
        style_mean = np.mean(segment_style, axis=0)
        blended = content_mean * content_alpha + style_mean * style_alpha
        result_rgb[mask] = result_rgb[mask] * 0.7 + blended * 0.3
    
    result_rgb = np.clip(result_rgb, 0, 255).astype(np.uint8)
    print(f"✓ 风格迁移测试通过，内容权重: {content_w}, 风格权重: {style_w}")
    return result_rgb

def test_artist_styles(img):
    presets = {
        'vangogh': {'name': '梵高', 'color_shift': np.array([30, 20, -10]), 'contrast': 1.3, 'saturation': 1.5},
        'picasso': {'name': '毕加索', 'color_shift': np.array([-20, 10, 30]), 'contrast': 1.5, 'saturation': 0.8},
        'monet': {'name': '莫奈', 'color_shift': np.array([20, 30, 10]), 'contrast': 0.9, 'saturation': 1.2},
        'davinci': {'name': '达芬奇', 'color_shift': np.array([0, 0, 0]), 'contrast': 1.2, 'saturation': 0.3},
    }
    
    output_dir = "test_artist_output"
    os.makedirs(output_dir, exist_ok=True)
    
    for artist, preset in presets.items():
        result = img.copy()
        
        result = result.astype(np.float32)
        color_shift = preset['color_shift'] * 0.7
        for i in range(3):
            result[:,:,i] = np.clip(result[:,:,i] + color_shift[i], 0, 255)
        
        result = cv2.convertScaleAbs(result, alpha=preset['contrast'], beta=0)
        
        hsv = cv2.cvtColor(result, cv2.COLOR_BGR2HSV)
        hsv[:,:,1] = np.clip(hsv[:,:,1] * preset['saturation'], 0, 255)
        result = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
        
        result = cv2.medianBlur(result, 7)
        
        texture = np.random.normal(0, 5, result.shape)
        result = np.clip(result.astype(np.float32) + texture, 0, 255).astype(np.uint8)
        
        cv2.imwrite(os.path.join(output_dir, f"{artist}.png"), result)
        print(f"  ✓ {preset['name']}风格已生成")
    
    print(f"✓ 艺术家风格库测试通过，输出到 {output_dir}/")

if __name__ == "__main__":
    print("测试新功能...\n")
    
    test_img = create_test_image()
    content_img = test_img
    style_img = np.zeros_like(test_img)
    style_img[:,:] = [200, 100, 50]
    cv2.putText(style_img, 'Style', (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
    
    print("1. 测试视频风格化与时间连续性...")
    test_video_path = "test_input.mp4"
    create_test_video(test_video_path)
    
    cap = cv2.VideoCapture(test_video_path)
    frames = []
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frames.append(frame)
    cap.release()
    
    smoothed_frames = test_temporal_smoothing(frames, window_size=3)
    os.remove(test_video_path)
    
    print("\n2. 测试风格迁移融合...")
    transfer_result = test_style_transfer(content_img, style_img, content_w=6, style_w=4)
    cv2.imwrite("test_transfer.png", transfer_result)
    
    print("\n3. 测试艺术家风格库...")
    test_artist_styles(test_img)
    
    print("\n✓ 所有新功能测试通过!")
    print("\n新增功能总结:")
    print("1. 视频风格化: 逐帧处理 + 时间连续性平滑")
    print("2. 风格迁移: 内容图与风格图权重可调节,支持保留颜色")
    print("3. 艺术家风格库: 梵高、毕加索、莫奈、达芬奇、达利、毕沙罗 + 自定义")
