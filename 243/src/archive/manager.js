const fs = require('fs-extra');
const path = require('path');
const tar = require('tar');
const { v4: uuidv4 } = require('uuid');

class ArchiveManager {
  constructor({ logger, config }) {
    this.logger = logger;
    this.config = config;
    this.archiveDir = config.archiveDir;
    this.archives = new Map();
    this.indexPath = path.join(this.archiveDir, 'archive-index.json');
  }

  async initialize() {
    await fs.ensureDir(this.archiveDir);
    await this.loadArchiveIndex();
    this.logger.info('归档管理器初始化完成', { archiveDir: this.archiveDir });
  }

  async loadArchiveIndex() {
    try {
      if (await fs.pathExists(this.indexPath)) {
        const data = await fs.readJson(this.indexPath);
        this.archives = new Map(Object.entries(data));
      }
    } catch (err) {
      this.logger.warn('加载归档索引失败，创建新索引', { error: err.message });
      this.archives = new Map();
    }
  }

  async saveArchiveIndex() {
    try {
      const data = Object.fromEntries(this.archives);
      await fs.writeJson(this.indexPath, data, { spaces: 2 });
    } catch (err) {
      this.logger.error('保存归档索引失败', { error: err.message });
    }
  }

  async createArchive(pipelineId, artifactPaths, workspace, options = {}) {
    try {
      const archiveId = uuidv4();
      const archivePath = path.join(this.archiveDir, pipelineId, archiveId);
      
      this.logger.info('创建归档', { pipelineId, archiveId, artifactPaths });

      const filesToArchive = [];
      for (const relativePath of artifactPaths) {
        const fullPath = path.join(workspace, relativePath);
        if (await fs.pathExists(fullPath)) {
          const stat = await fs.stat(fullPath);
          if (stat.isDirectory()) {
            const files = await this.getAllFiles(fullPath);
            files.forEach(f => filesToArchive.push(path.relative(workspace, f)));
          } else {
            filesToArchive.push(relativePath);
          }
        }
      }

      if (filesToArchive.length === 0) {
        this.logger.info('没有文件需要归档', { pipelineId });
        return null;
      }

      await fs.ensureDir(archivePath);
      
      const archiveFile = path.join(archivePath, 'artifacts.tar.gz');
      
      await tar.c({
        cwd: workspace,
        file: archiveFile,
        gzip: true
      }, filesToArchive);

      const stats = await fs.stat(archiveFile);
      
      const archiveInfo = {
        id: archiveId,
        pipelineId,
        name: options.name || 'artifacts',
        files: filesToArchive,
        size: stats.size,
        createdAt: Date.now(),
        expiresAt: options.retentionDays 
          ? Date.now() + (options.retentionDays * 24 * 60 * 60 * 1000)
          : null,
        metadata: options.metadata || {}
      };

      this.archives.set(archiveId, archiveInfo);
      await this.saveArchiveIndex();

      this.logger.info('归档创建成功', { 
        pipelineId, 
        archiveId, 
        size: stats.size,
        fileCount: filesToArchive.length 
      });

      return archiveInfo;
    } catch (err) {
      this.logger.error('创建归档失败', { pipelineId, error: err.message });
      return null;
    }
  }

  async getAllFiles(dir) {
    const files = [];
    const items = await fs.readdir(dir);
    
    for (const item of items) {
      const fullPath = path.join(dir, item);
      const stat = await fs.stat(fullPath);
      
      if (stat.isDirectory()) {
        files.push(...await this.getAllFiles(fullPath));
      } else {
        files.push(fullPath);
      }
    }
    
    return files;
  }

  async getArchive(archiveId) {
    return this.archives.get(archiveId);
  }

  async getArchivesByPipeline(pipelineId) {
    return Array.from(this.archives.values())
      .filter(a => a.pipelineId === pipelineId);
  }

  async extractArchive(archiveId, targetPath) {
    try {
      const archiveInfo = this.archives.get(archiveId);
      if (!archiveInfo) {
        throw new Error(`归档 ${archiveId} 不存在`);
      }

      const archiveFile = path.join(
        this.archiveDir, 
        archiveInfo.pipelineId, 
        archiveId, 
        'artifacts.tar.gz'
      );

      if (!await fs.pathExists(archiveFile)) {
        throw new Error(`归档文件不存在`);
      }

      await fs.ensureDir(targetPath);
      
      await tar.x({
        cwd: targetPath,
        file: archiveFile
      });

      this.logger.info('归档提取成功', { archiveId, targetPath });
      return true;
    } catch (err) {
      this.logger.error('提取归档失败', { archiveId, error: err.message });
      return false;
    }
  }

  async deleteArchive(archiveId) {
    try {
      const archiveInfo = this.archives.get(archiveId);
      if (!archiveInfo) {
        return false;
      }

      const archivePath = path.join(
        this.archiveDir, 
        archiveInfo.pipelineId, 
        archiveId
      );

      if (await fs.pathExists(archivePath)) {
        await fs.remove(archivePath);
      }

      this.archives.delete(archiveId);
      await this.saveArchiveIndex();

      this.logger.info('归档已删除', { archiveId });
      return true;
    } catch (err) {
      this.logger.error('删除归档失败', { archiveId, error: err.message });
      return false;
    }
  }

  async cleanupExpiredArchives() {
    this.logger.info('开始清理过期归档');
    
    const now = Date.now();
    let deletedCount = 0;
    let freedSize = 0;

    for (const [archiveId, info] of this.archives.entries()) {
      if (info.expiresAt && info.expiresAt < now) {
        try {
          const archivePath = path.join(
            this.archiveDir, 
            info.pipelineId, 
            archiveId
          );
          
          if (await fs.pathExists(archivePath)) {
            await fs.remove(archivePath);
          }
          
          this.archives.delete(archiveId);
          deletedCount++;
          freedSize += info.size || 0;
        } catch (err) {
          this.logger.warn('清理归档失败', { archiveId, error: err.message });
        }
      }
    }

    if (deletedCount > 0) {
      await this.saveArchiveIndex();
    }

    this.logger.info('过期归档清理完成', { 
      deletedCount, 
      freedSize: `${(freedSize / 1024 / 1024).toFixed(2)}MB` 
    });
  }

  async getArchiveStats() {
    let totalSize = 0;
    let expiredCount = 0;
    const now = Date.now();

    for (const info of this.archives.values()) {
      totalSize += info.size || 0;
      if (info.expiresAt && info.expiresAt < now) {
        expiredCount++;
      }
    }

    return {
      totalArchives: this.archives.size,
      expiredCount,
      totalSize,
      totalSizeMB: (totalSize / 1024 / 1024).toFixed(2)
    };
  }

  async downloadArchive(archiveId, res) {
    const archiveInfo = this.archives.get(archiveId);
    if (!archiveInfo) {
      throw new Error('归档不存在');
    }

    const archiveFile = path.join(
      this.archiveDir, 
      archiveInfo.pipelineId, 
      archiveId, 
      'artifacts.tar.gz'
    );

    if (!await fs.pathExists(archiveFile)) {
      throw new Error('归档文件不存在');
    }

    return archiveFile;
  }
}

module.exports = ArchiveManager;
