import 'dart:typed_data';
import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import '../models/bookmark.dart';

enum CardTemplate {
  minimalist,
  elegant,
  creative,
  quote,
}

class CardGeneratorService {
  static final Map<CardTemplate, CardStyle> _styles = {
    CardTemplate.minimalist: CardStyle(
      backgroundColor: Colors.white,
      textColor: Colors.black87,
      accentColor: Colors.grey[400]!,
      titleFontSize: 20,
      contentFontSize: 16,
      borderRadius: 8,
      showBorder: true,
    ),
    CardTemplate.elegant: CardStyle(
      backgroundColor: const Color(0xFFF8F5F0),
      textColor: const Color(0xFF2C3E50),
      accentColor: const Color(0xFFC9A86C),
      titleFontSize: 22,
      contentFontSize: 17,
      borderRadius: 16,
      showBorder: false,
    ),
    CardTemplate.creative: CardStyle(
      backgroundColor: const Color(0xFFFFF8E1),
      textColor: const Color(0xFF5D4037),
      accentColor: const Color(0xFFFF8A65),
      titleFontSize: 18,
      contentFontSize: 15,
      borderRadius: 24,
      showBorder: false,
    ),
    CardTemplate.quote: CardStyle(
      backgroundColor: const Color(0xFF37474F),
      textColor: Colors.white,
      accentColor: const Color(0xFFFFD54F),
      titleFontSize: 24,
      contentFontSize: 18,
      borderRadius: 0,
      showBorder: false,
    ),
  };

  static Future<Uint8List> generateBookmarkCard({
    required Bookmark bookmark,
    String? author,
    CardTemplate template = CardTemplate.elegant,
    Size size = const Size(600, 800),
    bool includeQrCode = false,
    String? customFooter,
  }) async {
    final style = _styles[template]!;

    final widget = _buildCardWidget(
      bookmark: bookmark,
      author: author,
      style: style,
      size: size,
      includeQrCode: includeQrCode,
      customFooter: customFooter,
    );

    return _captureWidgetToImage(widget, size);
  }

