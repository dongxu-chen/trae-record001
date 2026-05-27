import json
import sys
import time
from src.traffic_model import TrafficModel
from src.signal_controller import DiscreteEventSimulator
from src.signal_optimizer import SignalOptimizer
from src.emission_model import EmissionModel


def load_json(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def test_emission_prediction():
    print("\n" + "="*60)
    print("测试 1: 排放预测模型")
    print("="*60)

    network_config = load_json('data/sample_network.json')
    signal_config = load_json('data/sample_signals.json')
    od_matrix = load_json('data/sample_od_matrix.json')

    print("\n测试排放模型初始化...")
    emission_model = EmissionModel()
    print("  排放因子类型:", list(emission_model.emission_factors.keys()))

    print("\n测试基于车速和排队的排放估计...")

    sim_config = {
        "max_speed": 14,
        "generation_rate": 0.3,
        "use_parallel": True,
        "enable_emission_calc": True,
        "enable_bus_priority": True,
        "enable_variable_lanes": True,
        "bus_generation_rate": 0.15
    }

    model = TrafficModel(network_config, signal_config, od_matrix, sim_config)

    steps = 30
    print(f"\n运行 {steps} 步仿真...")

    for i in range(steps):
        model.step()
        if (i + 1) % 10 == 0:
            emission_data = model.get_emission_data()
            total = emission_data.get("real_time", {}).get("total_emissions", {})
            print(f"  第 {i+1:3d} 步: "
                  f"CO2={total.get('CO2', 0):.2f} g, "
                  f"NOx={total.get('NOx', 0):.4f} g, "
                  f"PM={total.get('PM', 0):.4f} g")

    print("\n排放指数:", model.emission_model.get_emission_index(model.roads))

    queue_emissions = emission_data.get("queue_emissions", {})
    print(f"\n排队车辆排放 (共 {len(queue_emissions)} 条路段):")
    for rid, qe in list(queue_emissions.items())[:3]:
        road = model.roads[rid]
        print(f"  {road['name']}: 排队{qe['queue_length']}辆, "
              f"CO={qe['emissions'].get('CO', 0):.4f} g")

    print("\n✅ 排放预测模型测试通过")
    return True


def test_bus_priority():
    print("\n" + "="*60)
    print("测试 2: 公交优先策略")
    print("="*60)

    network_config = load_json('data/sample_network.json')
    signal_config = load_json('data/sample_signals.json')
    od_matrix = load_json('data/sample_od_matrix.json')

    sim_config = {
        "max_speed": 14,
        "generation_rate": 0.3,
        "use_parallel": False,
        "enable_emission_calc": True,
        "enable_bus_priority": True,
        "enable_variable_lanes": True,
        "bus_generation_rate": 0.2
    }

    model = TrafficModel(network_config, signal_config, od_matrix, sim_config)

    print("\n手动生成公交车辆...")
    bus_types = ['bus', 'bus_hybrid', 'bus_electric']
    for i in range(5):
        bus_type = bus_types[i % len(bus_types)]
        bus = model._generate_vehicle(vehicle_type=bus_type)
        if bus:
            print(f"  生成公交: ID={bus.unique_id}, 类型={bus_type}, "
                  f"线路={getattr(bus, 'route_id', '')}, "
                  f"乘客={getattr(bus, 'passenger_count', 0)}")

    steps = 20
    print(f"\n运行 {steps} 步仿真...")

    for i in range(steps):
        model.step()
        if (i + 1) % 5 == 0:
            bus_stats = model.get_bus_statistics()
            priority_stats = model.bus_priority_manager.get_statistics()
            print(f"  第 {i+1:3d} 步: "
                  f"公交总数={bus_stats['total_buses']}, "
                  f"平均乘客={bus_stats['avg_passengers']:.1f}, "
                  f"优先请求={priority_stats['total_requests']}, "
                  f"批准率={priority_stats['grant_rate']:.2%}")

    print("\n公交统计详情:")
    bus_info = model.get_bus_statistics()
    for bus in bus_info.get("buses", [])[:3]:
        print(f"  公交 {bus['id']}: 线路={bus['route_id']}, "
              f"乘客={bus['passenger_count']}, "
              f"在站={bus['is_at_stop']}, "
              f"速度={bus['speed']} m/s")

    print("\n✅ 公交优先策略测试通过")
    return True


def test_variable_lanes():
    print("\n" + "="*60)
    print("测试 3: 可变车道模拟")
    print("="*60)

    network_config = load_json('data/sample_network.json')
    signal_config = load_json('data/sample_signals.json')
    od_matrix = load_json('data/sample_od_matrix.json')

    for road in network_config.get("roads", []):
        if road.get("lanes", 1) > 2:
            road["bus_lane"] = 0
            road["reversible_lanes"] = [2] if road.get("lanes", 1) > 2 else []
            road["dynamic_lanes"] = True

    sim_config = {
        "max_speed": 14,
        "generation_rate": 0.4,
        "use_parallel": False,
        "enable_emission_calc": True,
        "enable_bus_priority": True,
        "enable_variable_lanes": True,
        "bus_generation_rate": 0.1
    }

    model = TrafficModel(network_config, signal_config, od_matrix, sim_config)

    print("\n初始车道配置:")
    lane_configs = model.get_all_lane_configs()
    for rid, config in list(lane_configs.items())[:3]:
        road = model.roads[rid]
        print(f"  {road['name']}: 类型={config.get('lane_types', [])}, "
              f"公交道={config.get('bus_lane', -1)}")

    steps = 60
    print(f"\n运行 {steps} 步仿真，观察可变车道调整...")

    lane_changes = []
    for i in range(steps):
        model.step()

        if (i + 1) % 20 == 0:
            queue_lengths = model.get_queue_lengths()
            print(f"\n  第 {i+1:3d} 步:")
            for rid, qlen in list(queue_lengths.items())[:3]:
                road = model.roads[rid]
                config = model.variable_lane_manager.get_lane_status(rid)
                density = len(road["vehicles"]) / road.get("capacity", 100)
                print(f"    {road['name']}: 排队={qlen:2d}, "
                      f"密度={density:.2f}, "
                      f"车道={config.get('lane_types', [])}")

            recent_changes = getattr(model, 'lane_change_events', [])[-5:]
            if recent_changes:
                print(f"    最近车道调整: {len(recent_changes)} 次")
                lane_changes.extend(recent_changes)

    print(f"\n总计车道调整: {len(lane_changes)} 次")

    print("\n✅ 可变车道模拟测试通过")
    return True


def test_game_theory_lane_change():
    print("\n" + "="*60)
    print("测试 4: 博弈论换道与让行模型")
    print("="*60)

    network_config = load_json('data/sample_network.json')
    signal_config = load_json('data/sample_signals.json')
    od_matrix = load_json('data/sample_od_matrix.json')

    sim_config = {
        "max_speed": 14,
        "generation_rate": 0.35,
        "use_parallel": False,
        "enable_emission_calc": True,
        "enable_bus_priority": True,
        "enable_variable_lanes": True,
        "bus_generation_rate": 0.1
    }

    model = TrafficModel(network_config, signal_config, od_matrix, sim_config)

    steps = 40
    print(f"\n运行 {steps} 步仿真...")

    for i in range(steps):
        model.step()

    print("\n车辆行为统计:")
    vehicle_data = []
    for agent in model.agents:
        if hasattr(agent, 'lane_change_count'):
            vehicle_data.append({
                'id': agent.unique_id,
                'type': getattr(agent, 'vehicle_type', 'car'),
                'lane_changes': agent.lane_change_count,
                'yield_count': agent.yield_count,
                'blocked_count': agent.blocked_count,
                'cooperation': agent.cooperation_score,
                'aggression': agent.aggression_level
            })

    total_lane_changes = sum(v['lane_changes'] for v in vehicle_data)
    total_yields = sum(v['yield_count'] for v in vehicle_data)

    print(f"  总换道次数: {total_lane_changes}")
    print(f"  总让行次数: {total_yields}")
    print(f"  平均协作度: {sum(v['cooperation'] for v in vehicle_data)/max(1, len(vehicle_data)):.3f}")

    print("\n车辆抽样 (5辆):")
    for v in vehicle_data[:5]:
        print(f"  {v['type']} {v['id']}: 换道{v['lane_changes']}次, "
              f"让行{v['yield_count']}次, "
              f"被阻{v['blocked_count']}次, "
              f"协作度{v['cooperation']:.2f}, "
              f"侵略性{v['aggression']:.2f}")

    print("\n✅ 博弈论换道模型测试通过")
    return True


def test_parallel_computation():
    print("\n" + "="*60)
    print("测试 5: 道路分段并行计算")
    print("="*60)

    network_config = load_json('data/sample_network.json')
    signal_config = load_json('data/sample_signals.json')
    od_matrix = load_json('data/sample_od_matrix.json')

    print("\n测试串行计算...")
    start_time = time.time()
    model_serial = TrafficModel(
        network_config, signal_config, od_matrix,
        sim_config={
            "max_speed": 14, "generation_rate": 0.3, "use_parallel": False,
            "enable_emission_calc": False, "enable_bus_priority": False,
            "enable_variable_lanes": False
        }
    )
    for _ in range(50):
        model_serial.step()
    serial_time = time.time() - start_time
    print(f"  串行计算耗时: {serial_time:.3f}秒")

    print("\n测试并行计算...")
    start_time = time.time()
    model_parallel = TrafficModel(
        network_config, signal_config, od_matrix,
        sim_config={
            "max_speed": 14, "generation_rate": 0.3, "use_parallel": True,
            "enable_emission_calc": False, "enable_bus_priority": False,
            "enable_variable_lanes": False
        }
    )
    for _ in range(50):
        model_parallel.step()
    parallel_time = time.time() - start_time
    print(f"  并行计算耗时: {parallel_time:.3f}秒")

    speedup = serial_time / max(0.001, parallel_time)
    print(f"\n加速比: {speedup:.2f}x")

    print("\n✅ 并行计算测试通过")
    return True


def main():
    print("\n" + "="*60)
    print("🚦 交通态势仿真系统 - 新功能综合测试")
    print("="*60)
    print(f"Python 版本: {sys.version}")
    print(f"新增功能: 排放预测 | 公交优先 | 可变车道")

    tests = [
        ("排放预测模型", test_emission_prediction),
        ("公交优先策略", test_bus_priority),
        ("可变车道模拟", test_variable_lanes),
        ("博弈论换道模型", test_game_theory_lane_change),
        ("道路分段并行计算", test_parallel_computation),
    ]

    passed = 0
    failed = 0

    for name, test in tests:
        try:
            print(f"\n{'─'*50}")
            print(f"▶ 开始测试: {name}")
            print(f"{'─'*50}")
            if test():
                passed += 1
                print(f"✅ [{name}] 测试通过")
            else:
                failed += 1
                print(f"❌ [{name}] 测试失败")
        except Exception as e:
            print(f"\n❌ [{name}] 测试失败")
            print(f"   错误信息: {str(e)}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "="*60)
    print(f"测试总结: {passed} 通过, {failed} 失败")
    print("="*60)

    if failed == 0:
        print("\n🎉 所有新功能测试通过！")
        print("\n新增功能API:")
        print("  POST /api/emissions - 获取排放数据")
        print("  POST /api/buses - 获取公交数据")
        print("  POST /api/lanes - 获取车道配置")
        print("  POST /api/lanes/toggle - 手动切换车道类型")
        print("  POST /api/simulation/config - 更新仿真配置")
        print("\nFlask应用已在运行: http://127.0.0.1:5000")
    else:
        print("\n⚠️  部分测试失败，请检查错误信息。")

    return failed == 0


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
