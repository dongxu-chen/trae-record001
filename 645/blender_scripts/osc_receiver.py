import bpy
from pythonosc import dispatcher
from pythonosc import osc_server
import threading
from typing import Dict, Callable


class FaceOSCReceiver:
    def __init__(self, ip: str = "127.0.0.1", port: int = 9000):
        self.ip = ip
        self.port = port
        self.server = None
        self.server_thread = None
        self.running = False
        
        self.head_pose: Dict[str, float] = {
            'pitch': 0.0,
            'yaw': 0.0,
            'roll': 0.0
        }
        
        self.eye_params: Dict[str, float] = {
            'open_left': 0.5,
            'open_right': 0.5,
            'x': 0.0,
            'y': 0.0,
            'blink_left': 0.0,
            'blink_right': 0.0
        }
        
        self.mouth_params: Dict[str, float] = {
            'open': 0.0,
            'jaw_open': 0.0,
            'wide': 0.0,
            'narrow': 0.0,
            'smile': 0.0,
            'frown': 0.0
        }
        
        self.brow_params: Dict[str, float] = {
            'inner_up': 0.0,
            'outer_up': 0.0,
            'left_up': 0.0,
            'right_up': 0.0
        }
        
        self.target_objects: Dict[str, str] = {
            'head_bone': 'head',
            'eye_left_bone': 'eye.L',
            'eye_right_bone': 'eye.R',
            'jaw_bone': 'jaw',
        }
        
        self.shape_keys: Dict[str, str] = {
            'eye_blink_left': 'Blink_L',
            'eye_blink_right': 'Blink_R',
            'eye_open_left': 'Eye_Open_L',
            'eye_open_right': 'Eye_Open_R',
            'mouth_open': 'Mouth_Open',
            'mouth_wide': 'Mouth_Wide',
            'mouth_narrow': 'Mouth_Narrow',
            'smile_left': 'Smile_L',
            'smile_right': 'Smile_R',
            'frown': 'Frown',
            'brow_inner_up': 'Brow_Inner_Up',
            'brow_outer_up': 'Brow_Outer_Up',
        }
        
        self.scale_factors: Dict[str, float] = {
            'head_rotation': 0.01,
            'eye_rotation': 0.02,
        }
        
        self.dispatcher = dispatcher.Dispatcher()
        self._register_handlers()

    def _register_handlers(self):
        self.dispatcher.map("/head/pitch", self._handle_head_pitch)
        self.dispatcher.map("/head/yaw", self._handle_head_yaw)
        self.dispatcher.map("/head/roll", self._handle_head_roll)
        
        self.dispatcher.map("/eye/open_left", self._handle_eye_open_left)
        self.dispatcher.map("/eye/open_right", self._handle_eye_open_right)
        self.dispatcher.map("/eye/x", self._handle_eye_x)
        self.dispatcher.map("/eye/y", self._handle_eye_y)
        self.dispatcher.map("/eye/blink_left", self._handle_blink_left)
        self.dispatcher.map("/eye/blink_right", self._handle_blink_right)
        
        self.dispatcher.map("/mouth/open", self._handle_mouth_open)
        self.dispatcher.map("/mouth/jaw_open", self._handle_jaw_open)
        self.dispatcher.map("/mouth/wide", self._handle_mouth_wide)
        self.dispatcher.map("/mouth/narrow", self._handle_mouth_narrow)
        self.dispatcher.map("/mouth/smile", self._handle_smile)
        self.dispatcher.map("/mouth/frown", self._handle_frown)
        
        self.dispatcher.map("/brow/inner_up", self._handle_brow_inner_up)
        self.dispatcher.map("/brow/outer_up", self._handle_brow_outer_up)
        self.dispatcher.map("/brow/left_up", self._handle_brow_left_up)
        self.dispatcher.map("/brow/right_up", self._handle_brow_right_up)

    def _handle_head_pitch(self, address: str, *args):
        self.head_pose['pitch'] = args[0]
        self._update_head_rotation()

    def _handle_head_yaw(self, address: str, *args):
        self.head_pose['yaw'] = args[0]
        self._update_head_rotation()

    def _handle_head_roll(self, address: str, *args):
        self.head_pose['roll'] = args[0]
        self._update_head_rotation()

    def _handle_eye_open_left(self, address: str, *args):
        self.eye_params['open_left'] = args[0]
        self._update_eye_shapes()

    def _handle_eye_open_right(self, address: str, *args):
        self.eye_params['open_right'] = args[0]
        self._update_eye_shapes()

    def _handle_eye_x(self, address: str, *args):
        self.eye_params['x'] = args[0]
        self._update_eye_rotation()

    def _handle_eye_y(self, address: str, *args):
        self.eye_params['y'] = args[0]
        self._update_eye_rotation()

    def _handle_blink_left(self, address: str, *args):
        self.eye_params['blink_left'] = args[0]
        self._update_eye_shapes()

    def _handle_blink_right(self, address: str, *args):
        self.eye_params['blink_right'] = args[0]
        self._update_eye_shapes()

    def _handle_mouth_open(self, address: str, *args):
        self.mouth_params['open'] = args[0]
        self._update_mouth_shapes()

    def _handle_jaw_open(self, address: str, *args):
        self.mouth_params['jaw_open'] = args[0]
        self._update_jaw_rotation()

    def _handle_mouth_wide(self, address: str, *args):
        self.mouth_params['wide'] = args[0]
        self._update_mouth_shapes()

    def _handle_mouth_narrow(self, address: str, *args):
        self.mouth_params['narrow'] = args[0]
        self._update_mouth_shapes()

    def _handle_smile(self, address: str, *args):
        self.mouth_params['smile'] = args[0]
        self._update_mouth_shapes()

    def _handle_frown(self, address: str, *args):
        self.mouth_params['frown'] = args[0]
        self._update_mouth_shapes()

    def _handle_brow_inner_up(self, address: str, *args):
        self.brow_params['inner_up'] = args[0]
        self._update_brow_shapes()

    def _handle_brow_outer_up(self, address: str, *args):
        self.brow_params['outer_up'] = args[0]
        self._update_brow_shapes()

    def _handle_brow_left_up(self, address: str, *args):
        self.brow_params['left_up'] = args[0]
        self._update_brow_shapes()

    def _handle_brow_right_up(self, address: str, *args):
        self.brow_params['right_up'] = args[0]
        self._update_brow_shapes()

    def _update_head_rotation(self):
        head_bone_name = self.target_objects.get('head_bone')
        if not head_bone_name:
            return
        
        for obj in bpy.data.objects:
            if obj.type == 'ARMATURE':
                bone = obj.pose.bones.get(head_bone_name)
                if bone:
                    scale = self.scale_factors['head_rotation']
                    bone.rotation_euler[0] = self.head_pose['pitch'] * scale
                    bone.rotation_euler[1] = self.head_pose['yaw'] * scale
                    bone.rotation_euler[2] = self.head_pose['roll'] * scale
                    break

    def _update_eye_rotation(self):
        eye_l_name = self.target_objects.get('eye_left_bone')
        eye_r_name = self.target_objects.get('eye_right_bone')
        
        for obj in bpy.data.objects:
            if obj.type == 'ARMATURE':
                scale = self.scale_factors['eye_rotation']
                
                if eye_l_name:
                    bone_l = obj.pose.bones.get(eye_l_name)
                    if bone_l:
                        bone_l.rotation_euler[0] = -self.eye_params['y'] * scale
                        bone_l.rotation_euler[1] = self.eye_params['x'] * scale
                
                if eye_r_name:
                    bone_r = obj.pose.bones.get(eye_r_name)
                    if bone_r:
                        bone_r.rotation_euler[0] = -self.eye_params['y'] * scale
                        bone_r.rotation_euler[1] = self.eye_params['x'] * scale
                break

    def _update_eye_shapes(self):
        mesh_obj = self._get_mesh_object()
        if not mesh_obj or not mesh_obj.data.shape_keys:
            return
        
        kb = mesh_obj.data.shape_keys.key_blocks
        
        blink_l = self.shape_keys.get('eye_blink_left')
        blink_r = self.shape_keys.get('eye_blink_right')
        
        if blink_l and blink_l in kb:
            kb[blink_l].value = self.eye_params['blink_left']
        if blink_r and blink_r in kb:
            kb[blink_r].value = self.eye_params['blink_right']

    def _update_jaw_rotation(self):
        jaw_bone_name = self.target_objects.get('jaw_bone')
        if not jaw_bone_name:
            return
        
        for obj in bpy.data.objects:
            if obj.type == 'ARMATURE':
                bone = obj.pose.bones.get(jaw_bone_name)
                if bone:
                    bone.rotation_euler[0] = self.mouth_params['jaw_open'] * 0.05
                    break

    def _update_mouth_shapes(self):
        mesh_obj = self._get_mesh_object()
        if not mesh_obj or not mesh_obj.data.shape_keys:
            return
        
        kb = mesh_obj.data.shape_keys.key_blocks
        
        mouth_open = self.shape_keys.get('mouth_open')
        mouth_wide = self.shape_keys.get('mouth_wide')
        mouth_narrow = self.shape_keys.get('mouth_narrow')
        smile_l = self.shape_keys.get('smile_left')
        smile_r = self.shape_keys.get('smile_right')
        frown = self.shape_keys.get('frown')
        
        if mouth_open and mouth_open in kb:
            kb[mouth_open].value = self.mouth_params['open']
        if mouth_wide and mouth_wide in kb:
            kb[mouth_wide].value = self.mouth_params['wide']
        if mouth_narrow and mouth_narrow in kb:
            kb[mouth_narrow].value = self.mouth_params['narrow']
        if smile_l and smile_l in kb:
            kb[smile_l].value = self.mouth_params['smile']
        if smile_r and smile_r in kb:
            kb[smile_r].value = self.mouth_params['smile']
        if frown and frown in kb:
            kb[frown].value = self.mouth_params['frown']

    def _update_brow_shapes(self):
        mesh_obj = self._get_mesh_object()
        if not mesh_obj or not mesh_obj.data.shape_keys:
            return
        
        kb = mesh_obj.data.shape_keys.key_blocks
        
        brow_inner = self.shape_keys.get('brow_inner_up')
        brow_outer = self.shape_keys.get('brow_outer_up')
        
        if brow_inner and brow_inner in kb:
            kb[brow_inner].value = max(0.0, self.brow_params['inner_up'])
        if brow_outer and brow_outer in kb:
            kb[brow_outer].value = max(0.0, self.brow_params['outer_up'])

    def _get_mesh_object(self):
        for obj in bpy.data.objects:
            if obj.type == 'MESH' and obj.data.shape_keys:
                return obj
        return None

    def start(self):
        if self.running:
            return
        
        self.server = osc_server.ThreadingOSCUDPServer((self.ip, self.port), self.dispatcher)
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()
        self.running = True
        print(f"OSC接收器已启动: {self.ip}:{self.port}")

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        self.running = False
        print("OSC接收器已停止")


