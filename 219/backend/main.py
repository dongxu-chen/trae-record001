from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
import json
from typing import List, Optional, Dict
from datetime import datetime
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from .models import BusGPSData, HeatmapResponse, UploadResponse
from .utils import (
    parse_gps_data, process_heatmap_data, generate_heatmap_image,
    calculate_bounds_from_data, generate_time_windows,
    get_congestion_alerts, get_route_trajectory, get_all_routes,
    compare_time_windows, lonlat_to_pixel
)

app = FastAPI(title="交通流量热力图API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

current_data = {
    "df": None,
    "city": "",
    "heatmap_result": None,
    "bounds": None,
    "pre_generated_images": {},
    "pre_generation_complete": False,
    "pre_generation_progress": 0
}

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
CACHE_DIR = os.path.join(DATA_DIR, "tile_cache")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)


@app.get("/", response_class=HTMLResponse)
async def root():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return {"message": "交通流量热力图API服务运行中"}


@app.post("/api/upload", response_model=UploadResponse)
async def upload_gps_data(
    file: UploadFile = File(...),
    city: str = Query(..., description="城市名称")
):
    try:
        content = await file.read()
        data = json.loads(content.decode("utf-8"))
        
        if isinstance(data, dict) and "data" in data:
            data_list = data["data"]
        elif isinstance(data, list):
            data_list = data
        else:
            raise HTTPException(status_code=400, detail="数据格式错误，应为数组或包含data字段的对象")
        
        df = parse_gps_data(data_list)
        
        if len(df) == 0:
            raise HTTPException(status_code=400, detail="未解析到有效数据")
        
        current_data["df"] = df
        current_data["city"] = city
        current_data["heatmap_result"] = None
        current_data["bounds"] = None
        current_data["pre_generated_images"] = {}
        current_data["pre_generation_complete"] = False
        current_data["pre_generation_progress"] = 0
        
        save_filename = f"{city}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        save_path = os.path.join(DATA_DIR, save_filename)
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        time_range = {
            "start": df["timestamp"].min().isoformat(),
            "end": df["timestamp"].max().isoformat(),
            "total_records": len(df)
        }
        
        return UploadResponse(
            success=True,
            message=f"成功上传 {len(df)} 条GPS数据",
            record_count=len(df),
            time_range=time_range
        )
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="JSON格式错误")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")


