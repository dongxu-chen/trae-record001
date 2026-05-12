import { useEffect, useRef } from 'react';

function Output({ output, error, isRunning }) {
  const outputRef = useRef(null);

  useEffect(() => {
    if (outputRef.current) {
      outputRef.current.scrollTop = outputRef.current.scrollHeight;
    }
  }, [output, error, isRunning]);

  const getLogStyle = (level) => {
    switch (level) {
      case 'error':
        return 'log-error';
      case 'warn':
        return 'log-warn';
      case 'info':
        return 'log-info';
      default:
        return 'log-default';
    }
  };

  const formatMessage = (message) => {
    return message.split('\n').map((line, index) => (
      <span key={index}>
        {line}
        {index < message.split('\n').length - 1 && <br />}
      </span>
    ));
  };

  return (
    <div className="output-container" ref={outputRef}>
      {isRunning && (
        <div className="output-message log-info">
          <span className="log-prefix">▶</span>
          <span className="log-content">代码运行中...</span>
        </div>
      )}

      {output.map((item, index) => (
        <div key={index} className={`output-message ${getLogStyle(item.level)}`}>
          <span className="log-prefix">
            {item.level === 'error' ? '✖' : item.level === 'warn' ? '⚠' : '›'}
          </span>
          <span className="log-content">{formatMessage(item.message)}</span>
        </div>
      ))}

      {error && (
        <div className="output-message log-error">
          <span className="log-prefix">✖</span>
          <span className="log-content">{formatMessage(error)}</span>
        </div>
      )}

      {!isRunning && output.length === 0 && !error && (
        <div className="output-empty">
          <span>点击「运行」按钮执行代码</span>
        </div>
      )}
    </div>
  );
}

export default Output;
