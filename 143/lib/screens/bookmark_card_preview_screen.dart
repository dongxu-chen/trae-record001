import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import '../models/bookmark.dart';
import '../services/card_generator_service.dart';
import 'dart:ui' as ui;

class BookmarkCardPreviewScreen extends StatefulWidget {
  final Bookmark bookmark;

  const BookmarkCardPreviewScreen({
    super.key,
    required this.bookmark,
  });

  @override
  State<BookmarkCardPreviewScreen> createState() => _BookmarkCardPreviewScreenState();
}

class _BookmarkCardPreviewScreenState extends State<BookmarkCardPreviewScreen> {
  CardTemplate _selectedTemplate = CardTemplate.elegant;
  final GlobalKey _cardKey = GlobalKey();
  bool _isExporting = false;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('书摘卡片'),
        actions: [
          IconButton(
            icon: const Icon(Icons.download),
            onPressed: _exportCard,
            tooltip: '保存图片',
          ),
          IconButton(
            icon: const Icon(Icons.share),
            onPressed: _shareCard,
            tooltip: '分享',
          ),
        ],
      ),
      body: Column(
        children: [
          Expanded(
            child: Center(
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(24),
                child: _buildPreviewCard(),
              ),
            ),
          ),
          _buildTemplateSelector(),
        ],
      ),
    );
  }

  Widget _buildPreviewCard() {
    return RepaintBoundary(
      key: _cardKey,
      child: CardGeneratorService.buildPreviewCard(
        bookmark: widget.bookmark,
        template: _selectedTemplate,
        aspectRatio: 0.75,
      ),
    );
  }

  Widget _buildTemplateSelector() {
    final templates = [
      (CardTemplate.minimalist, '极简', Icons.crop_square),
      (CardTemplate.elegant, '优雅', Icons.brush),
      (CardTemplate.creative, '创意', Icons.palette),
      (CardTemplate.quote, '名言', Icons.format_quote),
    ];

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 8,
            offset: const Offset(0, -2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            '选择模板',
            style: TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 12),
          Row(
            children: templates.map((template) {
              final isSelected = _selectedTemplate == template.$1;
              return Expanded(
                child: GestureDetector(
                  onTap: () {
                    setState(() {
                      _selectedTemplate = template.$1;
                    });
                  },
                  child: Container(
                    margin: const EdgeInsets.symmetric(horizontal: 4),
                    padding: const EdgeInsets.symmetric(vertical: 12),
                    decoration: BoxDecoration(
                      color: isSelected ? Colors.blue.shade50 : Colors.grey.shade50,
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(
                        color: isSelected ? Colors.blue : Colors.grey.shade200,
                        width: 2,
                      ),
                    ),
                    child: Column(
                      children: [
                        Icon(
                          template.$3,
                          color: isSelected ? Colors.blue : Colors.grey,
                          size: 24,
                        ),
                        const SizedBox(height: 4),
                        Text(
                          template.$2,
                          style: TextStyle(
                            fontSize: 12,
                            color: isSelected ? Colors.blue : Colors.grey,
                            fontWeight: isSelected ? FontWeight.w600 : FontWeight.normal,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              );
            }).toList(),
          ),
        ],
      ),
    );
  }

  Future<Uint8List?> _captureCard() async {
    try {
      final boundary = _cardKey.currentContext?.findRenderObject() as RenderRepaintBoundary?;
      if (boundary == null) return null;

      final image = await boundary.toImage(pixelRatio: 3.0);
      final byteData = await image.toByteData(format: ui.ImageByteFormat.png);
      return byteData?.buffer.asUint8List();
    } catch (e) {
      debugPrint('Error capturing card: $e');
      return null;
    }
  }

  Future<void> _exportCard() async {
    if (_isExporting) return;

    setState(() => _isExporting = true);

    try {
      final imageData = await CardGeneratorService.generateBookmarkCard(
        bookmark: widget.bookmark,
        template: _selectedTemplate,
      );

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: const Text('书摘卡片已生成'),
            action: SnackBarAction(
              label: '查看',
              onPressed: () => _showImagePreview(imageData),
            ),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('生成失败: $e')),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isExporting = false);
      }
    }
  }

  void _showImagePreview(Uint8List imageData) {
    showDialog(
      context: context,
      builder: (context) => Dialog(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Image.memory(imageData),
            Padding(
              padding: const EdgeInsets.all(16),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  TextButton(
                    onPressed: () => Navigator.pop(context),
                    child: const Text('关闭'),
                  ),
                  const SizedBox(width: 8),
                  ElevatedButton(
                    onPressed: () => Navigator.pop(context),
                    child: const Text('保存'),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  void _shareCard() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('分享书摘'),
        content: const Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            ListTile(
              leading: Icon(Icons.image),
              title: Text('分享图片'),
              subtitle: Text('生成精美的书摘卡片图片'),
            ),
            ListTile(
              leading: Icon(Icons.text_fields),
              title: Text('分享文本'),
              subtitle: Text('复制书摘内容为纯文本'),
            ),
            ListTile(
              leading: Icon(Icons.link),
              title: Text('分享链接'),
              subtitle: Text('生成可分享的网页链接'),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('取消'),
          ),
        ],
      ),
    );
  }
}
