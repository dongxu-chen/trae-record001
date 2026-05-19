import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/bookmark.dart';
import '../providers/bookmark_provider.dart';

class BookmarksScreen extends StatefulWidget {
  const BookmarksScreen({super.key});

  @override
  State<BookmarksScreen> createState() => _BookmarksScreenState();
}

class _BookmarksScreenState extends State<BookmarksScreen> {
  String? _selectedTag;
  final TextEditingController _searchController = TextEditingController();
  String _searchQuery = '';

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Consumer<BookmarkProvider>(
        builder: (context, bookmarkProvider, child) {
          return StreamBuilder<List<Bookmark>>(
            stream: bookmarkProvider.bookmarksStream,
            builder: (context, snapshot) {
              if (snapshot.connectionState == ConnectionState.waiting) {
                return const Center(child: CircularProgressIndicator());
              }

              final allBookmarks = snapshot.data ?? [];
              final allTags = bookmarkProvider.allTags;

              var filteredBookmarks = allBookmarks;

              if (_selectedTag != null) {
                filteredBookmarks = filteredBookmarks
                    .where((b) => b.tags.contains(_selectedTag))
                    .toList();
              }

              if (_searchQuery.isNotEmpty) {
                final query = _searchQuery.toLowerCase();
                filteredBookmarks = filteredBookmarks.where((b) {
                  return b.title.toLowerCase().contains(query) ||
                      (b.excerpt?.toLowerCase().contains(query) ?? false) ||
                      b.tags.any((tag) => tag.toLowerCase().contains(query));
                }).toList();
              }

              return CustomScrollView(
                slivers: [
                  SliverAppBar(
                    title: const Text('Bookmarks'),
                    floating: true,
                    pinned: true,
                    bottom: PreferredSize(
                      preferredSize: const Size.fromHeight(100),
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          children: [
                            TextField(
                              controller: _searchController,
                              decoration: InputDecoration(
                                hintText: 'Search bookmarks...',
                                prefixIcon: const Icon(Icons.search),
                                border: OutlineInputBorder(
                                  borderRadius: BorderRadius.circular(24),
                                ),
                                contentPadding: const EdgeInsets.symmetric(
                                  horizontal: 16,
                                  vertical: 8,
                                ),
                              ),
                              onChanged: (value) {
                                setState(() {
                                  _searchQuery = value;
                                });
                              },
                            ),
                            const SizedBox(height: 8),
                            if (allTags.isNotEmpty)
                              SizedBox(
                                height: 36,
                                child: ListView(
                                  scrollDirection: Axis.horizontal,
                                  children: [
                                    Padding(
                                      padding: const EdgeInsets.only(right: 8),
                                      child: FilterChip(
                                        label: const Text('All'),
                                        selected: _selectedTag == null,
                                        onSelected: (selected) {
                                          setState(() {
                                            _selectedTag = null;
                                          });
                                        },
                                      ),
                                    ),
                                    ...allTags.map((tag) {
                                      return Padding(
                                        padding: const EdgeInsets.only(right: 8),
                                        child: FilterChip(
                                          label: Text(tag),
                                          selected: _selectedTag == tag,
                                          onSelected: (selected) {
                                            setState(() {
                                              _selectedTag = selected ? tag : null;
                                            });
                                          },
                                        ),
                                      );
                                    }),
                                  ],
                                ),
                              ),
                          ],
                        ),
                      ),
                    ),
                  ),
                  if (filteredBookmarks.isEmpty)
                    SliverFillRemaining(
                      child: Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(
                              Icons.bookmark_outline,
                              size: 80,
                              color: Colors.grey[400],
                            ),
                            const SizedBox(height: 16),
                            Text(
                              'No bookmarks yet',
                              style: Theme.of(context)
                                  .textTheme
                                  .headlineSmall
                                  ?.copyWith(color: Colors.grey),
                            ),
                            const SizedBox(height: 8),
                            Text(
                              'Add bookmarks while reading',
                              style: TextStyle(color: Colors.grey[600]),
                            ),
                          ],
                        ),
                      ),
                    )
                  else
                    SliverList(
                      delegate: SliverChildBuilderDelegate(
                        (context, index) {
                          final bookmark = filteredBookmarks[index];
                          return BookmarkCard(
                            bookmark: bookmark,
                            onDelete: () =>
                                bookmarkProvider.deleteBookmark(bookmark.id),
                          );
                        },
                        childCount: filteredBookmarks.length,
                      ),
                    ),
                ],
              );
            },
          );
        },
      ),
    );
  }
}

class BookmarkCard extends StatelessWidget {
  final Bookmark bookmark;
  final VoidCallback onDelete;

  const BookmarkCard({
    super.key,
    required this.bookmark,
    required this.onDelete,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Text(
                    bookmark.title,
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.delete_outline),
                  onPressed: onDelete,
                  iconSize: 20,
                ),
              ],
            ),
            if (bookmark.excerpt != null)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.grey[100],
                    borderRadius: BorderRadius.circular(8),
                    border: Border(
                      left: BorderSide(
                        color: Theme.of(context).colorScheme.primary,
                        width: 3,
                      ),
                    ),
                  ),
                  child: Text(
                    '"${bookmark.excerpt!}"',
                    style: TextStyle(
                      fontStyle: FontStyle.italic,
                      color: Colors.grey[700],
                    ),
                  ),
                ),
              ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                Chip(
                  label: Text('Page ${bookmark.pageNumber + 1}'),
                  avatar: const Icon(Icons.pageview, size: 16),
                ),
                ...bookmark.tags.map((tag) {
                  return Chip(
                    label: Text(tag),
                    backgroundColor: Theme.of(context)
                        .colorScheme
                        .secondaryContainer
                        .withOpacity(0.5),
                  );
                }),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              'Created: ${_formatDate(bookmark.createdAt)}',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Colors.grey,
                  ),
            ),
          ],
        ),
      ),
    );
  }

  String _formatDate(DateTime date) {
    return '${date.month}/${date.day}/${date.year} ${date.hour}:${date.minute.toString().padLeft(2, '0')}';
  }
}
