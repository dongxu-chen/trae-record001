import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:uuid/uuid.dart';
import '../models/task.dart';
import '../services/database.dart';
import '../services/notification.dart';
import 'calendar.dart';
import 'stats.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _selectedIndex = 0;

  final List<Widget> _pages = [
    const TaskListScreen(),
    const CalendarScreen(),
    const StatsScreen(),
  ];

  void _onItemTapped(int index) {
    setState(() {
      _selectedIndex = index;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(
        index: _selectedIndex,
        children: _pages,
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _selectedIndex,
        onDestinationSelected: _onItemTapped,
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.list_alt),
            selectedIcon: Icon(Icons.list_alt),
            label: 'Tasks',
          ),
          NavigationDestination(
            icon: Icon(Icons.calendar_today),
            selectedIcon: Icon(Icons.calendar_today),
            label: 'Calendar',
          ),
          NavigationDestination(
            icon: Icon(Icons.bar_chart),
            selectedIcon: Icon(Icons.bar_chart),
            label: 'Stats',
          ),
        ],
      ),
    );
  }
}

class TaskListScreen extends StatefulWidget {
  const TaskListScreen({super.key});

  @override
  State<TaskListScreen> createState() => _TaskListScreenState();
}

class _TaskListScreenState extends State<TaskListScreen>
    with AutomaticKeepAliveClientMixin {
  List<Task> _tasks = [];
  final DatabaseService _dbService = DatabaseService();
  final NotificationService _notificationService = NotificationService();
  final ScrollController _scrollController = ScrollController();
  final _pageStorageKey = const PageStorageKey('task_list_scroll');

  @override
  bool get wantKeepAlive => true;

  @override
  void initState() {
    super.initState();
    _loadTasks();
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  Future<void> _loadTasks() async {
    final tasks = await _dbService.getAllTasks();
    setState(() {
      _tasks = tasks;
    });
  }

  Future<void> _showAddTaskDialog({Task? existingTask}) async {
    final titleController = TextEditingController(text: existingTask?.title);
    final descriptionController =
        TextEditingController(text: existingTask?.description);
    DateTime selectedDate = existingTask?.scheduledTime ??
        DateTime.now().add(const Duration(hours: 1));
    TimeOfDay selectedTime = TimeOfDay.fromDateTime(
        existingTask?.scheduledTime ?? DateTime.now().add(const Duration(hours: 1)));

    showDialog(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setState) => AlertDialog(
          title: Text(existingTask == null ? 'Add Reminder' : 'Edit Reminder'),
          content: SizedBox(
            width: 400,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(
                  controller: titleController,
                  decoration: const InputDecoration(
                    labelText: 'Title',
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 16),
                TextField(
                  controller: descriptionController,
                  decoration: const InputDecoration(
                    labelText: 'Description (Optional)',
                    border: OutlineInputBorder(),
                  ),
                  maxLines: 2,
                ),
                const SizedBox(height: 16),
                Row(
                  children: [
                    Expanded(
                      child: ListTile(
                        title: const Text('Date'),
                        subtitle: Text(DateFormat('yyyy-MM-dd').format(selectedDate)),
                        onTap: () async {
                          final picked = await showDatePicker(
                            context: context,
                            initialDate: selectedDate,
                            firstDate: DateTime.now(),
                            lastDate: DateTime.now().add(const Duration(days: 365)),
                          );
                          if (picked != null) {
                            setState(() {
                              selectedDate = picked;
                            });
                          }
                        },
                      ),
                    ),
                    Expanded(
                      child: ListTile(
                        title: const Text('Time'),
                        subtitle: Text(selectedTime.format(context)),
                        onTap: () async {
                          final picked = await showTimePicker(
                            context: context,
                            initialTime: selectedTime,
                          );
                          if (picked != null) {
                            setState(() {
                              selectedTime = picked;
                            });
                          }
                        },
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Cancel'),
            ),
            ElevatedButton(
              onPressed: () async {
                if (titleController.text.trim().isEmpty) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Please enter a title')),
                  );
                  return;
                }

                final scheduledDateTime = DateTime(
                  selectedDate.year,
                  selectedDate.month,
                  selectedDate.day,
                  selectedTime.hour,
                  selectedTime.minute,
                );

                if (existingTask == null) {
                  final task = Task(
                    id: const Uuid().v4(),
                    title: titleController.text.trim(),
                    description: descriptionController.text.trim().isEmpty
                        ? null
                        : descriptionController.text.trim(),
                    scheduledTime: scheduledDateTime,
                  );
                  await _dbService.insertTask(task);
                  await _notificationService.scheduleNotification(task);
                } else {
                  final updatedTask = existingTask.copyWith(
                    title: titleController.text.trim(),
                    description: descriptionController.text.trim().isEmpty
                        ? null
                        : descriptionController.text.trim(),
                    scheduledTime: scheduledDateTime,
                    isNotified: false,
                  );
                  await _dbService.updateTask(updatedTask);
                  await _notificationService.cancelNotification(existingTask.id);
                  await _notificationService.scheduleNotification(updatedTask);
                }

                await _loadTasks();
                if (mounted) {
                  Navigator.pop(context);
                }
              },
              child: Text(existingTask == null ? 'Add' : 'Save'),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _toggleTaskComplete(Task task) async {
    final updatedTask = task.copyWith(isCompleted: !task.isCompleted);
    await _dbService.updateTask(updatedTask);
    
    if (updatedTask.isCompleted) {
      await _notificationService.cancelNotification(task.id);
    }
    
    await _loadTasks();
  }

  Future<void> _deleteTask(Task task) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Reminder'),
        content: Text('Are you sure you want to delete "${task.title}"?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Delete', style: TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );

    if (confirm == true) {
      await _dbService.deleteTask(task.id);
      await _notificationService.cancelNotification(task.id);
      await _loadTasks();
    }
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
    super.build(context);
    final pendingTasks = _tasks.where((t) => !t.isCompleted).toList();
    final completedTasks = _tasks.where((t) => t.isCompleted).toList();

    return Scaffold(
      appBar: AppBar(
        title: const Text('Task Reminder'),
        centerTitle: true,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadTasks,
            tooltip: 'Refresh',
          ),
        ],
      ),
      body: _tasks.isEmpty
          ? const Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.notifications_none, size: 80, color: Colors.grey),
                  SizedBox(height: 16),
                  Text(
                    'No reminders yet',
                    style: TextStyle(fontSize: 18, color: Colors.grey),
                  ),
                  SizedBox(height: 8),
                  Text(
                    'Tap + to add your first reminder',
                    style: TextStyle(color: Colors.grey),
                  ),
                ],
              ),
            )
          : ListView(
              key: _pageStorageKey,
              controller: _scrollController,
              padding: const EdgeInsets.all(16),
              children: [
                if (pendingTasks.isNotEmpty) ...[
                  Text(
                    'Pending (${pendingTasks.length})',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 8),
                  ...pendingTasks.map((task) => _buildTaskCard(task)),
                ],
                if (completedTasks.isNotEmpty) ...[
                  const SizedBox(height: 24),
                  Text(
                    'Completed (${completedTasks.length})',
                    style: Theme.of(context).textTheme.titleLarge?.copyWith(
                          color: Colors.grey,
                        ),
                  ),
                  const SizedBox(height: 8),
                  ...completedTasks.map((task) => _buildTaskCard(task)),
                ],
              ],
            ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => _showAddTaskDialog(),
        child: const Icon(Icons.add),
      ),
    );
  }

  Widget _buildTaskCard(Task task) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        leading: Icon(
          _getStatusIcon(task),
          color: _getStatusColor(task),
          size: 32,
        ),
        title: Text(
          task.title,
          style: TextStyle(
            decoration: task.isCompleted ? TextDecoration.lineThrough : null,
            color: task.isCompleted ? Colors.grey : null,
            fontWeight: FontWeight.w500,
          ),
        ),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (task.description != null) ...[
              Text(
                task.description!,
                style: TextStyle(
                  color: task.isCompleted ? Colors.grey : null,
                ),
              ),
            ],
            const SizedBox(height: 4),
            Row(
              children: [
                Icon(Icons.schedule, size: 16, color: _getStatusColor(task)),
                const SizedBox(width: 4),
                Text(
                  task.formattedDate,
                  style: TextStyle(
                    color: _getStatusColor(task),
                    fontSize: 12,
                  ),
                ),
                if (task.isOverdue && !task.isCompleted) ...[
                  const SizedBox(width: 8),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                    decoration: BoxDecoration(
                      color: Colors.red,
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: const Text(
                      'Overdue',
                      style: TextStyle(color: Colors.white, fontSize: 10),
                    ),
                  ),
                ],
              ],
            ),
          ],
        ),
        trailing: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            IconButton(
              icon: Icon(
                task.isCompleted ? Icons.undo : Icons.check,
                color: task.isCompleted ? Colors.grey : Colors.green,
              ),
              onPressed: () => _toggleTaskComplete(task),
              tooltip: task.isCompleted ? 'Mark as incomplete' : 'Mark as complete',
            ),
            IconButton(
              icon: const Icon(Icons.edit, color: Colors.blue),
              onPressed: () => _showAddTaskDialog(existingTask: task),
              tooltip: 'Edit',
            ),
            IconButton(
              icon: const Icon(Icons.delete, color: Colors.red),
              onPressed: () => _deleteTask(task),
              tooltip: 'Delete',
            ),
          ],
        ),
      ),
    );
  }
}
