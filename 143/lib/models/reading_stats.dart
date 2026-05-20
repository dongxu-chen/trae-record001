import 'dart:collection';

class ReadingSession {
  final String id;
  final String bookId;
  final String bookTitle;
  final DateTime startTime;
  final DateTime endTime;
  final int durationSeconds;
  final int? startPage;
  final int? endPage;

  ReadingSession({
    required this.id,
    required this.bookId,
    required this.bookTitle,
    required this.startTime,
    required this.endTime,
    required this.durationSeconds,
    this.startPage,
    this.endPage,
  });

  int get durationMinutes => (durationSeconds / 60).round();

  Map<String, dynamic> toMap() {
    return {
      'id': id,
      'bookId': bookId,
      'bookTitle': bookTitle,
      'startTime': startTime.toIso8601String(),
      'endTime': endTime.toIso8601String(),
      'durationSeconds': durationSeconds,
      'startPage': startPage,
      'endPage': endPage,
    };
  }

  factory ReadingSession.fromMap(Map<String, dynamic> map) {
    return ReadingSession(
      id: map['id'] as String,
      bookId: map['bookId'] as String,
      bookTitle: map['bookTitle'] as String,
      startTime: DateTime.parse(map['startTime'] as String),
      endTime: DateTime.parse(map['endTime'] as String),
      durationSeconds: map['durationSeconds'] as int,
      startPage: map['startPage'] as int?,
      endPage: map['endPage'] as int?,
    );
  }
}

class ReadingStats {
  final List<ReadingSession> sessions;
  final int totalReadMinutes;
  final int readingDays;
  final int booksCompleted;
  final int totalBookmarks;
  final int currentStreak;
  final int longestStreak;
  final double averageDailyMinutes;
  final Map<int, int> hourlyDistribution;
  final Map<int, int> weeklyDistribution;
  final Map<String, int> bookReadingTime;

  ReadingStats({
    required this.sessions,
    required this.totalReadMinutes,
    required this.readingDays,
    required this.booksCompleted,
    required this.totalBookmarks,
    required this.currentStreak,
    required this.longestStreak,
    required this.averageDailyMinutes,
    required this.hourlyDistribution,
    required this.weeklyDistribution,
    required this.bookReadingTime,
  });

  factory ReadingStats.calculate(List<ReadingSession> sessions, {
    int booksCompleted = 0,
    int totalBookmarks = 0,
  }) {
    final now = DateTime.now();
    final totalMinutes = sessions.fold<int>(0, (sum, s) => sum + s.durationMinutes);

    final readingDates = sessions.map((s) => _normalizeDate(s.startTime)).toSet();

    final hourly = <int, int>{};
    final weekly = <int, int>{};
    final bookTime = <String, int>{};

    for (final session in sessions) {
      final hour = session.startTime.hour;
      hourly[hour] = (hourly[hour] ?? 0) + session.durationMinutes;

      final weekday = session.startTime.weekday - 1;
      weekly[weekday] = (weekly[weekday] ?? 0) + session.durationMinutes;

      bookTime[session.bookTitle] = (bookTime[session.bookTitle] ?? 0) + session.durationMinutes;
    }

    final streakInfo = _calculateStreak(sessions);

    return ReadingStats(
      sessions: sessions,
      totalReadMinutes: totalMinutes,
      readingDays: readingDates.length,
      booksCompleted: booksCompleted,
      totalBookmarks: totalBookmarks,
      currentStreak: streakInfo.current,
      longestStreak: streakInfo.longest,
      averageDailyMinutes: readingDates.isEmpty ? 0 : totalMinutes / readingDates.length,
      hourlyDistribution: hourly,
      weeklyDistribution: weekly,
      bookReadingTime: bookTime,
    );
  }

  static DateTime _normalizeDate(DateTime date) {
    return DateTime(date.year, date.month, date.day);
  }

  static ({int current, int longest}) _calculateStreak(List<ReadingSession> sessions) {
    if (sessions.isEmpty) return (current: 0, longest: 0);

    final dates = sessions.map((s) => _normalizeDate(s.startTime)).toSet().toList()
      ..sort((a, b) => b.compareTo(a));

    if (dates.isEmpty) return (current: 0, longest: 0);

    int longest = 1;
    int current = 1;

    for (int i = 1; i < dates.length; i++) {
      final diff = dates[i - 1].difference(dates[i]).inDays;
      if (diff == 1) {
        current++;
        longest = longest > current ? longest : current;
      } else if (diff > 1) {
        break;
      }
    }

    return (current: current, longest: longest);
  }

  List<DailyReading> get dailyReadingsLast30Days {
    final now = DateTime.now();
    final result = <DailyReading>[];

    for (int i = 29; i >= 0; i--) {
      final date = now.subtract(Duration(days: i));
      final normalizedDate = _normalizeDate(date);

      final minutes = sessions
          .where((s) => _normalizeDate(s.startTime) == normalizedDate)
          .fold<int>(0, (sum, s) => sum + s.durationMinutes);

      result.add(DailyReading(date: normalizedDate, minutes: minutes));
    }

    return result;
  }
}

class DailyReading {
  final DateTime date;
  final int minutes;

  DailyReading({required this.date, required this.minutes});

  bool get hasReading => minutes > 0;
}

class BookmarkSummary {
  final String bookmarkId;
  final String bookTitle;
  final String excerpt;
  final String summary;
  final List<String> generatedTags;
  final DateTime generatedAt;

  BookmarkSummary({
    required this.bookmarkId,
    required this.bookTitle,
    required this.excerpt,
    required this.summary,
    required this.generatedTags,
    required this.generatedAt,
  });

  Map<String, dynamic> toMap() {
    return {
      'bookmarkId': bookmarkId,
      'bookTitle': bookTitle,
      'excerpt': excerpt,
      'summary': summary,
      'generatedTags': generatedTags,
      'generatedAt': generatedAt.toIso8601String(),
    };
  }

  factory BookmarkSummary.fromMap(Map<String, dynamic> map) {
    return BookmarkSummary(
      bookmarkId: map['bookmarkId'] as String,
      bookTitle: map['bookTitle'] as String,
      excerpt: map['excerpt'] as String,
      summary: map['summary'] as String,
      generatedTags: List<String>.from(map['generatedTags'] as List),
      generatedAt: DateTime.parse(map['generatedAt'] as String),
    );
  }
}
