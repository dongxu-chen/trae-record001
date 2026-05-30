import os
import numpy as np
import tensorrt as trt
import pycuda.driver as cuda
import pycuda.autoinit
from typing import List, Tuple, Optional

TRT_LOGGER = trt.Logger(trt.Logger.WARNING)


class HostDeviceMem:
    def __init__(self, host_mem, device_mem):
        self.host = host_mem
        self.device = device_mem

    def __str__(self):
        return "Host:\n" + str(self.host) + "\nDevice:\n" + str(self.device)

    def __repr__(self):
        return self.__str__()


class TensorRTEngine:
    def __init__(self, engine_path: str, batch_size: int = 1):
        self.engine_path = engine_path
        self.batch_size = batch_size
        self.engine = None
        self.context = None
        self.inputs = []
        self.outputs = []
        self.bindings = []
        self.stream = None
        self._load_engine()

    def _load_engine(self):
        if not os.path.exists(self.engine_path):
            raise FileNotFoundError(f"TensorRT engine not found: {self.engine_path}")

        with open(self.engine_path, 'rb') as f, trt.Runtime(TRT_LOGGER) as runtime:
            self.engine = runtime.deserialize_cuda_engine(f.read())
        
        self.context = self.engine.create_execution_context()
        self.stream = cuda.Stream()
        
        for binding in self.engine:
            binding_idx = self.engine.get_binding_index(binding)
            size = trt.volume(self.engine.get_binding_shape(binding_idx)) * self.batch_size
            dtype = trt.nptype(self.engine.get_binding_dtype(binding_idx))
            
            host_mem = cuda.pagelocked_empty(size, dtype)
            device_mem = cuda.mem_alloc(host_mem.nbytes)
            
            self.bindings.append(int(device_mem))
            
            if self.engine.binding_is_input(binding):
                self.inputs.append(HostDeviceMem(host_mem, device_mem))
            else:
                self.outputs.append(HostDeviceMem(host_mem, device_mem))

    def infer(self, input_data: np.ndarray) -> np.ndarray:
        if input_data.shape[0] != self.batch_size:
            raise ValueError(f"Input batch size {input_data.shape[0]} != engine batch size {self.batch_size}")
        
        self.inputs[0].host = np.ascontiguousarray(input_data.ravel())
        
        [cuda.memcpy_htod_async(inp.device, inp.host, self.stream) for inp in self.inputs]
        
        self.context.execute_async_v2(bindings=self.bindings, stream_handle=self.stream.handle)
        
        [cuda.memcpy_dtoh_async(out.host, out.device, self.stream) for out in self.outputs]
        
        self.stream.synchronize()
        
        outputs = [out.host.reshape(self.batch_size, -1) for out in self.outputs]
        return outputs[0]

    def infer_batch(self, input_data: np.ndarray) -> np.ndarray:
        if len(input_data.shape) == 3:
            input_data = np.expand_dims(input_data, axis=0)
        
        batch_size = input_data.shape[0]
        output_size = self.engine.get_binding_shape(1)[1:]
        output_shape = [batch_size] + list(output_size)
        outputs = np.zeros(output_shape, dtype=np.float32)
        
        for i in range(0, batch_size, self.batch_size):
            end = min(i + self.batch_size, batch_size)
            chunk = input_data[i:end]
            
            if chunk.shape[0] < self.batch_size:
                padded = np.zeros((self.batch_size,) + chunk.shape[1:], dtype=np.float32)
                padded[:chunk.shape[0]] = chunk
                chunk = padded
            
            result = self.infer(chunk)
            result = result.reshape((self.batch_size,) + tuple(output_size))
            outputs[i:end] = result[:end - i]
        
        return outputs

    def __del__(self):
        if self.stream:
            del self.stream
        if self.context:
            del self.context
        if self.engine:
            del self.engine


