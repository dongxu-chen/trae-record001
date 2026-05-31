import { Router } from 'express';
import { issuesRepository } from '../db/repositories.js';
import type { QualityIssue } from '../../shared/types.js';

const router = Router();

declare global {
  namespace Express {
    interface Request {
      currentUser?: { id: string; name: string; role: string };
    }
  }
}

function getCurrentUser(req: { headers: Record<string, string | undefined> }) {
  const userHeader = req.headers['x-current-user'];
  if (!userHeader) return { id: 'user_admin', name: '管理员', role: 'admin' };
  try {
    return JSON.parse(userHeader);
  } catch {
    return { id: 'user_admin', name: '管理员', role: 'admin' };
  }
}

router.get('/', (req, res) => {
  const status = req.query.status as string | undefined;
  const issues = issuesRepository.getAll(status ? { status } : undefined);
  res.json(issues);
});

router.put('/:id', (req, res) => {
  try {
    const currentUser = getCurrentUser(req);
    const issueId = req.params.id;
    const updates = req.body as Partial<QualityIssue>;

    const existingIssues = issuesRepository.getAll();
    const existing = existingIssues.find(i => i.id === issueId);
    if (!existing) {
      res.status(404).json({ error: 'Issue not found' });
      return;
    }

    if (currentUser.role !== 'admin') {
      if (updates.status === 'in_progress') {
        if (existing.assignee && existing.assignee !== currentUser.name) {
          res.status(403).json({ error: '只能处理指派给自己的问题' });
          return;
        }
        issuesRepository.update(issueId, { status: 'in_progress', assignee: currentUser.name });
        res.json({ message: 'Issue updated successfully' });
        return;
      }

      if (updates.status === 'resolved') {
        if (existing.assignee !== currentUser.name) {
          res.status(403).json({ error: '只能关闭指派给自己的问题' });
          return;
        }
        issuesRepository.update(issueId, { status: 'resolved' });
        res.json({ message: 'Issue updated successfully' });
        return;
      }

      if (updates.assignee !== undefined) {
        if (existing.assignee && existing.assignee !== currentUser.name && currentUser.role !== 'admin') {
          res.status(403).json({ error: '只能指派自己的问题' });
          return;
        }
        issuesRepository.update(issueId, { assignee: updates.assignee });
        res.json({ message: 'Issue updated successfully' });
        return;
      }

      res.status(403).json({ error: '无权限执行此操作' });
      return;
    }

    issuesRepository.update(issueId, updates);
    res.json({ message: 'Issue updated successfully' });
  } catch (error) {
    res.status(400).json({ error: 'Failed to update issue' });
  }
});

export default router;
