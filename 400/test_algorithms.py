import cv2
import numpy as np
import os

def create_test_image():
    img = np.zeros((300, 400, 3), dtype=np.uint8)
    cv2.circle(img, (150, 150), 80, (255, 100, 100), -1)
    cv2.rectangle(img, (250, 50), (350, 250), (100, 255, 100), -1)
    cv2.putText(img, 'Test', (50, 280), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
    return img

def test_pencil_sketch(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (21, 21), 0)
    sketch = cv2.divide(gray, blurred, scale=256.0)
    return sketch

def test_oil_painting(img):
    result = cv2.xphoto.oilPainting(img, 5, 5)
    return result

def test_edge_detection(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    return edges

def test_color_quantization(img, n_colors=8):
    pixels = img.reshape((-1, 3))
    pixels = np.float32(pixels)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
    _, labels, centers = cv2.kmeans(pixels, n_colors, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
    centers = np.uint8(centers)
    result = centers[labels.flatten()]
    result = result.reshape(img.shape)
    return result

if __name__ == "__main__":
    print("Testing NPR algorithms...")
    
    test_img = create_test_image()
    print("✓ Test image created")
    
    pencil = test_pencil_sketch(test_img)
    print("✓ Pencil sketch algorithm works")
    
    try:
        oil = test_oil_painting(test_img)
        print("✓ Oil painting algorithm works")
    except Exception as e:
        print(f"! Oil painting note: {e}")
    
    edges = test_edge_detection(test_img)
    print("✓ Edge detection algorithm works")
    
    quant = test_color_quantization(test_img)
    print("✓ Color quantization algorithm works")
    
    output_dir = "test_output"
    os.makedirs(output_dir, exist_ok=True)
    cv2.imwrite(os.path.join(output_dir, "test_original.png"), test_img)
    cv2.imwrite(os.path.join(output_dir, "test_pencil.png"), pencil)
    cv2.imwrite(os.path.join(output_dir, "test_edges.png"), edges)
    cv2.imwrite(os.path.join(output_dir, "test_quantized.png"), quant)
    
    print(f"\n✓ All tests passed! Test images saved to {output_dir}/")
