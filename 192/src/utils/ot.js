import { Transforms, Range, Editor, Point, Node, Path } from 'slate';
import { v4 as uuidv4 } from 'uuid';

const LIST_TYPES = ['bulleted-list', 'numbered-list'];

export function slateOpsToDelta(editor, operations) {
  const delta = [];
  let currentPath = [0];
  let currentOffset = 0;

  for (const op of operations) {
    switch (op.type) {
      case 'insert_text': {
        const pathInfo = getPathPosition(editor, op.path);
        const targetOffset = pathInfo.totalOffset + op.offset;
        
        if (targetOffset > currentOffset) {
          delta.push(targetOffset - currentOffset);
        }
        delta.push({ insert: op.text });
        currentOffset = targetOffset + op.text.length;
        currentPath = op.path;
        break;
      }
      case 'remove_text': {
        const pathInfo = getPathPosition(editor, op.path);
        const targetOffset = pathInfo.totalOffset + op.offset;
        
        if (targetOffset > currentOffset) {
          delta.push(targetOffset - currentOffset);
        }
        delta.push({ delete: op.text.length });
        currentOffset = targetOffset;
        currentPath = op.path;
        break;
      }
      case 'split_node': {
        const pathInfo = getPathPosition(editor, op.path);
        const targetOffset = pathInfo.totalOffset + op.position;
        
        if (targetOffset > currentOffset) {
          delta.push(targetOffset - currentOffset);
        }
        delta.push({ insert: '\n', attributes: { blockType: 'paragraph' } });
        currentOffset = targetOffset + 1;
        currentPath = op.path;
        break;
      }
      case 'merge_node': {
        const pathInfo = getPathPosition(editor, op.path);
        const targetOffset = pathInfo.totalOffset;
        
        if (targetOffset > currentOffset) {
          delta.push(targetOffset - currentOffset);
        }
        delta.push({ delete: 1 });
        currentOffset = targetOffset;
        currentPath = op.path;
        break;
      }
      case 'set_node': {
        if (op.newProperties && (op.newProperties.type || op.newProperties.align)) {
          const pathInfo = getPathPosition(editor, op.path);
          const blockStart = pathInfo.blockStartOffset;
          const blockEnd = pathInfo.blockEndOffset;
          
          if (blockStart > currentOffset) {
            delta.push(blockStart - currentOffset);
          }
          
          const attributes = {};
          if (op.newProperties.type) attributes.blockType = op.newProperties.type;
          if (op.newProperties.align) attributes.align = op.newProperties.align;
          
          delta.push({ retain: blockEnd - blockStart, attributes });
          currentOffset = blockEnd;
        }
        break;
      }
      case 'wrap_node': {
        if (op.newProperties && LIST_TYPES.includes(op.newProperties.type)) {
          const pathInfo = getPathPosition(editor, op.path);
          delta.push({
            wrapList: {
              type: op.newProperties.type,
              at: pathInfo.blockStartOffset,
              length: pathInfo.blockEndOffset - pathInfo.blockStartOffset
            }
          });
        }
        break;
      }
      case 'unwrap_node': {
        const pathInfo = getPathPosition(editor, op.path);
        delta.push({
          unwrapList: {
            at: pathInfo.blockStartOffset,
            length: pathInfo.blockEndOffset - pathInfo.blockStartOffset
          }
        });
        break;
      }
      case 'set_selection': {
        break;
      }
    }
  }

  return delta;
}

export function applyDeltaToEditor(editor, delta) {
  Editor.withoutNormalizing(editor, () => {
    let currentOffset = 0;

    for (const component of delta) {
      if (typeof component === 'number') {
        currentOffset += component;
      } else if (component.insert !== undefined) {
        const insertText = component.insert;
        const point = findPointAtOffset(editor, currentOffset);
        if (point) {
          if (insertText === '\n') {
            const blockType = component.attributes?.blockType || 'paragraph';
            Transforms.splitNodes(editor, { at: point });
            if (blockType !== 'paragraph') {
              Transforms.setNodes(editor, { type: blockType }, { match: n => Editor.isBlock(editor, n) });
            }
          } else {
            Transforms.insertText(editor, insertText, { at: point });
          }
        }
        currentOffset += insertText.length;
      } else if (component.delete !== undefined) {
        const startPoint = findPointAtOffset(editor, currentOffset);
        const endPoint = findPointAtOffset(editor, currentOffset + component.delete);
        if (startPoint && endPoint) {
          Transforms.delete(editor, {
            at: { anchor: startPoint, focus: endPoint },
          });
        }
      } else if (component.retain !== undefined && component.attributes) {
        const startPoint = findPointAtOffset(editor, currentOffset);
        if (startPoint) {
          const [block] = Editor.node(editor, startPoint.path.slice(0, -1));
          if (block && component.attributes.blockType) {
            Transforms.setNodes(
              editor,
              { type: component.attributes.blockType },
              { at: startPoint.path.slice(0, -1) }
            );
          }
        }
        currentOffset += component.retain;
      } else if (component.retain !== undefined) {
        currentOffset += component.retain;
      } else if (component.wrapList) {
        const point = findPointAtOffset(editor, component.wrapList.at);
        if (point) {
          Transforms.wrapNodes(
            editor,
            { type: component.wrapList.type, children: [] },
            { at: point.path.slice(0, -1) }
          );
          Transforms.wrapNodes(
            editor,
            { type: 'list-item', children: [] },
            { at: point.path.slice(0, -1) }
          );
        }
      } else if (component.unwrapList) {
        const point = findPointAtOffset(editor, component.unwrapList.at);
        if (point) {
          Transforms.unwrapNodes(editor, {
            at: point.path.slice(0, -1),
            match: n => n.type === 'list-item'
          });
          Transforms.unwrapNodes(editor, {
            at: point.path.slice(0, -2),
            match: n => LIST_TYPES.includes(n.type)
          });
        }
      }
    }
  });
}

