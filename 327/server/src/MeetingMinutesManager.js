import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { v4 as uuidv4 } from 'uuid';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const MINUTES_DIR = path.join(__dirname, '../meeting-minutes');

if (!fs.existsSync(MINUTES_DIR)) {
  fs.mkdirSync(MINUTES_DIR, { recursive: true });
}

class MeetingMinutesSession {
  constructor(roomId, participants = []) {
    this.roomId = roomId;
    this.minutesId = uuidv4();
    this.participants = new Map();
    this.messages = [];
    this.actionItems = [];
    this.decisions = [];
    this.topics = [];
    this.speakingTime = new Map();
    this.startTime = Date.now();
    this.endTime = null;
    this.summary = null;
    this.isGenerating = false;
    this.lastActivity = Date.now();

    participants.forEach(p => {
      this.participants.set(p.user?.id || p.id, p.user || p);
    });
  }

  addMessage(message) {
    this.messages.push({
      ...message,
      timestamp: message.timestamp || Date.now()
    });
    this.lastActivity = Date.now();

    const userId = message.userId;
    if (userId && this.participants.has(userId)) {
      const current = this.speakingTime.get(userId) || 0;
      this.speakingTime.set(userId, current + 1);
    }

    this._analyzeMessage(message);
  }

  _analyzeMessage(message) {
    const content = message.content?.toLowerCase() || '';
    const userId = message.userId;
    const userName = message.userName || '未知用户';

    const actionPatterns = [
      /(?:需要|应该|必须|要|计划|安排|负责|跟进)/,
      /(?:todo|action\s*item|待办|任务)/i,
      /(?:截止|deadline|完成时间|时间点)/i,
      /(?:@|提醒|找).+做/
    ];

    const decisionPatterns = [
      /(?:决定|同意|通过|确定|定下来|就这么|就按)/,
      /(?:一致同意|达成共识|结论是)/,
      /(?:决议|决策|方案)/
    ];

    const topicPatterns = [
      /(?:关于|讨论|议题|主题|我们来|说一下|谈谈)/,
      /^(?:关于|对于|针对)/,
      /(?:问题|方案|计划|进展|情况|汇报)/
    ];

    if (actionPatterns.some(p => p.test(content))) {
      this.actionItems.push({
        id: uuidv4(),
        content: message.content,
        assignee: this._extractAssignee(content, userName),
        createdBy: userId,
        createdAt: message.timestamp,
        status: 'pending',
        priority: this._extractPriority(content)
      });
    }

    if (decisionPatterns.some(p => p.test(content))) {
      this.decisions.push({
        id: uuidv4(),
        content: message.content,
        createdBy: userId,
        createdAt: message.timestamp
      });
    }

    if (topicPatterns.some(p => p.test(content)) && content.length > 5) {
      const topic = this._extractTopic(content);
      if (topic && !this.topics.some(t => 
        t.content.toLowerCase().includes(topic.toLowerCase()) ||
        topic.toLowerCase().includes(t.content.toLowerCase())
      )) {
        this.topics.push({
          id: uuidv4(),
          content: topic,
          firstMentioned: message.timestamp,
          mentionedBy: userId,
          mentionCount: 1
        });
      } else {
        const existingTopic = this.topics.find(t =>
          t.content.toLowerCase().includes(topic?.toLowerCase()) ||
          topic?.toLowerCase().includes(t.content.toLowerCase())
        );
        if (existingTopic) {
          existingTopic.mentionCount++;
        }
      }
    }
  }

  _extractAssignee(content, defaultAssignee) {
    const atPattern = /@([^\s，。！？、；：]+)/;
    const match = content.match(atPattern);
    if (match) {
      return match[1];
    }

    const assignPatterns = [
      /(?:由|请|让|安排)\s*([^\s，。！？、；：]{2,10})\s*(?:负责|处理|做|跟进)/,
      /([^\s，。！？、；：]{2,10})\s*(?:负责|处理|做|跟进)/
    ];

    for (const pattern of assignPatterns) {
      const m = content.match(pattern);
      if (m && m[1] && !['我们', '大家', '一起'].includes(m[1])) {
        return m[1];
      }
    }

    return defaultAssignee;
  }

