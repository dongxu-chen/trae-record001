TRAFFIC_SIGN_CLASSES = [
    "speed_limit_20", "speed_limit_30", "speed_limit_40", "speed_limit_50",
    "speed_limit_60", "speed_limit_70", "speed_limit_80", "speed_limit_100",
    "speed_limit_120", "no_overtaking", "no_overtaking_trucks", "no_parking",
    "no_stopping", "no_entry", "no_u_turn", "no_right_turn", "no_left_turn",
    "yield", "stop", "roundabout", "keep_right", "keep_left",
    "straight_only", "turn_right", "turn_left", "pedestrian_crossing",
    "children_crossing", "bicycle_crossing", "wild_animals",
    "speed_bump", "slippery_road", "road_narrows_right",
    "road_narrows_left", "road_construction", "traffic_signals",
    "warning_other", "mandatory_direction", "mandatory_turn_right",
    "mandatory_turn_left", "mandatory_roundabout"
]

CLASS_ZH_CN = {
    "speed_limit_20": "限速20",
    "speed_limit_30": "限速30",
    "speed_limit_40": "限速40",
    "speed_limit_50": "限速50",
    "speed_limit_60": "限速60",
    "speed_limit_70": "限速70",
    "speed_limit_80": "限速80",
    "speed_limit_100": "限速100",
    "speed_limit_120": "限速120",
    "no_overtaking": "禁止超车",
    "no_overtaking_trucks": "禁止货车超车",
    "no_parking": "禁止停车",
    "no_stopping": "禁止长时停车",
    "no_entry": "禁止驶入",
    "no_u_turn": "禁止掉头",
    "no_right_turn": "禁止右转",
    "no_left_turn": "禁止左转",
    "yield": "让行",
    "stop": "停车",
    "roundabout": "环岛",
    "keep_right": "靠右行驶",
    "keep_left": "靠左行驶",
    "straight_only": "只准直行",
    "turn_right": "右转",
    "turn_left": "左转",
    "pedestrian_crossing": "人行横道",
    "children_crossing": "注意儿童",
    "bicycle_crossing": "注意非机动车",
    "wild_animals": "注意野生动物",
    "speed_bump": "减速带",
    "slippery_road": "路面湿滑",
    "road_narrows_right": "右侧变窄",
    "road_narrows_left": "左侧变窄",
    "road_construction": "道路施工",
    "traffic_signals": "注意信号灯",
    "warning_other": "注意危险",
    "mandatory_direction": "方向指示",
    "mandatory_turn_right": "必须右转",
    "mandatory_turn_left": "必须左转",
    "mandatory_roundabout": "必须绕环岛"
}

CLASS_CATEGORIES = {
    "speed_limit": [
        "speed_limit_20", "speed_limit_30", "speed_limit_40", "speed_limit_50",
        "speed_limit_60", "speed_limit_70", "speed_limit_80", "speed_limit_100",
        "speed_limit_120"
    ],
    "prohibitory": [
        "no_overtaking", "no_overtaking_trucks", "no_parking", "no_stopping",
        "no_entry", "no_u_turn", "no_right_turn", "no_left_turn"
    ],
    "indicative": [
        "roundabout", "keep_right", "keep_left", "straight_only",
        "turn_right", "turn_left", "mandatory_direction",
        "mandatory_turn_right", "mandatory_turn_left", "mandatory_roundabout"
    ],
    "warning": [
        "yield", "stop", "pedestrian_crossing", "children_crossing",
        "bicycle_crossing", "wild_animals", "speed_bump", "slippery_road",
        "road_narrows_right", "road_narrows_left", "road_construction",
        "traffic_signals", "warning_other"
    ]
}
