from fastapi import FastAPI, UploadFile, File, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import os
import asyncio
import json

from predictor import DemandPredictor

app = FastAPI(title="Taxi Demand Prediction API")

app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

predictor = DemandPredictor()

class PredictionResponse(BaseModel):
    predictions: list
    latency_ms: float

class VehicleData(BaseModel):
    vehicle_id: str
    lat: float
    lng: float
    status: str

class DispatchRequest(BaseModel):
    strategy: str
    orders_count: int = 20

vehicles_db = []
dispatch_history = []
alerts = []

def generate_mock_vehicles(count=50):
    vehicles = []
    for i in range(count):
        vehicles.append({
            'vehicle_id': f'TAXI_{i:03d}',
            'lat': 39.8 + np.random.random() * 0.3,
            'lng': 116.2 + np.random.random() * 0.4,
            'status': np.random.choice(['idle', 'busy'], p=[0.4, 0.6])
        })
    return vehicles

vehicles_db = generate_mock_vehicles(50)

active_connections = []

async def update_vehicles_loop():
    while True:
        for v in vehicles_db:
            v['lat'] += np.random.normal(0, 0.0002)
            v['lng'] += np.random.normal(0, 0.0002)
            v['lat'] = np.clip(v['lat'], 39.8, 40.1)
            v['lng'] = np.clip(v['lng'], 116.2, 116.6)
            
            if np.random.random() < 0.05:
                v['status'] = np.random.choice(['idle', 'busy'], p=[0.4, 0.6])
        
        await broadcast_vehicles()
        await asyncio.sleep(2)

async def broadcast_vehicles():
    idle_vehicles = [v for v in vehicles_db if v['status'] == 'idle']
    message = json.dumps({
        'type': 'vehicles_update',
        'data': {
            'total': len(vehicles_db),
            'idle_count': len(idle_vehicles),
            'vehicles': vehicles_db,
            'timestamp': datetime.now().isoformat()
        }
    })
    
    for connection in active_connections:
        try:
            await connection.send_text(message)
        except:
            pass

@app.on_event("startup")
async def startup_event():
    if os.path.exists('models.pkl'):
        predictor.load_models('models.pkl')
        print(f"Loaded {len(predictor.models)} pre-trained models")
    else:
        print("No pre-trained models found. Please upload training data first.")
    
    asyncio.create_task(update_vehicles_loop())

@app.websocket("/ws/vehicles")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    print(f"New WebSocket connection. Total: {len(active_connections)}")
    
    try:
        idle_vehicles = [v for v in vehicles_db if v['status'] == 'idle']
        initial_message = json.dumps({
            'type': 'vehicles_update',
            'data': {
                'total': len(vehicles_db),
                'idle_count': len(idle_vehicles),
                'vehicles': vehicles_db,
                'timestamp': datetime.now().isoformat()
            }
        })
        await websocket.send_text(initial_message)
        
        while True:
            data = await websocket.receive_text()
            pass
            
    except WebSocketDisconnect:
        active_connections.remove(websocket)
        print(f"WebSocket disconnected. Total: {len(active_connections)}")
    except Exception as e:
        if websocket in active_connections:
            active_connections.remove(websocket)
        print(f"WebSocket error: {e}")

@app.get("/")
async def root():
    return FileResponse('static/index.html')

@app.post("/api/train")
async def train_model(file: UploadFile = File(...)):
    try:
        df = pd.read_csv(file.file)
        required_columns = ['lat', 'lng', 'timestamp', 'order_count']
        for col in required_columns:
            if col not in df.columns:
                raise HTTPException(status_code=400, detail=f"Missing required column: {col}")
        
        start_time = time.time()
        predictor.train_models(df)
        predictor.save_models('models.pkl')
        training_time = (time.time() - start_time) * 1000
        
        return {
            "status": "success",
            "grids_trained": len(predictor.models),
            "training_time_ms": training_time
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/predict/next-hour", response_model=PredictionResponse)
async def predict_next_hour():
    if not predictor.models:
        raise HTTPException(status_code=400, detail="No models trained. Please upload training data first.")
    
    start_time = time.time()
    predictions = predictor.predict_next_hour()
    latency_ms = (time.time() - start_time) * 1000
    
    return {
        "predictions": predictions,
        "latency_ms": latency_ms
    }

@app.get("/api/predict/hours/{hours}", response_model=PredictionResponse)
async def predict_hours(hours: int = 12):
    if not predictor.models:
        raise HTTPException(status_code=400, detail="No models trained. Please upload training data first.")
    
    if hours < 1 or hours > 24:
        raise HTTPException(status_code=400, detail="Hours must be between 1 and 24")
    
    start_time = time.time()
    predictions = predictor.predict_hours(hours)
    latency_ms = (time.time() - start_time) * 1000
    
    return {
        "predictions": predictions,
        "latency_ms": latency_ms
    }

@app.get("/api/vehicles")
async def get_vehicles():
    idle_vehicles = [v for v in vehicles_db if v['status'] == 'idle']
    return {
        "total": len(vehicles_db),
        "idle_count": len(idle_vehicles),
        "vehicles": vehicles_db
    }

@app.put("/api/vehicles/{vehicle_id}")
async def update_vehicle(vehicle_id: str, data: VehicleData):
    for v in vehicles_db:
        if v['vehicle_id'] == vehicle_id:
            v['lat'] = data.lat
            v['lng'] = data.lng
            v['status'] = data.status
            return {"status": "success", "vehicle": v}
    raise HTTPException(status_code=404, detail="Vehicle not found")

@app.get("/api/grid-bounds")
async def get_grid_bounds():
    return predictor.grid_bounds

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "models_loaded": len(predictor.models)}

