from style_transfer import StyleTransfer
from PIL import Image
import time

test_img = Image.new('RGB', (512, 512), color=(100, 150, 200))
test_img.save('test_perf.jpg')

st = StyleTransfer()

print('Testing SD Turbo performance...')
print('Image size: 512x512')
print()

styles = ['vangogh', 'cyberpunk', 'watercolor', 'sketch']

for style in styles:
    start = time.time()
    result = st._sd_turbo_transfer(test_img, style, st.curve_intensity_map(0.7))
    elapsed = (time.time() - start) * 1000
    status = 'PASS' if elapsed < 1000 else 'FAIL'
    print(f'{style}: {elapsed:.1f}ms - {status}')

print()
print('Curve intensity mapping test:')
for slider_val in [0.1, 0.3, 0.5, 0.7, 0.9]:
    mapped = st.curve_intensity_map(slider_val)
    print(f'  {slider_val} -> {mapped:.3f}')
