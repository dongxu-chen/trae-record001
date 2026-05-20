import 'package:flutter/foundation.dart';
import '../models/bookmark.dart';
import '../models/reading_stats.dart';
import '../services/ai_service.dart';
import '../services/local_storage_service.dart';

class AIProvider extends ChangeNotifier {
  final AIService _aiService = AIService();
  final LocalDataManager _storage = LocalDataManager();

  bool _isLoading = false;
  bool get isLoading => _isLoading;

  String? _aiAnalysis;
  String? get aiAnalysis => _aiAnalysis;

  Map<String, BookmarkSummary> _bookmarkSummaries = {};
  Map<String, BookmarkSummary> get bookmarkSummaries => _bookmarkSummaries;

  List<BookmarkSearchResult> _searchResults = [];
  List<BookmarkSearchResult> get searchResults => _searchResults;

  String? _searchQuery;
  String? get searchQuery => _searchQuery;

  bool _isSearching = false;
  bool get isSearching => _isSearching;

  Future<String> generateBookmarkSummary(Bookmark bookmark) async {
    try {
      _isLoading = true;
      notifyListeners();

      final summary = await _aiService.generateBookmarkSummary(
        bookTitle: bookmark.bookTitle ?? '未知书籍',
        excerpt: bookmark.excerpt ?? bookmark.title,
      );

      final tags = await _aiService.generateTagsFromContent(bookmark.excerpt ?? bookmark.title);

      final bookmarkSummary = BookmarkSummary(
        bookmarkId: bookmark.id,
        bookTitle: bookmark.bookTitle ?? '未知书籍',
        excerpt: bookmark.excerpt ?? bookmark.title,
        summary: summary,
        generatedTags: tags,
        generatedAt: DateTime.now(),
      );

      _bookmarkSummaries[bookmark.id] = bookmarkSummary;
      await _storage.saveBookmarkSummary(bookmarkSummary);

      return summary;
    } catch (e) {
      debugPrint('Error generating summary: $e');
      return '生成摘要时出错，请重试';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> analyzeReadingHabits(ReadingStats stats) async {
    try {
      _isLoading = true;
      notifyListeners();

      _aiAnalysis = await _aiService.analyzeReadingHabits(stats);
    } catch (e) {
      debugPrint('Error analyzing habits: $e');
      _aiAnalysis = '分析阅读习惯时出错';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> generateInsights(List<Bookmark> bookmarks) async {
    if (bookmarks.isEmpty) {
      _aiAnalysis = '暂无书摘可生成洞察';
      notifyListeners();
      return;
    }

    try {
      _isLoading = true;
      notifyListeners();

      _aiAnalysis = await _aiService.generateInsights(bookmarks);
    } catch (e) {
      debugPrint('Error generating insights: $e');
      _aiAnalysis = '生成洞察时出错';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> searchBookmarks(String query, List<Bookmark> bookmarks) async {
    if (query.isEmpty) {
      _searchResults = [];
      _searchQuery = null;
      notifyListeners();
      return;
    }

    try {
      _isSearching = true;
      _searchQuery = query;
      notifyListeners();

      _searchResults = await _aiService.searchBookmarks(query, bookmarks);
    } catch (e) {
      debugPrint('Error searching bookmarks: $e');
      _searchResults = [];
    } finally {
      _isSearching = false;
      notifyListeners();
    }
  }

  void clearSearch() {
    _searchResults = [];
    _searchQuery = null;
    notifyListeners();
  }

  Future<String> performOCR(Uint8List imageData) async {
    try {
      _isLoading = true;
      notifyListeners();

      return await _aiService.ocrImage(imageData);
    } catch (e) {
      debugPrint('Error performing OCR: $e');
      return 'OCR识别失败';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  void clearAnalysis() {
    _aiAnalysis = null;
    notifyListeners();
  }

  BookmarkSummary? getSummaryForBookmark(String bookmarkId) {
    return _bookmarkSummaries[bookmarkId];
  }

  Future<void> loadSavedSummaries() async {
    try {
      final summaries = await _storage.getBookmarkSummaries();
      _bookmarkSummaries = {for (final s in summaries) s.bookmarkId: s};
      notifyListeners();
    } catch (e) {
      debugPrint('Error loading summaries: $e');
    }
  }
}
