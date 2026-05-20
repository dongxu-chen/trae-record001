class ReadingProgress {
  final String id;
  final String bookId;
  final String userId;
  final int currentPage;
  final double progressPercentage;
  final DateTime lastReadAt;
  final String? deviceInfo;

  ReadingProgress({
    required this.id,
    required this.bookId,
    required this.userId,
    required this.currentPage,
    required this.progressPercentage,
    required this.lastReadAt,
    this.deviceInfo,
  });

  ReadingProgress copyWith({
    String? id,
    String? bookId,
    String? userId,
    int? currentPage,
    double? progressPercentage,
    DateTime? lastReadAt,
    String? deviceInfo,
  }) {
    return ReadingProgress(
      id: id ?? this.id,
      bookId: bookId ?? this.bookId,
      userId: userId ?? this.userId,
      currentPage: currentPage ?? this.currentPage,
      progressPercentage: progressPercentage ?? this.progressPercentage,
      lastReadAt: lastReadAt ?? this.lastReadAt,
      deviceInfo: deviceInfo ?? this.deviceInfo,
    );
  }

  Map<String, dynamic> toMap() {
    return {
      'id': id,
      'bookId': bookId,
      'userId': userId,
      'currentPage': currentPage,
      'progressPercentage': progressPercentage,
      'lastReadAt': lastReadAt.toIso8601String(),
      'deviceInfo': deviceInfo,
    };
  }

  factory ReadingProgress.fromMap(Map<String, dynamic> map) {
    return ReadingProgress(
      id: map['id'] as String,
      bookId: map['bookId'] as String,
      userId: map['userId'] as String,
      currentPage: map['currentPage'] as int,
      progressPercentage: (map['progressPercentage'] as num).toDouble(),
      lastReadAt: DateTime.parse(map['lastReadAt'] as String),
      deviceInfo: map['deviceInfo'] as String?,
    );
  }
}