class TensorRTBuilder:
    def __init__(self, max_batch_size: int = 8, fp16: bool = True, int8: bool = False):
        self.max_batch_size = max_batch_size
        self.fp16 = fp16
        self.int8 = int8
        self.calibration_data = None

    def set_calibration_data(self, data: np.ndarray):
        self.calibration_data = data

    def build_engine(self, onnx_model_path: str, save_path: str, 
                     input_shape: Tuple[int, int, int] = (3, 256, 256)) -> bool:
        if not os.path.exists(onnx_model_path):
            raise FileNotFoundError(f"ONNX model not found: {onnx_model_path}")
        
        builder = trt.Builder(TRT_LOGGER)
        network = builder.create_network(1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH))
        parser = trt.OnnxParser(network, TRT_LOGGER)
        
        with open(onnx_model_path, 'rb') as model:
            if not parser.parse(model.read()):
                print("ERROR: Failed to parse ONNX model")
                for error in range(parser.num_errors):
                    print(parser.get_error(error))
                return False
        
        config = builder.create_builder_config()
        config.max_workspace_size = 1 << 30
        
        profile = builder.create_optimization_profile()
        input_name = network.get_input(0).name
        min_shape = (1,) + input_shape
        opt_shape = (self.max_batch_size // 2,) + input_shape
        max_shape = (self.max_batch_size,) + input_shape
        profile.set_shape(input_name, min_shape, opt_shape, max_shape)
        config.add_optimization_profile(profile)
        
        if self.fp16 and builder.platform_has_fast_fp16:
            config.set_flag(trt.BuilderFlag.FP16)
            print("Using FP16 precision")
        
        if self.int8 and builder.platform_has_fast_int8:
            if self.calibration_data is None:
                print("WARNING: No calibration data provided, skipping INT8")
            else:
                config.set_flag(trt.BuilderFlag.INT8)
                config.int8_calibrator = self._get_calibrator(input_shape)
                print("Using INT8 precision")
        
        print("Building TensorRT engine...")
        serialized_engine = builder.build_serialized_network(network, config)
        
        if serialized_engine is None:
            print("ERROR: Failed to build engine")
            return False
        
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with open(save_path, 'wb') as f:
            f.write(serialized_engine)
        
        print(f"TensorRT engine saved to: {save_path}")
        return True

    def _get_calibrator(self, input_shape):
        class Calibrator(trt.IInt8EntropyCalibrator2):
            def __init__(self, data, input_shape):
                super().__init__()
                self.data = data
                self.input_shape = input_shape
                self.batch_size = 1
                self.current_idx = 0
                self.device_input = cuda.mem_alloc(
                    self.batch_size * input_shape[0] * input_shape[1] * input_shape[2] * 4
                )
            
            def get_batch_size(self):
                return self.batch_size
            
            def get_batch(self, names):
                if self.current_idx + self.batch_size > self.data.shape[0]:
                    return None
                
                batch = self.data[self.current_idx:self.current_idx + self.batch_size]
                self.current_idx += self.batch_size
                
                cuda.memcpy_htod(self.device_input, batch)
                return [int(self.device_input)]
            
            def read_calibration_cache(self):
                return None
            
            def write_calibration_cache(self, cache):
                return None
        
        return Calibrator(self.calibration_data, input_shape)


def convert_onnx_to_tensorrt(
    onnx_path: str,
    output_path: str,
    max_batch_size: int = 8,
    fp16: bool = True,
    int8: bool = False,
    input_shape: Tuple[int, int, int] = (3, 256, 256)
) -> bool:
    builder = TensorRTBuilder(max_batch_size=max_batch_size, fp16=fp16, int8=int8)
    return builder.build_engine(onnx_path, output_path, input_shape)


def load_tensorrt_engine(engine_path: str, batch_size: int = 1) -> Optional[TensorRTEngine]:
    try:
        return TensorRTEngine(engine_path, batch_size)
    except Exception as e:
        print(f"Failed to load TensorRT engine: {e}")
        return None