@app.post("/api/upload/json", response_model=UploadResponse)
async def upload_gps_json(
    data: List[dict],
    city: str = Query(..., description="城市名称")
):
    try:
        df = parse_gps_data(data)
        
        if len(df) == 0:
            raise HTTPException(status_code=400, detail="未解析到有效数据")
        
        current_data["df"] = df
        current_data["city"] = city
        current_data["heatmap_result"] = None
        current_data["bounds"] = None
        current_data["pre_generated_images"] = {}
        current_data["pre_generation_complete"] = False
        current_data["pre_generation_progress"] = 0
        
        save_filename = f"{city}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        save_path = os.path.join(DATA_DIR, save_filename)
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        time_range = {
            "start": df["timestamp"].min().isoformat(),
            "end": df["timestamp"].max().isoformat(),
            "total_records": len(df)
        }
        
        return UploadResponse(
            success=True,
            message=f"成功上传 {len(df)} 条GPS数据",
            record_count=len(df),
            time_range=time_range
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")


@app.get("/api/heatmap")
async def get_heatmap(
    grid_size: Optional[float] = Query(0.001, description="网格大小（度）", ge=0.0001, le=0.01),
    window_minutes: Optional[int] = Query(5, description="时间窗口（分钟）", ge=1, le=60),
    congestion_threshold: Optional[float] = Query(0.3, description="拥堵阈值", ge=0.1, le=1.0),
    pre_generate: Optional[bool] = Query(True, description="是否预生成热力图图片")
):
    if current_data["df"] is None or len(current_data["df"]) == 0:
        raise HTTPException(status_code=400, detail="请先上传GPS数据")
    
    try:
        time_windows, time_range, bounds = process_heatmap_data(
            current_data["df"],
            grid_size=grid_size,
            window_minutes=window_minutes,
            congestion_threshold=congestion_threshold
        )
        
        result = HeatmapResponse(
            city=current_data["city"],
            time_windows=time_windows,
            time_range=time_range,
            grid_size=grid_size,
            congestion_threshold=congestion_threshold
        )
        
        current_data["heatmap_result"] = result
        current_data["bounds"] = bounds
        current_data["pre_generated_images"] = {}
        current_data["pre_generation_complete"] = False
        current_data["pre_generation_progress"] = 0
        
        if pre_generate:
            threading.Thread(
                target=pre_generate_heatmap_images,
                args=(current_data["df"], bounds, window_minutes, grid_size),
                daemon=True
            ).start()
        
        return {
            "city": result.city,
            "time_windows": result.time_windows,
            "time_range": result.time_range,
            "grid_size": result.grid_size,
            "congestion_threshold": result.congestion_threshold,
            "bounds": bounds,
            "pre_generation_started": pre_generate
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成热力图失败: {str(e)}")


def pre_generate_heatmap_images(df, bounds, window_minutes, grid_size):
    start_time = df["timestamp"].min()
    end_time = df["timestamp"].max()
    time_windows = generate_time_windows(start_time, end_time, window_minutes)
    
    total = len(time_windows)
    current_data["pre_generation_progress"] = 0
    current_data["pre_generation_complete"] = False
    
    def generate_single(idx, t_start, t_end):
        mask = (df["timestamp"] >= t_start) & (df["timestamp"] < t_end)
        df_window = df[mask]
        
        img_data = generate_heatmap_image(
            df_window,
            bounds["lon_min"], bounds["lon_max"],
            bounds["lat_min"], bounds["lat_max"],
            img_width=1024,
            img_height=1024
        )
        return idx, img_data
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = []
        for idx, (t_start, t_end) in enumerate(time_windows):
            futures.append(executor.submit(generate_single, idx, t_start, t_end))
        
        completed = 0
        for future in as_completed(futures):
            idx, img_data = future.result()
            current_data["pre_generated_images"][idx] = img_data
            completed += 1
            current_data["pre_generation_progress"] = int(completed / total * 100)
    
    current_data["pre_generation_complete"] = True


@app.get("/api/heatmap/progress")
async def get_pre_generation_progress():
    return {
        "progress": current_data["pre_generation_progress"],
        "complete": current_data["pre_generation_complete"],
        "total_cached": len(current_data["pre_generated_images"])
    }


@app.get("/api/heatmap/image/{window_index}")
async def get_heatmap_image(
    window_index: int,
    width: Optional[int] = Query(1024, description="图片宽度", ge=256, le=4096),
    height: Optional[int] = Query(1024, description="图片高度", ge=256, le=4096),
    use_cache: Optional[bool] = Query(True, description="是否使用缓存")
):
    if current_data["df"] is None or len(current_data["df"]) == 0:
        raise HTTPException(status_code=400, detail="请先上传GPS数据")
    
    if current_data["bounds"] is None:
        current_data["bounds"] = calculate_bounds_from_data(current_data["df"])
    
    bounds = current_data["bounds"]
    
    if use_cache and window_index in current_data["pre_generated_images"]:
        img_data = current_data["pre_generated_images"][window_index]
        return Response(content=img_data, media_type="image/png")
    
    if current_data["heatmap_result"] is None:
        raise HTTPException(status_code=400, detail="请先生成热力图数据")
    
    result = current_data["heatmap_result"]
    if window_index < 0 or window_index >= len(result.time_windows):
        raise HTTPException(status_code=400, detail=f"时间窗口索引越界，有效范围: 0-{len(result.time_windows)-1}")
    
    window = result.time_windows[window_index]
    t_start = window.time_start
    t_end = window.time_end
    
    mask = (current_data["df"]["timestamp"] >= t_start) & (current_data["df"]["timestamp"] < t_end)
    df_window = current_data["df"][mask]
    
    img_data = generate_heatmap_image(
        df_window,
        bounds["lon_min"], bounds["lon_max"],
        bounds["lat_min"], bounds["lat_max"],
        img_width=width,
        img_height=height
    )
    
    return Response(content=img_data, media_type="image/png")


@app.get("/api/heatmap/bounds")
async def get_heatmap_bounds():
    if current_data["df"] is None or len(current_data["df"]) == 0:
        raise HTTPException(status_code=400, detail="请先上传GPS数据")
    
    if current_data["bounds"] is None:
        current_data["bounds"] = calculate_bounds_from_data(current_data["df"])
    
    return current_data["bounds"]


@app.get("/api/heatmap/window/{window_index}")
async def get_heatmap_window(
    window_index: int,
    grid_size: Optional[float] = Query(0.001, description="网格大小（度）"),
    window_minutes: Optional[int] = Query(5, description="时间窗口（分钟）"),
    congestion_threshold: Optional[float] = Query(0.3, description="拥堵阈值")
):
    if current_data["heatmap_result"] is None:
        if current_data["df"] is None:
            raise HTTPException(status_code=400, detail="请先上传GPS数据并生成热力图")
        await get_heatmap(grid_size, window_minutes, congestion_threshold)
    
    result = current_data["heatmap_result"]
    if window_index < 0 or window_index >= len(result.time_windows):
        raise HTTPException(status_code=400, detail=f"时间窗口索引越界，有效范围: 0-{len(result.time_windows)-1}")
    
    has_image = window_index in current_data["pre_generated_images"]
    
    return {
        "city": result.city,
        "window_index": window_index,
        "window_data": result.time_windows[window_index],
        "total_windows": len(result.time_windows),
        "grid_size": result.grid_size,
        "bounds": current_data["bounds"],
        "has_cached_image": has_image
    }


@app.get("/api/heatmap/preview/{window_index}")
async def get_heatmap_preview(window_index: int):
    return await get_heatmap_image(window_index, width=512, height=512, use_cache=True)


@app.get("/api/congestion/routes")
async def get_congestion_routes(
    top_n: Optional[int] = Query(10, description="返回前N条最拥堵路段"),
    window_minutes: Optional[int] = Query(5, description="时间窗口（分钟）")
):
    if current_data["heatmap_result"] is None:
        if current_data["df"] is None:
            raise HTTPException(status_code=400, detail="请先上传GPS数据并生成热力图")
        await get_heatmap(window_minutes=window_minutes)
    
    result = current_data["heatmap_result"]
    
    all_congestion = []
    for idx, window in enumerate(result.time_windows):
        for seg in window.congestion_segments:
            all_congestion.append({
                **seg,
                "window_index": idx,
                "time_start": window.time_start.isoformat(),
                "time_end": window.time_end.isoformat()
            })
    
    all_congestion.sort(key=lambda x: x["count"], reverse=True)
    
    return {
        "city": result.city,
        "total_congestion_segments": len(all_congestion),
        "top_congestion": all_congestion[:top_n]
    }


@app.get("/api/data/info")
async def get_data_info():
    if current_data["df"] is None:
        return {
            "has_data": False,
            "message": "暂无上传数据"
        }
    
    df = current_data["df"]
    bounds = calculate_bounds_from_data(df)
    
    return {
        "has_data": True,
        "city": current_data["city"],
        "total_records": len(df),
        "unique_buses": df["bus_id"].nunique(),
        "unique_routes": df["route_id"].nunique(),
        "time_range": {
            "start": df["timestamp"].min().isoformat(),
            "end": df["timestamp"].max().isoformat()
        },
        "bounds": {
            "lon_min": bounds[0],
            "lon_max": bounds[1],
            "lat_min": bounds[2],
            "lat_max": bounds[3]
        },
        "auto_calculated_bounds": True
    }


@app.get("/api/data/files")
async def get_data_files():
    files = []
    if os.path.exists(DATA_DIR):
        for filename in os.listdir(DATA_DIR):
            if filename.endswith(".json"):
                filepath = os.path.join(DATA_DIR, filename)
                files.append({
                    "filename": filename,
                    "size": os.path.getsize(filepath),
                    "modified": datetime.fromtimestamp(os.path.getmtime(filepath)).isoformat()
                })
    return {"files": files}


@app.post("/api/data/load/{filename}")
async def load_data_file(
    filename: str,
    city: str = Query(..., description="城市名称")
):
    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="文件不存在")
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        if isinstance(data, dict) and "data" in data:
            data_list = data["data"]
        elif isinstance(data, list):
            data_list = data
        else:
            raise HTTPException(status_code=400, detail="数据格式错误")
        
        df = parse_gps_data(data_list)
        if len(df) == 0:
            raise HTTPException(status_code=400, detail="未解析到有效数据")
        
        current_data["df"] = df
        current_data["city"] = city
        current_data["heatmap_result"] = None
        current_data["bounds"] = None
        current_data["pre_generated_images"] = {}
        current_data["pre_generation_complete"] = False
        current_data["pre_generation_progress"] = 0
        
        return {
            "success": True,
            "message": f"成功加载 {len(df)} 条数据",
            "record_count": len(df)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"加载失败: {str(e)}")


@app.get("/api/alerts/current")
async def get_current_alerts(
    window_index: Optional[int] = Query(0, description="时间窗口索引"),
    alert_threshold: Optional[float] = Query(0.7, description="告警阈值", ge=0.1, le=1.0),
    min_vehicles: Optional[int] = Query(3, description="最小车辆数", ge=1)
):
    if current_data["df"] is None or len(current_data["df"]) == 0:
        raise HTTPException(status_code=400, detail="请先上传GPS数据")
    
    if current_data["heatmap_result"] is None:
        raise HTTPException(status_code=400, detail="请先生成热力图")
    
    result = current_data["heatmap_result"]
    if window_index < 0 or window_index >= len(result.time_windows):
        raise HTTPException(status_code=400, detail=f"时间窗口索引越界")
    
    window = result.time_windows[window_index]
    t_start = window.time_start
    t_end = window.time_end
    
    mask = (current_data["df"]["timestamp"] >= t_start) & (current_data["df"]["timestamp"] < t_end)
    df_window = current_data["df"][mask]
    
    if current_data["bounds"] is None:
        current_data["bounds"] = calculate_bounds_from_data(current_data["df"])
    
    bounds = current_data["bounds"]
    
    alerts = get_congestion_alerts(
        df_window,
        bounds["lon_min"], bounds["lon_max"],
        bounds["lat_min"], bounds["lat_max"],
        grid_size=result.grid_size,
        alert_threshold=alert_threshold,
        min_vehicles=min_vehicles
    )
    
    return {
        "window_index": window_index,
        "time_start": t_start.isoformat(),
        "time_end": t_end.isoformat(),
        "alert_count": len(alerts),
        "alert_threshold": alert_threshold,
        "alerts": alerts
    }


@app.get("/api/routes/list")
async def get_routes_list():
    if current_data["df"] is None or len(current_data["df"]) == 0:
        raise HTTPException(status_code=400, detail="请先上传GPS数据")
    
    routes = get_all_routes(current_data["df"])
    
    return {
        "total_routes": len(routes),
        "routes": routes
    }


@app.get("/api/routes/trajectory/{route_id}")
async def get_route_trajectory_api(
    route_id: str,
    smooth: Optional[bool] = Query(True, description="是否平滑轨迹")
):
    if current_data["df"] is None or len(current_data["df"]) == 0:
        raise HTTPException(status_code=400, detail="请先上传GPS数据")
    
    trajectory = get_route_trajectory(current_data["df"], route_id, smooth)
    
    if not trajectory["exists"]:
        raise HTTPException(status_code=404, detail=f"线路 {route_id} 不存在")
    
    return trajectory


@app.get("/api/compare/windows")
async def compare_two_windows(
    window_index1: int = Query(..., description="第一个时间窗口索引"),
    window_index2: int = Query(..., description="第二个时间窗口索引"),
    grid_size: Optional[float] = Query(0.001, description="网格大小")
):
    if current_data["df"] is None or len(current_data["df"]) == 0:
        raise HTTPException(status_code=400, detail="请先上传GPS数据")
    
    if current_data["heatmap_result"] is None:
        raise HTTPException(status_code=400, detail="请先生成热力图")
    
    result = current_data["heatmap_result"]
    
    if window_index1 < 0 or window_index1 >= len(result.time_windows):
        raise HTTPException(status_code=400, detail=f"窗口1索引越界")
    if window_index2 < 0 or window_index2 >= len(result.time_windows):
        raise HTTPException(status_code=400, detail=f"窗口2索引越界")
    
    window1 = result.time_windows[window_index1]
    window2 = result.time_windows[window_index2]
    
    if current_data["bounds"] is None:
        current_data["bounds"] = calculate_bounds_from_data(current_data["df"])
    
    bounds = current_data["bounds"]
    
    comparison = compare_time_windows(
        current_data["df"],
        window1.time_start, window1.time_end,
        window2.time_start, window2.time_end,
        bounds["lon_min"], bounds["lon_max"],
        bounds["lat_min"], bounds["lat_max"],
        grid_size=grid_size
    )
    
    return comparison


@app.get("/api/compare/image")
async def get_comparison_image(
    window_index1: int = Query(..., description="第一个时间窗口索引"),
    window_index2: int = Query(..., description="第二个时间窗口索引"),
    width: Optional[int] = Query(1024, description="图片宽度"),
    height: Optional[int] = Query(1024, description="图片高度")
):
    if current_data["df"] is None or len(current_data["df"]) == 0:
        raise HTTPException(status_code=400, detail="请先上传GPS数据")
    
    if current_data["heatmap_result"] is None:
        raise HTTPException(status_code=400, detail="请先生成热力图")
    
    result = current_data["heatmap_result"]
    bounds = current_data["bounds"]
    
    if current_data["bounds"] is None:
        bounds = calculate_bounds_from_data(current_data["df"])
    
    window1 = result.time_windows[window_index1]
    window2 = result.time_windows[window_index2]
    
    comparison = compare_time_windows(
        current_data["df"],
        window1.time_start, window1.time_end,
        window2.time_start, window2.time_end,
        bounds["lon_min"], bounds["lon_max"],
        bounds["lat_min"], bounds["lat_max"]
    )
    
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    for grid in comparison["comparison"]:
        x, y = lonlat_to_pixel(
            grid["center_lon"], grid["center_lat"],
            bounds["lon_min"], bounds["lon_max"],
            bounds["lat_min"], bounds["lat_max"],
            width, height
        )
        
        if grid["change_type"] == "increase":
            color = (255, 0, 0, min(255, int(abs(grid["density_diff"]) * 500)))
            radius = int(10 + abs(grid["density_diff"]) * 20)
        elif grid["change_type"] == "decrease":
            color = (0, 255, 0, min(255, int(abs(grid["density_diff"]) * 500)))
            radius = int(10 + abs(grid["density_diff"]) * 20)
        else:
            color = (200, 200, 200, 80)
            radius = 6
        
        draw.ellipse([x-radius, y-radius, x+radius, y+radius], fill=color)
    
    try:
        img_array = np.array(img)
        from scipy.ndimage import gaussian_filter
        
        rgb = img_array[:, :, :3]
        alpha = img_array[:, :, 3]
        
        alpha_blur = gaussian_filter(alpha.astype(float), sigma=3)
        alpha_blur = np.clip(alpha_blur, 0, 255).astype(np.uint8)
        
        result_array = np.dstack([rgb, alpha_blur])
        result_img = Image.fromarray(result_array, 'RGBA')
    except ImportError:
        result_img = img
    
    buffer = io.BytesIO()
    result_img.save(buffer, format='PNG')
    return Response(content=buffer.getvalue(), media_type="image/png")
