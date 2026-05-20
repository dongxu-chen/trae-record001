class Note {
  final String id;
  final String bookId;
  final String userId;
  final String content;
  final int pageNumber;
  final String? highlightText;
  final Color color;
  final DateTime createdAt;
  final DateTime updatedAt;

  Note({
    required this.id,
    required this.bookId,
    required this.userId,
    required this.content,
    required this.pageNumber,
    this.highlightText,
    required this.color,
    required this.createdAt,
    required this.updatedAt,
  });

  Note copyWith({
    String? id,
    String? bookId,
    String? userId,
    String? content,
    int? pageNumber,
    String? highlightText,
    Color? color,
    DateTime? createdAt,
    DateTime? updatedAt,
  }) {
    return Note(
      id: id ?? this.id,
      bookId: bookId ?? this.bookId,
      userId: userId ?? this.userId,
      content: content ?? this.content,
      pageNumber: pageNumber ?? this.pageNumber,
      highlightText: highlightText ?? this.highlightText,
      color: color ?? this.color,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
    );
  }

  Map<String, dynamic> toMap() {
    return {
      'id': id,
      'bookId': bookId,
      'userId': userId,
      'content': content,
      'pageNumber': pageNumber,
      'highlightText': highlightText,
      'color': color.value,
      'createdAt': createdAt.toIso8601String(),
      'updatedAt': updatedAt.toIso8601String(),
    };
  }

  factory Note.fromMap(Map<String, dynamic> map) {
    return Note(
      id: map['id'] as String,
      bookId: map['bookId'] as String,
      userId: map['userId'] as String,
      content: map['content'] as String,
      pageNumber: map['pageNumber'] as int,
      highlightText: map['highlightText'] as String?,
      color: Color(map['color'] as int),
      createdAt: DateTime.parse(map['createdAt'] as String),
      updatedAt: DateTime.parse(map['updatedAt'] as String),
    );
  }
}
