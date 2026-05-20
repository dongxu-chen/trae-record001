from config import Config


class HealthAdvisor:
    def __init__(self):
        self.config = Config()

    def get_aqi_level(self, aqi):
        for low, high, level, color, desc in self.config.AQI_LEVELS:
            if low <= aqi <= high:
                return {
                    'level': level,
                    'color': color,
                    'description': desc,
                    'aqi': aqi
                }
        return {
            'level': '严重污染',
            'color': 'maroon',
            'description': '空气质量指数超出测量范围',
            'aqi': aqi
        }

    def get_detailed_advice(self, aqi_level):
        advice_map = {
            '优': {
                'summary': '空气质量令人满意，基本无空气污染',
                'general': '空气质量极佳，是进行户外活动的最佳时机。',
                'outdoor_activity': '非常适宜户外活动，可尽情享受清新空气',
                'exercise': '各类运动皆宜，建议多进行户外运动，如跑步、骑行、打球等',
                'travel': '非常适宜出行，是旅游观光的好天气',
                'window': '建议全天开窗通风，保持室内空气流通',
                'mask': '无需佩戴口罩',
                'children': '儿童可正常进行户外活动，建议多参加户外游戏和体育锻炼',
                'elderly': '老年人可正常外出活动，适合散步、打太极等轻度运动',
                'respiratory_patients': '呼吸系统疾病患者可正常活动，症状通常会减轻',
                'heart_patients': '心脏病患者可正常活动，适宜进行轻度户外锻炼',
                'pregnant_women': '孕妇可正常外出，多呼吸新鲜空气对胎儿有益',
                'office_workers': '适合开窗办公，工作效率会更高',
                'dining': '非常适合户外用餐和烧烤',
                'clothing': '穿着舒适即可，无特殊要求',
                'transportation': '适宜骑行和步行，绿色出行',
                'home_air': '无需开启空气净化器',
                'plants': '非常适合养护绿植',
                'emotion': '心情愉悦，精神状态佳'
            },
            '良': {
                'summary': '空气质量可接受，某些污染物可能对极少数敏感人群有健康影响',
                'general': '空气质量良好，基本不影响正常活动。',
                'outdoor_activity': '适宜户外活动，天气晴朗时更适合外出',
                'exercise': '适合进行各类运动，敏感人群可适当减少高强度运动',
                'travel': '适宜出行，外出游玩不受影响',
                'window': '建议开窗通风，保持室内空气新鲜',
                'mask': '一般无需佩戴口罩，极少数过敏体质者可根据自身情况选择',
                'children': '儿童可正常进行户外活动',
                'elderly': '老年人可正常外出活动，建议选择空气质量较好的时段',
                'respiratory_patients': '呼吸系统疾病患者如出现不适可适当减少户外活动',
                'heart_patients': '心脏病患者可正常活动，如有不适请及时休息',
                'pregnant_women': '孕妇可正常外出，避免在交通繁忙区域长时间停留',
                'office_workers': '适合开窗办公，保持室内空气流通',
                'dining': '适合户外用餐',
                'clothing': '穿着舒适即可',
                'transportation': '适宜骑行和步行',
                'home_air': '一般无需开启空气净化器',
                'plants': '适合养护绿植',
                'emotion': '心情舒畅，精神状态良好'
            },
            '轻度污染': {
                'summary': '易感人群症状有轻度加剧，健康人群出现刺激症状',
                'general': '空气质量轻度污染，敏感人群需注意防护。',
                'outdoor_activity': '建议减少户外活动，如需外出请做好防护',
                'exercise': '减少高强度户外运动，可选择轻度运动如散步',
                'travel': '可正常出行，敏感人群需注意防护，尽量避开交通拥堵区域',
                'window': '适当减少开窗时间，尤其是早晚高峰时段',
                'mask': '敏感人群建议佩戴口罩，健康人群可根据自身情况选择',
                'children': '儿童应减少长时间户外活动，避免在交通要道附近玩耍',
                'elderly': '老年人应减少外出，如需外出建议佩戴口罩',
                'respiratory_patients': '呼吸系统疾病患者应减少户外活动，外出必须佩戴口罩，按时服药',
                'heart_patients': '心脏病患者应减少户外活动，注意休息，避免劳累',
                'pregnant_women': '孕妇应减少外出，如需外出请佩戴口罩，避免长时间停留',
                'office_workers': '建议关闭窗户，开启空调新风系统',
                'dining': '减少户外用餐，选择室内通风良好的场所',
                'clothing': '穿着长袖衣物，减少皮肤暴露',
                'transportation': '建议选择公共交通或私家车，减少骑行',
                'home_air': '敏感人群建议开启空气净化器',
                'plants': '可正常养护室内绿植',
                'emotion': '可能会有轻微不适，保持心情平和'
            },
            '中度污染': {
                'summary': '进一步加剧易感人群症状，可能对健康人群心脏、呼吸系统有影响',
                'general': '空气质量中度污染，建议减少不必要的外出。',
                'outdoor_activity': '建议避免长时间户外活动，尽量留在室内',
                'exercise': '避免高强度户外运动，可在室内进行轻度运动',
                'travel': '减少不必要的出行，如需外出请做好防护措施',
                'window': '建议关闭门窗，减少室外污染物进入',
                'mask': '外出建议佩戴口罩，优先选择KN95/N95级别的防护口罩',
                'children': '儿童应避免户外活动，在家中进行安静的游戏和学习',
                'elderly': '老年人应留在室内，避免外出，注意监测身体状况',
                'respiratory_patients': '呼吸系统疾病患者避免户外活动，留在室内，按时用药，如有不适及时就医',
                'heart_patients': '心脏病患者避免户外活动，保持情绪稳定，注意休息，备好急救药品',
                'pregnant_women': '孕妇应避免外出，留在室内，保持心情放松，注意胎动',
                'office_workers': '关闭门窗，开启空气净化器和新风系统',
                'dining': '避免户外用餐，选择室内空气质量好的餐厅',
                'clothing': '外出穿着长袖长裤，回家后及时清洗面部和口鼻',
                'transportation': '尽量避免骑行和步行，选择密闭性好的交通工具',
                'home_air': '必须开启空气净化器，使用HEPA滤网',
                'plants': '继续养护室内绿植，可适当增加空气湿度',
                'emotion': '可能会感到不适，保持良好心态，减少焦虑'
            },
            '重度污染': {
                'summary': '心脏病和肺病患者症状显著加剧，运动耐受力降低，健康人群普遍出现症状',
                'general': '空气质量重度污染，请尽量留在室内，避免外出。',
                'outdoor_activity': '强烈建议留在室内，停止所有户外活动',
                'exercise': '停止所有户外运动，可在室内进行简单的拉伸活动',
                'travel': '尽量避免外出，取消非必要的行程安排',
                'window': '关闭门窗，防止室外污染空气进入室内',
                'mask': '外出必须佩戴KN95/N95及以上级别的防护口罩',
                'children': '儿童严禁户外活动，在家中活动，注意多喝水',
                'elderly': '老年人必须留在室内，避免任何外出，密切关注身体状况',
                'respiratory_patients': '呼吸系统疾病患者严禁外出，留在室内，坚持规范治疗，如症状加重立即就医',
                'heart_patients': '心脏病患者严禁外出，保持室内安静，避免情绪激动，按时服药',
                'pregnant_women': '孕妇必须留在室内，避免任何外出，保持室内空气清新，注意休息',
                'office_workers': '关闭门窗，全程开启空气净化器，建议减少面对面会议',
                'dining': '严禁户外用餐，建议在家就餐或选择外卖',
                'clothing': '如必须外出，穿戴齐全，回家后立即换洗衣物、清洁身体',
                'transportation': '严禁骑行和步行，如必须外出请选择私家车',
                'home_air': '24小时开启空气净化器，保持室内湿度在40%-60%',
                'plants': '室内绿植可正常养护，帮助净化空气',
                'emotion': '可能会有明显不适，保持心态平和，通过听音乐等方式放松'
            },
            '严重污染': {
                'summary': '健康人群运动耐受力降低，有明显强烈症状，提前出现某些疾病',
                'general': '空气质量严重污染，所有人都应采取严格的防护措施！',
                'outdoor_activity': '严禁任何户外活动，必须留在室内',
                'exercise': '停止所有运动，包括室内高强度运动，保持安静休息',
                'travel': '严禁外出，取消所有行程，紧急情况除外',
                'window': '紧闭门窗，使用密封条减少缝隙，必要时使用湿毛巾封堵',
                'mask': '如遇紧急情况必须外出，必须佩戴N95及以上级别口罩，且停留时间尽可能短',
                'children': '儿童必须留在室内，避免剧烈活动，多喝水，注意观察身体反应',
                'elderly': '老年人必须留在室内，绝对避免外出，家人密切关注其身体状况',
                'respiratory_patients': '呼吸系统疾病患者必须留在室内，坚持用药，备好急救用品，如出现严重呼吸困难立即拨打120',
                'heart_patients': '心脏病患者必须留在室内，绝对卧床休息，保持情绪稳定，如有胸痛等症状立即就医',
                'pregnant_women': '孕妇必须留在室内，保持左侧卧位，注意胎动，如有异常立即联系医生',
                'office_workers': '建议居家办公，如必须到岗，关闭门窗，开启所有空气净化设备',
                'dining': '严禁外出就餐，在家准备清淡饮食，多喝水',
                'clothing': '如必须外出，穿戴全套防护装备，回家后立即洗澡、彻底清洁',
                'transportation': '严禁任何形式的外出，紧急情况呼叫救护车',
                'home_air': '24小时不间断开启空气净化器，使用最高档位，定期更换滤网',
                'plants': '室内绿植可继续养护，注意保持适当湿度',
                'emotion': '可能会有严重不适，保持冷静，避免恐慌，通过室内活动缓解压力'
            }
        }
        return advice_map.get(aqi_level, {})

    def generate_hourly_advice(self, predictions_df):
        results = []
        for _, row in predictions_df.iterrows():
            aqi = row['AQI']
            level_info = self.get_aqi_level(aqi)
            detailed_advice = self.get_detailed_advice(level_info['level'])
            results.append({
                'time': row['timestamp'],
                'aqi': round(aqi, 1),
                'pm25': round(row['PM2.5'], 1),
                'pm10': round(row['PM10'], 1),
                'so2': round(row['SO2'], 1),
                'no2': round(row['NO2'], 1),
                'o3': round(row['O3'], 1),
                'level': level_info['level'],
                'color': level_info['color'],
                'description': level_info['description'],
                'advice': detailed_advice
            })
        return results

    def generate_summary(self, predictions_df):
        avg_aqi = predictions_df['AQI'].mean()
        max_aqi = predictions_df['AQI'].max()
        min_aqi = predictions_df['AQI'].min()

        avg_level = self.get_aqi_level(avg_aqi)
        max_level = self.get_aqi_level(max_aqi)

        time_periods = []
        current_level = None
        start_time = None

        for _, row in predictions_df.iterrows():
            level = self.get_aqi_level(row['AQI'])['level']
            if level != current_level:
                if current_level is not None:
                    time_periods.append({
                        'start': start_time,
                        'end': row['timestamp'],
                        'level': current_level
                    })
                current_level = level
                start_time = row['timestamp']

        if current_level is not None:
            time_periods.append({
                'start': start_time,
                'end': predictions_df.iloc[-1]['timestamp'],
                'level': current_level
            })

        return {
            'avg_aqi': round(avg_aqi, 1),
            'max_aqi': round(max_aqi, 1),
            'min_aqi': round(min_aqi, 1),
            'avg_level': avg_level['level'],
            'max_level': max_level['level'],
            'time_periods': time_periods,
            'overall_advice': self.get_detailed_advice(avg_level['level'])
        }
