import json
import time
import threading
from typing import Dict, List, Optional, Callable
from pythonosc import udp_client, osc_server, dispatcher


class VRCSDKParams:
    def __init__(self):
        self.params = {}
        self.param_info = {}

    def set_param(self, name: str, value: float):
        self.params[name] = max(0.0, min(1.0, value))

    def get_param(self, name: str) -> float:
        return self.params.get(name, 0.0)

    def get_all_params(self) -> Dict[str, float]:
        return self.params.copy()

    def clear(self):
        self.params.clear()


class VRChatOSCDriver:
    def __init__(self, ip: str = "127.0.0.1", send_port: int = 9000, 
                 receive_port: int = 9001):
        self.ip = ip
        self.send_port = send_port
        self.receive_port = receive_port
        
        self.send_client = None
        self.receive_server = None
        self.receive_thread = None
        
        self.connected = False
        self.running = False
        
        self.vrc_params = VRCSDKParams()
        
        self.on_param_received: Optional[Callable[[str, float], None]] = None
        
        self.default_params = {
            'VRCFaceBlendH': 0.0,
            'VRCFaceBlendV': 0.0,
            'VRCFaceTrackingEnabled': 1.0,
            
            'EyeLeftX': 0.0,
            'EyeLeftY': 0.0,
            'EyeLeftWiden': 0.0,
            'EyeLeftSquint': 0.0,
            'EyeLeftLid': 0.0,
            
            'EyeRightX': 0.0,
            'EyeRightY': 0.0,
            'EyeRightWiden': 0.0,
            'EyeRightSquint': 0.0,
            'EyeRightLid': 0.0,
            
            'BrowLeftUp': 0.0,
            'BrowLeftDown': 0.0,
            'BrowRightUp': 0.0,
            'BrowRightDown': 0.0,
            
            'JawOpen': 0.0,
            'JawForward': 0.0,
            'JawLeft': 0.0,
            'JawRight': 0.0,
            
            'MouthApeShape': 0.0,
            'MouthUpperUpLeft': 0.0,
            'MouthUpperUpRight': 0.0,
            'MouthLowerDownLeft': 0.0,
            'MouthLowerDownRight': 0.0,
            'MouthFunnel': 0.0,
            'MouthPucker': 0.0,
            
            'MouthLeft': 0.0,
            'MouthRight': 0.0,
            
            'MouthSmileLeft': 0.0,
            'MouthSmileRight': 0.0,
            'MouthFrownLeft': 0.0,
            'MouthFrownRight': 0.0,
            
            'MouthDimpleLeft': 0.0,
            'MouthDimpleRight': 0.0,
            
            'MouthUpperLeft': 0.0,
            'MouthUpperRight': 0.0,
            'MouthLowerLeft': 0.0,
            'MouthLowerRight': 0.0,
            
            'MouthPressLeft': 0.0,
            'MouthPressRight': 0.0,
            
            'MouthRaiserUpper': 0.0,
            'MouthRaiserLower': 0.0,
            
            'NostrilSqueezeLeft': 0.0,
            'NostrilSqueezeRight': 0.0,
            'NoseSneerLeft': 0.0,
            'NoseSneerRight': 0.0,
            
            'CheekPuffLeft': 0.0,
            'CheekPuffRight': 0.0,
            'CheekSquintLeft': 0.0,
            'CheekSquintRight': 0.0,
            
            'TongueLongStep1': 0.0,
            'TongueLongStep2': 0.0,
            'TongueDown': 0.0,
            'TongueUp': 0.0,
            'TongueLeft': 0.0,
            'TongueRight': 0.0,
            'TongueRoll': 0.0,
            'TongueBendDown': 0.0,
            'TongueBendUp': 0.0,
            
            'HeadPitch': 0.0,
            'HeadYaw': 0.0,
            'HeadRoll': 0.0,
        }
        
        self._init_client()

    def _init_client(self):
        try:
            self.send_client = udp_client.SimpleUDPClient(self.ip, self.send_port)
            self.connected = True
            print(f"VRChat OSC 客户端已连接: {self.ip}:{self.send_port}")
        except Exception as e:
            print(f"VRChat OSC 连接失败: {e}")
            self.connected = False

    def _init_receiver(self):
        try:
            d = dispatcher.Dispatcher()
            d.map("/avatar/parameters/*", self._handle_vrc_param)
            
            self.receive_server = osc_server.ThreadingOSCUDPServer(
                (self.ip, self.receive_port), d
            )
            
            self.receive_thread = threading.Thread(
                target=self.receive_server.serve_forever,
                daemon=True
            )
            self.receive_thread.start()
            
            print(f"VRChat OSC 接收器已启动: {self.ip}:{self.receive_port}")
        except Exception as e:
            print(f"VRChat OSC 接收器启动失败: {e}")

    def _handle_vrc_param(self, address: str, *args):
        param_name = address.split('/')[-1]
        if args and len(args) > 0:
            value = args[0]
            self.vrc_params.set_param(param_name, float(value))
            
            if self.on_param_received:
                self.on_param_received(param_name, float(value))

    def send_param(self, param_name: str, value: float):
        if not self.connected or not self.send_client:
            return
        
        try:
            value_clamped = max(0.0, min(1.0, float(value)))
            self.send_client.send_message(f"/avatar/parameters/{param_name}", value_clamped)
            self.vrc_params.set_param(param_name, value_clamped)
        except Exception as e:
            print(f"发送VRC参数失败 {param_name}: {e}")

    def send_param_float(self, param_name: str, value: float, min_val: float = -1.0, max_val: float = 1.0):
        if not self.connected or not self.send_client:
            return
        
        try:
            value_clamped = max(min_val, min(max_val, float(value)))
            self.send_client.send_message(f"/avatar/parameters/{param_name}", value_clamped)
        except Exception as e:
            print(f"发送VRC浮点参数失败 {param_name}: {e}")

    def send_bool(self, param_name: str, value: bool):
        if not self.connected or not self.send_client:
            return
        
        try:
            self.send_client.send_message(f"/avatar/parameters/{param_name}", value)
        except Exception as e:
            print(f"发送VRC布尔参数失败 {param_name}: {e}")

    def send_int(self, param_name: str, value: int, min_val: int = 0, max_val: int = 255):
        if not self.connected or not self.send_client:
            return
        
        try:
            value_clamped = max(min_val, min(max_val, int(value)))
            self.send_client.send_message(f"/avatar/parameters/{param_name}", value_clamped)
        except Exception as e:
            print(f"发送VRC整数参数失败 {param_name}: {e}")

    def send_eye_params(self, eye_left: Dict[str, float], eye_right: Dict[str, float]):
        self.send_param_float('EyeLeftX', eye_left.get('x', 0.0), -1.0, 1.0)
        self.send_param_float('EyeLeftY', eye_left.get('y', 0.0), -1.0, 1.0)
        self.send_param('EyeLeftLid', eye_left.get('lid', 0.0))
        self.send_param('EyeLeftWiden', eye_left.get('widen', 0.0))
        self.send_param('EyeLeftSquint', eye_left.get('squint', 0.0))
        
        self.send_param_float('EyeRightX', eye_right.get('x', 0.0), -1.0, 1.0)
        self.send_param_float('EyeRightY', eye_right.get('y', 0.0), -1.0, 1.0)
        self.send_param('EyeRightLid', eye_right.get('lid', 0.0))
        self.send_param('EyeRightWiden', eye_right.get('widen', 0.0))
        self.send_param('EyeRightSquint', eye_right.get('squint', 0.0))
        
        self.send_param('EyeLeftLid', eye_left.get('blink', 0.0))
        self.send_param('EyeRightLid', eye_right.get('blink', 0.0))

    def send_mouth_params(self, mouth: Dict[str, float]):
        self.send_param('JawOpen', mouth.get('jaw_open', 0.0))
        self.send_param('MouthApeShape', mouth.get('mouth_open', 0.0))
        
        smile = mouth.get('smile', 0.0)
        self.send_param('MouthSmileLeft', smile)
        self.send_param('MouthSmileRight', smile)
        
        frown = mouth.get('frown', 0.0)
        self.send_param('MouthFrownLeft', frown)
        self.send_param('MouthFrownRight', frown)
        
        wide = mouth.get('mouth_wide', 0.0)
        narrow = mouth.get('mouth_narrow', 0.0)
        self.send_param('MouthFunnel', wide)
        self.send_param('MouthPucker', narrow)
        
        upper_up = mouth.get('upper_up', 0.0)
        self.send_param('MouthUpperUpLeft', upper_up)
        self.send_param('MouthUpperUpRight', upper_up)
        
        lower_down = mouth.get('lower_down', 0.0)
        self.send_param('MouthLowerDownLeft', lower_down)
        self.send_param('MouthLowerDownRight', lower_down)

    def send_brow_params(self, brow: Dict[str, float]):
        left_up = max(0.0, brow.get('left_up', 0.0))
        left_down = max(0.0, -brow.get('left_up', 0.0))
        right_up = max(0.0, brow.get('right_up', 0.0))
        right_down = max(0.0, -brow.get('right_up', 0.0))
        
        self.send_param('BrowLeftUp', left_up)
        self.send_param('BrowLeftDown', left_down)
        self.send_param('BrowRightUp', right_up)
        self.send_param('BrowRightDown', right_down)
        
        inner_up = max(0.0, brow.get('inner_up', 0.0))
        outer_up = max(0.0, brow.get('outer_up', 0.0))
        self.send_param('BrowLeftUp', max(left_up, inner_up))
        self.send_param('BrowRightUp', max(right_up, inner_up))

    def send_head_pose(self, head_pose: Dict[str, float]):
        pitch = head_pose.get('pitch', 0.0) / 90.0
        yaw = head_pose.get('yaw', 0.0) / 90.0
        roll = head_pose.get('roll', 0.0) / 90.0
        
        self.send_param_float('HeadPitch', pitch, -1.0, 1.0)
        self.send_param_float('HeadYaw', yaw, -1.0, 1.0)
        self.send_param_float('HeadRoll', roll, -1.0, 1.0)

    def send_au_params(self, au_params: Dict[str, float]):
        au_mapping = {
            'AU1': 'BrowLeftUp',
            'AU2': 'BrowRightUp',
            'AU4': 'BrowLeftDown',
            'AU5': 'EyeLeftWiden',
            'AU6': 'CheekSquintLeft',
            'AU7': 'EyeLeftSquint',
            'AU9': 'NoseSneerLeft',
            'AU10': 'MouthRaiserUpper',
            'AU12': 'MouthSmileLeft',
            'AU14': 'MouthDimpleLeft',
            'AU15': 'MouthFrownLeft',
            'AU17': 'MouthRaiserLower',
            'AU20': 'MouthLeft',
            'AU23': 'MouthPressLeft',
            'AU25': 'MouthApeShape',
            'AU26': 'JawOpen',
            'AU27': 'MouthApeShape',
        }
        
        for au, param in au_mapping.items():
            if au in au_params:
                value = au_params[au]
                if param in self.default_params:
                    self.send_param(param, value)
                    
                    if 'Left' in param:
                        right_param = param.replace('Left', 'Right')
                        self.send_param(right_param, value)

    def send_face_tracking_enabled(self, enabled: bool = True):
        self.send_bool('VRCFaceTrackingEnabled', enabled)
        if enabled:
            self.send_param('VRCFaceBlendH', 0.0)
            self.send_param('VRCFaceBlendV', 0.0)

    def send_all_params(self, head_pose: Dict[str, float], 
                        eye_params: Dict[str, float],
                        mouth_params: Dict[str, float],
                        brow_params: Dict[str, float],
                        au_params: Optional[Dict[str, float]] = None):
        if not self.connected:
            return
        
        eye_left = {
            'x': eye_params.get('eye_x', 0.0),
            'y': eye_params.get('eye_y', 0.0),
            'blink': eye_params.get('blink_left', 0.0),
            'lid': eye_params.get('eye_open_left', 0.0),
            'widen': max(0.0, brow_params.get('brow_outer_up', 0.0)),
            'squint': max(0.0, -eye_params.get('eye_open_left', 0.0) + 0.5)
        }
        
        eye_right = {
            'x': eye_params.get('eye_x', 0.0),
            'y': eye_params.get('eye_y', 0.0),
            'blink': eye_params.get('blink_right', 0.0),
            'lid': eye_params.get('eye_open_right', 0.0),
            'widen': max(0.0, brow_params.get('brow_outer_up', 0.0)),
            'squint': max(0.0, -eye_params.get('eye_open_right', 0.0) + 0.5)
        }
        
        self.send_eye_params(eye_left, eye_right)
        self.send_mouth_params(mouth_params)
        self.send_brow_params(brow_params)
        self.send_head_pose(head_pose)
        
        if au_params:
            self.send_au_params(au_params)

    def start_receiver(self):
        if self.running:
            return
        self.running = True
        self._init_receiver()

    def stop_receiver(self):
        self.running = False
        if self.receive_server:
            self.receive_server.shutdown()
            self.receive_server.server_close()
        if self.receive_thread:
            self.receive_thread.join(timeout=1.0)

    def reconnect(self):
        self._init_client()

    def close(self):
        self.stop_receiver()
        self.connected = False


