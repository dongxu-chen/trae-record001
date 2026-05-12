import 'package:flutter/material.dart';
import 'package:table_calendar/table_calendar.dart';
import 'package:intl/intl.dart';
import '../models/task.dart';
import '../services/database.dart';
import 'home.dart';

class CalendarScreen extends StatefulWidget {
  const CalendarScreen({super.key});

  @override
  State<CalendarScreen> createState() => _CalendarScreenState();
}

class _CalendarScreenState extends State<CalendarScreen> {
  final DatabaseService _dbService = DatabaseService();
  CalendarFormat _calendarFormat = CalendarFormat.month;
  DateTime _focusedDay = DateTime.now();
  DateTime? _selectedDay;
  Map<DateTime, List<Task>> _events = {};
  List<Task> _selectedDayTasks = [];

  @override
  void initState() {
    super.initState();
    _selectedDay = _focusedDay;
    _loadEvents();
  }

  Future<void> _loadEvents() async {
    final now = DateTime.now();
    final start = DateTime(now.year - 1, 1, 1);
    final end = DateTime(now.year + 1, 12, 31);
    final taskCounts = await _dbService.getTaskCountByDateRange(start, end);
    final allTasks = await _dbService.getAllTasks();

    final Map<DateTime, List<Task>> events = {};
    for (final task in allTasks) {
      final dateKey = DateTime(
        task.scheduledTime.year,
        task.scheduledTime.month,
        task.scheduledTime.day,
      );
      if (events[dateKey] == null) {
        events[dateKey] = [];
      }
      events[dateKey]!.add(task);
    }

    setState(() {
      _events = events;
    });
  }

  Future<void> _loadSelectedDayTasks() async {
    if (_selectedDay != null) {
      final tasks = await _dbService.getTasksByDate(_selectedDay!);
      setState(() {
        _selectedDayTasks = tasks;
      });
    }
  }

  List<Task> _getTasksForDay(DateTime day) {
    final dateKey = DateTime(day.year, day.month, day.day);
    return _events[dateKey] ?? [];
  }

  Color _getStatusColor(Task task) {
    if (task.isCompleted) {
      return Colors.grey;
    } else if (task.isOverdue) {
      return Colors.red;
    } else if (task.isToday) {
      return Colors.orange;
    }
    return Colors.blue;
  }

  IconData _getStatusIcon(Task task) {
    if (task.isCompleted) {
      return Icons.check_circle;
    } else if (task.isOverdue) {
      return Icons.warning;
    }
    return Icons.access_time;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Calendar'),
        centerTitle: true,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () async {
              await _loadEvents();
              await _loadSelectedDayTasks();
            },
            tooltip: 'Refresh',
          ),
        ],
      ),
      body: Column(
        children: [
          TableCalendar<Task>(
            firstDay: DateTime.utc(2020, 1, 1),
            lastDay: DateTime.utc(2030, 12, 31),
            focusedDay: _focusedDay,
            calendarFormat: _calendarFormat,
            eventLoader: _getTasksForDay,
            selectedDayPredicate: (day) {
              return isSameDay(_selectedDay, day);
            },
            onDaySelected: (selectedDay, focusedDay) {
              if (!isSameDay(_selectedDay, selectedDay)) {
                setState(() {
                  _selectedDay = selectedDay;
                  _focusedDay = focusedDay;
                });
                _loadSelectedDayTasks();
              }
            },
            onFormatChanged: (format) {
              if (_calendarFormat != format) {
                setState(() {
                  _calendarFormat = format;
                });
              }
            },
            onPageChanged: (focusedDay) {
              _focusedDay = focusedDay;
            },
            calendarStyle: CalendarStyle(
              markerDecoration: const BoxDecoration(
                color: Colors.blue,
                shape: BoxShape.circle,
              ),
              todayDecoration: BoxDecoration(
                color: Theme.of(context).colorScheme.primary.withOpacity(0.3),
                shape: BoxShape.circle,
              ),
              selectedDecoration: BoxDecoration(
                color: Theme.of(context).colorScheme.primary,
                shape: BoxShape.circle,
              ),
            ),
            headerStyle: const HeaderStyle(
              formatButtonVisible: true,
              titleCentered: true,
            ),
          ),
          const Divider(height: 1),
          Expanded(
            child: _selectedDayTasks.isEmpty
                ? Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.event_busy, size: 60, color: Colors.grey[300]),
                        const SizedBox(height: 16),
                        Text(
                          _selectedDay != null
                              ? 'No tasks for ${DateFormat('MMMM d, yyyy').format(_selectedDay!)}'
                              : 'Select a date to view tasks',
                          style: TextStyle(color: Colors.grey[600]),
                        ),
                      ],
                    ),
                  )
                : ListView.builder(
                    padding: const EdgeInsets.all(8),
                    itemCount: _selectedDayTasks.length,
                    itemBuilder: (context, index) {
                      final task = _selectedDayTasks[index];
                      return Card(
                        margin: const EdgeInsets.only(bottom: 8),
                        child: ListTile(
                          leading: Icon(
                            _getStatusIcon(task),
                            color: _getStatusColor(task),
                          ),
                          title: Text(
                            task.title,
                            style: TextStyle(
                              decoration: task.isCompleted
                                  ? TextDecoration.lineThrough
                                  : null,
                              color: task.isCompleted ? Colors.grey : null,
                            ),
                          ),
                          subtitle: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              if (task.description != null) ...[
                                Text(task.description!),
                              ],
                              Text(
                                DateFormat('HH:mm').format(task.scheduledTime),
                                style: TextStyle(
                                  color: _getStatusColor(task),
                                  fontSize: 12,
                                ),
                              ),
                            ],
                          ),
                          trailing: Chip(
                            label: Text(task.isCompleted ? 'Done' : 'Pending'),
                            backgroundColor:
                                task.isCompleted ? Colors.green[100] : Colors.blue[100],
                            labelStyle: TextStyle(
                              color: task.isCompleted ? Colors.green[700] : Colors.blue[700],
                            ),
                          ),
                          onTap: () {
                            Navigator.of(context).push(
                              MaterialPageRoute(
                                builder: (context) => const HomeScreen(),
                              ),
                            );
                          },
                        ),
                      );
                    },
                  ),
          ),
        ],
      ),
    );
  }
}
