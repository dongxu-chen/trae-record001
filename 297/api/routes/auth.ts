import { Router } from 'express'
import bcrypt from 'bcryptjs'
import jwt from 'jsonwebtoken'
import db from '../database'

const router = Router()
const JWT_SECRET = 'your-secret-key-change-in-production'

router.post('/login', (req, res) => {
  const { username, password } = req.body

  const user = db.prepare('SELECT * FROM users WHERE username = ?').get(username) as any

  if (!user) {
    return res.status(401).json({ error: 'Invalid credentials' })
  }

  const isValidPassword = bcrypt.compareSync(password, user.password_hash)
  if (!isValidPassword) {
    return res.status(401).json({ error: 'Invalid credentials' })
  }

  const token = jwt.sign(
    { userId: user.id, username: user.username, role: user.role },
    JWT_SECRET,
    { expiresIn: '7d' }
  )

  res.json({
    user: {
      id: user.id.toString(),
      username: user.username,
      role: user.role,
    },
    token,
  })
})

export default router
