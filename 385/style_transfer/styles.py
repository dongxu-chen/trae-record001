"""
预训练风格模型配置
支持多种知名艺术风格
"""

PRETRAINED_STYLES = {
    "starry_night": {
        "name": "星夜",
        "artist": "文森特·梵高",
        "description": "梵高的经典后印象派作品，以旋涡状的星空闻名",
        "style_weight": 1e4,
        "content_weight": 1.0,
        "tv_weight": 1e-6,
    },
    "the_scream": {
        "name": "呐喊",
        "artist": "爱德华·蒙克",
        "description": "表现主义代表作，以扭曲的人物和夸张的色彩闻名",
        "style_weight": 2e4,
        "content_weight": 1.0,
        "tv_weight": 1e-5,
    },
    "muse": {
        "name": "缪斯",
        "artist": "巴勃罗·毕加索",
        "description": "立体主义风格，以几何形状和多角度表现著称",
        "style_weight": 1.5e4,
        "content_weight": 1.0,
        "tv_weight": 1e-6,
    },
    "wave": {
        "name": "神奈川冲浪里",
        "artist": "葛饰北斋",
        "description": "日本浮世绘经典作品，以波浪的动态表现著称",
        "style_weight": 1e4,
        "content_weight": 1.0,
        "tv_weight": 1e-6,
    },
    "composition_vii": {
        "name": "构成第七号",
        "artist": "瓦西里·康定斯基",
        "description": "抽象表现主义代表作，以几何形状和鲜艳色彩著称",
        "style_weight": 3e4,
        "content_weight": 1.0,
        "tv_weight": 1e-5,
    },
    "feathers": {
        "name": "羽毛",
        "artist": "现代艺术",
        "description": "柔和的羽毛纹理，适合人像风格化",
        "style_weight": 5e3,
        "content_weight": 1.0,
        "tv_weight": 1e-6,
    },
    "candy": {
        "name": "糖果",
        "artist": "现代艺术",
        "description": "鲜艳的糖果色彩，适合风景照片",
        "style_weight": 8e3,
        "content_weight": 1.0,
        "tv_weight": 1e-6,
    },
    "mosaic": {
        "name": "马赛克",
        "artist": "现代艺术",
        "description": "马赛克纹理效果，适合建筑照片",
        "style_weight": 1.5e4,
        "content_weight": 1.0,
        "tv_weight": 1e-4,
    },
    "udnie": {
        "name": "Udnie",
        "artist": "弗朗西斯·皮卡比亚",
        "description": "未来主义风格，以动态线条和几何形状著称",
        "style_weight": 1e4,
        "content_weight": 1.0,
        "tv_weight": 1e-5,
    },
    "rain_princess": {
        "name": "雨中公主",
        "artist": "莱昂尼德·阿夫列莫夫",
        "description": "调色刀油画风格，以鲜艳色彩和厚涂技法著称",
        "style_weight": 1e4,
        "content_weight": 1.0,
        "tv_weight": 1e-6,
    },
}


def get_style_config(style_name):
    """
    获取指定风格的配置

    Args:
        style_name: 风格名称

    Returns:
        风格配置字典

    Raises:
        ValueError: 风格名称不存在
    """
    if style_name not in PRETRAINED_STYLES:
        available = ", ".join(PRETRAINED_STYLES.keys())
        raise ValueError(
            f"未知的风格: {style_name}\n可用的风格: {available}"
        )
    return PRETRAINED_STYLES[style_name]


def list_available_styles():
    """列出所有可用风格"""
    print("可用的预训练风格:")
    print("-" * 60)
    for key, config in PRETRAINED_STYLES.items():
        print(f"  {key:20s} - {config['name']}")
        print(f"  {'':20s}   艺术家: {config['artist']}")
        print(f"  {'':20s}   {config['description']}")
        print()
