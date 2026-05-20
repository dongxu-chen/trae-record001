import 'package:flutter/material.dart';
import '../models/reading_stats.dart';

class ReadingHeatMap extends StatelessWidget {
  final List<DailyReading> data;
  final Color? color;

  const ReadingHeatMap({
    super.key,
    required this.data,
    this.color,
  });

  @override
  Widget build(BuildContext context) {
    final themeColor = color ?? Theme.of(context).primaryColor;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildMonthHeader(),
        const SizedBox(height: 8),
        GridView.builder(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: 7,
            crossAxisSpacing: 4,
            mainAxisSpacing: 4,
          ),
          itemCount: data.length,
          itemBuilder: (context, index) {
            final day = data[index];
            final intensity = _calculateIntensity(day.minutes);

            return Tooltip(
              message: '${_formatDate(day.date)}: ${day.minutes} 分钟',
              child: Container(
                decoration: BoxDecoration(
                  color: day.hasReading
                      ? themeColor.withOpacity(0.2 + intensity * 0.8)
                      : Colors.grey[100],
                  borderRadius: BorderRadius.circular(4),
                  border: day.minutes > 30
                      ? Border.all(color: themeColor, width: 1.5)
                      : null,
                ),
                child: Center(
                  child: Text(
                    '${day.date.day}',
                    style: TextStyle(
                      fontSize: 10,
                      color: day.hasReading
                          ? intensity > 0.5
                              ? Colors.white
                              : Colors.black87
                          : Colors.grey[400],
                      fontWeight: day.hasReading ? FontWeight.w600 : FontWeight.normal,
                    ),
                  ),
                ),
              ),
            );
          },
        ),
        const SizedBox(height: 12),
        _buildLegend(themeColor),
      ],
    );
  }

  Widget _buildMonthHeader() {
    if (data.isEmpty) return const SizedBox.shrink();

    final months = data.map((d) => '${d.date.year}年${d.date.month}月').toSet();

    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          months.first,
          style: const TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w500,
            color: Colors.grey,
          ),
        ),
        const Row(
          children: [
            Text('一 二 三 四 五 六 日', style: TextStyle(fontSize: 10, color: Colors.grey)),
          ],
        ),
      ],
    );
  }

  Widget _buildLegend(Color themeColor) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.end,
      children: [
        const Text('少', style: TextStyle(fontSize: 10, color: Colors.grey)),
        const SizedBox(width: 8),
        ...[0.0, 0.25, 0.5, 0.75, 1.0].map((opacity) {
          return Container(
            width: 16,
            height: 16,
            margin: const EdgeInsets.symmetric(horizontal: 2),
            decoration: BoxDecoration(
              color: themeColor.withOpacity(0.2 + opacity * 0.6),
              borderRadius: BorderRadius.circular(3),
            ),
          );
        }),
        const SizedBox(width: 8),
        const Text('多', style: TextStyle(fontSize: 10, color: Colors.grey)),
      ],
    );
  }

  double _calculateIntensity(int minutes) {
    if (minutes <= 0) return 0.0;
    if (minutes <= 10) return 0.2;
    if (minutes <= 30) return 0.4;
    if (minutes <= 60) return 0.6;
    if (minutes <= 120) return 0.8;
    return 1.0;
  }

  String _formatDate(DateTime date) {
    return '${date.month}月${date.day}日';
  }
}

class HourlyChart extends StatelessWidget {
  final Map<int, int> data;
  final Color? color;

  const HourlyChart({
    super.key,
    required this.data,
    this.color,
  });

  @override
  Widget build(BuildContext context) {
    final themeColor = color ?? Theme.of(context).primaryColor;
    final maxValue = data.values.isNotEmpty ? data.values.reduce((a, b) => a > b ? a : b) : 1;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          '时段分布',
          style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600),
        ),
        const SizedBox(height: 16),
        SizedBox(
          height: 150,
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: List.generate(24, (index) {
              final hour = index;
              final value = data[hour] ?? 0;
              final height = maxValue > 0 ? (value / maxValue) * 100 : 0.0;

              return Expanded(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    Container(
                      height: height > 0 ? height.toDouble() : 2,
                      margin: const EdgeInsets.symmetric(horizontal: 1),
                      decoration: BoxDecoration(
                        color: _isPeakHour(hour)
                            ? themeColor
                            : themeColor.withOpacity(0.4),
                        borderRadius: const BorderRadius.vertical(top: Radius.circular(4)),
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '$hour',
                      style: TextStyle(
                        fontSize: 8,
                        color: _isPeakHour(hour) ? themeColor : Colors.grey,
                        fontWeight: _isPeakHour(hour) ? FontWeight.bold : FontWeight.normal,
                      ),
                    ),
                  ],
                ),
              );
            }),
          ),
        ),
      ],
    );
  }

  bool _isPeakHour(int hour) {
    if (data.isEmpty) return false;
    final maxVal = data.values.reduce((a, b) => a > b ? a : b);
    return data[hour] == maxVal;
  }
}

