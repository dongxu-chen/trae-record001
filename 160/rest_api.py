import asyncio
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from contextlib import asynccontextmanager
import threading

from brainflow_acquisition import DataAcquisition, DeviceType, DEVICE_CONFIG
from signal_processing import RealtimePipeline
from lsl_integration import LSLOutput, LSLStreamInfo, BandPowerLSLOutput


class GlobalState:
    def __init__(self):
        self.acquisition: Optional[DataAcquisition] = None
        self.pipeline: Optional[RealtimePipeline] = None
        self.lsl_output: Optional[LSLOutput] = None
        self.bandpower_lsl: Optional[BandPowerLSLOutput] = None
        self.lock = threading.Lock()
        self.api_enabled = False
        
    def is_connected(self) -> bool:
        return self.acquisition is not None and self.acquisition._is_running
        
    def is_streaming(self) -> bool:
        return self.acquisition is not None and self.acquisition._is_streaming


global_state = GlobalState()


class ConnectRequest(BaseModel):
    device_type: str = "synthetic"
    serial_port: str = ""
    ip_address: str = ""
    ip_port: int = 0


class FilterConfig(BaseModel):
    low_freq: float = 1.0
    high_freq: float = 50.0
    notch_freq: float = 50.0


class LSLConfig(BaseModel):
    stream_name: str = "EEG_Stream"
    stream_type: str = "EEG"
    enabled: bool = True


class APIResponse(BaseModel):
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None


