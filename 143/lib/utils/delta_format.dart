import 'dart:convert';

enum DeltaOperationType {
  insert,
  delete,
  retain,
  format,
}

class DeltaOperation {
  final DeltaOperationType type;
  final int? length;
  final String? insert;
  final int? delete;
  final Map<String, dynamic>? attributes;

  DeltaOperation({
    required this.type,
    this.length,
    this.insert,
    this.delete,
    this.attributes,
  });

  Map<String, dynamic> toMap() {
    switch (type) {
      case DeltaOperationType.insert:
        return {
          'insert': insert,
          if (attributes != null) 'attributes': attributes,
        };
      case DeltaOperationType.delete:
        return {'delete': delete};
      case DeltaOperationType.retain:
        return {
          'retain': length,
          if (attributes != null) 'attributes': attributes,
        };
      case DeltaOperationType.format:
        return {
          'retain': length,
          'attributes': attributes,
        };
    }
  }

  factory DeltaOperation.fromMap(Map<String, dynamic> map) {
    if (map.containsKey('insert')) {
      return DeltaOperation(
        type: DeltaOperationType.insert,
        insert: map['insert'] as String,
        attributes: map['attributes'] as Map<String, dynamic>?,
      );
    } else if (map.containsKey('delete')) {
      return DeltaOperation(
        type: DeltaOperationType.delete,
        delete: map['delete'] as int,
      );
    } else if (map.containsKey('retain')) {
      return DeltaOperation(
        type: map.containsKey('attributes')
            ? DeltaOperationType.format
            : DeltaOperationType.retain,
        length: map['retain'] as int,
        attributes: map['attributes'] as Map<String, dynamic>?,
      );
    }
    throw ArgumentError('Invalid Delta operation');
  }
}

class NoteDelta {
  final String id;
  final List<DeltaOperation> operations;
  final DateTime timestamp;
  final String deviceId;
  final int version;

  NoteDelta({
    required this.id,
    required this.operations,
    required this.timestamp,
    required this.deviceId,
    this.version = 1,
  });

  Map<String, dynamic> toMap() {
    return {
      'id': id,
      'operations': operations.map((op) => op.toMap()).toList(),
      'timestamp': timestamp.toIso8601String(),
      'deviceId': deviceId,
      'version': version,
    };
  }

  factory NoteDelta.fromMap(Map<String, dynamic> map) {
    return NoteDelta(
      id: map['id'] as String,
      operations: (map['operations'] as List)
          .map((op) => DeltaOperation.fromMap(op as Map<String, dynamic>))
          .toList(),
      timestamp: DateTime.parse(map['timestamp'] as String),
      deviceId: map['deviceId'] as String,
      version: map['version'] as int? ?? 1,
    );
  }

  String toJson() => json.encode(toMap());

  factory NoteDelta.fromJson(String source) =>
      NoteDelta.fromMap(json.decode(source) as Map<String, dynamic>);

  String getContent() {
    final buffer = StringBuffer();
    for (final op in operations) {
      if (op.type == DeltaOperationType.insert) {
        buffer.write(op.insert);
      }
    }
    return buffer.toString();
  }

  NoteDelta applyDelta(NoteDelta other) {
    final newOps = List<DeltaOperation>.from(operations);
    
    int currentIndex = 0;
    for (final op in other.operations) {
      switch (op.type) {
        case DeltaOperationType.insert:
          newOps.insert(currentIndex, op);
          currentIndex++;
          break;
        case DeltaOperationType.delete:
          if (currentIndex < newOps.length) {
            newOps.removeRange(currentIndex, currentIndex + (op.delete ?? 1));
          }
          break;
        case DeltaOperationType.retain:
          currentIndex += op.length ?? 0;
          break;
        case DeltaOperationType.format:
          if (currentIndex < newOps.length && op.attributes != null) {
            final targetOp = newOps[currentIndex];
            if (targetOp.type == DeltaOperationType.insert) {
              final newAttrs = Map<String, dynamic>.from(targetOp.attributes ?? {});
              newAttrs.addAll(op.attributes!);
              newOps[currentIndex] = DeltaOperation(
                type: DeltaOperationType.insert,
                insert: targetOp.insert,
                attributes: newAttrs,
              );
            }
          }
          currentIndex += op.length ?? 0;
          break;
      }
    }

    return NoteDelta(
      id: id,
      operations: newOps,
      timestamp: DateTime.now(),
      deviceId: other.deviceId,
      version: version + 1,
    );
  }
}