class WeeklyChart extends StatelessWidget {
  final Map<int, int> data;
  final Color? color;

  const WeeklyChart({
    super.key,
    required this.data,
    this.color,
  });

  static const List<String> _weekdays = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];

  @override
  Widget build(BuildContext context) {
    final themeColor = color ?? Theme.of(context).primaryColor;
    final maxValue = data.values.isNotEmpty ? data.values.reduce((a, b) => a > b ? a : b) : 1;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          '周分布',
          style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600),
        ),
        const SizedBox(height: 16),
        SizedBox(
          height: 120,
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: List.generate(7, (index) {
              final value = data[index] ?? 0;
              final height = maxValue > 0 ? (value / maxValue) * 80 : 0.0;
              final isMax = value == maxValue && value > 0;

              return Expanded(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    Text(
                      '${value}m',
                      style: TextStyle(
                        fontSize: 9,
                        color: isMax ? themeColor : Colors.grey,
                        fontWeight: isMax ? FontWeight.bold : FontWeight.normal,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Container(
                      height: height > 0 ? height.toDouble() : 4,
                      margin: const EdgeInsets.symmetric(horizontal: 4),
                      decoration: BoxDecoration(
                        color: isMax ? themeColor : themeColor.withOpacity(0.35),
                        borderRadius: BorderRadius.circular(6),
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      _weekdays[index],
                      style: TextStyle(
                        fontSize: 10,
                        color: isMax ? themeColor : Colors.grey[600],
                        fontWeight: isMax ? FontWeight.w600 : FontWeight.normal,
                      ),
                    ),
                  ],
                ),
              );
            }),
          ),
        ),
      ],
    );
  }
}

class StatCard extends StatelessWidget {
  final String title;
  final String value;
  final String? subtitle;
  final IconData icon;
  final Color color;
  final VoidCallback? onTap;

  const StatCard({
    super.key,
    required this.title,
    required this.value,
    this.subtitle,
    required this.icon,
    required this.color,
    this.onTap,
  });

  factory StatCard.totalTime(int minutes, {VoidCallback? onTap}) {
    return StatCard(
      title: '总阅读时长',
      value: _formatDuration(minutes),
      subtitle: '${(minutes / 60).toStringAsFixed(1)} 小时',
      icon: Icons.timer,
      color: Colors.blue,
      onTap: onTap,
    );
  }

  factory StatCard.readingDays(int days, {VoidCallback? onTap}) {
    return StatCard(
      title: '阅读天数',
      value: '$days',
      subtitle: '天',
      icon: Icons.calendar_today,
      color: Colors.green,
      onTap: onTap,
    );
  }

  factory StatCard.streak(int streak, {VoidCallback? onTap}) {
    return StatCard(
      title: streak > 0 ? '连续阅读' : '开始阅读',
      value: streak > 0 ? '$streak' : '-',
      subtitle: streak > 0 ? '天' : '',
      icon: Icons.local_fire_department,
      color: Colors.orange,
      onTap: onTap,
    );
  }

  factory StatCard.bookmarks(int count, {VoidCallback? onTap}) {
    return StatCard(
      title: '书摘数量',
      value: '$count',
      subtitle: '条',
      icon: Icons.bookmark,
      color: Colors.purple,
      onTap: onTap,
    );
  }

  factory StatCard.booksCompleted(int count, {VoidCallback? onTap}) {
    return StatCard(
      title: '完成书籍',
      value: '$count',
      subtitle: '本',
      icon: Icons.check_circle,
      color: Colors.teal,
      onTap: onTap,
    );
  }

  static String _formatDuration(int minutes) {
    if (minutes < 60) return '$minutes分钟';
    final hours = minutes ~/ 60;
    final mins = minutes % 60;
    return mins > 0 ? '${hours}h${mins}m' : '${hours}h';
  }

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(16),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: color.withOpacity(0.08),
          borderRadius: BorderRadius.circular(16),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Icon(icon, color: color, size: 24),
                if (subtitle != null)
                  Text(
                    subtitle!,
                    style: TextStyle(fontSize: 12, color: Colors.grey[600]),
                  ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              value,
              style: TextStyle(
                fontSize: 28,
                fontWeight: FontWeight.bold,
                color: color,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              title,
              style: TextStyle(
                fontSize: 12,
                color: Colors.grey[600],
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