def calculate_distance(lat1, lng1, lat2, lng2):
    return np.sqrt((lat1 - lat2)**2 + (lng1 - lng2)**2)

def generate_mock_orders(count):
    orders = []
    for i in range(count):
        orders.append({
            'order_id': f'ORDER_{i:04d}',
            'lat': 39.8 + np.random.random() * 0.3,
            'lng': 116.2 + np.random.random() * 0.4,
            'demand_level': np.random.choice(['low', 'medium', 'high'], p=[0.3, 0.5, 0.2]),
            'timestamp': datetime.now().isoformat()
        })
    return orders

def nearest_dispatch(orders, vehicles):
    idle_vehicles = [v for v in vehicles if v['status'] == 'idle']
    assignments = []
    unassigned = []
    
    used_vehicles = set()
    
    for order in orders:
        best_vehicle = None
        min_dist = float('inf')
        
        for v in idle_vehicles:
            if v['vehicle_id'] in used_vehicles:
                continue
            dist = calculate_distance(order['lat'], order['lng'], v['lat'], v['lng'])
            if dist < min_dist:
                min_dist = dist
                best_vehicle = v
        
        if best_vehicle:
            assignments.append({
                'order': order,
                'vehicle': best_vehicle,
                'distance': min_dist
            })
            used_vehicles.add(best_vehicle['vehicle_id'])
        else:
            unassigned.append(order)
    
    return assignments, unassigned

def balanced_dispatch(orders, vehicles):
    idle_vehicles = [v for v in vehicles if v['status'] == 'idle']
    assignments = []
    unassigned = []
    
    vehicle_load = {v['vehicle_id']: 0 for v in idle_vehicles}
    
    for order in orders:
        candidates = []
        for v in idle_vehicles:
            dist = calculate_distance(order['lat'], order['lng'], v['lat'], v['lng'])
            score = dist * (1 + vehicle_load[v['vehicle_id']] * 0.1)
            candidates.append((score, v, dist))
        
        candidates.sort(key=lambda x: x[0])
        
        if candidates:
            best_score, best_vehicle, dist = candidates[0]
            assignments.append({
                'order': order,
                'vehicle': best_vehicle,
                'distance': dist
            })
            vehicle_load[best_vehicle['vehicle_id']] += 1
        else:
            unassigned.append(order)
    
    return assignments, unassigned

@app.post("/api/dispatch/simulate")
async def simulate_dispatch(request: DispatchRequest):
    if request.strategy not in ['nearest', 'balanced']:
        raise HTTPException(status_code=400, detail="Invalid strategy. Use 'nearest' or 'balanced'")
    
    orders = generate_mock_orders(request.orders_count)
    
    if request.strategy == 'nearest':
        assignments, unassigned = nearest_dispatch(orders, vehicles_db)
    else:
        assignments, unassigned = balanced_dispatch(orders, vehicles_db)
    
    result = {
        'strategy': request.strategy,
        'total_orders': len(orders),
        'assigned_count': len(assignments),
        'unassigned_count': len(unassigned),
        'avg_distance': np.mean([a['distance'] for a in assignments]) * 111 if assignments else 0,
        'assignments': assignments,
        'unassigned_orders': unassigned,
        'timestamp': datetime.now().isoformat()
    }
    
    dispatch_history.append(result)
    if len(dispatch_history) > 10:
        dispatch_history.pop(0)
    
    return result

@app.get("/api/dispatch/history")
async def get_dispatch_history():
    return {"history": dispatch_history}

@app.get("/api/alerts")
async def get_alerts():
    if not predictor.models:
        return {"alerts": []}
    
    predictions = predictor.predict_next_hour()
    total_demand = sum(p['demand'] for p in predictions)
    idle_count = sum(1 for v in vehicles_db if v['status'] == 'idle')
    
    demand_vehicle_ratio = total_demand / max(idle_count, 1)
    
    new_alerts = []
    
    if demand_vehicle_ratio >= 2:
        new_alerts.append({
            'type': 'supply_demand_imbalance',
            'level': 'critical',
            'message': f'供需严重不平衡！预测需求量({total_demand:.1f}) 是空闲车辆({idle_count}) 的 {demand_vehicle_ratio:.1f} 倍',
            'ratio': demand_vehicle_ratio,
            'total_demand': total_demand,
            'idle_vehicles': idle_count,
            'timestamp': datetime.now().isoformat()
        })
    elif demand_vehicle_ratio >= 1.5:
        new_alerts.append({
            'type': 'supply_demand_imbalance',
            'level': 'warning',
            'message': f'供需紧张！预测需求量({total_demand:.1f}) 是空闲车辆({idle_count}) 的 {demand_vehicle_ratio:.1f} 倍',
            'ratio': demand_vehicle_ratio,
            'total_demand': total_demand,
            'idle_vehicles': idle_count,
            'timestamp': datetime.now().isoformat()
        })
    
    high_demand_zones = [p for p in predictions if p['demand_level'] == 'high']
    if len(high_demand_zones) >= 5:
        new_alerts.append({
            'type': 'high_demand_cluster',
            'level': 'warning',
            'message': f'高需求区域集中！共 {len(high_demand_zones)} 个区域需求旺盛',
            'high_demand_count': len(high_demand_zones),
            'timestamp': datetime.now().isoformat()
        })
    
    if predictions and predictions[0].get('is_holiday'):
        holiday_name = predictions[0].get('holiday_name', '节假日')
        new_alerts.append({
            'type': 'holiday_adjustment',
            'level': 'info',
            'message': f'节假日预测调整：{holiday_name}',
            'holiday_name': holiday_name,
            'timestamp': datetime.now().isoformat()
        })
    
    alerts.clear()
    alerts.extend(new_alerts)
    
    return {"alerts": new_alerts}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
