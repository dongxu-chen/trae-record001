const https = require('https');

const GIST_API_BASE = 'https://api.github.com';

function httpsRequest(options, body = null) {
  return new Promise((resolve, reject) => {
    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', (chunk) => {
        data += chunk;
      });
      res.on('end', () => {
        try {
          const response = {
            statusCode: res.statusCode,
            headers: res.headers,
            data: data ? JSON.parse(data) : null
          };
          if (res.statusCode >= 200 && res.statusCode < 300) {
            resolve(response);
          } else {
            reject(new Error(`HTTP ${res.statusCode}: ${data || res.statusMessage}`));
          }
        } catch (error) {
          reject(error);
        }
      });
    });

    req.on('error', reject);

    if (body) {
      req.write(JSON.stringify(body));
    }
    req.end();
  });
}

class GistSync {
  constructor(token = null) {
    this.token = token;
  }

  setToken(token) {
    this.token = token;
  }

  _getHeaders(method = 'GET') {
    const headers = {
      'User-Agent': 'CodeSnippetManager/1.0',
      'Accept': 'application/vnd.github.v3+json'
    };
    if (this.token) {
      headers['Authorization'] = `token ${this.token}`;
    }
    if (method === 'POST' || method === 'PATCH') {
      headers['Content-Type'] = 'application/json';
    }
    return headers;
  }

  async getGist(gistId) {
    const options = {
      hostname: 'api.github.com',
      path: `/gists/${gistId}`,
      method: 'GET',
      headers: this._getHeaders()
    };
    const response = await httpsRequest(options);
    return response.data;
  }

  async createGist(description, files, isPublic = false) {
    const options = {
      hostname: 'api.github.com',
      path: '/gists',
      method: 'POST',
      headers: this._getHeaders('POST')
    };
    const body = {
      description,
      public: isPublic,
      files
    };
    const response = await httpsRequest(options, body);
    return response.data;
  }

  async updateGist(gistId, description, files) {
    const options = {
      hostname: 'api.github.com',
      path: `/gists/${gistId}`,
      method: 'PATCH',
      headers: this._getHeaders('PATCH')
    };
    const body = {
      description,
      files
    };
    const response = await httpsRequest(options, body);
    return response.data;
  }

  async uploadSnippets(snippets, existingGistId = null) {
    if (!this.token) {
      throw new Error('GitHub token not configured');
    }

    const files = {};
    snippets.forEach((snippet, index) => {
      const safeTitle = (snippet.title || `snippet_${index}`)
        .replace(/[\\/:*?"<>|]/g, '_');
      const ext = this._getExtension(snippet.language);
      const filename = `${safeTitle}.${ext}`;

      let uniqueFilename = filename;
      let counter = 1;
      while (files[uniqueFilename]) {
        uniqueFilename = `${safeTitle}_${counter}.${ext}`;
        counter++;
      }

      files[uniqueFilename] = {
        content: snippet.code || ''
      };
    });

    const metadata = {
      version: 1,
      exportedAt: new Date().toISOString(),
      snippetCount: snippets.length
    };

    files['.snippets-meta.json'] = {
      content: JSON.stringify({
        ...metadata,
        snippets: snippets.map(s => ({
          id: s.id,
          title: s.title,
          language: s.language,
          tags: s.tags || [],
          createdAt: s.createdAt,
          updatedAt: s.updatedAt
        }))
      }, null, 2)
    };

    const description = `Code Snippets Backup - ${metadata.exportedAt}`;

    if (existingGistId) {
      return await this.updateGist(existingGistId, description, files);
    } else {
      return await this.createGist(description, files, false);
    }
  }

  async downloadSnippets(gistId) {
    if (!this.token) {
      throw new Error('GitHub token not configured');
    }

    const gist = await this.getGist(gistId);
    const files = gist.files;

    const metaFile = files['.snippets-meta.json'];
    let metadata = null;
    if (metaFile && metaFile.content) {
      try {
        metadata = JSON.parse(metaFile.content);
      } catch (error) {
        console.warn('Failed to parse metadata:', error);
      }
    }

    const snippets = [];
    const snippetMetaMap = {};

    if (metadata && metadata.snippets) {
      metadata.snippets.forEach(m => {
        snippetMetaMap[m.id] = m;
      });
    }

    for (const [filename, file] of Object.entries(files)) {
      if (filename.startsWith('.')) continue;

      const baseName = filename.replace(/\.[^.]+$/, '');
      const ext = filename.split('.').pop().toLowerCase();
      const language = this._getLanguage(ext);

      const foundMeta = metadata?.snippets?.find(m => {
        const safeTitle = (m.title || '').replace(/[\\/:*?"<>|]/g, '_');
        const mExt = this._getExtension(m.language);
        return safeTitle === baseName || safeTitle.startsWith(baseName);
      });

      const snippet = {
        id: foundMeta?.id || `gist_${Date.now()}_${snippets.length}`,
        title: foundMeta?.title || baseName,
        language: foundMeta?.language || language,
        code: file.content || '',
        tags: foundMeta?.tags || [],
        createdAt: foundMeta?.createdAt || Date.now(),
        updatedAt: foundMeta?.updatedAt || Date.now(),
        syncedAt: Date.now()
      };

      snippets.push(snippet);
    }

    return { snippets, gist };
  }

  _getExtension(language) {
    const map = {
      javascript: 'js',
      js: 'js',
      typescript: 'ts',
      ts: 'ts',
      python: 'py',
      py: 'py',
      html: 'html',
      css: 'css',
      json: 'json',
      sql: 'sql',
      go: 'go',
      rust: 'rs',
      java: 'java',
      c: 'c',
      cpp: 'cpp',
      csharp: 'cs',
      php: 'php',
      ruby: 'rb',
      swift: 'swift',
      kotlin: 'kt',
      bash: 'sh',
      shell: 'sh'
    };
    return map[language?.toLowerCase()] || 'txt';
  }

  _getLanguage(ext) {
    const map = {
      js: 'javascript',
      ts: 'typescript',
      py: 'python',
      html: 'html',
      css: 'css',
      json: 'json',
      sql: 'sql',
      go: 'go',
      rs: 'rust',
      java: 'java',
      c: 'c',
      cpp: 'cpp',
      cs: 'csharp',
      php: 'php',
      rb: 'ruby',
      swift: 'swift',
      kt: 'kotlin',
      sh: 'bash',
      txt: 'text'
    };
    return map[ext?.toLowerCase()] || 'text';
  }
}

module.exports = GistSync;
