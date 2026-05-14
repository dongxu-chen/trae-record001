# 智能插座能耗面板配置指南

## 功能概览

本智能插座组件支持以下能耗统计功能：

- **功率 (Power)**: 实时功率显示（单位：W）
- **能耗 (Energy)**: 累计用电量统计（单位：kWh）
- **电压 (Voltage)**: 电压显示（单位：V）
- **电流 (Current)**: 电流显示（单位：A）

## 配置步骤

### 1. 添加设备到 Home Assistant

1. 进入 **设置 > 设备与服务 > 添加集成**
2. 搜索 **"智能插座"** 或 **"Smart Plug"**
3. 填写设备名称和 IP 地址
4. 进入高级配置页面：
   - **默认功率**: 设备开启时的默认功率（如 100W）
   - **电压**: 所在地区的电压（中国默认为 220V）
   - **最大功率限制**: 可选，设置过功率保护阈值
   - **更新间隔**: 能耗数据更新频率（10-3600秒）

### 2. 配置能耗面板

1. 进入 **设置 > 面板 > 能源**
2. 点击 **添加能源来源**
3. 选择 **电网输入**
4. 在下拉列表中找到对应设备的能耗传感器：
   - 格式：`sensor.{设备名称}_energy`
   - 例如：`sensor.my_plug_energy`

### 3. 验证配置

检查设备是否正确显示：
- 实体列表中应包含 4 个传感器：
  - `switch.{设备名称}` - 开关控制
  - `sensor.{设备名称}_power` - 功率
  - `sensor.{设备名称}_energy` - 能耗（用于能源面板）
  - `sensor.{设备名称}_voltage` - 电压
  - `sensor.{设备名称}_current` - 电流

## 自动化联动示例

### 示例 1: 用电高峰自动关闭高功率设备

```yaml
- alias: "用电高峰自动关闭空调"
  trigger:
    - platform: numeric_state
      entity_id: sensor.smart_plug_power
      above: 2000
  condition:
    - condition: time
      after: "18:00:00"
      before: "22:00:00"
  action:
    - service: switch.turn_off
      target:
        entity_id: switch.smart_plug
    - service: notify.mobile_app
      data:
        title: "节能提醒"
        message: "用电高峰期已自动关闭高功率设备"
```

### 示例 2: 设备故障检测（功率异常）

```yaml
- alias: "设备故障检测"
  trigger:
    - platform: state
      entity_id: switch.smart_plug
      to: "on"
      for:
        minutes: 2
  condition:
    - condition: numeric_state
      entity_id: sensor.smart_plug_power
      below: 1
  action:
    - service: persistent_notification.create
      data:
        title: "设备异常"
        message: "智能插座已开启但功率为 0，可能设备故障或未连接"
```

### 示例 3: 定时统计每日用电量

```yaml
- alias: "每日用电统计"
  trigger:
    - platform: time
      at: "23:59:00"
  action:
    - service: input_number.set_value
      target:
        entity_id: input_number.daily_energy_usage
      data:
        value: "{{ states('sensor.smart_plug_energy') | float }}"
```

## 功率计算说明

组件使用以下公式计算能耗：

```
能耗 (kWh) = 功率 (kW) × 时间 (h)
功率 (W) = 电压 (V) × 电流 (A)
```

**注意**: 默认功率值用于模拟真实功率。在实际硬件集成中，这些值应该从设备 API 读取。

## 服务功能

### smart_plug.reset 服务

重置插座电源（先关后开），适合用于重启设备。

**参数**:
- `delay`: 关闭后等待的秒数（默认 2 秒）

**调用示例**:
```yaml
- service: smart_plug.reset
  target:
    entity_id: switch.smart_plug
  data:
    delay: 3
```

## 常见问题

### Q: 能耗面板中找不到传感器？

A: 确保：
1. 已添加智能插座设备
2. 设备名称中没有特殊字符
3. 检查 `sensor.{设备名称}_energy` 实体是否存在

### Q: 如何重置能耗统计？

A: 目前能耗是累计的，如需重置：
1. 重新配置设备（删除并重新添加）
2. 或使用模板传感器进行日/月统计

### Q: 功率值不准确？

A: 在高级配置中调整：
1. **默认功率**: 设置更精确的设备功率
2. **电压**: 确保使用正确的地区电压

## 版本信息

- **版本**: 1.1.0
- **支持平台**: switch, sensor
- **IoT 类别**: local_polling
