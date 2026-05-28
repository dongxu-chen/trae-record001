import type { ScanRecord } from '../types';

export interface HourlyStats {
  hour: number;
  count: number;
  label: string;
}

export interface DailyStats {
  date: string;
  count: number;
  label: string;
}

export interface WeeklyStats {
  day: string;
  count: number;
  label: string;
}

export interface HeatmapData {
  day: string;
  dayIndex: number;
  hour: number;
  count: number;
  intensity: number;
}

export interface ScanStatistics {
  totalScans: number;
  todayScans: number;
  weeklyScans: number;
  hourlyStats: HourlyStats[];
  dailyStats: DailyStats[];
  weeklyStats: WeeklyStats[];
  heatmapData: HeatmapData[];
  maxHourlyPeak: { hour: number; count: number };
  scanTypes: Record<string, number>;
}

const HOUR_LABELS = [
  '00:00', '01:00', '02:00', '03:00', '04:00', '05:00',
  '06:00', '07:00', '08:00', '09:00', '10:00', '11:00',
  '12:00', '13:00', '14:00', '15:00', '16:00', '17:00',
  '18:00', '19:00', '20:00', '21:00', '22:00', '23:00',
];

const DAY_LABELS = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];

function getStartOfDay(date: Date): Date {
  const d = new Date(date);
  d.setHours(0, 0, 0, 0);
  return d;
}

function getStartOfWeek(date: Date): Date {
  const d = getStartOfDay(date);
  const day = d.getDay();
  d.setDate(d.getDate() - day);
  return d;
}

function formatDate(date: Date): string {
  return date.toISOString().split('T')[0];
}

export function calculateStatistics(records: ScanRecord[]): ScanStatistics {
  const now = new Date();
  const startOfToday = getStartOfDay(now);
  const startOfWeek = getStartOfWeek(now);

  let totalScans = records.length;
  let todayScans = 0;
  let weeklyScans = 0;

  const hourlyCounts = new Array(24).fill(0);
  const dailyCounts = new Map<string, number>();
  const weeklyCounts = new Array(7).fill(0);
  const typeCounts: Record<string, number> = {};

  records.forEach((record) => {
    const recordDate = new Date(record.timestamp);
    const hour = recordDate.getHours();
    const dayOfWeek = recordDate.getDay();
    const dateStr = formatDate(recordDate);

    hourlyCounts[hour]++;
    dailyCounts.set(dateStr, (dailyCounts.get(dateStr) || 0) + 1);
    weeklyCounts[dayOfWeek]++;

    const type = record.type || 'unknown';
    typeCounts[type] = (typeCounts[type] || 0) + 1;

    if (recordDate >= startOfToday) {
      todayScans++;
    }

    if (recordDate >= startOfWeek) {
      weeklyScans++;
    }
  });

  const hourlyStats: HourlyStats[] = hourlyCounts.map((count, hour) => ({
    hour,
    count,
    label: HOUR_LABELS[hour],
  }));

  const dailyStats: DailyStats[] = Array.from(dailyCounts.entries())
    .sort((a, b) => a[0].localeCompare(b[0]))
    .slice(-7)
    .map(([date, count]) => {
      const d = new Date(date);
      return {
        date,
        count,
        label: `${d.getMonth() + 1}/${d.getDate()}`,
      };
    });

  const weeklyStats: WeeklyStats[] = weeklyCounts.map((count, day) => ({
    day: DAY_LABELS[day],
    count,
    label: DAY_LABELS[day],
  }));

  let maxCount = 0;
  let maxHour = 0;
  hourlyCounts.forEach((count, hour) => {
    if (count > maxCount) {
      maxCount = count;
      maxHour = hour;
    }
  });

  const heatmapData: HeatmapData[] = [];
  const intensityScale = 4;
  for (let day = 0; day < 7; day++) {
    for (let hour = 0; hour < 24; hour++) {
      const key = `${day}-${hour}`;
      const count = hourlyCounts[hour];
      const intensity = count > 0 ? Math.min(1, count / Math.max(1, maxCount)) * intensityScale : 0;
      heatmapData.push({
        day: DAY_LABELS[day],
        dayIndex: day,
        hour,
        count,
        intensity,
      });
    }
  }

  return {
    totalScans,
    todayScans,
    weeklyScans,
    hourlyStats,
    dailyStats,
    weeklyStats,
    heatmapData,
    maxHourlyPeak: { hour: maxHour, count: maxCount },
    scanTypes: typeCounts,
  };
}

export function getHourLabels(): string[] {
  return HOUR_LABELS;
}

export function getDayLabels(): string[] {
  return DAY_LABELS;
}
