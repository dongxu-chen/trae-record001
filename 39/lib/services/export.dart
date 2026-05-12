import 'dart:io';
import 'package:intl/intl.dart';
import 'package:path_provider/path_provider.dart';
import '../models/task.dart';
import 'database.dart';

class ExportService {
  static final ExportService instance = ExportService._constructor();

  factory ExportService() {
    return instance;
  }

  ExportService._constructor();

  String _escapeCsvValue(String? value) {
    if (value == null || value.isEmpty) {
      return '';
    }
    if (value.contains(',') ||
        value.contains('"') ||
        value.contains('\n') ||
        value.contains('\r')) {
      return '"${value.replaceAll('"', '""')}"';
    }
    return value;
  }

  String _generateCsvContent(List<Task> tasks) {
    final buffer = StringBuffer();

    buffer.writeln('ID,Title,Description,Scheduled Time,Completed,Notified,Created At');

    final dateFormat = DateFormat('yyyy-MM-dd HH:mm:ss');

    for (final task in tasks) {
      buffer.writeln([
        _escapeCsvValue(task.id),
        _escapeCsvValue(task.title),
        _escapeCsvValue(task.description),
        _escapeCsvValue(dateFormat.format(task.scheduledTime)),
        task.isCompleted ? 'Yes' : 'No',
        task.isNotified ? 'Yes' : 'No',
        _escapeCsvValue(dateFormat.format(task.createdAt)),
      ].join(','));
    }

    return buffer.toString();
  }

  Future<String> exportTasksToCsv() async {
    final tasks = await DatabaseService().getAllTasks();
    final csvContent = _generateCsvContent(tasks);

    final directory = await getApplicationDocumentsDirectory();
    final timestamp = DateFormat('yyyyMMdd_HHmmss').format(DateTime.now());
    final filePath = '${directory.path}/task_reminders_$timestamp.csv';

    final file = File(filePath);
    await file.writeAsString(csvContent, encoding: utf8);

    return filePath;
  }

  Future<String> exportCompletedTasksToCsv() async {
    final allTasks = await DatabaseService().getAllTasks();
    final completedTasks = allTasks.where((t) => t.isCompleted).toList();
    final csvContent = _generateCsvContent(completedTasks);

    final directory = await getApplicationDocumentsDirectory();
    final timestamp = DateFormat('yyyyMMdd_HHmmss').format(DateTime.now());
    final filePath = '${directory.path}/completed_task_reminders_$timestamp.csv';

    final file = File(filePath);
    await file.writeAsString(csvContent, encoding: utf8);

    return filePath;
  }

  Future<String> exportPendingTasksToCsv() async {
    final allTasks = await DatabaseService().getAllTasks();
    final pendingTasks = allTasks.where((t) => !t.isCompleted).toList();
    final csvContent = _generateCsvContent(pendingTasks);

    final directory = await getApplicationDocumentsDirectory();
    final timestamp = DateFormat('yyyyMMdd_HHmmss').format(DateTime.now());
    final filePath = '${directory.path}/pending_task_reminders_$timestamp.csv';

    final file = File(filePath);
    await file.writeAsString(csvContent, encoding: utf8);

    return filePath;
  }
}
