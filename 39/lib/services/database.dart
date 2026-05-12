import 'package:path/path.dart';
import 'package:sqflite/sqflite.dart';
import 'package:synchronized/synchronized.dart';
import '../models/task.dart';

class DatabaseService {
  static Database? _database;
  static final DatabaseService instance = DatabaseService._constructor();
  static final _lock = Lock();

  factory DatabaseService() {
    return instance;
  }

  DatabaseService._constructor();

  Future<Database> get database async {
    if (_database != null) return _database!;
    await _lock.synchronized(() async {
      if (_database == null) {
        _database = await _initDatabase();
      }
    });
    return _database!;
  }

  Future<Database> _initDatabase() async {
    final databasePath = await getDatabasesPath();
    final path = join(databasePath, 'reminder_app.db');

    return await openDatabase(
      path,
      version: 1,
      onCreate: _onCreate,
    );
  }

  Future<void> _onCreate(Database db, int version) async {
    await db.execute('''
      CREATE TABLE tasks(
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        description TEXT,
        scheduledTime TEXT NOT NULL,
        isCompleted INTEGER NOT NULL,
        isNotified INTEGER NOT NULL,
        createdAt TEXT NOT NULL
      )
    ''');
  }

  Future<int> insertTask(Task task) async {
    final db = await database;
    return await db.insert(
      'tasks',
      task.toMap(),
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }

  Future<List<Task>> getAllTasks() async {
    final db = await database;
    final List<Map<String, dynamic>> maps = await db.query(
      'tasks',
      orderBy: 'scheduledTime ASC',
    );

    return List.generate(maps.length, (i) {
      return Task.fromMap(maps[i]);
    });
  }

  Future<List<Task>> getPendingTasks() async {
    final db = await database;
    final List<Map<String, dynamic>> maps = await db.query(
      'tasks',
      where: 'isCompleted = ?',
      whereArgs: [0],
      orderBy: 'scheduledTime ASC',
    );

    return List.generate(maps.length, (i) {
      return Task.fromMap(maps[i]);
    });
  }

  Future<List<Task>> getTasksForNotification() async {
    final db = await database;
    final now = DateTime.now().toIso8601String();
    final List<Map<String, dynamic>> maps = await db.query(
      'tasks',
      where: 'isCompleted = ? AND isNotified = ? AND scheduledTime <= ?',
      whereArgs: [0, 0, now],
      orderBy: 'scheduledTime ASC',
    );

    return List.generate(maps.length, (i) {
      return Task.fromMap(maps[i]);
    });
  }

  Future<int> updateTask(Task task) async {
    final db = await database;
    return await db.update(
      'tasks',
      task.toMap(),
      where: 'id = ?',
      whereArgs: [task.id],
    );
  }

  Future<int> markAsNotified(String taskId) async {
    final db = await database;
    return await db.update(
      'tasks',
      {'isNotified': 1},
      where: 'id = ?',
      whereArgs: [taskId],
    );
  }

  Future<int> deleteTask(String id) async {
    final db = await database;
    return await db.delete(
      'tasks',
      where: 'id = ?',
      whereArgs: [id],
    );
  }

  Future<int> deleteCompletedTasks() async {
    final db = await database;
    return await db.delete(
      'tasks',
      where: 'isCompleted = ?',
      whereArgs: [1],
    );
  }

  Future<List<Task>> getTasksByDate(DateTime date) async {
    final db = await database;
    final startOfDay = DateTime(date.year, date.month, date.day).toIso8601String();
    final endOfDay = DateTime(date.year, date.month, date.day, 23, 59, 59).toIso8601String();

    final List<Map<String, dynamic>> maps = await db.query(
      'tasks',
      where: 'scheduledTime >= ? AND scheduledTime <= ?',
      whereArgs: [startOfDay, endOfDay],
      orderBy: 'scheduledTime ASC',
    );

    return List.generate(maps.length, (i) {
      return Task.fromMap(maps[i]);
    });
  }

  Future<Map<DateTime, int>> getTaskCountByDateRange(
      DateTime start, DateTime end) async {
    final db = await database;
    final startStr = start.toIso8601String();
    final endStr = end.toIso8601String();

    final List<Map<String, dynamic>> maps = await db.query(
      'tasks',
      columns: ['scheduledTime'],
      where: 'scheduledTime >= ? AND scheduledTime <= ?',
      whereArgs: [startStr, endStr],
    );

    final Map<DateTime, int> result = {};
    for (final map in maps) {
      final scheduledTime = DateTime.parse(map['scheduledTime'] as String);
      final dateKey = DateTime(scheduledTime.year, scheduledTime.month, scheduledTime.day);
      result[dateKey] = (result[dateKey] ?? 0) + 1;
    }

    return result;
  }

  Future<Map<String, int>> getTaskStats() async {
    final db = await database;

    final totalResult = await db.rawQuery(
      'SELECT COUNT(*) as count FROM tasks',
    );
    final completedResult = await db.rawQuery(
      'SELECT COUNT(*) as count FROM tasks WHERE isCompleted = 1',
    );
    final pendingResult = await db.rawQuery(
      'SELECT COUNT(*) as count FROM tasks WHERE isCompleted = 0',
    );
    final overdueResult = await db.rawQuery(
      'SELECT COUNT(*) as count FROM tasks WHERE isCompleted = 0 AND scheduledTime < ?',
      [DateTime.now().toIso8601String()],
    );

    final total = Sqflite.firstIntValue(totalResult) ?? 0;
    final completed = Sqflite.firstIntValue(completedResult) ?? 0;
    final pending = Sqflite.firstIntValue(pendingResult) ?? 0;
    final overdue = Sqflite.firstIntValue(overdueResult) ?? 0;

    return {
      'total': total,
      'completed': completed,
      'pending': pending,
      'overdue': overdue,
    };
  }

  Future<List<Map<String, dynamic>>> getWeeklyTaskStats() async {
    final db = await database;
    final now = DateTime.now();
    final startOfWeek = now.subtract(Duration(days: now.weekday - 1));
    final endOfWeek = startOfWeek.add(const Duration(days: 6, hours: 23, minutes: 59, seconds: 59));

    final List<Map<String, dynamic>> maps = await db.query(
      'tasks',
      columns: ['scheduledTime', 'isCompleted'],
      where: 'scheduledTime >= ? AND scheduledTime <= ?',
      whereArgs: [startOfWeek.toIso8601String(), endOfWeek.toIso8601String()],
    );

    final Map<int, Map<String, int>> weekStats = {};
    for (var i = 1; i <= 7; i++) {
      weekStats[i] = {'completed': 0, 'total': 0};
    }

    for (final map in maps) {
      final scheduledTime = DateTime.parse(map['scheduledTime'] as String);
      final weekday = scheduledTime.weekday;
      final isCompleted = (map['isCompleted'] as int) == 1;

      weekStats[weekday]!['total'] = (weekStats[weekday]!['total'] ?? 0) + 1;
      if (isCompleted) {
        weekStats[weekday]!['completed'] = (weekStats[weekday]!['completed'] ?? 0) + 1;
      }
    }

    const weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    return List.generate(7, (i) {
      final dayStats = weekStats[i + 1] ?? {'completed': 0, 'total': 0};
      return {
        'day': weekdays[i],
        'completed': dayStats['completed'] ?? 0,
        'total': dayStats['total'] ?? 0,
      };
    });
  }

  Future<void> close() async {
    final db = await database;
    await db.close();
  }
}