osc_receiver_instance = None


def start_osc_receiver():
    global osc_receiver_instance
    osc_receiver_instance = FaceOSCReceiver()
    osc_receiver_instance.start()


def stop_osc_receiver():
    global osc_receiver_instance
    if osc_receiver_instance:
        osc_receiver_instance.stop()
        osc_receiver_instance = None


class OSC_OT_StartReceiver(bpy.types.Operator):
    bl_idname = "osc.start_receiver"
    bl_label = "启动OSC接收"
    bl_description = "启动面部捕捉OSC接收器"

    def execute(self, context):
        start_osc_receiver()
        return {'FINISHED'}


class OSC_OT_StopReceiver(bpy.types.Operator):
    bl_idname = "osc.stop_receiver"
    bl_label = "停止OSC接收"
    bl_description = "停止面部捕捉OSC接收器"

    def execute(self, context):
        stop_osc_receiver()
        return {'FINISHED'}


class FACE_PT_MocapPanel(bpy.types.Panel):
    bl_label = "面部动画面板"
    bl_idname = "FACE_PT_mocap_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = '面部捕捉'

    def draw(self, context):
        layout = self.layout
        
        box = layout.box()
        box.label(text="OSC控制")
        row = box.row(align=True)
        row.operator("osc.start_receiver", icon='PLAY')
        row.operator("osc.stop_receiver", icon='PAUSE')
        
        box = layout.box()
        box.label(text="骨骼映射")
        col = box.column()
        col.prop(context.scene, "face_mocap_head_bone")
        col.prop(context.scene, "face_mocap_eye_l_bone")
        col.prop(context.scene, "face_mocap_eye_r_bone")
        col.prop(context.scene, "face_mocap_jaw_bone")
        
        box = layout.box()
        box.label(text="缩放参数")
        col = box.column()
        col.prop(context.scene, "face_mocap_head_scale")
        col.prop(context.scene, "face_mocap_eye_scale")


