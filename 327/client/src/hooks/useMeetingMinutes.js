import { useState, useCallback, useEffect } from 'react';
import useSocket from './useSocket';
import useMeetingStore from '../store/useMeetingStore';

const useMeetingMinutes = () => {
  const { socket, connected } = useSocket();
  const { roomId } = useMeetingStore();

  const [isGenerating, setIsGenerating] = useState(false);
  const [currentMinutes, setCurrentMinutes] = useState(null);
  const [minutesStats, setMinutesStats] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!socket) return;

    const handleMinutesUpdated = ({ summary }) => {
      setCurrentMinutes(summary);
      setIsGenerating(false);
      setError(null);
    };

    const handleMeetingEnded = ({ minutes }) => {
      if (minutes) {
        setCurrentMinutes(minutes);
      }
    };

    socket.on('minutes-updated', handleMinutesUpdated);
    socket.on('meeting-ended', handleMeetingEnded);

    return () => {
      socket.off('minutes-updated', handleMinutesUpdated);
      socket.off('meeting-ended', handleMeetingEnded);
    };
  }, [socket]);

  const generateMinutes = useCallback(async () => {
    if (!connected || !socket || !roomId) {
      return { success: false, error: 'Not connected' };
    }

    setIsGenerating(true);
    setError(null);

    return new Promise((resolve) => {
      socket.emit('generate-minutes', { roomId }, (result) => {
        if (result.success) {
          setCurrentMinutes(result.summary);
        } else {
          setError(result.error);
        }
        setIsGenerating(false);
        resolve(result);
      });
    });
  }, [connected, socket, roomId]);

  const getMinutesStats = useCallback(async () => {
    if (!connected || !socket || !roomId) return null;

    return new Promise((resolve) => {
      socket.emit('get-minutes-stats', { roomId }, (result) => {
        if (result.success) {
          setMinutesStats(result.stats);
        }
        resolve(result.success ? result.stats : null);
      });
    });
  }, [connected, socket, roomId]);

  const endMeeting = useCallback(async () => {
    if (!connected || !socket || !roomId) {
      return { success: false, error: 'Not connected' };
    }

    setIsGenerating(true);

    return new Promise((resolve) => {
      socket.emit('end-meeting', { roomId }, (result) => {
        if (result.success && result.minutes) {
          setCurrentMinutes(result.minutes);
        }
        setIsGenerating(false);
        resolve(result);
      });
    });
  }, [connected, socket, roomId]);

  const listMinutes = useCallback(async () => {
    try {
      const response = await fetch('http://localhost:3001/api/minutes');
      const data = await response.json();
      return data.minutes || [];
    } catch (error) {
      console.error('Failed to list minutes:', error);
      return [];
    }
  }, []);

  const getMinutes = useCallback(async (filename) => {
    try {
      const response = await fetch(`http://localhost:3001/api/minutes/${filename}`);
      if (!response.ok) return null;
      return await response.json();
    } catch (error) {
      console.error('Failed to get minutes:', error);
      return null;
    }
  }, []);

  const downloadMinutes = useCallback((filename) => {
    const url = `http://localhost:3001/api/minutes/${filename}/download`;
    const a = document.createElement('a');
    a.href = url;
    a.download = filename.replace('.json', '.md');
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  }, []);

  const deleteMinutes = useCallback(async (filename) => {
    try {
      const response = await fetch(`http://localhost:3001/api/minutes/${filename}`, {
        method: 'DELETE'
      });
      return response.ok;
    } catch (error) {
      console.error('Failed to delete minutes:', error);
      return false;
    }
  }, []);

  const exportMinutesAsMarkdown = useCallback((summary) => {
    if (!summary) return '';

    let markdown = `# ${summary.title || '会议纪要'}\n\n`;
    
    if (summary.overallSummary) {
      markdown += `## 会议概述\n\n${summary.overallSummary}\n\n`;
    }

    if (summary.keyPoints?.length > 0) {
      markdown += `## 核心讨论要点\n\n`;
      summary.keyPoints.forEach((point, i) => {
        markdown += `${i + 1}. ${point}\n`;
      });
      markdown += `\n`;
    }

    if (summary.decisions?.length > 0) {
      markdown += `## 会议决议\n\n`;
      summary.decisions.forEach((decision, i) => {
        markdown += `${i + 1}. ${decision}\n`;
      });
      markdown += `\n`;
    }

    if (summary.actionItems?.length > 0) {
      markdown += `## 待办事项\n\n`;
      markdown += `| 序号 | 内容 | 负责人 | 优先级 |\n`;
      markdown += `| --- | --- | --- | --- |\n`;
      summary.actionItems.forEach((item, i) => {
        const priorityText = { high: '高', medium: '中', low: '低' }[item.priority] || '中';
        markdown += `| ${i + 1} | ${item.content} | ${item.assignee} | ${priorityText} |\n`;
      });
      markdown += `\n`;
    }

    if (summary.nextMeeting) {
      markdown += `## 下次会议建议\n\n${summary.nextMeeting}\n\n`;
    }

    if (summary.autoGenerated) {
      markdown += `> 本纪要由AI自动生成，仅供参考\n`;
    }

    return markdown;
  }, []);

  const copyToClipboard = useCallback(async (summary) => {
    const markdown = exportMinutesAsMarkdown(summary);
    try {
      await navigator.clipboard.writeText(markdown);
      return true;
    } catch {
      const textarea = document.createElement('textarea');
      textarea.value = markdown;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      return true;
    }
  }, [exportMinutesAsMarkdown]);

  const reset = useCallback(() => {
    setCurrentMinutes(null);
    setMinutesStats(null);
    setError(null);
    setIsGenerating(false);
  }, []);

  return {
    generateMinutes,
    getMinutesStats,
    endMeeting,
    listMinutes,
    getMinutes,
    downloadMinutes,
    deleteMinutes,
    exportMinutesAsMarkdown,
    copyToClipboard,
    reset,
    isGenerating,
    currentMinutes,
    minutesStats,
    error
  };
};

export default useMeetingMinutes;
