import { useMemo } from 'react';
import type { HeatmapData } from '../../utils/statistics';
import { getHourLabels, getDayLabels } from '../../utils/statistics';

interface HeatmapProps {
  data: HeatmapData[];
  title?: string;
}

const COLOR_SCALE = [
  'bg-gray-800',
  'bg-green-900/50',
  'bg-green-700/60',
  'bg-green-500/70',
  'bg-green-400/80',
  'bg-green-300',
];

export function Heatmap({ data, title = '扫码时段热力图' }: HeatmapProps) {
  const hourLabels = getHourLabels();
  const dayLabels = getDayLabels();

  const intensityMap = useMemo(() => {
    const map = new Map<string, number>();
    data.forEach((d) => {
      map.set(`${d.dayIndex}-${d.hour}`, d.count);
    });
    return map;
  }, [data]);

  const getColor = (count: number): string => {
    if (count === 0) return COLOR_SCALE[0];
    if (count <= 2) return COLOR_SCALE[1];
    if (count <= 5) return COLOR_SCALE[2];
    if (count <= 10) return COLOR_SCALE[3];
    if (count <= 20) return COLOR_SCALE[4];
    return COLOR_SCALE[5];
  };

  return (
    <div className="bg-[#161b22] rounded-xl border border-gray-700/50 p-4">
      <h3 className="text-sm font-medium text-gray-400 mb-4">{title}</h3>
      
      <div className="overflow-x-auto">
        <div className="min-w-max">
          <div className="flex gap-0.5 mb-1 pl-12">
            {hourLabels.filter((_, i) => i % 3 === 0).map((label, i) => (
              <div key={i} className="w-6 text-center text-[10px] text-gray-500">
                {label.replace(':00', '')}
              </div>
            ))}
          </div>
          
          {dayLabels.map((day, dayIndex) => (
            <div key={day} className="flex items-center gap-1 mb-0.5">
              <div className="w-10 text-xs text-gray-500 text-right pr-2">
                {day}
              </div>
              <div className="flex gap-0.5">
                {Array.from({ length: 24 }, (_, hour) => {
                  const count = intensityMap.get(`${dayIndex}-${hour}`) || 0;
                  return (
                    <div
                      key={hour}
                      className={`w-3 h-3 rounded-sm transition-colors ${getColor(count)}`}
                      title={`${day} ${hour}:00 - ${count} 次扫码`}
                    />
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </div>
      
      <div className="flex items-center justify-end gap-1 mt-3">
        <span className="text-[10px] text-gray-500 mr-2">少</span>
        {COLOR_SCALE.map((color, i) => (
          <div key={i} className={`w-3 h-3 rounded-sm ${color}`} />
        ))}
        <span className="text-[10px] text-gray-500 ml-2">多</span>
      </div>
    </div>
  );
}
