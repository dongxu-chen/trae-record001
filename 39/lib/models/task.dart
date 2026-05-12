import 'package:intl/intl.dart';

class Task {
  final String id;
  final String title;
  final String? description;
  final DateTime scheduledTime;
  final bool isCompleted;
  final bool isNotified;
  final DateTime createdAt;

  Task({
    required this.id,
    required this.title,
    this.description,
    required this.scheduledTime,
    this.isCompleted = false,
    this.isNotified = false,
    DateTime? createdAt,
  }) : createdAt = createdAt ?? DateTime.now();

  String get formattedDate {
    return DateFormat('yyyy-MM-dd HH:mm').format(scheduledTime);
  }

  bool get isOverdue {
    return !isCompleted && scheduledTime.isBefore(DateTime.now());
  }

  bool get isToday {
    final now = DateTime.now();
    return scheduledTime.year == now.year &&
        scheduledTime.month == now.month &&
        scheduledTime.day == now.day;
  }

  Task copyWith({
    String? id,
    String? title,
    String? description,
    DateTime? scheduledTime,
    bool? isCompleted,
    bool? isNotified,
    DateTime? createdAt,
  }) {
    return Task(
      id: id ?? this.id,
      title: title ?? this.title,
      description: description ?? this.description,
      scheduledTime: scheduledTime ?? this.scheduledTime,
      isCompleted: isCompleted ?? this.isCompleted,
      isNotified: isNotified ?? this.isNotified,
      createdAt: createdAt ?? this.createdAt,
    );
  }

  Map<String, dynamic> toMap() {
    return {
      'id': id,
      'title': title,
      'description': description,
      'scheduledTime': scheduledTime.toIso8601String(),
      'isCompleted': isCompleted ? 1 : 0,
      'isNotified': isNotified ? 1 : 0,
      'createdAt': createdAt.toIso8601String(),
    };
  }

  factory Task.fromMap(Map<String, dynamic> map) {
    return Task(
      id: map['id'] as String,
      title: map['title'] as String,
      description: map['description'] as String?,
      scheduledTime: DateTime.parse(map['scheduledTime'] as String),
      isCompleted: (map['isCompleted'] as int) == 1,
      isNotified: (map['isNotified'] as int) == 1,
      createdAt: DateTime.parse(map['createdAt'] as String),
    );
  }
}