def create_app(state: GlobalState) -> FastAPI:
    
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        state.api_enabled = True
        yield
        state.api_enabled = False
        if state.is_streaming():
            state.acquisition.stop_stream()
            state.acquisition.disconnect()
        if state.lsl_output:
            state.lsl_output.close()
        if state.bandpower_lsl:
            state.bandpower_lsl.close()
    
    app = FastAPI(
        title="EEG Processing Toolbox API",
        description="基于BrainFlow的实时脑电信号处理工具包REST API",
        version="2.0.0",
        lifespan=lifespan
    )
    
    @app.get("/", response_model=APIResponse)
    async def root():
        return APIResponse(
            status="ok",
            message="EEG Processing Toolbox API is running",
            data={"version": "2.0.0"}
        )
    
    @app.get("/devices", response_model=APIResponse)
    async def get_available_devices():
        devices = DataAcquisition.get_available_devices()
        return APIResponse(
            status="ok",
            message="Available devices",
            data={"devices": devices}
        )
    
    @app.post("/connect", response_model=APIResponse)
    async def connect_device(req: ConnectRequest):
        with state.lock:
            if state.is_connected():
                return APIResponse(
                    status="warning",
                    message="Device already connected"
                )
                
            try:
                device_enum = DeviceType(req.device_type)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid device type: {req.device_type}"
                )
                
            state.acquisition = DataAcquisition(device_enum)
            
            connected = state.acquisition.connect(
                serial_port=req.serial_port,
                ip_address=req.ip_address,
                ip_port=req.ip_port
            )
            
            if connected:
                sampling_rate = state.acquisition.get_sampling_rate()
                num_channels = state.acquisition.get_num_channels()
                
                state.pipeline = RealtimePipeline(sampling_rate, num_channels)
                
                def process_callback(eeg_data):
                    filtered = state.pipeline.process_sample(eeg_data)
                    if state.lsl_output and state.lsl_output.outlet:
                        state.lsl_output.push_sample(filtered)
                
                state.acquisition.add_callback(process_callback)
                
                return APIResponse(
                    status="ok",
                    message="Device connected successfully",
                    data={
                        "device": DEVICE_CONFIG[device_enum]["name"],
                        "sampling_rate": sampling_rate,
                        "num_channels": num_channels
                    }
                )
            else:
                state.acquisition = None
                raise HTTPException(status_code=500, detail="Failed to connect device")
    
    @app.post("/start_stream", response_model=APIResponse)
    async def start_stream():
        with state.lock:
            if not state.is_connected():
                raise HTTPException(status_code=400, detail="No device connected")
                
            if state.is_streaming():
                return APIResponse(status="warning", message="Already streaming")
                
            started = state.acquisition.start_stream()
            
            if started:
                return APIResponse(
                    status="ok",
                    message="Streaming started"
                )
            else:
                raise HTTPException(status_code=500, detail="Failed to start stream")
    
    @app.post("/stop_stream", response_model=APIResponse)
    async def stop_stream():
        with state.lock:
            if state.is_streaming():
                state.acquisition.stop_stream()
                return APIResponse(status="ok", message="Streaming stopped")
            return APIResponse(status="warning", message="Not streaming")
    
    @app.post("/disconnect", response_model=APIResponse)
    async def disconnect_device():
        with state.lock:
            if state.is_connected():
                state.acquisition.disconnect()
                state.acquisition = None
                state.pipeline = None
                return APIResponse(status="ok", message="Device disconnected")
            return APIResponse(status="warning", message="No device connected")
    
    @app.get("/status", response_model=APIResponse)
    async def get_status():
        with state.lock:
            return APIResponse(
                status="ok",
                message="Current status",
                data={
                    "connected": state.is_connected(),
                    "streaming": state.is_streaming(),
                    "lsl_output": state.lsl_output is not None and state.lsl_output.outlet is not None
                }
            )
    
    @app.get("/data/latest", response_model=APIResponse)
    async def get_latest_data(num_samples: int = 100):
        with state.lock:
            if not state.is_connected():
                raise HTTPException(status_code=400, detail="No device connected")
                
            eeg_data, times = state.acquisition.get_latest_data(num_samples)
            
            if eeg_data.size == 0:
                return APIResponse(
                    status="warning",
                    message="No data available",
                    data={"samples": 0}
                )
                
            return APIResponse(
                status="ok",
                message=f"Retrieved {eeg_data.shape[1]} samples",
                data={
                    "num_channels": eeg_data.shape[0],
                    "num_samples": eeg_data.shape[1],
                    "data": eeg_data.tolist(),
                    "timestamps": times.tolist()
                }
            )
    
    @app.get("/bandpower", response_model=APIResponse)
    async def get_band_powers():
        with state.lock:
            if not state.pipeline:
                raise HTTPException(status_code=400, detail="Pipeline not initialized")
                
            filtered_data = state.pipeline.get_filtered_data(num_samples=512)
            
            if filtered_data.size == 0:
                return APIResponse(status="warning", message="Not enough data")
                
            band_powers = {}
            for i in range(filtered_data.shape[0]):
                channel_data = filtered_data[i]
                ch_bands = state.pipeline.band_extractor.compute_band_powers(channel_data)
                band_powers[f"channel_{i}"] = ch_bands
                
            return APIResponse(
                status="ok",
                message="Band powers computed",
                data=band_powers
            )
    
    @app.post("/lsl/start", response_model=APIResponse)
    async def start_lsl_output(config: LSLConfig):
        with state.lock:
            if not state.is_connected():
                raise HTTPException(status_code=400, detail="No device connected")
                
            if state.lsl_output:
                state.lsl_output.close()
                
            stream_info = LSLStreamInfo(
                name=config.stream_name,
                type=config.stream_type,
                channel_count=state.acquisition.get_num_channels(),
                sampling_rate=state.acquisition.get_sampling_rate(),
                channel_format="float32"
            )
            
            state.lsl_output = LSLOutput(stream_info)
            
            if state.lsl_output.create_stream():
                return APIResponse(
                    status="ok",
                    message="LSL output stream created",
                    data={
                        "stream_name": config.stream_name,
                        "num_channels": state.acquisition.get_num_channels()
                    }
                )
            else:
                state.lsl_output = None
                raise HTTPException(status_code=500, detail="Failed to create LSL stream")
    
    @app.post("/lsl/stop", response_model=APIResponse)
    async def stop_lsl_output():
        with state.lock:
            if state.lsl_output:
                state.lsl_output.close()
                state.lsl_output = None
                return APIResponse(status="ok", message="LSL output stopped")
            return APIResponse(status="warning", message="LSL output not active")
    
    @app.post("/lsl/bandpower/start", response_model=APIResponse)
    async def start_bandpower_lsl():
        with state.lock:
            if not state.pipeline:
                raise HTTPException(status_code=400, detail="Pipeline not initialized")
                
            state.bandpower_lsl = BandPowerLSLOutput()
            
            if state.bandpower_lsl.initialize():
                def bandpower_callback(data, band_powers):
                    state.bandpower_lsl.push_band_powers(band_powers)
                    
                state.pipeline.add_callback(bandpower_callback)
                
                return APIResponse(status="ok", message="BandPower LSL stream started")
            else:
                state.bandpower_lsl = None
                raise HTTPException(status_code=500, detail="Failed to create BandPower LSL stream")
    
    @app.post("/lsl/bandpower/stop", response_model=APIResponse)
    async def stop_bandpower_lsl():
        with state.lock:
            if state.bandpower_lsl:
                state.bandpower_lsl.close()
                state.bandpower_lsl = None
                return APIResponse(status="ok", message="BandPower LSL stream stopped")
            return APIResponse(status="warning", message="BandPower LSL not active")
    
    return app


def run_api_server(host: str = "0.0.0.0", port: int = 8000):
    import uvicorn
    app = create_app(global_state)
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_api_server()
