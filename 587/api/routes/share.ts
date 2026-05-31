import { Router, Request, Response } from 'express';
import { store } from '../store/memoryStore';

const router = Router();

router.post('/', (req: Request, res: Response) => {
  try {
    const { sessionId, expiresIn = 86400000, password, permissions = 'write' } = req.body;
    
    if (!sessionId) {
      return res.status(400).json({ error: 'sessionId is required' });
    }
    
    const session = store.getSession(sessionId);
    
    if (!session) {
      return res.status(404).json({ error: 'Session not found' });
    }
    
    const result = store.createShareLink(sessionId, expiresIn, password, permissions);
    
    if (result) {
      const shareUrl = `${req.protocol}://${req.get('host')}${result.shareUrl}`;
      res.json({
        shareId: result.shareId,
        shareUrl,
        hasPassword: !!password,
        permissions,
      });
    } else {
      res.status(500).json({ error: 'Failed to create share link' });
    }
  } catch (error) {
    res.status(500).json({ error: 'Failed to create share link' });
  }
});

router.post('/:shareId/verify', (req: Request, res: Response) => {
  try {
    const { shareId } = req.params;
    const { password } = req.body;
    
    const shareLink = store.getShareLink(shareId);
    
    if (!shareLink) {
      return res.status(404).json({ error: 'Share link expired or not found' });
    }
    
    if (shareLink.passwordHash) {
      if (!password) {
        return res.status(401).json({ error: 'Password required', requiresPassword: true });
      }
      
      const isValid = store.verifySharePassword(shareId, password);
      if (!isValid) {
        return res.status(401).json({ error: 'Invalid password', requiresPassword: true });
      }
    }
    
    const result = store.getSessionByShareId(shareId, password);
    
    if (result) {
      res.json({
        sessionId: result.session.id,
        permissions: result.permissions,
      });
    } else {
      res.status(404).json({ error: 'Share link expired or not found' });
    }
  } catch (error) {
    res.status(500).json({ error: 'Failed to verify share link' });
  }
});

router.get('/:shareId/info', (req: Request, res: Response) => {
  try {
    const shareLink = store.getShareLink(req.params.shareId);
    
    if (!shareLink) {
      return res.status(404).json({ error: 'Share link expired or not found' });
    }
    
    res.json({
      requiresPassword: !!shareLink.passwordHash,
      permissions: shareLink.permissions,
      expiresAt: shareLink.expiresAt,
      accessCount: shareLink.accessCount,
    });
  } catch (error) {
    res.status(500).json({ error: 'Failed to get share link info' });
  }
});

export default router;
