import React from 'react';
import { useSlateStatic } from 'slate-react';

export const Leaf = ({ attributes, children, leaf }) => {
  if (leaf.bold) {
    children = <strong>{children}</strong>;
  }
  if (leaf.italic) {
    children = <em>{children}</em>;
  }
  if (leaf.underline) {
    children = <u>{children}</u>;
  }
  if (leaf.strikethrough) {
    children = <s>{children}</s>;
  }
  if (leaf.code) {
    children = <code className="inline-code">{children}</code>;
  }
  if (leaf.comment) {
    children = (
      <span className="comment-highlight" data-comment-id={leaf.commentId}>
        {children}
      </span>
    );
  }
  return <span {...attributes}>{children}</span>;
};

export const Element = ({ attributes, children, element }) => {
  const editor = useSlateStatic();
  
  const style = { textAlign: element.align };

  switch (element.type) {
    case 'block-quote':
      return (
        <blockquote style={style} {...attributes}>
          {children}
        </blockquote>
      );
    case 'bulleted-list':
      return (
        <ul style={style} {...attributes}>
          {children}
        </ul>
      );
    case 'heading-one':
      return (
        <h1 style={style} {...attributes}>
          {children}
        </h1>
      );
    case 'heading-two':
      return (
        <h2 style={style} {...attributes}>
          {children}
        </h2>
      );
    case 'heading-three':
      return (
        <h3 style={style} {...attributes}>
          {children}
        </h3>
      );
    case 'list-item':
      return (
        <li style={style} {...attributes}>
          {children}
        </li>
      );
    case 'numbered-list':
      return (
        <ol style={style} {...attributes}>
          {children}
        </ol>
      );
    case 'code-block':
      return (
        <pre style={style} {...attributes}>
          <code>{children}</code>
        </pre>
      );
    case 'thematic-break':
      return (
        <hr style={style} {...attributes}>
          {children}
        </hr>
      );
    case 'paragraph':
    default:
      return (
        <p style={style} {...attributes}>
          {children}
        </p>
      );
  }
};