function getPathPosition(editor, path) {
  let totalOffset = 0;
  let blockStartOffset = 0;
  let blockEndOffset = 0;
  let foundBlock = false;
  let blockPath = path.slice(0, -1);

  const nodes = Editor.nodes(editor, { at: [] });

  for (const [node, nodePath] of nodes) {
    if (node.text) {
      const currentBlockPath = nodePath.slice(0, -1);
      const isTargetBlock = Path.equals(currentBlockPath, blockPath);
      
      if (isTargetBlock && !foundBlock) {
        blockStartOffset = totalOffset;
        foundBlock = true;
      }
      
      if (Path.equals(nodePath, path)) {
        return {
          totalOffset,
          blockStartOffset,
          blockEndOffset: 0,
        };
      }
      
      totalOffset += node.text.length;
      
      if (isTargetBlock) {
        blockEndOffset = totalOffset;
      }
    }
    
    if (node.type === 'paragraph' || LIST_TYPES.includes(node.type) || node.type === 'list-item') {
      if (foundBlock && Path.equals(nodePath, blockPath)) {
        totalOffset += 1;
        blockEndOffset = totalOffset;
      } else if (!foundBlock) {
        totalOffset += 1;
      }
    }
  }

  return { totalOffset, blockStartOffset, blockEndOffset };
}

function findPointAtOffset(editor, targetOffset) {
  let currentOffset = 0;
  const nodes = Editor.nodes(editor, { at: [] });

  for (const [node, path] of nodes) {
    if (node.text) {
      if (currentOffset + node.text.length >= targetOffset) {
        return { path, offset: targetOffset - currentOffset };
      }
      currentOffset += node.text.length;
    }
    
    if (Editor.isBlock(editor, node)) {
      if (currentOffset === targetOffset) {
        const firstChildPath = [...path, 0];
        return { path: firstChildPath, offset: 0 };
      }
      currentOffset += 1;
    }
  }

  const lastNode = Array.from(Node.nodes(editor, { at: [] })).pop();
  if (lastNode) {
    const [node, path] = lastNode;
    if (node.text) {
      return { path, offset: node.text.length };
    }
  }

  return null;
}

export function transformCursorPosition(position, delta) {
  let pos = position;
  let deltaPos = 0;

  for (const component of delta) {
    if (typeof component === 'number') {
      deltaPos += component;
    } else if (component.insert !== undefined) {
      if (deltaPos <= pos) {
        pos += component.insert.length;
      }
      deltaPos += component.insert.length;
    } else if (component.delete !== undefined) {
      if (deltaPos + component.delete <= pos) {
        pos -= component.delete;
      } else if (deltaPos < pos) {
        pos = deltaPos;
      }
    } else if (component.retain !== undefined) {
      deltaPos += component.retain;
    }
  }

  return Math.max(0, pos);
}

export function slateRangeToPresence(editor, range) {
  if (!range) return null;

  const anchorOffset = getOffsetFromPoint(editor, range.anchor);
  const focusOffset = getOffsetFromPoint(editor, range.focus);

  return {
    index: Math.min(anchorOffset, focusOffset),
    length: Math.abs(focusOffset - anchorOffset),
    anchorPath: range.anchor.path,
    focusPath: range.focus.path,
    anchorOffset: range.anchor.offset,
    focusOffset: range.focus.offset,
  };
}

function getOffsetFromPoint(editor, point) {
  let offset = 0;
  const nodes = Editor.nodes(editor, { at: [] });

  for (const [node, path] of nodes) {
    if (node.text) {
      if (Path.equals(path, point.path)) {
        return offset + point.offset;
      }
      offset += node.text.length;
    }
    if (Editor.isBlock(editor, node)) {
      offset += 1;
    }
  }

  return offset;
}

