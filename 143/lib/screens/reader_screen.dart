import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/book.dart';
import '../models/note.dart';
import '../models/bookmark.dart';
import '../providers/note_provider.dart';
import '../providers/progress_provider.dart';
import '../providers/bookmark_provider.dart';

class ReaderScreen extends StatefulWidget {
  final Book book;

  const ReaderScreen({super.key, required this.book});

  @override
  State<ReaderScreen> createState() => _ReaderScreenState();
}

class _ReaderScreenState extends State<ReaderScreen> {
  final PageController _pageController = PageController();
  int _currentPage = 0;
  bool _showControls = true;
  double _fontSize = 18;
  Brightness _brightness = Brightness.light;

  final List<String> _samplePages = [
    "Chapter 1\n\nThe beginning of a wonderful journey. In the first chapter, we meet our protagonist who is about to embark on an adventure that will change their life forever.\n\nThe sun was setting over the horizon, painting the sky in hues of orange and purple. A gentle breeze carried the scent of jasmine through the open window.",
    "Chapter 2\n\nAs our hero ventures deeper into the unknown, they encounter challenges that test their courage and determination. Each step brings new discoveries and unexpected dangers.\n\nThe forest was dense and shadowy. Ancient trees towered above, their branches interlocking like fingers reaching for the sky. Strange sounds echoed in the distance.",
    "Chapter 3\n\nIn this chapter, friendships are forged and alliances are tested. The story takes an unexpected turn as secrets are revealed and truths come to light.\n\n\"You must trust me,\" said the stranger. Their eyes held a depth of wisdom that seemed beyond their years. \"The path ahead is treacherous, but together we can prevail.\"",
    "Chapter 4\n\nThe plot thickens as our characters face their greatest challenge yet. Will they overcome the obstacles in their path, or will adversity prove too great?\n\nTime seemed to stand still in that moment. The weight of the decision hung in the air like a storm cloud. Every choice would have consequences, rippling outward into the future.",
    "Chapter 5\n\nThe climax approaches. Tensions rise as the story builds to its dramatic conclusion. What will become of our heroes? Only time will tell.\n\nAnd so, with courage in their hearts and hope in their souls, they stepped forward into the unknown, ready to face whatever fate had in store.",
  ];

  @override
  void initState() {
    super.initState();
    _loadProgress();
  }

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  Future<void> _loadProgress() async {
    final progressProvider =
        Provider.of<ProgressProvider>(context, listen: false);
    await progressProvider.loadProgressForBook(widget.book.id);
    final progress = progressProvider.getProgressForBook(widget.book.id);
    if (progress != null) {
      setState(() {
        _currentPage = progress.currentPage;
      });
      _pageController.jumpToPage(_currentPage);
    }
  }

  void _saveProgress() {
    final progressProvider =
        Provider.of<ProgressProvider>(context, listen: false);
    progressProvider.updateProgress(
      widget.book.id,
      _currentPage,
      _samplePages.length,
      'Mobile',
    );
  }

  void _onPageChanged(int page) {
    setState(() {
      _currentPage = page;
    });
    _saveProgress();
  }

