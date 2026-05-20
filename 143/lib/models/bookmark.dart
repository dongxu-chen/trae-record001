class Bookmark {
  final String id;
  final String bookId;
  final String userId;
  final String title;
  final String? excerpt;
  final int pageNumber;
  final List<String> tags;
  final DateTime createdAt;
  final DateTime updatedAt;

  Bookmark({
    required this.id,
    required this.bookId,
    required this.userId,
    required this.title,
    this.excerpt,
    required this.pageNumber,
    required this.tags,
    required this.createdAt,
    required this.updatedAt,
  });

  Bookmark copyWith({
    String? id,
    String? bookId,
    String? userId,
    String? title,
    String? excerpt,
    int? pageNumber,
    List<String>? tags,
    DateTime? createdAt,
    DateTime? updatedAt,
  }) {
    return Bookmark(
      id: id ?? this.id,
      bookId: bookId ?? this.bookId,
      userId: userId ?? this.userId,
      title: title ?? this.title,
      excerpt: excerpt ?? this.excerpt,
      pageNumber: pageNumber ?? this.pageNumber,
      tags: tags ?? this.tags,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
    );
  }

  Map<String, dynamic> toMap() {
    return {
      'id': id,
      'bookId': bookId,
      'userId': userId,
      'title': title,
      'excerpt': excerpt,
      'pageNumber': pageNumber,
      'tags': tags,
      'createdAt': createdAt.toIso8601String(),
      'updatedAt': updatedAt.toIso8601String(),
    };
  }

  factory Bookmark.fromMap(Map<String, dynamic> map) {
    return Bookmark(
      id: map['id'] as String,
      bookId: map['bookId'] as String,
      userId: map['userId'] as String,
      title: map['title'] as String,
      excerpt: map['excerpt'] as String?,
      pageNumber: map['pageNumber'] as int,
      tags: List<String>.from(map['tags'] as List),
      createdAt: DateTime.parse(map['createdAt'] as String),
      updatedAt: DateTime.parse(map['updatedAt'] as String),
    );
  }
}
