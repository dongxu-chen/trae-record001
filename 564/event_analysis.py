import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')


@dataclass
class EmissionEvent:
    event_id: str
    start_date: pd.Timestamp
    end_date: pd.Timestamp
    event_type: str
    description: str
    sources_involved: List[str] = field(default_factory=list)
    detected: bool = False
    confidence: float = 0.0


@dataclass
class EventAnalysisResult:
    events: List[EmissionEvent]
    detection_metrics: Dict
    alignment_scores: Dict[str, float]
    event_impact: pd.DataFrame


def detect_anomaly_events(
    source_contribution: pd.DataFrame,
    threshold_method: str = 'iqr',
    threshold_multiplier: float = 1.5,
    min_duration: int = 1,
    max_gap: int = 1
) -> List[EmissionEvent]:
    events = []
    event_id_counter = 1
    
    for source in source_contribution.columns:
        data = source_contribution[source].values
        
        if threshold_method == 'iqr':
            q1 = np.percentile(data, 25)
            q3 = np.percentile(data, 75)
            iqr = q3 - q1
            threshold = q3 + threshold_multiplier * iqr
        elif threshold_method == 'std':
            mean = np.mean(data)
            std = np.std(data)
            threshold = mean + threshold_multiplier * std
        elif threshold_method == 'percentile':
            threshold = np.percentile(data, 95)
        else:
            threshold = np.percentile(data, 90)
        
        is_anomaly = data > threshold
        
        anomaly_periods = []
        current_start = None
        
        for i in range(len(is_anomaly)):
            if is_anomaly[i] and current_start is None:
                current_start = i
            elif not is_anomaly[i] and current_start is not None:
                duration = i - current_start
                if duration >= min_duration:
                    anomaly_periods.append((current_start, i - 1))
                current_start = None
        
        if current_start is not None:
            duration = len(is_anomaly) - current_start
            if duration >= min_duration:
                anomaly_periods.append((current_start, len(is_anomaly) - 1))
        
        merged_periods = []
        for start, end in anomaly_periods:
            if not merged_periods:
                merged_periods.append([start, end])
            else:
                last_start, last_end = merged_periods[-1]
                if start - last_end <= max_gap:
                    merged_periods[-1][1] = end
                else:
                    merged_periods.append([start, end])
        
        for start_idx, end_idx in merged_periods:
            start_date = source_contribution.index[start_idx]
            end_date = source_contribution.index[end_idx]
            avg_contribution = np.mean(data[start_idx:end_idx + 1])
            baseline = np.percentile(data, 50)
            confidence = min((avg_contribution - baseline) / baseline, 1.0)
            
            event = EmissionEvent(
                event_id=f'EVT_{event_id_counter:04d}',
                start_date=start_date,
                end_date=end_date,
                event_type='异常排放',
                description=f'{source} 异常排放事件，持续 {end_idx - start_idx + 1} 天',
                sources_involved=[source],
                detected=True,
                confidence=round(confidence, 3)
            )
            events.append(event)
            event_id_counter += 1
    
    events.sort(key=lambda x: x.start_date)
    
    return events


def create_manual_event(
    event_id: str,
    start_date: str,
    end_date: str,
    event_type: str,
    description: str,
    sources_involved: List[str] = None
) -> EmissionEvent:
    return EmissionEvent(
        event_id=event_id,
        start_date=pd.to_datetime(start_date),
        end_date=pd.to_datetime(end_date),
        event_type=event_type,
        description=description,
        sources_involved=sources_involved or [],
        detected=False,
        confidence=0.0
    )


def verify_event_alignment(
    event: EmissionEvent,
    source_contribution: pd.DataFrame,
    window_size: int = 7
) -> Dict:
    event_mask = (source_contribution.index >= event.start_date) & \
                 (source_contribution.index <= event.end_date)
    
    if not event_mask.any():
        return {
            'aligned': False,
            'overlap_days': 0,
            'mean_increase_ratio': 0,
            'peak_increase_ratio': 0,
            'sources_impacted': []
        }
    
    overlap_days = event_mask.sum()
    
    sources_impacted = []
    mean_increase_ratios = {}
    peak_increase_ratios = {}
    
    for source in event.sources_involved or source_contribution.columns:
        event_data = source_contribution.loc[event_mask, source].values
        baseline_data = source_contribution.loc[~event_mask, source].values
        
        if len(baseline_data) == 0 or len(event_data) == 0:
            continue
        
        baseline_mean = np.mean(baseline_data)
        event_mean = np.mean(event_data)
        event_peak = np.max(event_data)
        
        if baseline_mean > 0:
            mean_ratio = (event_mean - baseline_mean) / baseline_mean
            peak_ratio = (event_peak - baseline_mean) / baseline_mean
        else:
            mean_ratio = 0
            peak_ratio = 0
        
        mean_increase_ratios[source] = mean_ratio
        peak_increase_ratios[source] = peak_ratio
        
        if mean_ratio > 0.2:
            sources_impacted.append(source)
    
    overall_mean_ratio = np.mean(list(mean_increase_ratios.values())) if mean_increase_ratios else 0
    overall_peak_ratio = np.mean(list(peak_increase_ratios.values())) if peak_increase_ratios else 0
    
    aligned = len(sources_impacted) >= 1 and overall_mean_ratio > 0.1
    
    return {
        'aligned': aligned,
        'overlap_days': int(overlap_days),
        'mean_increase_ratio': round(overall_mean_ratio, 3),
        'peak_increase_ratio': round(overall_peak_ratio, 3),
        'sources_impacted': sources_impacted,
        'source_details': {
            source: {
                'mean_ratio': mean_increase_ratios.get(source, 0),
                'peak_ratio': peak_increase_ratios.get(source, 0)
            }
            for source in event.sources_involved or source_contribution.columns
        }
    }