  void _addNote() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (context) => AddNoteSheet(
        bookId: widget.book.id,
        pageNumber: _currentPage,
      ),
    );
  }

  void _addBookmark() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (context) => AddBookmarkSheet(
        bookId: widget.book.id,
        pageNumber: _currentPage,
        bookTitle: widget.book.title,
      ),
    );
  }

  void _showNotes() {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => NotesListScreen(
          bookId: widget.book.id,
          bookTitle: widget.book.title,
        ),
      ),
    );
  }

  void _showSettings() {
    showModalBottomSheet(
      context: context,
      builder: (context) => ReaderSettingsSheet(
        initialFontSize: _fontSize,
        initialBrightness: _brightness,
        onSettingsChanged: (fontSize, brightness) {
          setState(() {
            _fontSize = fontSize;
            _brightness = brightness;
          });
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Theme(
      data: _brightness == Brightness.dark
          ? ThemeData.dark()
          : ThemeData.light(),
      child: Scaffold(
        body: GestureDetector(
          onTap: () {
            setState(() {
              _showControls = !_showControls;
            });
          },
          child: Stack(
            children: [
              PageView.builder(
                controller: _pageController,
                onPageChanged: _onPageChanged,
                itemCount: _samplePages.length,
                itemBuilder: (context, index) {
                  return SingleChildScrollView(
                    padding: const EdgeInsets.all(24).copyWith(
                      top: MediaQuery.of(context).padding.top + 80,
                      bottom: 100,
                    ),
                    child: Text(
                      _samplePages[index],
                      style: TextStyle(
                        fontSize: _fontSize,
                        height: 1.5,
                      ),
                    ),
                  );
                },
              ),
              AnimatedPositioned(
                duration: const Duration(milliseconds: 200),
                top: _showControls ? 0 : -80,
                left: 0,
                right: 0,
                child: AppBar(
                  title: Text(widget.book.title),
                  leading: IconButton(
                    icon: const Icon(Icons.arrow_back),
                    onPressed: () => Navigator.pop(context),
                  ),
                  actions: [
                    IconButton(
                      icon: const Icon(Icons.note_outlined),
                      onPressed: _showNotes,
                      tooltip: 'Notes',
                    ),
                    IconButton(
                      icon: const Icon(Icons.settings),
                      onPressed: _showSettings,
                      tooltip: 'Settings',
                    ),
                  ],
                ),
              ),
              AnimatedPositioned(
                duration: const Duration(milliseconds: 200),
                bottom: _showControls ? 0 : -100,
                left: 0,
                right: 0,
                child: Container(
                  decoration: BoxDecoration(
                    color: Theme.of(context).colorScheme.surface,
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withOpacity(0.1),
                        blurRadius: 4,
                        offset: const Offset(0, -2),
                      ),
                    ],
                  ),
                  child: SafeArea(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Row(
                            children: [
                              IconButton(
                                icon: const Icon(Icons.bookmark_border),
                                onPressed: _addBookmark,
                                tooltip: 'Add Bookmark',
                              ),
                              IconButton(
                                icon: const Icon(Icons.edit_note),
                                onPressed: _addNote,
                                tooltip: 'Add Note',
                              ),
                              const Spacer(),
                              Text(
                                '${_currentPage + 1} / ${_samplePages.length}',
                                style: Theme.of(context).textTheme.bodySmall,
                              ),
                            ],
                          ),
                          Slider(
                            value: _currentPage.toDouble(),
                            min: 0,
                            max: (_samplePages.length - 1).toDouble(),
                            onChanged: (value) {
                              setState(() {
                                _currentPage = value.round();
                              });
                              _pageController.jumpToPage(_currentPage);
                              _saveProgress();
                            },
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class AddNoteSheet extends StatefulWidget {
  final String bookId;
  final int pageNumber;

  const AddNoteSheet({
    super.key,
    required this.bookId,
    required this.pageNumber,
  });

  @override
  State<AddNoteSheet> createState() => _AddNoteSheetState();
}

class _AddNoteSheetState extends State<AddNoteSheet> {
  final _formKey = GlobalKey<FormState>();
  final _contentController = TextEditingController();
  final _highlightController = TextEditingController();
  Color _selectedColor = Colors.yellow;

  final List<Color> _colors = [
    Colors.yellow,
    Colors.green,
    Colors.blue,
    Colors.pink,
    Colors.orange,
  ];

  @override
  void dispose() {
    _contentController.dispose();
    _highlightController.dispose();
    super.dispose();
  }

  void _submit() async {
    if (_formKey.currentState!.validate()) {
      final noteProvider = Provider.of<NoteProvider>(context, listen: false);
      final note = Note(
        id: '',
        bookId: widget.bookId,
        userId: '',
        content: _contentController.text,
        pageNumber: widget.pageNumber,
        highlightText: _highlightController.text.isNotEmpty
            ? _highlightController.text
            : null,
        color: _selectedColor,
        createdAt: DateTime.now(),
        updatedAt: DateTime.now(),
      );
      await noteProvider.addNote(note);
      if (mounted) {
        Navigator.pop(context);
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Note added successfully')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(
        bottom: MediaQuery.of(context).viewInsets.bottom,
      ),
      child: Container(
        padding: const EdgeInsets.all(24),
        child: Form(
          key: _formKey,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Add Note',
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              const SizedBox(height: 24),
              TextFormField(
                controller: _highlightController,
                decoration: const InputDecoration(
                  labelText: 'Highlighted Text (Optional)',
                  border: OutlineInputBorder(),
                ),
                maxLines: 2,
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _contentController,
                decoration: const InputDecoration(
                  labelText: 'Note Content',
                  border: OutlineInputBorder(),
                ),
                maxLines: 3,
                validator: (value) {
                  if (value == null || value.isEmpty) {
                    return 'Please enter your note';
                  }
                  return null;
                },
              ),
              const SizedBox(height: 16),
              const Text('Highlight Color:'),
              const SizedBox(height: 8),
              Row(
                children: _colors.map((color) {
                  return Padding(
                    padding: const EdgeInsets.only(right: 8),
                    child: GestureDetector(
                      onTap: () {
                        setState(() {
                          _selectedColor = color;
                        });
                      },
                      child: Container(
                        width: 40,
                        height: 40,
                        decoration: BoxDecoration(
                          color: color,
                          shape: BoxShape.circle,
                          border: _selectedColor == color
                              ? Border.all(
                                  color: Theme.of(context).colorScheme.primary,
                                  width: 3,
                                )
                              : null,
                        ),
                      ),
                    ),
                  );
                }).toList(),
              ),
              const SizedBox(height: 24),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: _submit,
                  child: const Text('Add Note'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class AddBookmarkSheet extends StatefulWidget {
  final String bookId;
  final int pageNumber;
  final String bookTitle;

  const AddBookmarkSheet({
    super.key,
    required this.bookId,
    required this.pageNumber,
    required this.bookTitle,
  });

  @override
  State<AddBookmarkSheet> createState() => _AddBookmarkSheetState();
}

class _AddBookmarkSheetState extends State<AddBookmarkSheet> {
  final _formKey = GlobalKey<FormState>();
  final _titleController = TextEditingController();
  final _excerptController = TextEditingController();
  final _tagController = TextEditingController();
  final List<String> _tags = [];

  @override
  void dispose() {
    _titleController.dispose();
    _excerptController.dispose();
    _tagController.dispose();
    super.dispose();
  }

  void _addTag() {
    if (_tagController.text.isNotEmpty && !_tags.contains(_tagController.text)) {
      setState(() {
        _tags.add(_tagController.text);
        _tagController.clear();
      });
    }
  }

  void _removeTag(String tag) {
    setState(() {
      _tags.remove(tag);
    });
  }

  void _submit() async {
    if (_formKey.currentState!.validate()) {
      final bookmarkProvider =
          Provider.of<BookmarkProvider>(context, listen: false);
      final bookmark = Bookmark(
        id: '',
        bookId: widget.bookId,
        userId: '',
        title: _titleController.text,
        excerpt: _excerptController.text.isNotEmpty
            ? _excerptController.text
            : null,
        pageNumber: widget.pageNumber,
        tags: _tags,
        createdAt: DateTime.now(),
        updatedAt: DateTime.now(),
      );
      await bookmarkProvider.addBookmark(bookmark);
      if (mounted) {
        Navigator.pop(context);
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Bookmark added successfully')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(
        bottom: MediaQuery.of(context).viewInsets.bottom,
      ),
      child: Container(
        padding: const EdgeInsets.all(24),
        child: Form(
          key: _formKey,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Add Bookmark',
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              const SizedBox(height: 8),
              Text(
                '${widget.bookTitle} - Page ${widget.pageNumber + 1}',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: Colors.grey,
                    ),
              ),
              const SizedBox(height: 24),
              TextFormField(
                controller: _titleController,
                decoration: const InputDecoration(
                  labelText: 'Bookmark Title',
                  border: OutlineInputBorder(),
                ),
                validator: (value) {
                  if (value == null || value.isEmpty) {
                    return 'Please enter a title';
                  }
                  return null;
                },
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _excerptController,
                decoration: const InputDecoration(
                  labelText: 'Excerpt (Optional)',
                  border: OutlineInputBorder(),
                ),
                maxLines: 3,
              ),
              const SizedBox(height: 16),
              Row(
                children: [
                  Expanded(
                    child: TextFormField(
                      controller: _tagController,
                      decoration: const InputDecoration(
                        labelText: 'Add Tag',
                        border: OutlineInputBorder(),
                      ),
                      onFieldSubmitted: (_) => _addTag(),
                    ),
                  ),
                  const SizedBox(width: 8),
                  IconButton(
                    icon: const Icon(Icons.add),
                    onPressed: _addTag,
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                children: _tags.map((tag) {
                  return Chip(
                    label: Text(tag),
                    deleteIcon: const Icon(Icons.close, size: 16),
                    onDeleted: () => _removeTag(tag),
                  );
                }).toList(),
              ),
              const SizedBox(height: 24),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: _submit,
                  child: const Text('Add Bookmark'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class NotesListScreen extends StatelessWidget {
  final String bookId;
  final String bookTitle;

  const NotesListScreen({
    super.key,
    required this.bookId,
    required this.bookTitle,
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Notes'),
        subtitle: Text(bookTitle),
      ),
      body: Consumer<NoteProvider>(
        builder: (context, noteProvider, child) {
          return StreamBuilder<List<Note>>(
            stream: noteProvider.getNotesStreamForBook(bookId),
            builder: (context, snapshot) {
              if (snapshot.connectionState == ConnectionState.waiting) {
                return const Center(child: CircularProgressIndicator());
              }

              final notes = snapshot.data ?? [];

              if (notes.isEmpty) {
                return Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(
                        Icons.note_outlined,
                        size: 80,
                        color: Colors.grey[400],
                      ),
                      const SizedBox(height: 16),
                      Text(
                        'No notes yet',
                        style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                              color: Colors.grey,
                            ),
                      ),
                    ],
                  ),
                );
              }

              return ListView.builder(
                padding: const EdgeInsets.all(16),
                itemCount: notes.length,
                itemBuilder: (context, index) {
                  final note = notes[index];
                  return Card(
                    margin: const EdgeInsets.only(bottom: 12),
                    child: ListTile(
                      leading: Container(
                        width: 8,
                        height: double.infinity,
                        color: note.color,
                      ),
                      title: Text(note.content),
                      subtitle: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          if (note.highlightText != null)
                            Padding(
                              padding: const EdgeInsets.only(top: 4),
                              child: Text(
                                '"${note.highlightText!}"',
                                style: TextStyle(
                                  fontStyle: FontStyle.italic,
                                  color: Colors.grey[600],
                                ),
                              ),
                            ),
                          const SizedBox(height: 4),
                          Text(
                            'Page ${note.pageNumber + 1}',
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                        ],
                      ),
                      trailing: IconButton(
                        icon: const Icon(Icons.delete_outline),
                        onPressed: () async {
                          await noteProvider.deleteNote(note.id, bookId);
                        },
                      ),
                    ),
                  );
                },
              );
            },
          );
        },
      ),
    );
  }
}

class ReaderSettingsSheet extends StatelessWidget {
  final double initialFontSize;
  final Brightness initialBrightness;
  final Function(double, Brightness) onSettingsChanged;

  const ReaderSettingsSheet({
    super.key,
    required this.initialFontSize,
    required this.initialBrightness,
    required this.onSettingsChanged,
  });

  @override
  Widget build(BuildContext context) {
    return StatefulBuilder(
      builder: (context, setState) {
        double fontSize = initialFontSize;
        Brightness brightness = initialBrightness;

        return Container(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Reader Settings',
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              const SizedBox(height: 24),
              const Text('Font Size'),
              Slider(
                value: fontSize,
                min: 14,
                max: 28,
                divisions: 14,
                label: fontSize.round().toString(),
                onChanged: (value) {
                  setState(() {
                    fontSize = value;
                  });
                  onSettingsChanged(fontSize, brightness);
                },
              ),
              const SizedBox(height: 16),
              const Text('Theme'),
              const SizedBox(height: 8),
              Row(
                children: [
                  Expanded(
                    child: ChoiceChip(
                      label: const Text('Light'),
                      selected: brightness == Brightness.light,
                      onSelected: (selected) {
                        if (selected) {
                          setState(() {
                            brightness = Brightness.light;
                          });
                          onSettingsChanged(fontSize, brightness);
                        }
                      },
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: ChoiceChip(
                      label: const Text('Dark'),
                      selected: brightness == Brightness.dark,
                      onSelected: (selected) {
                        if (selected) {
                          setState(() {
                            brightness = Brightness.dark;
                          });
                          onSettingsChanged(fontSize, brightness);
                        }
                      },
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
}
