import asyncio
import json
import websockets
from typing import Set
from datetime import datetime
from config import Config
from prediction.hybrid_predictor import HybridPredictor
from cache.redis_cache import RedisCache


class WebSocketServer:
    def __init__(self, predictor: HybridPredictor, cache: RedisCache):
        self.predictor = predictor
        self.cache = cache
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
    
    async def register(self, websocket):
        self.clients.add(websocket)
        print(f"新客户端连接，当前连接数: {len(self.clients)}")
        
        try:
            await self.send_initial_data(websocket)
        except Exception as e:
            print(f"发送初始数据失败: {e}")
    
    async def unregister(self, websocket):
        if websocket in self.clients:
            self.clients.remove(websocket)
        print(f"客户端断开，当前连接数: {len(self.clients)}")
    
    async def send_initial_data(self, websocket):
        routes_data = []
        for route_id, route_info in Config.BUS_ROUTES.items():
            routes_data.append({
                'route_id': route_id,
                'name': route_info['name'],
                'stations': route_info['stations']
            })
        
        initial_message = {
            'type': 'initial',
            'timestamp': datetime.now().isoformat(),
            'routes': routes_data,
            'traffic_levels': Config.TRAFFIC_LEVELS
        }
        
        await websocket.send(json.dumps(initial_message, ensure_ascii=False))
    
    async def broadcast(self, message: dict):
        if not self.clients:
            return
        
        message_str = json.dumps(message, ensure_ascii=False)
        
        disconnected = set()
        for websocket in self.clients:
            try:
                await websocket.send(message_str)
            except Exception as e:
                disconnected.add(websocket)
        
        for websocket in disconnected:
            await self.unregister(websocket)
    
    async def handle_message(self, websocket, message):
        try:
            data = json.loads(message)
            msg_type = data.get('type')
            
            if msg_type == 'subscribe_route':
                route_id = data.get('route_id')
                print(f"客户端订阅线路: {route_id}")
            
            elif msg_type == 'subscribe_bus':
                bus_id = data.get('bus_id')
                print(f"客户端订阅车辆: {bus_id}")
            
        except json.JSONDecodeError:
            print(f"无效的消息格式: {message}")
        except Exception as e:
            print(f"处理消息失败: {e}")
    
    async def update_loop(self):
        while True:
            try:
                all_predictions = []
                all_gps_data = []
                
                for bus_id, bus in self.predictor.data_generator.buses.items():
                    gps_data = self.predictor.data_generator.generate_gps_data(bus_id)
                    self.predictor.update_bus_gps(
                        gps_data, 
                        route_id=bus['route_id'], 
                        segment_idx=bus['current_station_index']
                    )
                    
                    all_gps_data.append(gps_data.to_dict())
                    self.cache.set_gps_data(bus_id, gps_data.to_dict())
                    
                    load_factor = bus.get('current_load', 40) / 80
                    boarding = random.randint(8, 15)
                    alighting = random.randint(5, 12)
                    
                    prediction = self.predictor.predict_next_station(
                        bus_id,
                        bus['route_id'],
                        bus['current_station_index'],
                        bus['lat'],
                        bus['lon'],
                        bus['speed'],
                        passenger_load_factor=load_factor,
                        boarding_count=boarding,
                        alighting_count=alighting
                    )
                    
                    prediction_dict = prediction.to_dict()
                    if hasattr(prediction, 'stop_light_density'):
                        prediction_dict['stop_light_density'] = prediction.stop_light_density
                    if hasattr(prediction, 'stop_light_delay'):
                        prediction_dict['stop_light_delay'] = prediction.stop_light_delay
                    
                    all_predictions.append(prediction_dict)
                    self.cache.set_prediction(bus_id, prediction_dict)
                    
                    bus_state = {
                        'bus_id': bus_id,
                        'route_id': bus['route_id'],
                        'current_station_index': bus['current_station_index'],
                        'lat': bus['lat'],
                        'lon': bus['lon'],
                        'speed': bus['speed'],
                        'prediction': prediction_dict
                    }
                    self.cache.set_bus_state(bus_id, bus_state)
                
                delay_warnings = self.predictor.get_delay_warnings()
                for warning in delay_warnings:
                    self.cache.add_delay_warning(warning)
                
                for route_id in Config.BUS_ROUTES.keys():
                    traffic_data = self.predictor.data_generator.generate_traffic_data(route_id)
                    traffic_list = [t.to_dict() for t in traffic_data]
                    
                    route_info = Config.BUS_ROUTES[route_id]
                    stop_light_densities = route_info.get('stop_light_density', [])
                    for i, td in enumerate(traffic_list):
                        if i < len(stop_light_densities):
                            td['stop_light_density'] = stop_light_densities[i]
                    
                    self.cache.set_traffic_data(route_id, traffic_list)
                
                punctuality_stats = self.predictor.get_punctuality_stats()
                self.cache.set_punctuality_stats(punctuality_stats)
                
                segment_stats = []
                for seg_id, stats in self.predictor.segment_delay_stats.items():
                    segment_stats.append(stats)
                
                high_risk_segments = self.predictor.get_delay_high_risk_segments(5)
                dispatch_suggestions = self.predictor.generate_dispatch_suggestions()
                announcements = self.predictor.check_announcement_triggers()
                
                all_passenger_data = []
                for bus_id, bus in self.predictor.data_generator.buses.items():
                    passenger_info = {
                        'bus_id': bus_id,
                        'route_id': bus['route_id'],
                        'current_load': bus.get('current_load', 40),
                        'max_capacity': 80,
                        'load_factor': bus.get('current_load', 40) / 80
                    }
                    all_passenger_data.append(passenger_info)
                
                update_message = {
                    'type': 'update',
                    'timestamp': datetime.now().isoformat(),
                    'gps_data': all_gps_data,
                    'predictions': all_predictions,
                    'delay_warnings': delay_warnings,
                    'punctuality_stats': punctuality_stats,
                    'segment_stats': segment_stats,
                    'high_risk_segments': high_risk_segments,
                    'dispatch_suggestions': dispatch_suggestions,
                    'announcements': announcements,
                    'passenger_data': all_passenger_data
                }
                
                await self.broadcast(update_message)
                
            except Exception as e:
                print(f"更新循环错误: {e}")
                import traceback
                traceback.print_exc()
            
            await asyncio.sleep(Config.PREDICTION_INTERVAL)
    
    async def handler(self, websocket):
        await self.register(websocket)
        try:
            async for message in websocket:
                await self.handle_message(websocket, message)
        finally:
            await self.unregister(websocket)
    
    async def start(self):
        print(f"WebSocket服务器启动在 {Config.WEBSOCKET_HOST}:{Config.WEBSOCKET_PORT}")
        
        update_task = asyncio.create_task(self.update_loop())
        
        async with websockets.serve(
            self.handler,
            Config.WEBSOCKET_HOST,
            Config.WEBSOCKET_PORT
        ):
            await update_task
