import cv2
import time
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'config'))

from face_capture import FaceCapture
from expression_extractor import ExpressionExtractor
from osc_sender import OSCSender
from config import Config
from audio_sync import LipSyncAudio
from action_units import ActionUnitAnalyzer
from expression_blender import ExpressionBlender, BlendMode
from vrchat_driver import VRChatOSCDriver, VRChatWebSocketDriver


class FaceMotionCapture:
    def __init__(self, config_path: str = None):
        self.config = Config.load(config_path) if config_path else Config()
        
        self.face_capture = FaceCapture(
            min_detection_confidence=self.config.min_detection_confidence,
            min_tracking_confidence=self.config.min_tracking_confidence
        )
        
        self.expression_extractor = ExpressionExtractor()
        self.expression_extractor.smoothing_factor = self.config.smoothing_factor
        
        self.osc_sender = OSCSender(
            ip=self.config.osc_ip,
            port=self.config.osc_port
        )
        
        self.lip_sync = LipSyncAudio()
        self.au_analyzer = ActionUnitAnalyzer()
        self.expression_blender = ExpressionBlender()
        
        self.vrc_driver = None
        self.websocket_driver = None
        
        self.cap = None
        self.fps = 0
        self.prev_frame_time = 0
        self.running = False
        
        self.enable_audio_sync = True
        self.audio_weight = 0.3
        self.enable_au_analysis = True
        self.enable_expression_blending = True
        self.enable_vrchat = False
        self.enable_websocket = False
        
        self.current_au_params = {}
        self.current_blended_params = {}
        self.current_preset = None
        self.preset_influence = 0.5
        
        self.current_audio_features = {}

    def init_camera(self):
        self.cap = cv2.VideoCapture(self.config.video_source)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.video_width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.video_height)
        self.cap.set(cv2.CAP_PROP_FPS, self.config.video_fps)
        
        if not self.cap.isOpened():
            raise RuntimeError("无法打开摄像头")

    def init_audio(self):
        if self.enable_audio_sync:
            try:
                self.lip_sync.start()
                print("音频同步已启用")
            except Exception as e:
                print(f"音频初始化失败: {e}")
                self.enable_audio_sync = False

    def init_vrchat(self):
        if not self.enable_vrchat:
            return
        
        try:
            self.vrc_driver = VRChatOSCDriver(
                ip=self.config.osc_ip,
                send_port=9000,
                receive_port=9001
            )
            self.vrc_driver.send_face_tracking_enabled(True)
            print("VRChat OSC驱动已启动")
        except Exception as e:
            print(f"VRChat初始化失败: {e}")
            self.enable_vrchat = False

    def init_websocket(self):
        if not self.enable_websocket:
            return
        
        try:
            self.websocket_driver = VRChatWebSocketDriver(host='127.0.0.1', port=8080)
            self.websocket_driver.start()
            print("WebSocket服务器已启动: ws://127.0.0.1:8080")
        except Exception as e:
            print(f"WebSocket初始化失败: {e}")
            self.enable_websocket = False

    def draw_overlay(self, frame, head_pose, expressions, audio_features=None, au_params=None, blend_info=None):
        h, w = frame.shape[:2]
        
        if self.config.show_fps:
            cv2.putText(frame, f'FPS: {self.fps:.1f}', (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        y_offset = 60
        
        if head_pose:
            yaw = head_pose.get('yaw', 0)
            pitch = head_pose.get('pitch', 0)
            roll = head_pose.get('roll', 0)
            
            cv2.putText(frame, f'Yaw: {yaw:.1f}', (10, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
            cv2.putText(frame, f'Pitch: {pitch:.1f}', (10, y_offset + 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
            cv2.putText(frame, f'Roll: {roll:.1f}', (10, y_offset + 40),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
            y_offset += 70
        
        if expressions:
            cv2.putText(frame, '--- Expressions ---', (10, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 200, 0), 1)
            y_offset += 15
            display_keys = ['mouth_open', 'jaw_open', 'smile', 'eye_open_left', 'blink_left']
            for i, key in enumerate(display_keys):
                if key in expressions:
                    cv2.putText(frame, f'{key}: {expressions[key]:.2f}', (10, y_offset + i * 15),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)
            y_offset += len(display_keys) * 15 + 10
        
        if au_params and self.enable_au_analysis:
            active_aus = {k: v for k, v in au_params.items() if v > 0.3}
            if active_aus:
                cv2.putText(frame, '--- Active AUs ---', (10, y_offset),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 150, 0), 1)
                y_offset += 15
                au_items = list(active_aus.items())[:6]
                for i, (au_id, intensity) in enumerate(au_items):
                    cv2.putText(frame, f'{au_id}: {intensity:.2f}', (10, y_offset + i * 15),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 150, 0), 1)
                y_offset += len(au_items) * 15 + 10
        
        if self.current_preset:
            cv2.putText(frame, f'Preset: {self.current_preset} ({self.preset_influence:.1f})', 
                       (10, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 255), 1)
            y_offset += 25
        
        if audio_features and self.enable_audio_sync:
            voice_active = audio_features.get('voice_activity', 0) > 0.5
            status_text = "Audio: Active" if voice_active else "Audio: Idle"
            cv2.putText(frame, status_text, (w - 150, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, 
                       (0, 255, 0) if voice_active else (128, 128, 128), 1)
            
            rms = audio_features.get('rms', 0)
            cv2.putText(frame, f'RMS: {rms:.3f}', (w - 150, 85),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 200, 0), 1)
            
            bar_width = int(min(rms * 500, 100))
            cv2.rectangle(frame, (w - 150, 100), (w - 150 + bar_width, 115), (0, 255, 0), -1)
            cv2.rectangle(frame, (w - 150, 100), (w - 50, 115), (255, 255, 255), 1)
        
        status_y = 30
        osc_status = "OSC: " + ("Connected" if self.osc_sender.connected else "Disconnected")
        cv2.putText(frame, osc_status, (w - 180, status_y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, 
                   (0, 255, 0) if self.osc_sender.connected else (0, 0, 255), 1)
        
        if self.enable_vrchat and self.vrc_driver:
            status_y += 25
            vrc_status = "VRChat: " + ("Connected" if self.vrc_driver.connected else "Disconnected")
            cv2.putText(frame, vrc_status, (w - 180, status_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, 
                       (0, 255, 0) if self.vrc_driver.connected else (0, 0, 255), 1)
        
        if self.enable_websocket and self.websocket_driver:
            status_y += 25
            ws_status = f"WebSocket: {len(self.websocket_driver.clients)} clients"
            cv2.putText(frame, ws_status, (w - 180, status_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, 
                       (0, 200, 255), 1)
        
        feature_status = []
        if self.enable_au_analysis:
            feature_status.append("AU")
        if self.enable_expression_blending:
            feature_status.append("Blend")
        if feature_status:
            status_text = "Features: " + ", ".join(feature_status)
            cv2.putText(frame, status_text, (w - 180, h - 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
        
        return frame

    def fuse_audio_visual(self, expressions: dict) -> dict:
        if not self.enable_audio_sync:
            return expressions
        
        fused = expressions.copy()
        
        if 'mouth_open' in expressions:
            visual_mouth_open = expressions['mouth_open']
            fused_mouth_open = self.lip_sync.get_fused_mouth_open(visual_mouth_open)
            fused['mouth_open'] = fused_mouth_open
            fused['mouth_open_visual'] = visual_mouth_open
        
        return fused

    def process_frame(self, frame):
        landmarks, head_pose, rgb_image = self.face_capture.process_frame(frame)
        
        expressions = {}
        au_params = {}
        blended_params = {}
        
        if landmarks:
            expressions = self.expression_extractor.extract_all_expressions(landmarks, frame.shape)
            
            expressions = self.fuse_audio_visual(expressions)
            
            if self.enable_au_analysis:
                au_params = self.au_analyzer.analyze(landmarks, frame.shape)
                self.current_au_params = au_params
            
            if self.enable_expression_blending:
                if self.enable_au_analysis:
                    blended_params = self.expression_blender.blend_with_aus(expressions, au_params)
                else:
                    blended_params = self.expression_blender.blend(expressions)
                expressions = blended_params
                self.current_blended_params = blended_params
            
            scaled_head_pose = {
                'pitch': head_pose['pitch'] * self.config.head_pose_scale,
                'yaw': head_pose['yaw'] * self.config.head_pose_scale,
                'roll': head_pose['roll'] * self.config.head_pose_scale
            }
            
            self.osc_sender.send_all_params(scaled_head_pose, expressions)
            
            if self.enable_vrchat and self.vrc_driver:
                self.vrc_driver.send_all_params(
                    scaled_head_pose,
                    expressions,
                    expressions,
                    expressions,
                    au_params if au_params else None
                )
            
            if self.enable_websocket and self.websocket_driver:
                face_data = {
                    'head_pose': scaled_head_pose,
                    'expressions': expressions,
                    'action_units': au_params,
                    'blend_info': self.expression_blender.get_blend_info()
                }
                self.websocket_driver.send_face_data(face_data)
        
        if self.config.draw_landmarks and landmarks:
            frame = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2BGR)
        
        if self.enable_audio_sync:
            self.current_audio_features = self.lip_sync.get_audio_features()
        
        if self.config.show_preview:
            blend_info = self.expression_blender.get_blend_info() if self.enable_expression_blending else None
            frame = self.draw_overlay(frame, head_pose, expressions, 
                                       self.current_audio_features, au_params, blend_info)
        
        return frame, landmarks, head_pose, expressions

    def cycle_preset(self, direction: int = 1):
        presets = self.expression_blender.library.list_presets()
        if not presets:
            return
        
        current_idx = 0
        if self.current_preset in presets:
            current_idx = presets.index(self.current_preset)
        
        new_idx = (current_idx + direction) % len(presets)
        self.current_preset = presets[new_idx]
        
        success = self.expression_blender.apply_preset(self.current_preset, self.preset_influence)
        if success:
            print(f"应用预设: {self.current_preset} (influence: {self.preset_influence:.2f})")

    def adjust_preset_influence(self, delta: float):
        self.preset_influence = max(0.0, min(1.0, self.preset_influence + delta))
        if self.current_preset:
            self.expression_blender.apply_preset(self.current_preset, self.preset_influence)
        print(f"预设影响力: {self.preset_influence:.2f}")

    def run(self):
        self.init_camera()
        self.init_audio()
        self.init_vrchat()
        self.init_websocket()
        self.running = True
        
        print("=" * 50)
        print("面部捕捉系统启动中...")
        print(f"OSC目标: {self.config.osc_ip}:{self.config.osc_port}")
        print(f"音频同步: {'已启用' if self.enable_audio_sync else '已禁用'}")
        print(f"AU分析: {'已启用' if self.enable_au_analysis else '已禁用'}")
        print(f"表情混合: {'已启用' if self.enable_expression_blending else '已禁用'}")
        print(f"VRChat驱动: {'已启用' if self.enable_vrchat else '已禁用'}")
        print(f"WebSocket: {'已启用' if self.enable_websocket else '已禁用'}")
        print("=" * 50)
        print("按键说明:")
        print("  q - 退出")
        print("  d - 切换面部网格显示")
        print("  a - 切换音频同步")
        print("  c - 切换参数压缩映射")
        print("  u - 切换AU分析")
        print("  b - 切换表情混合")
        print("  v - 切换VRChat驱动")
        print("  w - 切换WebSocket")
        print("  r - 重新连接OSC")
        print("  n/p - 下一个/上一个表情预设")
        print("  [ / ] - 减少/增加预设影响力")
        print("  0 - 重置表情混合")
        print("=" * 50)
        
        try:
            while self.running and self.cap.isOpened():
                ret, frame = self.cap.read()
                if not ret:
                    print("无法获取视频帧")
                    break
                
                frame = cv2.flip(frame, 1)
                
                current_time = time.time()
                frame, landmarks, head_pose, expressions = self.process_frame(frame)
                
                if current_time - self.prev_frame_time > 0:
                    self.fps = 1 / (current_time - self.prev_frame_time)
                self.prev_frame_time = current_time
                
                if self.config.show_preview:
                    cv2.imshow('Face Motion Capture', frame)
                
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('d'):
                    self.config.draw_landmarks = not self.config.draw_landmarks
                elif key == ord('r'):
                    self.osc_sender.reconnect()
                    if self.vrc_driver:
                        self.vrc_driver.reconnect()
                elif key == ord('a'):
                    self.enable_audio_sync = not self.enable_audio_sync
                    if self.enable_audio_sync:
                        self.init_audio()
                    else:
                        self.lip_sync.stop()
                    print(f"音频同步: {'已启用' if self.enable_audio_sync else '已禁用'}")
                elif key == ord('c'):
                    self.expression_extractor.enable_compression = not self.expression_extractor.enable_compression
                    print(f"参数压缩: {'已启用' if self.expression_extractor.enable_compression else '已禁用'}")
                elif key == ord('u'):
                    self.enable_au_analysis = not self.enable_au_analysis
                    print(f"AU分析: {'已启用' if self.enable_au_analysis else '已禁用'}")
                elif key == ord('b'):
                    self.enable_expression_blending = not self.enable_expression_blending
                    print(f"表情混合: {'已启用' if self.enable_expression_blending else '已禁用'}")
                elif key == ord('v'):
                    self.enable_vrchat = not self.enable_vrchat
                    if self.enable_vrchat:
                        self.init_vrchat()
                    else:
                        if self.vrc_driver:
                            self.vrc_driver.close()
                            self.vrc_driver = None
                    print(f"VRChat驱动: {'已启用' if self.enable_vrchat else '已禁用'}")
                elif key == ord('w'):
                    self.enable_websocket = not self.enable_websocket
                    if self.enable_websocket:
                        self.init_websocket()
                    else:
                        if self.websocket_driver:
                            self.websocket_driver.stop()
                            self.websocket_driver = None
                    print(f"WebSocket: {'已启用' if self.enable_websocket else '已禁用'}")
                elif key == ord('n'):
                    self.cycle_preset(1)
                elif key == ord('p'):
                    self.cycle_preset(-1)
                elif key == ord('['):
                    self.adjust_preset_influence(-0.1)
                elif key == ord(']'):
                    self.adjust_preset_influence(0.1)
                elif key == ord('0'):
                    self.expression_blender.reset()
                    self.current_preset = None
                    print("表情混合已重置")
                
        except KeyboardInterrupt:
            print("\n用户中断")
        finally:
            self.stop()

    def stop(self):
        self.running = False
        if self.cap:
            self.cap.release()
        self.face_capture.release()
        self.osc_sender.close()
        if self.enable_audio_sync:
            self.lip_sync.stop()
        if self.vrc_driver:
            self.vrc_driver.close()
        if self.websocket_driver:
            self.websocket_driver.stop()
        cv2.destroyAllWindows()
        print("系统已关闭")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='人脸面部捕捉与重定向系统')
    parser.add_argument('--config', type=str, help='配置文件路径')
    parser.add_argument('--video', type=int, default=0, help='视频源设备ID')
    parser.add_argument('--ip', type=str, default='127.0.0.1', help='OSC服务器IP')
    parser.add_argument('--port', type=int, default=9000, help='OSC服务器端口')
    parser.add_argument('--no-preview', action='store_true', help='不显示预览窗口')
    parser.add_argument('--no-audio', action='store_true', help='禁用音频同步')
    parser.add_argument('--audio-weight', type=float, default=0.3, help='音频融合权重 (0-1)')
    parser.add_argument('--no-compression', action='store_true', help='禁用参数压缩映射')
    parser.add_argument('--no-au', action='store_true', help='禁用AU分析')
    parser.add_argument('--no-blending', action='store_true', help='禁用表情混合')
    parser.add_argument('--vrchat', action='store_true', help='启用VRChat驱动')
    parser.add_argument('--websocket', action='store_true', help='启用WebSocket服务器')
    parser.add_argument('--preset', type=str, help='初始表情预设')
    parser.add_argument('--preset-influence', type=float, default=0.5, help='预设影响力 (0-1)')
    
    args = parser.parse_args()
    
    mocap = FaceMotionCapture(config_path=args.config)
    
    if args.video != 0:
        mocap.config.video_source = args.video
    if args.ip != '127.0.0.1':
        mocap.config.osc_ip = args.ip
    if args.port != 9000:
        mocap.config.osc_port = args.port
    if args.no_preview:
        mocap.config.show_preview = False
    if args.no_audio:
        mocap.enable_audio_sync = False
    if args.audio_weight != 0.3:
        mocap.audio_weight = args.audio_weight
        mocap.lip_sync.audio_weight = args.audio_weight
    if args.no_compression:
        mocap.expression_extractor.enable_compression = False
    if args.no_au:
        mocap.enable_au_analysis = False
    if args.no_blending:
        mocap.enable_expression_blending = False
    if args.vrchat:
        mocap.enable_vrchat = True
    if args.websocket:
        mocap.enable_websocket = True
    if args.preset:
        mocap.current_preset = args.preset
        mocap.preset_influence = args.preset_influence
        mocap.expression_blender.apply_preset(args.preset, args.preset_influence)
    
    mocap.run()


if __name__ == "__main__":
    main()