  _extractPriority(content) {
    if (/(?:紧急|马上|立刻|立即|high)/i.test(content)) return 'high';
    if (/(?:重要|优先|尽快|medium)/i.test(content)) return 'medium';
    return 'normal';
  }

  _extractTopic(content) {
    const topicPatterns = [
      /(?:关于|讨论|议题|主题|说一下|谈谈)\s*([^，。！？、；：]{3,50})/,
      /([^，。！？、；：]{3,30})\s*(?:问题|方案|计划|进展|情况|汇报)/
    ];

    for (const pattern of topicPatterns) {
      const match = content.match(pattern);
      if (match && match[1]) {
        return match[1].trim();
      }
    }

    if (content.length > 2 && content.length < 50) {
      return content.trim();
    }

    return content.slice(0, 30).trim();
  }

  async generateSummary(aiApiKey = null) {
    if (this.isGenerating) {
      return { success: false, error: 'Generating in progress' };
    }

    this.isGenerating = true;

    try {
      const context = {
        duration: this.endTime ? this.endTime - this.startTime : Date.now() - this.startTime,
        participantCount: this.participants.size,
        participants: Array.from(this.participants.values()),
        messageCount: this.messages.length,
        topics: this.topics,
        decisions: this.decisions,
        actionItems: this.actionItems,
        speakingStats: this._getSpeakingStats()
      };

      if (aiApiKey) {
        try {
          this.summary = await this._generateAISummary(context, aiApiKey);
        } catch (aiError) {
          console.warn('AI summary failed, using template:', aiError.message);
          this.summary = this._generateTemplateSummary(context);
        }
      } else {
        this.summary = this._generateTemplateSummary(context);
      }

      this.endTime = this.endTime || Date.now();
      this._saveToFile();

      this.isGenerating = false;
      return { success: true, summary: this.summary };
    } catch (error) {
      this.isGenerating = false;
      console.error('Summary generation failed:', error);
      return { success: false, error: error.message };
    }
  }