class DeltaRenderer {
  static Map<String, dynamic> _parseColor(String? colorStr) {
    if (colorStr == null) return {'color': null, 'background': null};
    
    final parts = colorStr.split(',');
    return {
      'color': parts.isNotEmpty ? parts[0] : null,
      'background': parts.length > 1 ? parts[1] : null,
    };
  }

  static List<RenderSegment> renderToSegments(NoteDelta delta) {
    final segments = <RenderSegment>[];
    int offset = 0;

    for (final op in delta.operations) {
      if (op.type == DeltaOperationType.insert && op.insert != null) {
        final attrs = op.attributes ?? {};
        final colorInfo = _parseColor(attrs['color'] as String?);
        
        segments.add(RenderSegment(
          text: op.insert!,
          start: offset,
          end: offset + op.insert!.length,
          isBold: attrs['bold'] as bool? ?? false,
          isItalic: attrs['italic'] as bool? ?? false,
          isUnderline: attrs['underline'] as bool? ?? false,
          textColor: colorInfo['color'] as String?,
          backgroundColor: colorInfo['background'] as String?,
          highlightColor: attrs['highlight'] as String?,
        ));
        offset += op.insert!.length;
      }
    }

    return segments;
  }

  static String renderToHtml(NoteDelta delta) {
    final buffer = StringBuffer();

    for (final op in delta.operations) {
      if (op.type == DeltaOperationType.insert && op.insert != null) {
        final attrs = op.attributes ?? {};
        String text = _escapeHtml(op.insert!);
        String openingTags = '';
        String closingTags = '';

        if (attrs['bold'] == true) {
          openingTags += '<strong>';
          closingTags = '</strong>' + closingTags;
        }
        if (attrs['italic'] == true) {
          openingTags += '<em>';
          closingTags = '</em>' + closingTags;
        }
        if (attrs['underline'] == true) {
          openingTags += '<u>';
          closingTags = '</u>' + closingTags;
        }
        if (attrs['highlight'] != null) {
          openingTags += '<span style="background-color: ${attrs['highlight']}">';
          closingTags = '</span>' + closingTags;
        }

        buffer.write('$openingTags$text$closingTags');
      }
    }

    return buffer.toString();
  }

  static String renderToMarkdown(NoteDelta delta) {
    final buffer = StringBuffer();

    for (final op in delta.operations) {
      if (op.type == DeltaOperationType.insert && op.insert != null) {
        final attrs = op.attributes ?? {};
        String text = op.insert!;

        if (attrs['bold'] == true) {
          text = '**$text**';
        }
        if (attrs['italic'] == true) {
          text = '*$text*';
        }
        if (attrs['underline'] == true) {
          text = '__${text}__';
        }

        buffer.write(text);
      }
    }

    return buffer.toString();
  }

  static String _escapeHtml(String text) {
    return text
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#039;');
  }
}

class RenderSegment {
  final String text;
  final int start;
  final int end;
  final bool isBold;
  final bool isItalic;
  final bool isUnderline;
  final String? textColor;
  final String? backgroundColor;
  final String? highlightColor;

  RenderSegment({
    required this.text,
    required this.start,
    required this.end,
    this.isBold = false,
    this.isItalic = false,
    this.isUnderline = false,
    this.textColor,
    this.backgroundColor,
    this.highlightColor,
  });
}
