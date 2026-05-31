import { Session, Annotation, User, ShareLink } from '../../shared/types';
import { OTState, createInitialOTState, applyOperation, applyOperations, createOperation, OTOperation } from '../../shared/ot';
import { v4 as uuidv4 } from 'uuid';
import { createHash } from 'crypto';

interface SessionWithOT extends Session {
  otState: OTState;
}

class MemoryStore {
  private sessions: Map<string, SessionWithOT> = new Map();
  private shareLinks: Map<string, ShareLink> = new Map();

  createSession(chartData: any, chartType: string = 'line'): Session {
    const sessionId = uuidv4();
    const session: SessionWithOT = {
      id: sessionId,
      annotations: [],
      users: [],
      chartData,
      chartType,
      createdAt: Date.now(),
      otState: createInitialOTState(),
    };
    this.sessions.set(sessionId, session);
    return this.stripOTState(session);
  }

  getSession(sessionId: string): Session | undefined {
    const session = this.sessions.get(sessionId);
    return session ? this.stripOTState(session) : undefined;
  }

  getOTState(sessionId: string): OTState | undefined {
    return this.sessions.get(sessionId)?.otState;
  }

  private stripOTState(session: SessionWithOT): Session {
    const { otState, ...rest } = session;
    return rest;
  }

  updateSession(sessionId: string, updates: Partial<Session>): Session | undefined {
    const session = this.sessions.get(sessionId);
    if (!session) return undefined;
    
    const updated = { ...session, ...updates };
    this.sessions.set(sessionId, updated);
    return this.stripOTState(updated);
  }

  addUser(sessionId: string, user: User): Session | undefined {
    const session = this.sessions.get(sessionId);
    if (!session) return undefined;
    
    const existingUser = session.users.find(u => u.id === user.id);
    if (!existingUser) {
      session.users.push(user);
    }
    return this.stripOTState(session);
  }

  removeUser(sessionId: string, userId: string): Session | undefined {
    const session = this.sessions.get(sessionId);
    if (!session) return undefined;
    
    session.users = session.users.filter(u => u.id !== userId);
    return this.stripOTState(session);
  }

  updateUserCursor(sessionId: string, userId: string, cursor: { x: number; y: number }): Session | undefined {
    const session = this.sessions.get(sessionId);
    if (!session) return undefined;
    
    const user = session.users.find(u => u.id === userId);
    if (user) {
      user.cursor = cursor;
    }
    return this.stripOTState(session);
  }

  applyOTOperation(sessionId: string, operation: OTOperation): { 
    success: boolean; 
    operation?: OTOperation; 
    annotation?: Annotation 
  } {
    const session = this.sessions.get(sessionId);
    if (!session) return { success: false };

    const result = applyOperation(session.otState, operation);
    session.otState = result.state;
    session.annotations = result.state.annotations;

    const updatedAnnotation = session.annotations.find(a => a.id === operation.annotationId);
    
    return {
      success: true,
      operation: result.transformedOp,
      annotation: updatedAnnotation,
    };
  }

  addAnnotation(sessionId: string, annotation: Omit<Annotation, 'id' | 'createdAt' | 'updatedAt' | 'version'>, userId: string): { 
    operation: OTOperation; 
    annotation: Annotation 
  } | undefined {
    const session = this.sessions.get(sessionId);
    if (!session) return undefined;

    const annotationId = uuidv4();
    const operation = createOperation(
      'add',
      annotationId,
      annotation,
      userId,
      session.otState.version
    );

    const result = applyOperation(session.otState, operation);
    session.otState = result.state;
    session.annotations = result.state.annotations;

    const newAnnotation = session.annotations.find(a => a.id === annotationId)!;
    return { operation: result.transformedOp, annotation: newAnnotation };
  }

  updateAnnotation(sessionId: string, annotationId: string, updates: Partial<Annotation>, userId: string): { 
    operation: OTOperation; 
    annotation?: Annotation 
  } | undefined {
    const session = this.sessions.get(sessionId);
    if (!session) return undefined;

    const existing = session.annotations.find(a => a.id === annotationId);
    if (!existing) return undefined;

    const operation = createOperation(
      'update',
      annotationId,
      updates,
      userId,
      session.otState.version
    );

    const result = applyOperation(session.otState, operation);
    session.otState = result.state;
    session.annotations = result.state.annotations;

    const updatedAnnotation = session.annotations.find(a => a.id === annotationId);
    return { operation: result.transformedOp, annotation: updatedAnnotation };
  }

  deleteAnnotation(sessionId: string, annotationId: string, userId: string): { 
    operation: OTOperation; 
    success: boolean 
  } | undefined {
    const session = this.sessions.get(sessionId);
    if (!session) return undefined;

    const existing = session.annotations.find(a => a.id === annotationId);
    if (!existing) return undefined;

    const operation = createOperation(
      'delete',
      annotationId,
      {},
      userId,
      session.otState.version
    );

    const result = applyOperation(session.otState, operation);
    session.otState = result.state;
    session.annotations = result.state.annotations;

    const success = !session.annotations.find(a => a.id === annotationId);
    return { operation: result.transformedOp, success };
  }

  getAnnotations(sessionId: string): Annotation[] | undefined {
    return this.sessions.get(sessionId)?.annotations;
  }

  getVersion(sessionId: string): number | undefined {
    return this.sessions.get(sessionId)?.otState.version;
  }

  createShareLink(
    sessionId: string,
    expiresIn: number = 86400000,
    password?: string,
    permissions: 'read' | 'write' = 'write'
  ): { shareId: string; shareUrl: string } | undefined {
    const session = this.sessions.get(sessionId);
    if (!session) return undefined;

    const shareId = uuidv4();
    const shareLink: ShareLink = {
      id: shareId,
      sessionId,
      expiresAt: Date.now() + expiresIn,
      accessCount: 0,
      permissions,
    };

    if (password) {
      shareLink.passwordHash = this.hashPassword(password);
    }

    this.shareLinks.set(shareId, shareLink);

    return {
      shareId,
      shareUrl: `/share/${shareId}`,
    };
  }

  private hashPassword(password: string): string {
    return createHash('sha256').update(password).digest('hex');
  }

  verifySharePassword(shareId: string, password: string): boolean {
    const link = this.shareLinks.get(shareId);
    if (!link || !link.passwordHash) return true;
    return this.hashPassword(password) === link.passwordHash;
  }

  getShareLink(shareId: string): ShareLink | undefined {
    const link = this.shareLinks.get(shareId);
    if (!link || link.expiresAt < Date.now()) {
      this.shareLinks.delete(shareId);
      return undefined;
    }
    return link;
  }

  getSessionByShareId(shareId: string, password?: string): { session: Session; permissions: 'read' | 'write' } | undefined {
    const link = this.getShareLink(shareId);
    if (!link) return undefined;

    if (link.passwordHash) {
      if (!password || !this.verifySharePassword(shareId, password)) {
        return undefined;
      }
    }

    link.accessCount++;
    const session = this.sessions.get(link.sessionId);
    if (!session) return undefined;

    return {
      session: this.stripOTState(session),
      permissions: link.permissions,
    };
  }
}

export const store = new MemoryStore();
