import React, { useState, useEffect, useCallback, useRef, forwardRef, useImperativeHandle } from 'react';
import { createEditor, Transforms, Editor } from 'slate';
import { Slate, Editable, withReact, ReactEditor } from 'slate-react';
import { withHistory } from 'slate-history';
import isHotkey from 'is-hotkey';

import { Element, Leaf } from './EditorComponents';
import { withMarkdown } from '../plugins/withMarkdown';
import { slateOpsToDelta, applyDeltaToEditor, slateRangeToPresence, presenceToSlateRange } from '../utils/ot';
import collaborationClient from '../utils/collaborationClient';

const HOTKEYS = {
  'mod+b': 'bold',
  'mod+i': 'italic',
  'mod+u': 'underline',
  'mod+`': 'code',
};

const initialValue = [
  {
    type: 'paragraph',
    children: [
      { text: '欢迎使用协同富文本编辑器' },
    ],
  },
];

export const CollaborativeEditor = forwardRef(({
  onUsersChange,
  onCommentAdd,
  onCommentResolve,
  onOplogUpdate,
  onValueChange,
}, ref) => {
  const [value, setValue] = useState(initialValue);
  const [remoteCursors, setRemoteCursors] = useState({});
  const [isConnected, setIsConnected] = useState(false);
  const editorRef = useRef(null);
  const applyRemoteOpRef = useRef(false);

  const editor = useCallback(() => {
    let e = createEditor();
    e = withReact(e);
    e = withHistory(e);
    e = withMarkdown(e);
    return e;
  }, [])();

  useImperativeHandle(ref, () => ({
    editor,
    getValue: () => value,
  }), [editor, value]);

  useEffect(() => {
    collaborationClient.connect();

    const handleInit = (data) => {
      setIsConnected(true);
      const slateValue = deltaToSlateValue(data.content);
      setValue(slateValue);
      collaborationClient.getOplog();
    };

    const handleOp = (data) => {
      applyRemoteOpRef.current = true;
      try {
        applyDeltaToEditor(editor, data.op);
      } catch (e) {
        console.error('Error applying remote op:', e);
      }
      applyRemoteOpRef.current = false;
    };

    const handlePresence = (data) => {
      const range = presenceToSlateRange(editor, data.range);
      if (range) {
        setRemoteCursors(prev => ({
          ...prev,
          [data.clientId]: {
            range,
            color: getClientColor(data.clientId),
          },
        }));
      }
    };

    const handlePresenceBatch = (data) => {
      const newCursors = {};
      for (const [clientId, range] of Object.entries(data.presence)) {
        const slateRange = presenceToSlateRange(editor, range);
        if (slateRange) {
          newCursors[clientId] = {
            range: slateRange,
            color: getClientColor(clientId),
          };
        }
      }
      setRemoteCursors(prev => ({ ...prev, ...newCursors));
    };

    const handleUsers = (data) => {
      onUsersChange && onUsersChange(data.users);
      setRemoteCursors(prev => {
        const newCursors = { ...prev };
        Object.keys(newCursors).forEach(id => {
          if (!data.users.includes(id)) {
            delete newCursors[id];
          }
        });
        return newCursors;
      });
    };

    const handleComment = (data) => {
      onCommentAdd && onCommentAdd(data.comment);
    };

    const handleResolveComment = (data) => {
      onCommentResolve && onCommentResolve(data.commentId);
    };

    const handleOplog = (data) => {
      onOplogUpdate && onOplogUpdate(data.entries);
    };

    const handleConnected = () => setIsConnected(true);
    const handleDisconnected = () => setIsConnected(false);

    collaborationClient.on('init', handleInit);
    collaborationClient.on('op', handleOp);
    collaborationClient.on('presence', handlePresence);
    collaborationClient.on('presenceBatch', handlePresenceBatch);
    collaborationClient.on('users', handleUsers);
    collaborationClient.on('comment', handleComment);
    collaborationClient.on('resolveComment', handleResolveComment);
    collaborationClient.on('oplog', handleOplog);
    collaborationClient.on('connected', handleConnected);
    collaborationClient.on('disconnected', handleDisconnected);

    return () => {
      collaborationClient.off('init', handleInit);
      collaborationClient.off('op', handleOp);
      collaborationClient.off('presence', handlePresence);
      collaborationClient.off('presenceBatch', handlePresenceBatch);
      collaborationClient.off('users', handleUsers);
      collaborationClient.off('comment', handleComment);
      collaborationClient.off('resolveComment', handleResolveComment);
      collaborationClient.off('oplog', handleOplog);
      collaborationClient.off('connected', handleConnected);
      collaborationClient.off('disconnected', handleDisconnected);
      collaborationClient.disconnect();
    };
  }, [editor, onUsersChange, onCommentAdd, onCommentResolve, onOplogUpdate, onValueChange]);

  const onChange = (newValue) => {
    setValue(newValue);
    onValueChange && onValueChange(newValue);

    if (!applyRemoteOpRef.current && editor.operations.length > 0) {
      const nonSelectionOps = editor.operations.filter(
        op => op.type !== 'set_selection'
      );

      if (nonSelectionOps.length > 0) {
        const delta = slateOpsToDelta(editor, nonSelectionOps);
        if (delta.length > 0) {
          collaborationClient.submitOp(delta);
        }
      }
    }
  };

  const onSelectionChange = () => {
    if (editor.selection && !applyRemoteOpRef.current) {
      const presence = slateRangeToPresence(editor, editor.selection);
      if (presence) {
        collaborationClient.submitPresence(presence);
      }
    }
  };

  const onKeyDown = (event) => {
    for (const hotkey in HOTKEYS) {
      if (isHotkey(hotkey, event)) {
        event.preventDefault();
        const mark = HOTKEYS[hotkey];
        const isActive = Editor.marks(editor)?.[mark];
        Editor.addMark(editor, mark, !isActive);
      }
    }
  };

  const renderLeaf = (props) => <Leaf {...props} />;
  const renderElement = (props) => <Element {...props} />;

  return (
    <div className="editor-container" ref={editorRef}>
      <div className="editor-toolbar">
        <div className={`connection-status ${isConnected ? 'connected' : 'disconnected'}`}>
          {isConnected ? '已连接' : '连接中断'}
        </div>
        <div className="toolbar-buttons">
          <button
            onMouseDown={(e) => {
              e.preventDefault();
              const isActive = Editor.marks(editor)?.bold;
              Editor.addMark(editor, 'bold', !isActive);
            }}
            className="toolbar-btn"
          >
            <strong>B</strong>
          </button>
          <button
            onMouseDown={(e) => {
              e.preventDefault();
              const isActive = Editor.marks(editor)?.italic;
              Editor.addMark(editor, 'italic', !isActive);
            }}
            className="toolbar-btn"
          >
            <em>I</em>
          </button>
          <button
            onMouseDown={(e) => {
              e.preventDefault();
              const isActive = Editor.marks(editor)?.underline;
              Editor.addMark(editor, 'underline', !isActive);
            }}
            className="toolbar-btn"
          >
            <u>U</u>
          </button>
          <button
            onMouseDown={(e) => {
              e.preventDefault();
              const isActive = Editor.marks(editor)?.code;
              Editor.addMark(editor, 'code', !isActive);
            }}
            className="toolbar-btn"
          >
            {'</>'}
          </button>
          <div className="toolbar-divider" />
          <button
            onMouseDown={(e) => {
              e.preventDefault();
              Transforms.setNodes(editor, { type: 'heading-one' }, { match: n => Editor.isBlock(editor, n) });
            }}
            className="toolbar-btn"
          >
            H1
          </button>
          <button
            onMouseDown={(e) => {
              e.preventDefault();
              Transforms.setNodes(editor, { type: 'heading-two' }, { match: n => Editor.isBlock(editor, n) });
            }}
            className="toolbar-btn"
          >
            H2
          </button>
          <button
            onMouseDown={(e) => {
              e.preventDefault();
              Transforms.setNodes(editor, { type: 'paragraph' }, { match: n => Editor.isBlock(editor, n) });
            }}
            className="toolbar-btn"
          >
            正文
          </button>
          <button
            onMouseDown={(e) => {
              e.preventDefault();
              Transforms.setNodes(editor, { type: 'bulleted-list' }, { match: n => Editor.isBlock(editor, n) });
            }}
            className="toolbar-btn"
          >
            列表
          </button>
          <button
            onMouseDown={(e) => {
              e.preventDefault();
              Transforms.setNodes(editor, { type: 'block-quote' }, { match: n => Editor.isBlock(editor, n) });
            }}
            className="toolbar-btn"
          >
            引用
          </button>
        </div>
      </div>
      <div className="editor-wrapper">
        <Slate editor={editor} initialValue={value} onChange={onChange}>
          <Editable
            renderLeaf={renderLeaf}
            renderElement={renderElement}
            onKeyDown={onKeyDown}
            onBlur={onSelectionChange}
            onFocus={onSelectionChange}
            onSelect={onSelectionChange}
            placeholder="开始输入内容..."
            className="slate-editor"
            spellCheck={false}
          />
          {Object.entries(remoteCursors).map(([clientId, cursor]) => (
            cursor.range && (
              <RemoteCursor
                key={clientId}
                clientId={clientId}
                range={cursor.range}
                color={cursor.color}
                editor={editor}
                containerRef={editorRef}
              />
            )
          ))}
        </Slate>
      </div>
    </div>
  );
};

const RemoteCursor = ({ clientId, range, color, editor, containerRef }) => {
  const [position, setPosition] = useState(null);

  useEffect(() => {
    const updatePosition = () => {
      try {
        const domRange = ReactEditor.toDOMRange(editor, range);
        const rect = domRange.getBoundingClientRect();
        const containerRect = containerRef.current?.getBoundingClientRect();
        if (containerRect) {
          setPosition({
            top: rect.top - containerRect.top,
            left: rect.left - containerRect.left,
            height: rect.height,
          });
        }
      } catch (e) {
          // 忽略范围不存在的情况
        }
      };

    updatePosition();
    const interval = setInterval(updatePosition, 100);
    window.addEventListener('resize', updatePosition);
    return () => {
      clearInterval(interval);
      window.removeEventListener('resize', updatePosition);
    };
  }, [range, editor, containerRef]);

  if (!position) return null;

  return (
    <div
      className="remote-cursor"
      style={{
        top: `${position.top}px`,
        left: `${position.left}px`,
        height: `${position.height}px`,
        borderColor: color,
      }}
    >
      <div className="remote-cursor-label" style={{ backgroundColor: color }}>
        {clientId.slice(0, 6)}
      </div>
    </div>
  );
};

function deltaToSlateValue(delta) {
  if (!delta || !Array.isArray(delta)) {
    return initialValue;
  }

  const paragraphs = [];
  let currentParagraph = { type: 'paragraph', children: [{ text: '' }] };

  for (const item of delta) {
    if (typeof item === 'object' && item.insert) {
      const lines = item.insert.split('\n');
      const attrs = item.attributes || {};

      lines.forEach((line, index) => {
        if (index > 0) {
          paragraphs.push(currentParagraph);
          currentParagraph = { type: 'paragraph', children: [] };
        }

        if (line.length > 0) {
          const textNode = { text: line };
          if (attrs.bold) textNode.bold = true;
          if (attrs.italic) textNode.italic = true;
          if (attrs.underline) textNode.underline = true;
          currentParagraph.children.push(textNode);
        } else {
          currentParagraph.children.push({ text: line, ...attrs });
        }
      });
    }
  }

  paragraphs.push(currentParagraph);
  return paragraphs.length > 0 ? paragraphs : initialValue;
}

function getClientColor(clientId) {
  const colors = [
    '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4',
    '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F',
    '#BB8FCE', '#85C1E9',
  ];
  let hash = 0;
  for (let i = 0; i < clientId.length; i++) {
    hash = clientId.charCodeAt(i) + ((hash << 5) - hash);
  }
  return colors[Math.abs(hash) % colors.length];
}