class VRChatWebSocketDriver:
    def __init__(self, host: str = "127.0.0.1", port: int = 8080):
        self.host = host
        self.port = port
        self.server = None
        self.clients = set()
        self.running = False
        self.thread = None
        
        self.message_queue = []
        
        try:
            import websockets
            import asyncio
            self.WEBSOCKETS_AVAILABLE = True
        except ImportError:
            self.WEBSOCKETS_AVAILABLE = False
            print("websockets 库未安装，WebSocket功能不可用")

    async def _handle_client(self, websocket):
        self.clients.add(websocket)
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    self.message_queue.append(data)
                except json.JSONDecodeError:
                    pass
        finally:
            self.clients.remove(websocket)

    async def _broadcast(self, data: dict):
        if not self.clients:
            return
        
        message = json.dumps(data)
        for client in list(self.clients):
            try:
                await client.send(message)
            except:
                pass

    def broadcast(self, data: dict):
        if not self.WEBSOCKETS_AVAILABLE:
            return
        
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._broadcast(data))
            loop.close()
        except Exception as e:
            print(f"WebSocket广播失败: {e}")

    def send_vrc_params(self, params: dict):
        self.broadcast({
            'type': 'vrc_params',
            'data': params,
            'timestamp': time.time()
        })

    def send_face_data(self, face_data: dict):
        self.broadcast({
            'type': 'face_data',
            'data': face_data,
            'timestamp': time.time()
        })

    async def _start_server(self):
        import websockets
        async with websockets.serve(self._handle_client, self.host, self.port):
            print(f"WebSocket服务器已启动: ws://{self.host}:{self.port}")
            await asyncio.Future()

    def start(self):
        if not self.WEBSOCKETS_AVAILABLE or self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run_server, daemon=True)
        self.thread.start()

    def _run_server(self):
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._start_server())
        except Exception as e:
            print(f"WebSocket服务器错误: {e}")

    def stop(self):
        self.running = False
        for client in list(self.clients):
            client.close()
        if self.thread:
            self.thread.join(timeout=1.0)