  async _generateAISummary(context, apiKey) {
    const messagesText = this.messages
      .slice(-200)
      .map(m => `[${new Date(m.timestamp).toLocaleTimeString()}] ${m.userName}: ${m.content}`)
      .join('\n');

    const prompt = `
你是一个专业的会议纪要助手。请根据以下会议信息生成结构化的会议纪要：

=== 会议基本信息 ===
时长: ${Math.round(context.duration / 60000)} 分钟
参会人数: ${context.participantCount}
参会人员: ${context.participants.map(p => p.name).join('、')}
消息总数: ${context.messageCount}

=== 自动识别的议题 ===
${context.topics.map((t, i) => `${i + 1}. ${t.content} (提到${t.mentionCount}次)`).join('\n')}

=== 自动识别的决议 ===
${context.decisions.map((d, i) => `${i + 1}. ${d.content}`).join('\n')}

=== 自动识别的待办事项 ===
${context.actionItems.map((a, i) => `${i + 1}. [${a.priority}] ${a.content} | 负责人: ${a.assignee}`).join('\n')}

=== 发言统计 ===
${context.speakingStats.map((s, i) => `${i + 1}. ${s.name}: ${s.messageCount}条消息`).join('\n')}

=== 会议聊天记录 ===
${messagesText}

请生成以下内容：
1. 会议主题（一句话总结）
2. 核心讨论要点（3-5条）
3. 会议决议（整理已识别的决议）
4. 待办事项清单（包含负责人、优先级）
5. 下次会议建议

请用JSON格式返回，包含字段：
{
  "title": "会议主题",
  "keyPoints": ["要点1", "要点2"],
  "decisions": ["决议1", "决议2"],
  "actionItems": [{"content": "内容", "assignee": "负责人", "priority": "high/medium/low", "deadline": null}],
  "nextMeeting": "建议",
  "overallSummary": "整体总结(200字以内)"
}
    `.trim();

    const response = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${apiKey}`
      },
      body: JSON.stringify({
        model: 'gpt-3.5-turbo-16k',
        messages: [{ role: 'user', content: prompt }],
        temperature: 0.3,
        max_tokens: 2000
      })
    });

    if (!response.ok) {
      throw new Error(`AI API error: ${response.status}`);
    }

    const data = await response.json();
    const content = data.choices[0].message.content;

    try {
      const jsonMatch = content.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        return JSON.parse(jsonMatch[0]);
      }
      throw new Error('Invalid JSON response');
    } catch {
      return {
        title: this._generateTitle(context),
        keyPoints: context.topics.map(t => t.content),
        decisions: context.decisions.map(d => d.content),
        actionItems: context.actionItems.map(a => ({
          content: a.content,
          assignee: a.assignee,
          priority: a.priority,
          deadline: null
        })),
        nextMeeting: '建议在完成本次待办事项后安排下次会议',
        overallSummary: `本次会议共${context.participantCount}人参会，讨论了${context.topics.length}个议题，形成了${context.decisions.length}项决议，明确了${context.actionItems.length}项待办事项。`
      };
    }
  }

  _generateTemplateSummary(context) {
    return {
      title: this._generateTitle(context),
      keyPoints: context.topics.length > 0 
        ? context.topics.map(t => t.content).slice(0, 5)
        : ['暂无明确议题'],
      decisions: context.decisions.length > 0
        ? context.decisions.map(d => d.content)
        : ['暂无明确决议'],
      actionItems: context.actionItems.map(a => ({
        content: a.content,
        assignee: a.assignee,
        priority: a.priority,
        deadline: null,
        status: a.status
      })),
      nextMeeting: '建议在完成本次待办事项后安排下次会议跟进',
      overallSummary: this._generateOverallSummary(context),
      autoGenerated: true
    };
  }

  _generateTitle(context) {
    const date = new Date(this.startTime).toLocaleDateString('zh-CN');
    const participants = context.participants.map(p => p.name).slice(0, 3).join('、');
    const suffix = context.participants.length > 3 ? `等${context.participants.length}人` : '';
    
    if (this.topics.length > 0) {
      const mainTopic = this.topics.reduce((a, b) => a.mentionCount > b.mentionCount ? a : b);
      return `${date} - ${mainTopic.content}讨论会`;
    }
    
    return `${date} - ${participants}${suffix}会议`;
  }

  _generateOverallSummary(context) {
    const duration = Math.round(context.duration / 60000);
    const parts = [];
    
    parts.push(`本次会议共${context.participantCount}人参会，时长约${duration}分钟。`);
    
    if (context.topics.length > 0) {
      parts.push(`围绕"${context.topics[0].content}"等${context.topics.length}个议题展开讨论。`);
    }
    
    if (context.decisions.length > 0) {
      parts.push(`会议形成了${context.decisions.length}项关键决议。`);
    }
    
    if (context.actionItems.length > 0) {
      const highPriority = context.actionItems.filter(a => a.priority === 'high').length;
      parts.push(`明确了${context.actionItems.length}项待办事项，其中${highPriority}项为高优先级。`);
    }
    
    if (context.speakingStats.length > 0) {
      const topSpeaker = context.speakingStats[0];
      parts.push(`${topSpeaker.name}发言最为活跃。`);
    }
    
    return parts.join('');
  }

  _getSpeakingStats() {
    const stats = [];
    this.participants.forEach((participant, userId) => {
      stats.push({
        userId,
        name: participant.name || '未知用户',
        messageCount: this.speakingTime.get(userId) || 0
      });
    });
    return stats.sort((a, b) => b.messageCount - a.messageCount);
  }

  _saveToFile() {
    const data = {
      minutesId: this.minutesId,
      roomId: this.roomId,
      startTime: this.startTime,
      endTime: this.endTime,
      participants: Array.from(this.participants.values()),
      messages: this.messages,
      summary: this.summary,
      actionItems: this.actionItems,
      decisions: this.decisions,
      topics: this.topics,
      speakingStats: this._getSpeakingStats()
    };

    const filename = `${this.roomId}-${this.minutesId.slice(0, 8)}.json`;
    const filepath = path.join(MINUTES_DIR, filename);

    try {
      fs.writeFileSync(filepath, JSON.stringify(data, null, 2));
      return filepath;
    } catch (error) {
      console.error('Failed to save minutes:', error);
      return null;
    }
  }

  addParticipant(participant) {
    this.participants.set(participant.user?.id || participant.id, participant.user || participant);
    this.lastActivity = Date.now();
  }

  removeParticipant(userId) {
    this.participants.delete(userId);
  }

  end() {
    this.endTime = Date.now();
  }

  toJSON() {
    return {
      minutesId: this.minutesId,
      roomId: this.roomId,
      startTime: this.startTime,
      endTime: this.endTime,
      participantCount: this.participants.size,
      messageCount: this.messages.length,
      actionItemCount: this.actionItems.length,
      decisionCount: this.decisions.length,
      topicCount: this.topics.length,
      isGenerating: this.isGenerating,
      summary: this.summary,
      lastActivity: this.lastActivity
    };
  }
}

class MeetingMinutesManager {
  constructor() {
    this.sessions = new Map();
    this.aiApiKey = process.env.OPENAI_API_KEY || null;
  }

  createSession(roomId, participants = []) {
    const session = new MeetingMinutesSession(roomId, participants);
    this.sessions.set(roomId, session);
    return session;
  }

  getSession(roomId) {
    return this.sessions.get(roomId);
  }

  getOrCreateSession(roomId, participants = []) {
    let session = this.sessions.get(roomId);
    if (!session) {
      session = this.createSession(roomId, participants);
    }
    return session;
  }

  addMessage(roomId, message) {
    const session = this.getOrCreateSession(roomId);
    session.addMessage(message);
    return session;
  }

  addParticipant(roomId, participant) {
    const session = this.getOrCreateSession(roomId);
    session.addParticipant(participant);
    return session;
  }

  removeParticipant(roomId, userId) {
    const session = this.getSession(roomId);
    if (session) {
      session.removeParticipant(userId);
    }
    return session;
  }

  async generateMinutes(roomId) {
    const session = this.getSession(roomId);
    if (!session) {
      return { success: false, error: 'Session not found' };
    }
    return session.generateSummary(this.aiApiKey);
  }

  endSession(roomId) {
    const session = this.getSession(roomId);
    if (session) {
      session.end();
      const result = {
        ...session.toJSON(),
        summary: session.summary
      };
      return result;
    }
    return null;
  }

  deleteSession(roomId) {
    return this.sessions.delete(roomId);
  }

  getSessionStats(roomId) {
    const session = this.getSession(roomId);
    if (!session) return null;
    return session.toJSON();
  }

  listMinutes() {
    const files = fs.readdirSync(MINUTES_DIR).filter(f => f.endsWith('.json'));
    return files.map(filename => {
      try {
        const filepath = path.join(MINUTES_DIR, filename);
        const data = JSON.parse(fs.readFileSync(filepath, 'utf8'));
        return {
          filename,
          minutesId: data.minutesId,
          roomId: data.roomId,
          startTime: data.startTime,
          endTime: data.endTime,
          title: data.summary?.title || '未命名会议',
          participantCount: data.participants?.length || 0,
          hasSummary: !!data.summary,
          autoGenerated: data.summary?.autoGenerated || false
        };
      } catch {
        return null;
      }
    }).filter(Boolean);
  }

  getMinutes(filename) {
    try {
      const filepath = path.join(MINUTES_DIR, filename);
      if (!fs.existsSync(filepath)) return null;
      return JSON.parse(fs.readFileSync(filepath, 'utf8'));
    } catch {
      return null;
    }
  }

  getMinutesFilePath(filename) {
    const filepath = path.join(MINUTES_DIR, filename);
    if (fs.existsSync(filepath)) {
      return filepath;
    }
    return null;
  }

  deleteMinutes(filename) {
    try {
      const filepath = path.join(MINUTES_DIR, filename);
      if (fs.existsSync(filepath)) {
        fs.unlinkSync(filepath);
        return true;
      }
      return false;
    } catch {
      return false;
    }
  }

  getAllSessions() {
    return Array.from(this.sessions.entries()).map(([roomId, session]) => ({
      roomId,
      ...session.toJSON()
    }));
  }
}

export default MeetingMinutesManager;
