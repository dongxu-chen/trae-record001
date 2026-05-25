import { useState, useEffect, useRef, useCallback } from 'react';

const GESTURE_DEBOUNCE = 1500;
const CONFIDENCE_THRESHOLD = 0.7;

const HAND_CONNECTIONS = [
  [0, 1], [1, 2], [2, 3], [3, 4],
  [0, 5], [5, 6], [6, 7], [7, 8],
  [5, 9], [9, 10], [10, 11], [11, 12],
  [9, 13], [13, 14], [14, 15], [15, 16],
  [13, 17], [17, 18], [18, 19], [19, 20],
  [0, 17]
];

class GestureRecognizer {
  constructor() {
    this.lastGestureTime = {};
    this.gestureHistory = [];
    this.historySize = 5;
  }

  getFingerState(landmarks) {
    const tips = [4, 8, 12, 16, 20];
    const pips = [3, 6, 10, 14, 18];
    const mcps = [2, 5, 9, 13, 17];

    const fingers = [];
    
    for (let i = 0; i < 5; i++) {
      const tip = landmarks[tips[i]];
      const pip = landmarks[pips[i]];
      const mcp = landmarks[mcps[i]];
      
      if (i === 0) {
        const thumbTip = landmarks[4];
        const indexBase = landmarks[5];
        const thumbMcp = landmarks[2];
        
        const dist1 = Math.hypot(thumbTip.x - indexBase.x, thumbTip.y - indexBase.y);
        const dist2 = Math.hypot(thumbMcp.x - indexBase.x, thumbMcp.y - indexBase.y);
        
        fingers.push(dist1 > dist2 * 1.2);
      } else {
        fingers.push(tip.y < pip.y && pip.y < mcp.y);
      }
    }
    
    return fingers;
  }

  calculateAngle(p1, p2, p3) {
    const v1 = { x: p1.x - p2.x, y: p1.y - p2.y };
    const v2 = { x: p3.x - p2.x, y: p3.y - p2.y };
    const dot = v1.x * v2.x + v1.y * v2.y;
    const mag1 = Math.hypot(v1.x, v1.y);
    const mag2 = Math.hypot(v2.x, v2.y);
    return Math.acos(dot / (mag1 * mag2)) * 180 / Math.PI;
  }

  recognizeGesture(landmarks) {
    if (!landmarks || landmarks.length < 21) return null;

    const fingers = this.getFingerState(landmarks);
    const [thumb, index, middle, ring, pinky] = fingers;

    const wrist = landmarks[0];
    const middleTip = landmarks[12];
    const handHeight = Math.abs(middleTip.y - wrist.y);

    if (index && middle && ring && pinky && !thumb) {
      const palmCenter = {
        x: (landmarks[0].x + landmarks[5].x + landmarks[9].x + landmarks[13].x + landmarks[17].x) / 5,
        y: (landmarks[0].y + landmarks[5].y + landmarks[9].y + landmarks[13].y + landmarks[17].y) / 5
      };
      
      const fingersUp = [8, 12, 16, 20].every(i => {
        const tip = landmarks[i];
        return tip.y < palmCenter.y - handHeight * 0.3;
      });
      
      if (fingersUp) {
        return {
          type: 'hand_raise',
          confidence: 0.85,
          name: '举手',
          icon: '✋'
        };
      }
    }

    if (thumb && !index && !middle && !ring && !pinky) {
      const thumbTip = landmarks[4];
      const thumbMcp = landmarks[2];
      
      const isPointingUp = thumbTip.y < thumbMcp.y - handHeight * 0.2;
      const isPointingSide = Math.abs(thumbTip.x - thumbMcp.x) > handHeight * 0.2;
      
      if (isPointingUp || isPointingSide) {
        return {
          type: 'thumbs_up',
          confidence: 0.8,
          name: '点赞',
          icon: '👍'
        };
      }
    }

    if (!thumb && index && middle && !ring && !pinky) {
      return {
        type: 'peace',
        confidence: 0.75,
        name: '胜利',
        icon: '✌️'
      };
    }

    if (thumb && index && !middle && !ring && !pinky) {
      return {
        type: 'love',
        confidence: 0.7,
        name: '爱你',
        icon: '🤟'
      };
    }

    if (!thumb && !index && !middle && !ring && !pinky) {
      return {
        type: 'fist',
        confidence: 0.7,
        name: '拳头',
        icon: '✊'
      };
    }

    if (thumb && index && middle && ring && pinky) {
      return {
        type: 'open_palm',
        confidence: 0.7,
        name: '手掌',
        icon: '🖐️'
      };
    }

    return null;
  }

  checkDebounce(gestureType) {
    const now = Date.now();
    const lastTime = this.lastGestureTime[gestureType] || 0;
    
    if (now - lastTime < GESTURE_DEBOUNCE) {
      return false;
    }
    
    this.lastGestureTime[gestureType] = now;
    return true;
  }

