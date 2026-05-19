const Imap = require('imap');
const { simpleParser } = require('mailparser');
const BaseAdapter = require('./BaseAdapter');
const logger = require('../utils/logger');

class EmailAdapter extends BaseAdapter {
  constructor(channelConfig) {
    super(channelConfig);
    this.imap = null;
  }

  async connect() {
    try {
      const imapConfig = {
        user: this.config.user,
        password: this.config.password,
        host: this.config.host,
        port: this.config.port || 993,
        tls: this.config.tls !== false,
        tlsOptions: {
          rejectUnauthorized: false
        },
        keepalive: {
          interval: 10000,
          idleInterval: 300000,
          forceNoop: true
        }
      };

      this.imap = new Imap(imapConfig);

      return new Promise((resolve, reject) => {
        this.imap.once('ready', () => {
          this.isConnected = true;
          logger.info('Email adapter connected successfully');
          resolve(true);
        });

        this.imap.once('error', (err) => {
          logger.error('Email adapter error:', err);
          this.isConnected = false;
          reject(err);
        });

        this.imap.once('end', () => {
          this.isConnected = false;
          logger.info('Email adapter disconnected');
        });

        this.imap.connect();
      });
    } catch (error) {
      logger.error('Email adapter connection failed:', error);
      throw error;
    }
  }

  async disconnect() {
    if (this.imap && this.isConnected) {
      this.imap.end();
      this.isConnected = false;
    }
  }

  async fetchMessages(since = null) {
    if (!this.isConnected) {
      await this.connect();
    }

    return new Promise((resolve, reject) => {
      this.imap.openBox('INBOX', false, async (err, box) => {
        if (err) {
          reject(err);
          return;
        }

        const searchCriteria = ['UNSEEN'];
        if (since) {
          searchCriteria.push(['SINCE', since]);
        }

        this.imap.search(searchCriteria, (err, results) => {
          if (err) {
            reject(err);
            return;
          }

          if (results.length === 0) {
            resolve([]);
            return;
          }

          const fetch = this.imap.fetch(results, {
            bodies: '',
            markSeen: false
          });

          const messages = [];

          fetch.on('message', (msg, seqno) => {
            let emailData = '';

            msg.on('body', (stream, info) => {
              let buffer = '';
              stream.on('data', (chunk) => {
                buffer += chunk.toString('utf8');
              });
              stream.once('end', () => {
                emailData = buffer;
              });
            });

            msg.once('attributes', (attrs) => {
              msg.attrs = attrs;
            });

            msg.once('end', async () => {
              try {
                const parsed = await simpleParser(emailData);
                const normalized = this.normalizeMessage(parsed, msg.attrs);
                messages.push(normalized);
              } catch (parseErr) {
                logger.error('Failed to parse email:', parseErr);
              }
            });
          });

          fetch.once('error', (err) => {
            reject(err);
          });

          fetch.once('end', () => {
            resolve(messages);
          });
        });
      });
    });
  }

  async markAsRead(messageIds) {
    if (!this.isConnected) {
      await this.connect();
    }

    return new Promise((resolve, reject) => {
      this.imap.openBox('INBOX', false, (err) => {
        if (err) {
          reject(err);
          return;
        }

        this.imap.addFlags(messageIds, ['\\Seen'], (err) => {
          if (err) {
            reject(err);
            return;
          }
          resolve(true);
        });
      });
    });
  }

  async markAsUnread(messageIds) {
    if (!this.isConnected) {
      await this.connect();
    }

    return new Promise((resolve, reject) => {
      this.imap.openBox('INBOX', false, (err) => {
        if (err) {
          reject(err);
          return;
        }

        this.imap.delFlags(messageIds, ['\\Seen'], (err) => {
          if (err) {
            reject(err);
            return;
          }
          resolve(true);
        });
      });
    });
  }

  normalizeMessage(parsedEmail, attrs) {
    const messageId = attrs.uid.toString();
    const title = parsedEmail.subject || '(无主题)';
    const content = parsedEmail.text || parsedEmail.html || '';

    const sender = parsedEmail.from?.value?.[0] || {};
    const recipients = parsedEmail.to?.value?.map(r => r.address) || [];
    const attachments = parsedEmail.attachments?.map(att => ({
      name: att.filename,
      size: att.size,
      type: att.contentType
    })) || [];

    return {
      channel: 'email',
      channelMessageId: messageId,
      title,
      content,
      summary: content.substring(0, 200),
      sender: {
        name: sender.name,
        email: sender.address
      },
      recipients,
      attachments,
      receivedAt: parsedEmail.date || new Date(),
      dedupKey: this.generateDedupKey({ title, content }),
      raw: {
        subject: parsedEmail.subject,
        from: parsedEmail.from?.text,
        to: parsedEmail.to?.text,
        date: parsedEmail.date,
        messageId: parsedEmail.messageId
      }
    };
  }
}

module.exports = EmailAdapter;