export function presenceToSlateRange(editor, presence) {
  if (!presence) return null;

  let anchor, focus;

  if (presence.anchorPath && presence.focusPath) {
    try {
      anchor = { path: presence.anchorPath, offset: presence.anchorOffset };
      focus = { path: presence.focusPath, offset: presence.focusOffset };
      
      const anchorNode = Node.get(editor, anchor.path.slice(0, -1));
      const focusNode = Node.get(editor, focus.path.slice(0, -1));
      
      if (anchorNode && focusNode) {
        return { anchor, focus };
      }
    } catch (e) {
      // 路径无效，回退到偏移量方式
    }
  }

  const { index, length } = presence;
  anchor = findPointAtOffset(editor, index);
  focus = findPointAtOffset(editor, index + length);

  if (anchor && focus) {
    return { anchor, focus };
  }

  return null;
}

export function generateCommentId() {
  return uuidv4();
}

export function getSelectedText(editor, range) {
  if (!range) return '';
  const fragment = Editor.fragment(editor, range);
  return fragment.map(n => n.children?.map(c => c.text).join('') || '').join('\n');
}

export function transformOpAgainstOp(op1, op2) {
  const result = [];
  let pos1 = 0;
  let pos2 = 0;

  const iter1 = op1[Symbol.iterator]();
  const iter2 = op2[Symbol.iterator]();
  
  let curr1 = iter1.next();
  let curr2 = iter2.next();

  while (!curr1.done && !curr2.done) {
    const comp1 = curr1.value;
    const comp2 = curr2.value;

    const len1 = getComponentLength(comp1);
    const len2 = getComponentLength(comp2);

    if (typeof comp1 === 'number' && typeof comp2 === 'number') {
      if (len1 <= len2) {
        result.push(comp1);
        pos1 += len1;
        pos2 += len1;
        curr1 = iter1.next();
        if (len1 === len2) {
          curr2 = iter2.next();
        }
      } else {
        result.push(len2);
        pos1 += len2;
        pos2 += len2;
        curr2 = iter2.next();
      }
    } else if (comp1.insert !== undefined) {
      result.push(comp1);
      pos1 += comp1.insert.length;
      curr1 = iter1.next();
    } else if (comp2.insert !== undefined) {
      pos2 += comp2.insert.length;
      curr2 = iter2.next();
    } else if (comp1.delete !== undefined && comp2.delete !== undefined) {
      if (len1 <= len2) {
        pos1 += len1;
        pos2 += len1;
        curr1 = iter1.next();
        if (len1 === len2) {
          curr2 = iter2.next();
        }
      } else {
        pos1 += len2;
        pos2 += len2;
        curr2 = iter2.next();
      }
    } else if (comp1.delete !== undefined) {
      if (len1 <= len2) {
        result.push(comp1);
        pos1 += len1;
        curr1 = iter1.next();
      } else {
        result.push({ delete: len2 });
        pos1 += len2;
      }
    } else if (comp2.delete !== undefined) {
      pos2 += len2;
      curr2 = iter2.next();
    } else {
      curr1 = iter1.next();
      curr2 = iter2.next();
    }
  }

  while (!curr1.done) {
    result.push(curr1.value);
    curr1 = iter1.next();
  }

  return result;
}

function getComponentLength(component) {
  if (typeof component === 'number') return component;
  if (component.insert) return component.insert.length;
  if (component.delete) return component.delete;
  if (component.retain) return component.retain;
  return 0;
}

export function invertDelta(delta, contentLength) {
  const inverted = [];
  let currentPos = 0;

  for (const component of delta) {
    if (typeof component === 'number') {
      inverted.push(component);
      currentPos += component;
    } else if (component.insert !== undefined) {
      inverted.push({ delete: component.insert.length });
    } else if (component.delete !== undefined) {
      inverted.push({ insert: 'x'.repeat(component.delete) });
      currentPos += component.delete;
    } else if (component.retain !== undefined) {
      inverted.push(component);
      currentPos += component.retain;
    }
  }

  if (currentPos < contentLength) {
    inverted.push(contentLength - currentPos);
  }

  return inverted;
}

export function applyDeltaToContent(content, delta) {
  let result = '';
  let pos = 0;

  for (const component of delta) {
    if (typeof component === 'number') {
      result += content.slice(pos, pos + component);
      pos += component;
    } else if (component.insert !== undefined) {
      result += component.insert;
    } else if (component.delete !== undefined) {
      pos += component.delete;
    } else if (component.retain !== undefined) {
      result += content.slice(pos, pos + component.retain);
      pos += component.retain;
    }
  }

  if (pos < content.length) {
    result += content.slice(pos);
  }

  return result;
}
