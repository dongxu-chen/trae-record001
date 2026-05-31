from pythonosc import udp_client
from typing import Dict, Optional


class OSCSender:
    def __init__(self, ip: str = "127.0.0.1", port: int = 9000):
        self.ip = ip
        self.port = port
        self.client = None
        self.connected = False
        self._connect()

    def _connect(self):
        try:
            self.client = udp_client.SimpleUDPClient(self.ip, self.port)
            self.connected = True
        except Exception as e:
            print(f"OSC连接失败: {e}")
            self.connected = False

    def send_head_pose(self, pitch: float, yaw: float, roll: float):
        if not self.connected:
            return
        try:
            self.client.send_message("/head/pitch", pitch)
            self.client.send_message("/head/yaw", yaw)
            self.client.send_message("/head/roll", roll)
        except Exception as e:
            print(f"发送头部姿态失败: {e}")

    def send_eye_params(self, eye_open_left: float, eye_open_right: float, 
                        eye_x: float, eye_y: float,
                        blink_left: float, blink_right: float):
        if not self.connected:
            return
        try:
            self.client.send_message("/eye/open_left", eye_open_left)
            self.client.send_message("/eye/open_right", eye_open_right)
            self.client.send_message("/eye/x", eye_x)
            self.client.send_message("/eye/y", eye_y)
            self.client.send_message("/eye/blink_left", blink_left)
            self.client.send_message("/eye/blink_right", blink_right)
        except Exception as e:
            print(f"发送眼部参数失败: {e}")

    def send_mouth_params(self, mouth_open: float, jaw_open: float,
                          mouth_wide: float, mouth_narrow: float,
                          smile: float, frown: float):
        if not self.connected:
            return
        try:
            self.client.send_message("/mouth/open", mouth_open)
            self.client.send_message("/mouth/jaw_open", jaw_open)
            self.client.send_message("/mouth/wide", mouth_wide)
            self.client.send_message("/mouth/narrow", mouth_narrow)
            self.client.send_message("/mouth/smile", smile)
            self.client.send_message("/mouth/frown", frown)
        except Exception as e:
            print(f"发送嘴部参数失败: {e}")

    def send_eyebrow_params(self, brow_inner_up: float, brow_outer_up: float,
                            brow_left_up: float, brow_right_up: float):
        if not self.connected:
            return
        try:
            self.client.send_message("/brow/inner_up", brow_inner_up)
            self.client.send_message("/brow/outer_up", brow_outer_up)
            self.client.send_message("/brow/left_up", brow_left_up)
            self.client.send_message("/brow/right_up", brow_right_up)
        except Exception as e:
            print(f"发送眉毛参数失败: {e}")

    def send_all_params(self, head_pose: Dict[str, float], expressions: Dict[str, float]):
        if not self.connected:
            return
        
        self.send_head_pose(
            head_pose.get('pitch', 0.0),
            head_pose.get('yaw', 0.0),
            head_pose.get('roll', 0.0)
        )
        
        self.send_eye_params(
            expressions.get('eye_open_left', 0.5),
            expressions.get('eye_open_right', 0.5),
            expressions.get('eye_x', 0.0),
            expressions.get('eye_y', 0.0),
            expressions.get('blink_left', 0.0),
            expressions.get('blink_right', 0.0)
        )
        
        self.send_mouth_params(
            expressions.get('mouth_open', 0.0),
            expressions.get('jaw_open', 0.0),
            expressions.get('mouth_wide', 0.0),
            expressions.get('mouth_narrow', 0.0),
            expressions.get('smile', 0.0),
            expressions.get('frown', 0.0)
        )
        
        self.send_eyebrow_params(
            expressions.get('brow_inner_up', 0.0),
            expressions.get('brow_outer_up', 0.0),
            expressions.get('brow_left_up', 0.0),
            expressions.get('brow_right_up', 0.0)
        )

    def send_custom(self, address: str, value: float):
        if not self.connected:
            return
        try:
            self.client.send_message(address, value)
        except Exception as e:
            print(f"发送自定义数据失败: {e}")

    def reconnect(self, ip: Optional[str] = None, port: Optional[int] = None):
        if ip:
            self.ip = ip
        if port:
            self.port = port
        self._connect()

    def close(self):
        self.connected = False
