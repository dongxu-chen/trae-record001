import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/stats_provider.dart';
import '../providers/ai_provider.dart';
import '../widgets/reading_charts.dart';
import '../models/reading_stats.dart';

class StatsScreen extends StatefulWidget {
  const StatsScreen({super.key});

  @override
  State<StatsScreen> createState() => _StatsScreenState();
}

class _StatsScreenState extends State<StatsScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      Provider.of<StatsProvider>(context, listen: false).loadStats();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('阅读统计'),
        actions: [
          IconButton(
            icon: const Icon(Icons.auto_awesome),
            onPressed: _analyzeHabits,
            tooltip: 'AI分析阅读习惯',
          ),
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => Provider.of<StatsProvider>(context, listen: false).loadStats(),
          ),
        ],
      ),
      body: Consumer2<StatsProvider, AIProvider>(
        builder: (context, statsProvider, aiProvider, _) {
          final stats = statsProvider.stats;

          if (stats == null) {
            return const Center(child: CircularProgressIndicator());
          }

          return RefreshIndicator(
            onRefresh: () => statsProvider.loadStats(),
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (statsProvider.hasActiveSession)
                    _buildActiveSessionCard(statsProvider),
                  const SizedBox(height: 16),
                  _buildStatCards(stats),
                  const SizedBox(height: 24),
                  _buildHeatMap(stats),
                  const SizedBox(height: 24),
                  _buildHourlyChart(stats),
                  const SizedBox(height: 24),
                  _buildWeeklyChart(stats),
                  const SizedBox(height: 24),
                  _buildReadingRanking(stats),
                  const SizedBox(height: 24),
                  if (aiProvider.aiAnalysis != null)
                    _buildAIAnalysis(aiProvider),
                  const SizedBox(height: 100),
                ],
              ),
            ),
          );
        },
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _generateDemoData,
        icon: const Icon(Icons.add_chart),
        label: const Text('生成演示数据'),
      ),
    );
  }

  Widget _buildActiveSessionCard(StatsProvider statsProvider) {
    return StreamBuilder(
      stream: Stream.periodic(const Duration(seconds: 1)),
      builder: (context, snapshot) {
        final duration = statsProvider.currentSessionDuration;
        final minutes = (duration / 60).floor();
        final seconds = duration % 60;

        return Card(
          elevation: 4,
          color: Colors.green.shade50,
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                const Icon(Icons.menu_book, color: Colors.green, size: 32),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        '正在阅读',
                        style: TextStyle(
                          fontSize: 14,
                          color: Colors.grey,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        statsProvider.activeSession?.bookTitle ?? '未知书籍',
                        style: const TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ],
                  ),
                ),
                Text(
                  '${minutes.toString().padLeft(2, '0')}:${seconds.toString().padLeft(2, '0')}',
                  style: const TextStyle(
                    fontSize: 24,
                    fontWeight: FontWeight.bold,
                    color: Colors.green,
                    fontFamily: 'monospace',
                  ),
                ),
                const SizedBox(width: 16),
                IconButton(
                  icon: const Icon(Icons.stop, color: Colors.red),
                  onPressed: () => statsProvider.endReadingSession(),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildStatCards(ReadingStats stats) {
    return GridView.count(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      crossAxisCount: 2,
      crossAxisSpacing: 12,
      mainAxisSpacing: 12,
      childAspectRatio: 1.3,
      children: [
        StatCard.totalTime(stats.totalReadMinutes),
        StatCard.readingDays(stats.readingDays),
        StatCard.streak(stats.currentStreak),
        StatCard.bookmarks(stats.totalBookmarks),
      ],
    );
  }

  Widget _buildHeatMap(ReadingStats stats) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text(
                  '近30天阅读热图',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                Text(
                  '连续${stats.currentStreak}天',
                  style: TextStyle(
                    fontSize: 12,
                    color: Colors.orange.shade700,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            ReadingHeatMap(data: stats.dailyReadingsLast30Days),
          ],
        ),
      ),
    );
  }

  Widget _buildHourlyChart(ReadingStats stats) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: HourlyChart(data: stats.hourlyDistribution),
      ),
    );
  }

  Widget _buildWeeklyChart(ReadingStats stats) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: WeeklyChart(data: stats.weeklyDistribution),
      ),
    );
  }

  Widget _buildReadingRanking(ReadingStats stats) {
    if (stats.bookReadingTime.isEmpty) {
      return const SizedBox.shrink();
    }

    final sortedBooks = stats.bookReadingTime.entries.toList()
      ..sort((a, b) => b.value.compareTo(a.value));

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              '书籍阅读时长排行',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 16),
            ...sortedBooks.take(5).map((entry) {
              final minutes = entry.value;
              final hours = (minutes / 60).toStringAsFixed(1);
              final index = sortedBooks.indexOf(entry);
              final isTop3 = index < 3;

              return Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Row(
                  children: [
                    Container(
                      width: 28,
                      height: 28,
                      decoration: BoxDecoration(
                        color: isTop3
                            ? [Colors.amber, Colors.grey, Colors.brown][index]
                            : Colors.grey.shade200,
                        borderRadius: BorderRadius.circular(14),
                      ),
                      child: Center(
                        child: Text(
                          '${index + 1}',
                          style: TextStyle(
                            color: isTop3 ? Colors.white : Colors.grey,
                            fontWeight: FontWeight.bold,
                            fontSize: 12,
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        entry.key,
                        style: TextStyle(
                          fontWeight: isTop3 ? FontWeight.w600 : FontWeight.normal,
                        ),
                      ),
                    ),
                    Text(
                      '${hours}h',
                      style: TextStyle(
                        color: Colors.grey.shade600,
                        fontSize: 12,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ],
                ),
              );
            }),
          ],
        ),
      ),
    );
  }

  Widget _buildAIAnalysis(AIProvider aiProvider) {
    return Card(
      color: Colors.purple.shade50,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.auto_awesome, color: Colors.purple.shade700),
                const SizedBox(width: 8),
                Text(
                  'AI 阅读习惯分析',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                    color: Colors.purple.shade900,
                  ),
                ),
                const Spacer(),
                if (aiProvider.isLoading)
                  const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  ),
              ],
            ),
            const SizedBox(height: 16),
            if (aiProvider.aiAnalysis != null)
              Text(
                aiProvider.aiAnalysis!,
                style: TextStyle(
                  height: 1.6,
                  color: Colors.purple.shade800,
                ),
              ),
          ],
        ),
      ),
    );
  }

  void _analyzeHabits() async {
    final statsProvider = Provider.of<StatsProvider>(context, listen: false);
    final aiProvider = Provider.of<AIProvider>(context, listen: false);

    if (statsProvider.stats != null) {
      await aiProvider.analyzeReadingHabits(statsProvider.stats!);
    }
  }

  void _generateDemoData() {
    Provider.of<StatsProvider>(context, listen: false).generateDemoData();
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('演示数据已生成')),
    );
  }
}