def analyze_event_impact(
    events: List[EmissionEvent],
    source_contribution: pd.DataFrame,
    concentration_data: pd.DataFrame
) -> pd.DataFrame:
    impact_data = []
    
    for event in events:
        event_mask = (source_contribution.index >= event.start_date) & \
                     (source_contribution.index <= event.end_date)
        
        if not event_mask.any():
            continue
        
        baseline_mask = ~event_mask
        row = {
            '事件ID': event.event_id,
            '事件类型': event.event_type,
            '开始日期': event.start_date.date(),
            '结束日期': event.end_date.date(),
            '持续天数': (event.end_date - event.start_date).days + 1,
            '置信度': event.confidence,
        }
        
        for source in source_contribution.columns:
            event_mean = source_contribution.loc[event_mask, source].mean()
            baseline_mean = source_contribution.loc[baseline_mask, source].mean()
            increase = ((event_mean - baseline_mean) / baseline_mean * 100) if baseline_mean > 0 else 0
            
            row[f'{source}_事件均值'] = round(event_mean, 2)
            row[f'{source}_基线均值'] = round(baseline_mean, 2)
            row[f'{source}_增幅(%)'] = round(increase, 1)
        
        for species in concentration_data.columns:
            event_mean = concentration_data.loc[event_mask, species].mean()
            baseline_mean = concentration_data.loc[baseline_mask, species].mean()
            increase = ((event_mean - baseline_mean) / baseline_mean * 100) if baseline_mean > 0 else 0
            
            row[f'{species}_事件均值'] = round(event_mean, 2)
            row[f'{species}_基线均值'] = round(baseline_mean, 2)
            row[f'{species}_增幅(%)'] = round(increase, 1)
        
        impact_data.append(row)
    
    return pd.DataFrame(impact_data)


def get_event_summary(events: List[EmissionEvent]) -> pd.DataFrame:
    data = []
    for event in events:
        data.append({
            '事件ID': event.event_id,
            '事件类型': event.event_type,
            '开始日期': event.start_date.date(),
            '结束日期': event.end_date.date(),
            '持续天数': (event.end_date - event.start_date).days + 1,
            '涉及污染源': ', '.join(event.sources_involved),
            '是否检测到': '是' if event.detected else '否',
            '置信度': event.confidence,
            '描述': event.description
        })
    return pd.DataFrame(data)


def load_events_from_file(file_path: str) -> List[EmissionEvent]:
    if file_path.endswith('.csv'):
        df = pd.read_csv(file_path)
    elif file_path.endswith('.xlsx'):
        df = pd.read_excel(file_path)
    else:
        raise ValueError("不支持的文件格式")
    
    events = []
    for _, row in df.iterrows():
        sources = []
        if '涉及污染源' in row:
            sources = [s.strip() for s in str(row['涉及污染源']).split(',')] if pd.notna(row['涉及污染源']) else []
        
        event = EmissionEvent(
            event_id=str(row.get('事件ID', f'EVT_{len(events)+1:04d}')),
            start_date=pd.to_datetime(row.get('开始日期', row.get('start_date'))),
            end_date=pd.to_datetime(row.get('结束日期', row.get('end_date'))),
            event_type=str(row.get('事件类型', row.get('event_type', '未知'))),
            description=str(row.get('描述', row.get('description', ''))),
            sources_involved=sources,
            detected=bool(row.get('是否检测到', row.get('detected', False))),
            confidence=float(row.get('置信度', row.get('confidence', 0.0)))
        )
        events.append(event)
    
    return events


def save_events_to_file(events: List[EmissionEvent], file_path: str):
    df = get_event_summary(events)
    
    if file_path.endswith('.csv'):
        df.to_csv(file_path, index=False, encoding='utf-8-sig')
    elif file_path.endswith('.xlsx'):
        df.to_excel(file_path, index=False)
    else:
        raise ValueError("不支持的文件格式")


def run_event_analysis_pipeline(
    source_contribution: pd.DataFrame,
    concentration_data: pd.DataFrame,
    manual_events: Optional[List[EmissionEvent]] = None,
    detect_params: Optional[Dict] = None
) -> EventAnalysisResult:
    detect_params = detect_params or {}
    
    detected_events = detect_anomaly_events(
        source_contribution,
        threshold_method=detect_params.get('threshold_method', 'iqr'),
        threshold_multiplier=detect_params.get('threshold_multiplier', 1.5),
        min_duration=detect_params.get('min_duration', 1),
        max_gap=detect_params.get('max_gap', 1)
    )
    
    all_events = detected_events.copy()
    
    if manual_events:
        all_events.extend(manual_events)
    
    alignment_scores = {}
    for event in all_events:
        result = verify_event_alignment(event, source_contribution)
        alignment_scores[event.event_id] = result['mean_increase_ratio']
    
    event_impact = analyze_event_impact(all_events, source_contribution, concentration_data)
    
    detection_metrics = {
        '检测事件数': len(detected_events),
        '手动事件数': len(manual_events) if manual_events else 0,
        '总事件数': len(all_events),
        '平均置信度': np.mean([e.confidence for e in detected_events]) if detected_events else 0
    }
    
    return EventAnalysisResult(
        events=all_events,
        detection_metrics=detection_metrics,
        alignment_scores=alignment_scores,
        event_impact=event_impact
    )
