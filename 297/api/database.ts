import Database from 'better-sqlite3'
import bcrypt from 'bcryptjs'
import path from 'path'
import fs from 'fs'

const dbDir = path.join(process.cwd(), 'data')
if (!fs.existsSync(dbDir)) {
  fs.mkdirSync(dbDir, { recursive: true })
}

const db = new Database(path.join(dbDir, 'app.db'))

export function initDatabase() {
  db.exec(`
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      username TEXT UNIQUE NOT NULL,
      password_hash TEXT NOT NULL,
      role TEXT DEFAULT 'annotator',
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS projects (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      description TEXT,
      point_cloud_path TEXT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      created_by INTEGER REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS annotations (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      project_id INTEGER REFERENCES projects(id),
      user_id INTEGER REFERENCES users(id),
      label TEXT NOT NULL,
      type TEXT NOT NULL,
      geometry TEXT NOT NULL,
      point_count INTEGER DEFAULT 0,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX IF NOT EXISTS idx_annotations_project ON annotations(project_id);
    CREATE INDEX IF NOT EXISTS idx_annotations_user ON annotations(user_id);
    CREATE INDEX IF NOT EXISTS idx_annotations_label ON annotations(label);
  `)

  const adminUser = db.prepare('SELECT * FROM users WHERE username = ?').get('admin')
  if (!adminUser) {
    const passwordHash = bcrypt.hashSync('admin123', 10)
    db.prepare(`
      INSERT INTO users (username, password_hash, role)
      VALUES (?, ?, ?)
    `).run('admin', passwordHash, 'admin')
    
    const demoPasswordHash = bcrypt.hashSync('demo123', 10)
    db.prepare(`
      INSERT INTO users (username, password_hash, role)
      VALUES (?, ?, ?)
    `).run('demo', demoPasswordHash, 'annotator')

    db.prepare(`
      INSERT INTO projects (name, description, created_by)
      VALUES (?, ?, ?)
    `).run('演示项目', '这是一个用于演示的点云标注项目', 1)
  }

  console.log('Database initialized')
}

export default db
