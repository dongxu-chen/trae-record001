import { Transforms, Range, Editor } from 'slate';

export const withMarkdown = (editor) => {
  const { insertText } = editor;

  editor.insertText = (text) => {
    const { selection } = editor;

    if (text === ' ' && selection) {
      const [start] = Range.edges(selection);
      const wordBefore = Editor.before(editor, start, { unit: 'word' });
      const before = wordBefore && Editor.before(editor, wordBefore);
      const beforeRange = before && Editor.range(editor, before, start);
      const beforeText = beforeRange && Editor.string(editor, beforeRange);
      const after = Editor.after(editor, start);
      const afterRange = Editor.range(editor, start, after);
      const afterText = Editor.string(editor, afterRange);
      const afterMatch = afterText.match(/^(\s|$)/);

      if (beforeText && afterMatch) {
        switch (beforeText) {
          case '#': {
            Transforms.delete(editor, { at: beforeRange });
            Transforms.setNodes(
              editor,
              { type: 'heading-one' },
              { match: n => Editor.isBlock(editor, n) }
            );
            return;
          }
          case '##': {
            Transforms.delete(editor, { at: beforeRange });
            Transforms.setNodes(
              editor,
              { type: 'heading-two' },
              { match: n => Editor.isBlock(editor, n) }
            );
            return;
          }
          case '###': {
            Transforms.delete(editor, { at: beforeRange });
            Transforms.setNodes(
              editor,
              { type: 'heading-three' },
              { match: n => Editor.isBlock(editor, n) }
            );
            return;
          }
          case '>': {
            Transforms.delete(editor, { at: beforeRange });
            Transforms.setNodes(
              editor,
              { type: 'block-quote' },
              { match: n => Editor.isBlock(editor, n) }
            );
            return;
          }
          case '```': {
            Transforms.delete(editor, { at: beforeRange });
            Transforms.setNodes(
              editor,
              { type: 'code-block' },
              { match: n => Editor.isBlock(editor, n) }
            );
            return;
          }
          case '-':
          case '*':
          case '+': {
            Transforms.delete(editor, { at: beforeRange });
            Transforms.setNodes(
              editor,
              { type: 'bulleted-list' },
              { match: n => Editor.isBlock(editor, n) }
            );
            Transforms.wrapNodes(
              editor,
              { type: 'list-item', children: [] },
              { match: n => Editor.isBlock(editor, n) }
            );
            return;
          }
          case '1.': {
            Transforms.delete(editor, { at: beforeRange });
            Transforms.setNodes(
              editor,
              { type: 'numbered-list' },
              { match: n => Editor.isBlock(editor, n) }
            );
            Transforms.wrapNodes(
              editor,
              { type: 'list-item', children: [] },
              { match: n => Editor.isBlock(editor, n) }
            );
            return;
          }
          case '---': {
            Transforms.delete(editor, { at: beforeRange });
            Transforms.insertNodes(editor, { type: 'thematic-break', children: [{ text: '' }] });
            return;
          }
        }
      }
    }

    const markdownFormats = {
      '**': 'bold',
      '__': 'bold',
      '*': 'italic',
      '_': 'italic',
      '~~': 'strikethrough',
      '`': 'code',
    };

    for (const [marker, format] of Object.entries(markdownFormats)) {
      if (text === marker[marker.length - 1] && selection) {
        const [start] = Range.edges(selection);
        const before = Editor.before(editor, start, { distance: marker.length });
        if (before) {
          const beforeRange = Editor.range(editor, before, start);
          const beforeText = Editor.string(editor, beforeRange);
          if (beforeText === marker) {
            Transforms.delete(editor, { at: beforeRange });
            editor.addMark(format, true);
            return;
          }
        }
      }
    }

    insertText(text);
  };

  return editor;
};