  processLandmarks(landmarks) {
    const gesture = this.recognizeGesture(landmarks);
    
    if (!gesture) {
      this.gestureHistory.push(null);
      if (this.gestureHistory.length > this.historySize) {
        this.gestureHistory.shift();
      }
      return null;
    }

    this.gestureHistory.push(gesture.type);
    if (this.gestureHistory.length > this.historySize) {
      this.gestureHistory.shift();
    }

    const counts = {};
    for (const g of this.gestureHistory) {
      if (g) counts[g] = (counts[g] || 0) + 1;
    }

    const majorityThreshold = Math.ceil(this.historySize * 0.6);
    for (const [type, count] of Object.entries(counts)) {
      if (count >= majorityThreshold && gesture.type === type) {
        if (this.checkDebounce(type)) {
          return gesture;
        }
      }
    }

    return null;
  }
}

const useGestureRecognition = (videoElement, enabled = false) => {
  const [isSupported, setIsSupported] = useState(false);
  const [isDetecting, setIsDetecting] = useState(false);
  const [currentGesture, setCurrentGesture] = useState(null);
  const [gestureHistory, setGestureHistory] = useState([]);
  const [error, setError] = useState(null);
  const [stats, setStats] = useState({ fps: 0, detections: 0 });

  const recognizerRef = useRef(null);
  const animationRef = useRef(null);
  const canvasRef = useRef(null);
  const lastTimeRef = useRef(0);
  const frameCountRef = useRef(0);
  const detectionCountRef = useRef(0);

  useEffect(() => {
    const supported = typeof window !== 'undefined' && 
      'MediaStream' in window && 
      'requestAnimationFrame' in window;
    
    setIsSupported(supported);
    
    if (supported) {
      recognizerRef.current = new GestureRecognizer();
    }

    return () => {
      stopDetection();
    };
  }, []);

  const loadMediaPipe = useCallback(async () => {
    try {
      if (window.Hands) return true;

      await new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = 'https://cdn.jsdelivr.net/npm/@mediapipe/hands/hands.js';
        script.crossOrigin = 'anonymous';
        script.onload = resolve;
        script.onerror = reject;
        document.body.appendChild(script);
      });

      await new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = 'https://cdn.jsdelivr.net/npm/@mediapipe/camera_utils/camera_utils.js';
        script.crossOrigin = 'anonymous';
        script.onload = resolve;
        script.onerror = reject;
        document.body.appendChild(script);
      });

      return true;
    } catch (error) {
      console.error('Failed to load MediaPipe:', error);
      return false;
    }
  }, []);

  const startDetection = useCallback(async () => {
    if (!enabled || !videoElement || !isSupported) {
      return false;
    }

    try {
      const loaded = await loadMediaPipe();
      if (!loaded || !window.Hands) {
        throw new Error('MediaPipe not available');
      }

      const hands = new window.Hands({
        locateFile: (file) => {
          return `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${file}`;
        }
      });

      hands.setOptions({
        maxNumHands: 2,
        modelComplexity: 1,
        minDetectionConfidence: CONFIDENCE_THRESHOLD,
        minTrackingConfidence: CONFIDENCE_THRESHOLD
      });

      hands.onResults((results) => {
        frameCountRef.current++;
        const now = Date.now();
        
        if (now - lastTimeRef.current >= 1000) {
          setStats(prev => ({
            fps: frameCountRef.current,
            detections: detectionCountRef.current
          }));
          frameCountRef.current = 0;
          lastTimeRef.current = now;
        }

        if (results.multiHandLandmarks && results.multiHandLandmarks.length > 0) {
          for (const landmarks of results.multiHandLandmarks) {
            const gesture = recognizerRef.current?.processLandmarks(landmarks);
            
            if (gesture) {
              detectionCountRef.current++;
              setCurrentGesture(gesture);
              setGestureHistory(prev => {
                const newHistory = [...prev, { ...gesture, timestamp: Date.now() }];
                return newHistory.slice(-10);
              });
            }
          }
        }
      });

      if (window.Camera) {
        const camera = new window.Camera(videoElement, {
          onFrame: async () => {
            if (isDetecting) {
              await hands.send({ image: videoElement });
            }
          },
          width: 640,
          height: 480
        });
        await camera.start();
      } else {
        const processFrame = async () => {
          if (isDetecting && videoElement.readyState >= 2) {
            await hands.send({ image: videoElement });
          }
          animationRef.current = requestAnimationFrame(processFrame);
        };
        processFrame();
      }

      setIsDetecting(true);
      setError(null);
      return true;
    } catch (err) {
      console.error('Failed to start gesture detection:', err);
      setError(err.message);
      setIsDetecting(false);
      return false;
    }
  }, [enabled, videoElement, isSupported, loadMediaPipe, isDetecting]);

  const stopDetection = useCallback(() => {
    setIsDetecting(false);
    setCurrentGesture(null);
    
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current);
      animationRef.current = null;
    }
    
    frameCountRef.current = 0;
    detectionCountRef.current = 0;
  }, []);

  const clearHistory = useCallback(() => {
    setGestureHistory([]);
    setCurrentGesture(null);
    if (recognizerRef.current) {
      recognizerRef.current.gestureHistory = [];
      recognizerRef.current.lastGestureTime = {};
    }
  }, []);

  useEffect(() => {
    if (enabled && !isDetecting) {
      startDetection();
    } else if (!enabled && isDetecting) {
      stopDetection();
    }
  }, [enabled, isDetecting, startDetection, stopDetection]);

  return {
    isSupported,
    isDetecting,
    currentGesture,
    gestureHistory,
    error,
    stats,
    startDetection,
    stopDetection,
    clearHistory
  };
};

export default useGestureRecognition;