def register():
    bpy.utils.register_class(OSC_OT_StartReceiver)
    bpy.utils.register_class(OSC_OT_StopReceiver)
    bpy.utils.register_class(FACE_PT_MocapPanel)
    
    bpy.types.Scene.face_mocap_head_bone = bpy.props.StringProperty(
        name="头部骨骼", default="head"
    )
    bpy.types.Scene.face_mocap_eye_l_bone = bpy.props.StringProperty(
        name="左眼骨骼", default="eye.L"
    )
    bpy.types.Scene.face_mocap_eye_r_bone = bpy.props.StringProperty(
        name="右眼骨骼", default="eye.R"
    )
    bpy.types.Scene.face_mocap_jaw_bone = bpy.props.StringProperty(
        name="下颚骨骼", default="jaw"
    )
    bpy.types.Scene.face_mocap_head_scale = bpy.props.FloatProperty(
        name="头部旋转缩放", default=0.01, min=0.001, max=0.1
    )
    bpy.types.Scene.face_mocap_eye_scale = bpy.props.FloatProperty(
        name="眼球旋转缩放", default=0.02, min=0.001, max=0.1
    )


def unregister():
    bpy.utils.unregister_class(OSC_OT_StartReceiver)
    bpy.utils.unregister_class(OSC_OT_StopReceiver)
    bpy.utils.unregister_class(FACE_PT_MocapPanel)
    
    del bpy.types.Scene.face_mocap_head_bone
    del bpy.types.Scene.face_mocap_eye_l_bone
    del bpy.types.Scene.face_mocap_eye_r_bone
    del bpy.types.Scene.face_mocap_jaw_bone
    del bpy.types.Scene.face_mocap_head_scale
    del bpy.types.Scene.face_mocap_eye_scale


if __name__ == "__main__":
    register()
