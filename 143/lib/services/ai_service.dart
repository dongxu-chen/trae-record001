import 'dart:convert';
import 'dart:typed_data';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import '../models/bookmark.dart';
import '../models/reading_stats.dart';
import 'image_preprocessor.dart';

class AIService {
  final String? apiKey;
  final String baseUrl;
  
  AIService({
    this.apiKey,
    this.baseUrl = 'https://api.openai.com/v1',
  });

  Future<String> generateBookmarkSummary({
    required String bookTitle,
    required String excerpt,
    String? author,
    List<String>? tags,
    String language = 'zh-CN',
  }) async {
    try {
      final prompt = _buildSummaryPrompt(
        bookTitle: bookTitle,
        excerpt: excerpt,
        author: author,
        tags: tags,
        language: language,
      );

      return await _callLLM(prompt);
    } catch (e) {
      debugPrint('Error generating summary: $e');
      return _generateFallbackSummary(excerpt);
    }
  }

  Future<String> generateInsights(List<Bookmark> bookmarks) async {
    try {
      final allExcerpts = bookmarks.map((b) => b.excerpt ?? b.title).join('\n---\n');
      final prompt = '''
基于以下书摘内容，生成深度阅读洞察：

$allExcerpts

请提供：
1. 核心主题总结（3-5个要点）
2. 关键观点提炼
3. 相关概念关联
4. 行动建议

请用中文回答，结构化展示。
''';

      return await _callLLM(prompt);
    } catch (e) {
      debugPrint('Error generating insights: $e');
      return '暂无足够书摘生成深度洞察';
    }
  }

  Future<List<String>> generateTagsFromContent(String content) async {
    try {
      final prompt = '''
为以下内容生成5-8个相关标签，用逗号分隔：

内容：$content

要求：
- 标签简洁（2-4个字）
- 覆盖核心主题
- 包含情感关键词
- 用中文
''';

      final response = await _callLLM(prompt);
      return response
          .split(RegExp(r'[,，、\n]'))
          .map((t) => t.trim())
          .where((t) => t.isNotEmpty && t.length <= 10)
          .take(8)
          .toList();
    } catch (e) {
      debugPrint('Error generating tags: $e');
      return [];
    }
  }

  Future<String> analyzeReadingHabits(ReadingStats stats) async {
    try {
      final prompt = '''
基于以下阅读数据，分析用户的阅读习惯并给出建议：

📊 阅读统计：
- 总阅读时长：${stats.totalReadMinutes} 分钟
- 阅读天数：${stats.readingDays} 天
- 完成书籍：${stats.booksCompleted} 本
- 平均每日阅读：${stats.averageDailyMinutes.toStringAsFixed(1)} 分钟
- 最长连续阅读：${stats.longestStreak} 天

📈 时段分布：
${stats.hourlyDistribution.entries.map((e) => '${e.key}点: ${e.value}分钟').join('\n')}

📅 周分布：
${stats.weeklyDistribution.entries.map((e) => '周${['一','二','三','四','五','六','日'][e.key]}: ${e.value}分钟').join('\n')}

请分析：
1. 阅读模式识别（晨读/夜读/碎片化）
2. 专注度评估
3. 习惯养成建议（3条）
4. 下月阅读目标建议

请用中文回答，亲切友好。
''';

      return await _callLLM(prompt);
    } catch (e) {
      debugPrint('Error analyzing habits: $e');
      return '阅读习惯分析暂不可用';
    }
  }

  Future<String> ocrImage(Uint8List imageData) async {
    try {
      final processedImage = await OCRPreprocessingPipeline.processImage(imageData);
      
      final base64Image = base64Encode(processedImage);
      
      final response = await http.post(
        Uri.parse('$baseUrl/chat/completions'),
        headers: {
          'Content-Type': 'application/json',
          if (apiKey != null) 'Authorization': 'Bearer $apiKey',
        },
        body: jsonEncode({
          'model': 'gpt-4-vision-preview',
          'messages': [
            {
              'role': 'user',
              'content': [
                {'type': 'text', 'text': '请提取图片中的所有文字，保持原有格式和换行。如果是书籍内容，请保留段落结构。'},
                {
                  'type': 'image_url',
                  'image_url': {'url': 'data:image/png;base64,$base64Image'}
                }
              ]
            }
          ],
          'max_tokens': 2000,
        }),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return data['choices'][0]['message']['content'];
      } else {
        throw Exception('OCR failed: ${response.statusCode}');
      }
    } catch (e) {
      debugPrint('OCR error: $e');
      return _mockOCRResult();
    }
  }

  Future<List<BookmarkSearchResult>> searchBookmarks(
    String query,
    List<Bookmark> bookmarks,
  ) async {
    final results = <BookmarkSearchResult>[];
    final lowerQuery = query.toLowerCase();

    for (final bookmark in bookmarks) {
      final content = '${bookmark.title} ${bookmark.excerpt ?? ''} ${bookmark.tags.join(' ')}'.toLowerCase();
      
      final score = _calculateRelevanceScore(query, content);
      
      if (score > 0.1) {
        final highlight = _generateHighlight(bookmark.excerpt ?? bookmark.title, query);
        
        results.add(BookmarkSearchResult(
          bookmark: bookmark,
          relevanceScore: score,
          highlight: highlight,
        ));
      }
    }

    results.sort((a, b) => b.relevanceScore.compareTo(a.relevanceScore));
    return results;
  }

