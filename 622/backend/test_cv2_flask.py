from flask import Flask, jsonify
import cv2
import numpy as np
from PIL import Image
import threading

app = Flask(__name__)

print('Main thread cv2.cvtColor exists:', hasattr(cv2, 'cvtColor'))
print('cv2.__file__ =', cv2.__file__)

@app.route('/test-cv2')
def test_cv2():
    import cv2 as cv2_local
    print('Request thread cv2.cvtColor exists:', hasattr(cv2_local, 'cvtColor'))
    print('Request thread cv2.__file__ =', cv2_local.__file__)
    
    try:
        img = Image.new('RGB', (100, 100), color=(100, 150, 200))
        arr = np.array(img)
        result = cv2.cvtColor(arr, cv2.COLOR_RGB2LAB)
        return jsonify({'status': 'success', 'cvtColor_works': True})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'error': str(e), 'cvtColor_works': hasattr(cv2_local, 'cvtColor')})

if __name__ == '__main__':
    app.run(port=8001, debug=False)
