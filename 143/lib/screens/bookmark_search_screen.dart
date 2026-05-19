import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/ai_provider.dart';
import '../providers/bookmark_provider.dart';
import '../models/bookmark.dart';

class BookmarkSearchScreen extends StatefulWidget {
  const BookmarkSearchScreen({super.key});

  @override
  State<BookmarkSearchScreen> createState() => _BookmarkSearchScreenState();
}

class _BookmarkSearchScreenState extends State<BookmarkSearchScreen> {
  final TextEditingController _searchController = TextEditingController();
  final FocusNode _focusNode = FocusNode();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _focusNode.requestFocus();
    });
  }

  @override
  void dispose() {
    _searchController.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: TextField(
          controller: _searchController,
          focusNode: _focusNode,
          decoration: InputDecoration(
            hintText: '搜索书摘内容、标签...',
            border: InputBorder.none,
            prefixIcon: const Icon(Icons.search),
            suffixIcon: IconButton(
              icon: const Icon(Icons.clear),
              onPressed: () {
                _searchController.clear();
                Provider.of<AIProvider>(context, listen: false).clearSearch();
              },
            ),
          ),
          onChanged: (value) => _performSearch(value),
          onSubmitted: (value) => _performSearch(value),
        ),
      ),
      body: Consumer2<AIProvider, BookmarkProvider>(
        builder: (context, aiProvider, bookmarkProvider, _) {
          final results = aiProvider.searchResults;
          final isSearching = aiProvider.isSearching;
          final hasQuery = aiProvider.searchQuery != null && aiProvider.searchQuery!.isNotEmpty;

          if (isSearching) {
            return const Center(child: CircularProgressIndicator());
          }

          if (!hasQuery) {
            return _buildSearchTips(bookmarkProvider);
          }

          if (results.isEmpty) {
            return _buildNoResults();
          }

          return ListView.builder(
            padding: const EdgeInsets.all(16),
            itemCount: results.length,
            itemBuilder: (context, index) {
              final result = results[index];
              return _buildSearchResultCard(result, bookmarkProvider, index);
            },
          );
        },
      ),
    );
  }

  void _performSearch(String query) async {
    if (query.isEmpty) {
      if (mounted) {
        Provider.of<AIProvider>(context, listen: false).clearSearch();
      }
      return;
    }

    final bookmarkProvider = Provider.of<BookmarkProvider>(context, listen: false);
    final aiProvider = Provider.of<AIProvider>(context, listen: false);

    await aiProvider.searchBookmarks(query, bookmarkProvider.bookmarks);
  }

  Widget _buildSearchTips(BookmarkProvider bookmarkProvider) {
    final recentTags = _getRecentTags(bookmarkProvider.bookmarks);
    final popularTerms = ['哲学', '成长', '投资', '心理学', '习惯', '效率'];

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            '热门搜索',
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: popularTerms.map((term) {
              return ActionChip(
                label: Text(term),
                avatar: Icon(Icons.trending_up, size: 16, color: Colors.orange.shade700),
                onPressed: () {
                  _searchController.text = term;
                  _performSearch(term);
                },
              );
            }).toList(),
          ),
          if (recentTags.isNotEmpty) ...[
            const SizedBox(height: 32),
            const Text(
              '常用标签',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 16),
            Wrap(
              spacing: 12,
              runSpacing: 12,
              children: recentTags.map((tag) {
                return ActionChip(
                  label: Text('#$tag'),
                  onPressed: () {
                    _searchController.text = tag;
                    _performSearch(tag);
                  },
                );
              }).toList(),
            ),
          ],
          const SizedBox(height: 32),
          Card(
            color: Colors.blue.shade50,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Row(
                children: [
                  Icon(Icons.tips_and_updates, color: Colors.blue.shade700),
                  const SizedBox(width: 12),
                  const Expanded(
                    child: Text(
                      '提示：可以搜索书摘中的关键词、标签或书名',
                      style: TextStyle(color: Colors.blueGrey),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildNoResults() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.search_off,
            size: 64,
            color: Colors.grey.shade400,
          ),
          const SizedBox(height: 16),
          Text(
            '未找到相关书摘',
            style: TextStyle(
              fontSize: 18,
              color: Colors.grey.shade600,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            '尝试使用其他关键词搜索',
            style: TextStyle(
              color: Colors.grey.shade500,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSearchResultCard(
    BookmarkSearchResult result,
    BookmarkProvider bookmarkProvider,
    int index,
  ) {
    final bookmark = result.bookmark;
    final relevancePercent = (result.relevanceScore * 100).toInt();

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: InkWell(
        onTap: () => _viewBookmarkDetail(bookmark),
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: Colors.green.shade100,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text(
                      '匹配度 $relevancePercent%',
                      style: TextStyle(
                        fontSize: 11,
                        color: Colors.green.shade700,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                  const Spacer(),
                  if (bookmark.bookTitle != null)
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: Colors.grey.shade100,
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        bookmark.bookTitle!,
                        style: const TextStyle(
                          fontSize: 11,
                          color: Colors.grey,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                ],
              ),
              const SizedBox(height: 12),
              Text(
                bookmark.title,
                style: const TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                ),
              ),
              if (bookmark.excerpt != null && bookmark.excerpt!.isNotEmpty) ...[
                const SizedBox(height: 8),
                Text(
                  result.highlight,
                  style: TextStyle(
                    fontSize: 13,
                    color: Colors.grey.shade600,
                    height: 1.5,
                  ),
                  maxLines: 3,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
              if (bookmark.tags.isNotEmpty) ...[
                const SizedBox(height: 12),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: bookmark.tags.take(3).map((tag) {
                    return Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: Colors.purple.shade50,
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Text(
                        '#$tag',
                        style: TextStyle(
                          fontSize: 11,
                          color: Colors.purple.shade700,
                        ),
                      ),
                    );
                  }).toList(),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  List<String> _getRecentTags(List<Bookmark> bookmarks) {
    final allTags = <String>[];
    for (final bookmark in bookmarks) {
      allTags.addAll(bookmark.tags);
    }
    final uniqueTags = allTags.toSet().toList();
    return uniqueTags.take(8).toList();
  }

  void _viewBookmarkDetail(Bookmark bookmark) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
      ),
      builder: (context) => _BookmarkDetailSheet(bookmark: bookmark),
    );
  }
}

class _BookmarkDetailSheet extends StatelessWidget {
  final Bookmark bookmark;

  const _BookmarkDetailSheet({required this.bookmark});

  @override
  Widget build(BuildContext context) {
    return DraggableScrollableSheet(
      initialChildSize: 0.8,
      minChildSize: 0.5,
      maxChildSize: 0.95,
      expand: false,
      builder: (context, scrollController) {
        return SingleChildScrollView(
          controller: scrollController,
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Center(
                child: Container(
                  width: 40,
                  height: 4,
                  decoration: BoxDecoration(
                    color: Colors.grey.shade300,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              const SizedBox(height: 24),
              Text(
                bookmark.title,
                style: const TextStyle(
                  fontSize: 22,
                  fontWeight: FontWeight.bold,
                ),
              ),
              if (bookmark.bookTitle != null) ...[
                const SizedBox(height: 8),
                Text(
                  '📚 来自：${bookmark.bookTitle}',
                  style: TextStyle(
                    fontSize: 14,
                    color: Colors.grey.shade600,
                  ),
                ),
              ],
              if (bookmark.pageNumber != null) ...[
                const SizedBox(height: 4),
                Text(
                  '第 ${bookmark.pageNumber} 页',
                  style: TextStyle(
                    fontSize: 13,
                    color: Colors.grey.shade500,
                  ),
                ),
              ],
              const SizedBox(height: 16),
              const Divider(),
              const SizedBox(height: 16),
              if (bookmark.excerpt != null && bookmark.excerpt!.isNotEmpty)
                Text(
                  bookmark.excerpt!,
                  style: TextStyle(
                    fontSize: 15,
                    height: 1.8,
                    color: Colors.grey.shade800,
                  ),
                ),
              const SizedBox(height: 24),
              if (bookmark.tags.isNotEmpty) ...[
                Wrap(
                  spacing: 10,
                  runSpacing: 10,
                  children: bookmark.tags.map((tag) {
                    return Container(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                      decoration: BoxDecoration(
                        color: Colors.purple.shade100,
                        borderRadius: BorderRadius.circular(16),
                      ),
                      child: Text(
                        '#$tag',
                        style: TextStyle(
                          fontSize: 13,
                          color: Colors.purple.shade800,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    );
                  }).toList(),
                ),
                const SizedBox(height: 24),
              ],
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: () => Navigator.pop(context),
                      icon: const Icon(Icons.auto_awesome),
                      label: const Text('AI生成摘要'),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: ElevatedButton.icon(
                      onPressed: () => _shareBookmark(context),
                      icon: const Icon(Icons.share),
                      label: const Text('分享卡片'),
                    ),
                  ),
                ],
              ),
            ],
          ),
        );
      },
    );
  }

  void _shareBookmark(BuildContext context) {
    Navigator.pop(context);
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('分享书摘'),
        content: const Text('书摘卡片生成功能即将上线！'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('确定'),
          ),
        ],
      ),
    );
  }
}
