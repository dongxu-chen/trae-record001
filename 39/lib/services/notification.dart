import 'dart:async';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:timezone/data/latest.dart' as tz;
import 'package:timezone/timezone.dart' as tz;
import '../models/task.dart';
import 'database.dart';

class NotificationService {
  static final NotificationService instance = NotificationService._constructor();
  final FlutterLocalNotificationsPlugin _flutterLocalNotificationsPlugin =
      FlutterLocalNotificationsPlugin();

  factory NotificationService() {
    return instance;
  }

  NotificationService._constructor();

  Timer? _checkTimer;

  Future<void> initialize() async {
    tz.initializeTimeZones();
    
    const AndroidInitializationSettings androidInitSettings =
        AndroidInitializationSettings('@mipmap/ic_launcher');

    const DarwinInitializationSettings iosInitSettings =
        DarwinInitializationSettings(
      requestAlertPermission: true,
      requestBadgePermission: true,
      requestSoundPermission: true,
    );

    const LinuxInitializationSettings linuxInitSettings =
        LinuxInitializationSettings(defaultActionName: 'open');

    const WindowsInitializationSettings windowsInitSettings =
        WindowsInitializationSettings();

    const InitializationSettings initSettings = InitializationSettings(
      android: androidInitSettings,
      iOS: iosInitSettings,
      macOS: iosInitSettings,
      linux: linuxInitSettings,
      windows: windowsInitSettings,
    );

    await _flutterLocalNotificationsPlugin.initialize(
      initSettings,
      onDidReceiveNotificationResponse: _onNotificationTap,
    );

    _startPeriodicCheck();
  }

  void _onNotificationTap(NotificationResponse response) {
    if (response.payload != null) {
      print('Notification tapped: ${response.payload}');
    }
  }

  void _startPeriodicCheck() {
    _checkTimer = Timer.periodic(const Duration(minutes: 1), (timer) async {
      await _checkAndSendNotifications();
    });
  }

  Future<void> _checkAndSendNotifications() async {
    final tasks = await DatabaseService().getTasksForNotification();
    
    for (final task in tasks) {
      if (!task.isNotified) {
        await _sendNotification(task);
        await DatabaseService().markAsNotified(task.id);
      }
    }
  }

  Future<void> _sendNotification(Task task) async {
    const AndroidNotificationDetails androidPlatformChannelSpecifics =
        AndroidNotificationDetails(
      'reminder_channel',
      'Task Reminders',
      channelDescription: 'Notification channel for task reminders',
      importance: Importance.max,
      priority: Priority.high,
      showWhen: true,
    );

    const DarwinNotificationDetails iosPlatformChannelSpecifics =
        DarwinNotificationDetails(
      presentAlert: true,
      presentBadge: true,
      presentSound: true,
    );

    const LinuxNotificationDetails linuxPlatformChannelSpecifics =
        LinuxNotificationDetails();

    const WindowsNotificationDetails windowsPlatformChannelSpecifics =
        WindowsNotificationDetails();

    const NotificationDetails platformChannelSpecifics = NotificationDetails(
      android: androidPlatformChannelSpecifics,
      iOS: iosPlatformChannelSpecifics,
      macOS: iosPlatformChannelSpecifics,
      linux: linuxPlatformChannelSpecifics,
      windows: windowsPlatformChannelSpecifics,
    );

    await _flutterLocalNotificationsPlugin.show(
      task.id.hashCode,
      task.title,
      task.description ?? 'Your scheduled reminder',
      platformChannelSpecifics,
      payload: task.id,
    );
  }

  Future<void> scheduleNotification(Task task) async {
    if (task.scheduledTime.isBefore(DateTime.now())) {
      return;
    }

    final scheduledTime = tz.TZDateTime.from(
      task.scheduledTime,
      tz.local,
    );

    const AndroidNotificationDetails androidPlatformChannelSpecifics =
        AndroidNotificationDetails(
      'reminder_channel',
      'Task Reminders',
      channelDescription: 'Notification channel for task reminders',
      importance: Importance.max,
      priority: Priority.high,
    );

    const DarwinNotificationDetails iosPlatformChannelSpecifics =
        DarwinNotificationDetails();

    const LinuxNotificationDetails linuxPlatformChannelSpecifics =
        LinuxNotificationDetails();

    const WindowsNotificationDetails windowsPlatformChannelSpecifics =
        WindowsNotificationDetails();

    const NotificationDetails platformChannelSpecifics = NotificationDetails(
      android: androidPlatformChannelSpecifics,
      iOS: iosPlatformChannelSpecifics,
      macOS: iosPlatformChannelSpecifics,
      linux: linuxPlatformChannelSpecifics,
      windows: windowsPlatformChannelSpecifics,
    );

    await _flutterLocalNotificationsPlugin.zonedSchedule(
      task.id.hashCode,
      task.title,
      task.description ?? 'Your scheduled reminder',
      scheduledTime,
      platformChannelSpecifics,
      androidScheduleMode: AndroidScheduleMode.exactAllowWhileIdle,
      uiLocalNotificationDateInterpretation:
          UILocalNotificationDateInterpretation.absoluteTime,
      matchDateTimeComponents: DateTimeComponents.time,
    );
  }

  Future<void> cancelNotification(String taskId) async {
    await _flutterLocalNotificationsPlugin.cancel(taskId.hashCode);
  }

  Future<void> cancelAllNotifications() async {
    await _flutterLocalNotificationsPlugin.cancelAll();
  }

  void dispose() {
    _checkTimer?.cancel();
  }
}
