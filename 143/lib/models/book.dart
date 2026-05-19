class Book {
  final String id;
  final String title;
  final String author;
  final String? coverUrl;
  final String? description;
  final int totalPages;
  final String? filePath;
  final DateTime createdAt;
  final DateTime updatedAt;
  final String userId;

  Book({
    required this.id,
    required this.title,
    required this.author,
    this.coverUrl,
    this.description,
    required this.totalPages,
    this.filePath,
    required this.createdAt,
    required this.updatedAt,
    required this.userId,
  });

  Book copyWith({
    String? id,
    String? title,
    String? author,
    String? coverUrl,
    String? description,
    int? totalPages,
    String? filePath,
    DateTime? createdAt,
    DateTime? updatedAt,
    String? userId,
  }) {
    return Book(
      id: id ?? this.id,
      title: title ?? this.title,
      author: author ?? this.author,
      coverUrl: coverUrl ?? this.coverUrl,
      description: description ?? this.description,
      totalPages: totalPages ?? this.totalPages,
      filePath: filePath ?? this.filePath,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      userId: userId ?? this.userId,
    );
  }

  Map<String, dynamic> toMap() {
    return {
      'id': id,
      'title': title,
      'author': author,
      'coverUrl': coverUrl,
      'description': description,
      'totalPages': totalPages,
      'filePath': filePath,
      'createdAt': createdAt.toIso8601String(),
      'updatedAt': updatedAt.toIso8601String(),
      'userId': userId,
    };
  }

  factory Book.fromMap(Map<String, dynamic> map) {
    return Book(
      id: map['id'] as String,
      title: map['title'] as String,
      author: map['author'] as String,
      coverUrl: map['coverUrl'] as String?,
      description: map['description'] as String?,
      totalPages: map['totalPages'] as int,
      filePath: map['filePath'] as String?,
      createdAt: DateTime.parse(map['createdAt'] as String),
      updatedAt: DateTime.parse(map['updatedAt'] as String),
      userId: map['userId'] as String,
    );
  }
}