  static Widget _buildCardWidget({
    required Bookmark bookmark,
    required String? author,
    required CardStyle style,
    required Size size,
    required bool includeQrCode,
    required String? customFooter,
  }) {
    return Material(
      color: Colors.transparent,
      child: Container(
        width: size.width,
        height: size.height,
        padding: const EdgeInsets.all(32),
        decoration: BoxDecoration(
          color: style.backgroundColor,
          borderRadius: BorderRadius.circular(style.borderRadius.toDouble()),
          border: style.showBorder
              ? Border.all(color: style.accentColor, width: 2)
              : null,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildHeader(bookmark, author, style),
            const SizedBox(height: 32),
            Expanded(
              child: _buildContent(bookmark.excerpt ?? bookmark.title, style),
            ),
            const SizedBox(height: 24),
            _buildTags(bookmark.tags, style),
            const SizedBox(height: 24),
            _buildFooter(bookmark, style, customFooter),
          ],
        ),
      ),
    );
  }

  static Widget _buildHeader(Bookmark bookmark, String? author, CardStyle style) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: 48,
          height: 4,
          decoration: BoxDecoration(
            color: style.accentColor,
            borderRadius: BorderRadius.circular(2),
          ),
        ),
        const SizedBox(height: 16),
        Text(
          bookmark.bookTitle ?? '📚 精彩书摘',
          style: TextStyle(
            fontSize: style.titleFontSize.toDouble(),
            fontWeight: FontWeight.bold,
            color: style.textColor,
            letterSpacing: 0.5,
          ),
        ),
        if (author != null) ...[
          const SizedBox(height: 8),
          Text(
            '—— $author',
            style: TextStyle(
              fontSize: style.contentFontSize.toDouble() - 2,
              color: style.textColor.withOpacity(0.6),
              fontStyle: FontStyle.italic,
            ),
          ),
        ],
      ],
    );
  }

  static Widget _buildContent(String content, CardStyle style) {
    return SingleChildScrollView(
      child: Text(
        content,
        style: TextStyle(
          fontSize: style.contentFontSize.toDouble(),
          color: style.textColor,
          height: 1.8,
          letterSpacing: 0.3,
        ),
      ),
    );
  }

  static Widget _buildTags(List<String> tags, CardStyle style) {
    if (tags.isEmpty) return const SizedBox.shrink();

    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: tags.take(5).map((tag) {
        return Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
          decoration: BoxDecoration(
            color: style.accentColor.withOpacity(0.15),
            borderRadius: BorderRadius.circular(16),
          ),
          child: Text(
            '#$tag',
            style: TextStyle(
              fontSize: 12,
              color: style.accentColor,
              fontWeight: FontWeight.w500,
            ),
          ),
        );
      }).toList(),
    );
  }

  static Widget _buildFooter(Bookmark bookmark, CardStyle style, String? customFooter) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Divider(height: 1),
        const SizedBox(height: 16),
        Row(
          children: [
            Icon(
              Icons.bookmark_border,
              color: style.accentColor,
              size: 20,
            ),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                customFooter ?? '用阅读记录生活 · Generated by BookSync',
                style: TextStyle(
                  fontSize: 11,
                  color: style.textColor.withOpacity(0.5),
                ),
              ),
            ),
          ],
        ),
        if (bookmark.pageNumber != null) ...[
          const SizedBox(height: 8),
          Text(
            '第 ${bookmark.pageNumber} 页',
            style: TextStyle(
              fontSize: 10,
              color: style.textColor.withOpacity(0.4),
            ),
          ),
        ],
      ],
    );
  }

  static Future<Uint8List> _captureWidgetToImage(Widget widget, Size size) async {
    final repaintBoundary = RenderRepaintBoundary();

    final view = ui.PlatformDispatcher.instance.views.first;
    final imageSize = Size(size.width * view.devicePixelRatio, size.height * view.devicePixelRatio);

    final renderView = RenderView(
      child: RenderPositionedBox(
        alignment: Alignment.center,
        child: repaintBoundary,
      ),
      configuration: ViewConfiguration(
        size: imageSize,
        devicePixelRatio: view.devicePixelRatio,
      ),
      view: view,
    );

    final pipelineOwner = PipelineOwner()..rootNode = renderView;
    renderView.prepareInitialFrame();

    final buildOwner = BuildOwner(focusManager: FocusManager());
    final rootElement = RenderObjectToWidgetAdapter<RenderBox>(
      container: repaintBoundary,
      child: Directionality(
        textDirection: TextDirection.ltr,
        child: widget,
      ),
    ).attachToRenderTree(buildOwner);

    buildOwner
      ..buildScope(rootElement)
      ..finalizeTree();

    pipelineOwner
      ..flushLayout()
      ..flushCompositingBits()
      ..flushPaint();

    final image = await repaintBoundary.toImage(pixelRatio: view.devicePixelRatio);
    final byteData = await image.toByteData(format: ui.ImageByteFormat.png);

    return byteData!.buffer.asUint8List();
  }

  static Widget buildPreviewCard({
    required Bookmark bookmark,
    String? author,
    CardTemplate template = CardTemplate.elegant,
    double aspectRatio = 0.75,
    VoidCallback? onTap,
  }) {
    final style = _styles[template]!;

    return GestureDetector(
      onTap: onTap,
      child: AspectRatio(
        aspectRatio: aspectRatio,
        child: Container(
          margin: const EdgeInsets.all(16),
          padding: const EdgeInsets.all(24),
          decoration: BoxDecoration(
            color: style.backgroundColor,
            borderRadius: BorderRadius.circular(style.borderRadius.toDouble()),
            border: style.showBorder
                ? Border.all(color: style.accentColor, width: 2)
                : null,
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.1),
                blurRadius: 16,
                offset: const Offset(0, 8),
              ),
            ],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 32,
                height: 3,
                decoration: BoxDecoration(
                  color: style.accentColor,
                  borderRadius: BorderRadius.circular(1.5),
                ),
              ),
              const SizedBox(height: 12),
              Text(
                bookmark.bookTitle ?? '📚 精彩书摘',
                style: TextStyle(
                  fontSize: style.titleFontSize.toDouble() - 4,
                  fontWeight: FontWeight.bold,
                  color: style.textColor,
                ),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
              if (author != null) ...[
                const SizedBox(height: 6),
                Text(
                  '—— $author',
                  style: TextStyle(
                    fontSize: style.contentFontSize.toDouble() - 4,
                    color: style.textColor.withOpacity(0.6),
                    fontStyle: FontStyle.italic,
                  ),
                ),
              ],
              const SizedBox(height: 16),
              Expanded(
                child: Text(
                  bookmark.excerpt ?? bookmark.title,
                  style: TextStyle(
                    fontSize: style.contentFontSize.toDouble() - 2,
                    color: style.textColor,
                    height: 1.6,
                  ),
                  maxLines: 6,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              const SizedBox(height: 12),
              if (bookmark.tags.isNotEmpty)
                Wrap(
                  spacing: 6,
                  runSpacing: 6,
                  children: bookmark.tags.take(3).map((tag) {
                    return Text(
                      '#$tag',
                      style: TextStyle(
                        fontSize: 10,
                        color: style.accentColor,
                        fontWeight: FontWeight.w500,
                      ),
                    );
                  }).toList(),
                ),
            ],
          ),
        ),
      ),
    );
  }

  static List<String> get templateNames => [
        '极简风格',
        '优雅风格',
        '创意风格',
        '名言风格',
      ];
}

class CardStyle {
  final Color backgroundColor;
  final Color textColor;
  final Color accentColor;
  final int titleFontSize;
  final int contentFontSize;
  final int borderRadius;
  final bool showBorder;

  CardStyle({
    required this.backgroundColor,
    required this.textColor,
    required this.accentColor,
    required this.titleFontSize,
    required this.contentFontSize,
    required this.borderRadius,
    required this.showBorder,
  });
}
