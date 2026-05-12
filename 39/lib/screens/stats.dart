import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:intl/intl.dart';
import '../services/database.dart';
import '../services/export.dart';

class StatsScreen extends StatefulWidget {
  const StatsScreen({super.key});

  @override
  State<StatsScreen> createState() => _StatsScreenState();
}

class _StatsScreenState extends State<StatsScreen> {
  final DatabaseService _dbService = DatabaseService();
  Map<String, int> _taskStats = {};
  List<Map<String, dynamic>> _weeklyStats = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadStats();
  }

  Future<void> _loadStats() async {
    setState(() {
      _isLoading = true;
    });

    final stats = await _dbService.getTaskStats();
    final weekly = await _dbService.getWeeklyTaskStats();

    setState(() {
      _taskStats = stats;
      _weeklyStats = weekly;
      _isLoading = false;
    });
  }

  double _getCompletionRate() {
    final total = _taskStats['total'] ?? 0;
    final completed = _taskStats['completed'] ?? 0;
    if (total == 0) return 0;
    return (completed / total) * 100;
  }

  List<PieChartSectionData> _getCompletionPieSections() {
    final completed = _taskStats['completed'] ?? 0;
    final pending = _taskStats['pending'] ?? 0;

    return [
      PieChartSectionData(
        color: Colors.green,
        value: completed.toDouble(),
        title: 'Completed\n$completed',
        radius: 100,
        titleStyle: const TextStyle(
          fontSize: 14,
          fontWeight: FontWeight.bold,
          color: Colors.white,
        ),
      ),
      PieChartSectionData(
        color: Colors.blue,
        value: pending.toDouble(),
        title: 'Pending\n$pending',
        radius: 100,
        titleStyle: const TextStyle(
          fontSize: 14,
          fontWeight: FontWeight.bold,
          color: Colors.white,
        ),
      ),
    ];
  }

  List<BarChartGroupData> _getWeeklyBarGroups() {
    return _weeklyStats.asMap().entries.map((entry) {
      final index = entry.key;
      final data = entry.value;
      return BarChartGroupData(
        x: index,
        barRods: [
          BarChartRodData(
            toY: (data['total'] as int).toDouble(),
            color: Colors.blue,
            width: 16,
            borderRadius: BorderRadius.circular(4),
          ),
          BarChartRodData(
            toY: (data['completed'] as int).toDouble(),
            color: Colors.green,
            width: 16,
            borderRadius: BorderRadius.circular(4),
          ),
        ],
        showingTooltipIndicators: [0, 1],
      );
    }).toList();
  }

  Future<void> _exportCsv(String type) async {
    try {
      String filePath;
      switch (type) {
        case 'completed':
          filePath = await ExportService().exportCompletedTasksToCsv();
          break;
        case 'pending':
          filePath = await ExportService().exportPendingTasksToCsv();
          break;
        default:
          filePath = await ExportService().exportTasksToCsv();
      }

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Exported to: $filePath')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Export failed: $e')),
        );
      }
    }
  }

  Widget _buildStatCard(String title, int value, IconData icon, Color color) {
    return Card(
      elevation: 4,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 32, color: color),
            const SizedBox(height: 8),
            Text(
              value.toString(),
              style: const TextStyle(
                fontSize: 24,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              title,
              style: const TextStyle(fontSize: 12, color: Colors.grey),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Statistics'),
        centerTitle: true,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadStats,
            tooltip: 'Refresh',
          ),
          PopupMenuButton<String>(
            icon: const Icon(Icons.file_download),
            tooltip: 'Export CSV',
            onSelected: _exportCsv,
            itemBuilder: (context) => [
              const PopupMenuItem(
                value: 'all',
                child: Text('Export All Tasks'),
              ),
              const PopupMenuItem(
                value: 'completed',
                child: Text('Export Completed Tasks'),
              ),
              const PopupMenuItem(
                value: 'pending',
                child: Text('Export Pending Tasks'),
              ),
            ],
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  GridView.count(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    crossAxisCount: 2,
                    childAspectRatio: 1.2,
                    mainAxisSpacing: 16,
                    crossAxisSpacing: 16,
                    children: [
                      _buildStatCard(
                        'Total Tasks',
                        _taskStats['total'] ?? 0,
                        Icons.event_note,
                        Colors.blue,
                      ),
                      _buildStatCard(
                        'Completed',
                        _taskStats['completed'] ?? 0,
                        Icons.check_circle,
                        Colors.green,
                      ),
                      _buildStatCard(
                        'Pending',
                        _taskStats['pending'] ?? 0,
                        Icons.pending_actions,
                        Colors.orange,
                      ),
                      _buildStatCard(
                        'Overdue',
                        _taskStats['overdue'] ?? 0,
                        Icons.warning,
                        Colors.red,
                      ),
                    ],
                  ),
                  const SizedBox(height: 24),
                  Card(
                    elevation: 4,
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Completion Rate: ${_getCompletionRate().toStringAsFixed(1)}%',
                            style: Theme.of(context).textTheme.titleLarge,
                          ),
                          const SizedBox(height: 16),
                          SizedBox(
                            height: 200,
                            child: (_taskStats['total'] ?? 0) > 0
                                ? PieChart(
                                    PieChartData(
                                      sectionsSpace: 2,
                                      centerSpaceRadius: 40,
                                      sections: _getCompletionPieSections(),
                                    ),
                                  )
                                : const Center(
                                    child: Text('No data available'),
                                  ),
                          ),
                          const SizedBox(height: 16),
                          Row(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Row(
                                children: [
                                  Container(
                                    width: 16,
                                    height: 16,
                                    color: Colors.green,
                                  ),
                                  const SizedBox(width: 8),
                                  const Text('Completed'),
                                ],
                              ),
                              const SizedBox(width: 24),
                              Row(
                                children: [
                                  Container(
                                    width: 16,
                                    height: 16,
                                    color: Colors.blue,
                                  ),
                                  const SizedBox(width: 8),
                                  const Text('Pending'),
                                ],
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 24),
                  Card(
                    elevation: 4,
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Weekly Overview (This Week)',
                            style: Theme.of(context).textTheme.titleLarge,
                          ),
                          const SizedBox(height: 16),
                          SizedBox(
                            height: 220,
                            child: _weeklyStats.isNotEmpty
                                ? BarChart(
                                    BarChartData(
                                      alignment: BarChartAlignment.spaceAround,
                                      maxY: _getMaxY(),
                                      barTouchData: BarTouchData(
                                        touchTooltipData: BarTouchTooltipData(
                                          getTooltipColor: (_) => Colors.grey[800]!,
                                          tooltipPadding: const EdgeInsets.all(8),
                                          getTooltipItem: (group, groupIndex, rod, rodIndex) {
                                            final day = _weeklyStats[group.x]['day'];
                                            final total = _weeklyStats[group.x]['total'];
                                            final completed = _weeklyStats[group.x]['completed'];
                                            return BarTooltipItem(
                                              '$day\n',
                                              const TextStyle(color: Colors.white),
                                              children: [
                                                TextSpan(
                                                  text: 'Total: $total\n',
                                                  style: const TextStyle(color: Colors.blue),
                                                ),
                                                TextSpan(
                                                  text: 'Done: $completed',
                                                  style: const TextStyle(color: Colors.green),
                                                ),
                                              ],
                                            );
                                          },
                                        ),
                                      ),
                                      titlesData: FlTitlesData(
                                        show: true,
                                        bottomTitles: AxisTitles(
                                          sideTitles: SideTitles(
                                            showTitles: true,
                                            getTitlesWidget: (value, meta) {
                                              final index = value.toInt();
                                              if (index >= 0 && index < _weeklyStats.length) {
                                                return Padding(
                                                  padding: const EdgeInsets.only(top: 8),
                                                  child: Text(
                                                    _weeklyStats[index]['day'],
                                                    style: const TextStyle(fontSize: 12),
                                                  ),
                                                );
                                              }
                                              return const Text('');
                                            },
                                            reservedSize: 30,
                                          ),
                                        ),
                                        leftTitles: const AxisTitles(
                                          sideTitles: SideTitles(
                                            showTitles: true,
                                            reservedSize: 30,
                                          ),
                                        ),
                                        topTitles: const AxisTitles(
                                          sideTitles: SideTitles(showTitles: false),
                                        ),
                                        rightTitles: const AxisTitles(
                                          sideTitles: SideTitles(showTitles: false),
                                        ),
                                      ),
                                      gridData: const FlGridData(show: true),
                                      borderData: FlBorderData(show: false),
                                      barGroups: _getWeeklyBarGroups(),
                                    ),
                                  )
                                : const Center(child: Text('No data available')),
                          ),
                          const SizedBox(height: 16),
                          Row(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Row(
                                children: [
                                  Container(
                                    width: 16,
                                    height: 16,
                                    color: Colors.blue,
                                  ),
                                  const SizedBox(width: 8),
                                  const Text('Total'),
                                ],
                              ),
                              const SizedBox(width: 24),
                              Row(
                                children: [
                                  Container(
                                    width: 16,
                                    height: 16,
                                    color: Colors.green,
                                  ),
                                  const SizedBox(width: 8),
                                  const Text('Completed'),
                                ],
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
    );
  }

  double _getMaxY() {
    if (_weeklyStats.isEmpty) return 5;
    int maxTotal = 0;
    for (final data in _weeklyStats) {
      final total = data['total'] as int;
      if (total > maxTotal) maxTotal = total;
    }
    return (maxTotal > 0) ? maxTotal.toDouble() + 1 : 5;
  }
}