  String _buildSummaryPrompt({
    required String bookTitle,
    required String excerpt,
    String? author,
    List<String>? tags,
    required String language,
  }) {
    return '''
你是一位专业的阅读助手。请为以下书摘生成精炼摘要：

📚 书籍：$bookTitle
${author != null ? '✍️ 作者：$author' : ''}
${tags != null && tags.isNotEmpty ? '🏷️ 标签：${tags.join(', ')}' : ''}

📝 书摘内容：
$excerpt

请生成：
1. 📌 一句话精华摘要（50字以内）
2. 💡 核心观点提炼（3点，每点不超过30字）
3. 🎯 个人感悟启发（50-100字）

请用中文回答，使用markdown格式，语气亲切有启发性。
''';
  }

  Future<String> _callLLM(String prompt) async {
    await Future.delayed(const Duration(milliseconds: 800));
    
    if (prompt.contains('书摘内容')) {
      return '''
📌 **一句话精华**：这段文字深刻揭示了成长的本质，启发我们在困境中寻找意义。

💡 **核心观点**：
1. 困难是成长的必经之路
2. 保持积极心态是关键
3. 持续行动带来改变

🎯 **个人感悟**：这本书让我重新认识了挫折的价值。每一次挑战都是成长的机会，重要的是我们如何面对。保持学习的心态，每天进步一点点，终会到达想去的地方。
''';
    }
    
    if (prompt.contains('阅读数据')) {
      return '''
📊 **阅读模式分析**

你是典型的「夜读型」读者，高峰阅读时段集中在20-22点。这表明你喜欢在一天结束时通过阅读来放松和充电。

💪 **专注度评估**
你的阅读连续性很好，平均每次阅读时长超过30分钟，说明具备良好的专注力。

🎯 **习惯养成建议**
1. 保持20点的阅读黄金时段，建议提前10分钟做准备
2. 尝试在早晨增加15分钟轻阅读，开启元气一天
3. 周末可以安排1-2次深度阅读（1小时以上）

📈 **下月目标建议**
- 保持当前连续阅读记录
- 尝试挑战1.5倍阅读量
- 增加2本不同类型的书籍
''';
    }

    if (prompt.contains('书摘内容')) {
      return '''
🔍 **核心主题**：个人成长、心态管理、行动导向

💎 **关键观点提炼**：
1. 成长源于舒适区外的探索
2. 心态决定面对困难的姿态
3. 小步迭代胜过完美主义

🔗 **概念关联**：这与「复利效应」和「微习惯」理论相通，持续的小行动积累会带来质的飞跃。

✨ **行动建议**：
• 每天设定一个小挑战
• 记录反思日志
• 每周回顾成长轨迹
''';
    }

    return 'AI 分析完成';
  }

  String _generateFallbackSummary(String content) {
    final sentences = content.split(RegExp(r'[。！？.!?]')).where((s) => s.trim().isNotEmpty).toList();
    final keySentences = sentences.take(3).join('。');
    
    return '''
📌 **一句话精华**：${sentences.isNotEmpty ? sentences.first.trim().substring(0, 40) : '精彩书摘'}...

💡 **核心要点**：精彩内容值得反复品味

🎯 **感悟**：这段文字触动人心，值得深入思考。
''';
  }

  double _calculateRelevanceScore(String query, String content) {
    final queryWords = query.toLowerCase().split(RegExp(r'\s+'));
    int matches = 0;
    
    for (final word in queryWords) {
      if (word.length >= 2) {
        matches += ' $content '.split(' $word ').length - 1;
      }
    }
    
    return matches / (content.length / 100);
  }

  String _generateHighlight(String content, String query) {
    final lowerContent = content.toLowerCase();
    final lowerQuery = query.toLowerCase();
    final index = lowerContent.indexOf(lowerQuery);
    
    if (index == -1) {
      return content.length > 100 ? '${content.substring(0, 100)}...' : content;
    }
    
    final start = (index - 30).clamp(0, content.length);
    final end = (index + query.length + 50).clamp(0, content.length);
    return '...${content.substring(start, end)}...';
  }

  String _mockOCRResult() {
    return '''
这是 OCR 识别的示例文本。在实际使用中，这里会显示从图片中识别出的文字内容。

OCR（光学字符识别）技术可以将图片中的文字转换为可编辑的文本格式，方便后续的搜索、编辑和管理。
''';
  }
}

class BookmarkSearchResult {
  final Bookmark bookmark;
  final double relevanceScore;
  final String highlight;

  BookmarkSearchResult({
    required this.bookmark,
    required this.relevanceScore,
    required this.highlight,
  });
}
