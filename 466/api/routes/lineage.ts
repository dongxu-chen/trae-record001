import { Router, type Request, type Response } from 'express'
import db from '../db.js'
import { v4 as uuidv4 } from 'uuid'

const router = Router()

function parseSqlDependencies(sql: string): string[] {
  const dependencies = new Set<string>()
  
  const fromMatches = sql.match(/(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)/gi)
  if (fromMatches) {
    fromMatches.forEach(match => {
      const tableName = match.replace(/^(FROM|JOIN)\s+/i, '').toLowerCase().trim()
      if (tableName && !['where', 'select', 'on', 'group', 'order', 'having', 'limit'].includes(tableName)) {
        dependencies.add(tableName)
      }
    })
  }
  
  const insertMatches = sql.match(/INSERT\s+(?:INTO\s+)?([a-zA-Z_][a-zA-Z0-9_]*)/i)
  if (insertMatches) {
    const targetTable = insertMatches[1].toLowerCase().trim()
    dependencies.delete(targetTable)
  }
  
  const updateMatches = sql.match(/UPDATE\s+([a-zA-Z_][a-zA-Z0-9_]*)/i)
  if (updateMatches) {
    const targetTable = updateMatches[1].toLowerCase().trim()
    dependencies.delete(targetTable)
  }
  
  return Array.from(dependencies)
}

router.get('/parse-log', (_req: Request, res: Response): void => {
  try {
    const logs = db.prepare(`
      SELECT l.*, t.name as target_table_name
      FROM sql_parse_log l
      LEFT JOIN monitored_table t ON l.target_table_id = t.id
      ORDER BY l.parsed_at DESC
      LIMIT 20
    `).all() as any[]
    
    res.json(logs)
  } catch (error) {
    console.error('Failed to fetch parse logs:', error)
    res.status(500).json({ error: 'Failed to fetch parse logs' })
  }
})

router.post('/parse-sql', (req: Request, res: Response): void => {
  try {
    const { target_table_id, sql_content } = req.body as { target_table_id: string; sql_content: string }
    
    if (!target_table_id || !sql_content) {
      res.status(400).json({ error: 'target_table_id and sql_content are required' })
      return
    }
    
    const targetTable = db.prepare('SELECT * FROM monitored_table WHERE id = ?').get(target_table_id) as any
    if (!targetTable) {
      res.status(404).json({ error: 'Target table not found' })
      return
    }
    
    const parsedAt = new Date().toISOString().replace('T', ' ').slice(0, 19)
    const logId = uuidv4()
    
    try {
      const sourceTableNames = parseSqlDependencies(sql_content)
      
      const sourceTables = db.prepare(`
        SELECT id, name FROM monitored_table WHERE name IN (${sourceTableNames.map(() => '?').join(', ')})
      `).all(...sourceTableNames) as { id: string; name: string }[]
      
      const foundSourceNames = sourceTables.map(t => t.name)
      const newEdges: { source_id: string; target_id: string; type: string }[] = []
      
      for (const st of sourceTables) {
        const existing = db.prepare(
          'SELECT id FROM lineage_edge WHERE source_id = ? AND target_id = ?'
        ).get(st.id, target_table_id)
        
        if (!existing) {
          const edgeId = uuidv4()
          db.prepare(
            'INSERT INTO lineage_edge (id, source_id, target_id, type) VALUES (?, ?, ?, ?)'
          ).run(edgeId, st.id, target_table_id, 'data_flow')
          newEdges.push({ source_id: st.id, target_id: target_table_id, type: 'data_flow' })
        }
      }
      
      db.prepare(`
        INSERT INTO sql_parse_log (id, target_table_id, sql_content, source_tables, parse_status, new_edges_count, error_message, parsed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
      `).run(logId, target_table_id, sql_content, foundSourceNames.join(','), 'success', newEdges.length, null, parsedAt)
      
      res.json({
        parse_status: 'success',
        source_tables: foundSourceNames,
        new_edges: newEdges,
        message: `成功解析SQL，识别到 ${foundSourceNames.length} 个源表，新增 ${newEdges.length} 条血缘边`
      })
    } catch (parseError) {
      db.prepare(`
        INSERT INTO sql_parse_log (id, target_table_id, sql_content, source_tables, parse_status, new_edges_count, error_message, parsed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
      `).run(logId, target_table_id, sql_content, null, 'failed', 0, (parseError as Error).message, parsedAt)
      
      res.status(400).json({
        parse_status: 'failed',
        source_tables: [],
        new_edges: [],
        error_message: (parseError as Error).message
      })
    }
  } catch (error) {
    console.error('Failed to parse SQL:', error)
    res.status(500).json({ error: 'Failed to parse SQL' })
  }
})

router.post('/auto-discover', (_req: Request, res: Response): void => {
  try {
    const now = new Date().toISOString().replace('T', ' ').slice(0, 19)
    const results: { table_name: string; status: string; edges_added: number }[] = []
    
    const tables = db.prepare('SELECT id, name FROM monitored_table').all() as { id: string; name: string }[]
    
    const sampleSqls: Record<string, string> = {
      'dws_user_daily': 'INSERT OVERWRITE dws_user_daily SELECT user_id, date, COUNT(*) as cnt FROM fact_orders GROUP BY user_id, date',
      'ads_sales_report': 'INSERT OVERWRITE ads_sales_report SELECT date, region, SUM(amount) FROM fact_orders o JOIN dim_store s ON o.store_id = s.id GROUP BY date, region',
      'fact_returns': 'INSERT INTO fact_returns SELECT r.* FROM fact_orders o JOIN return_source r ON o.order_id = r.order_id',
    }
    
    for (const table of tables) {
      const existingEdges = db.prepare('SELECT COUNT(*) as cnt FROM lineage_edge WHERE target_id = ?').get(table.id) as { cnt: number }
      if (existingEdges.cnt > 0) continue
      
      const sampleSql = sampleSqls[table.name] || `INSERT INTO ${table.name} SELECT * FROM source_table`
      
      try {
        const sourceTableNames = parseSqlDependencies(sampleSql)
        const sourceTables = db.prepare(`
          SELECT id, name FROM monitored_table WHERE name IN (${sourceTableNames.map(() => '?').join(', ')})
        `).all(...sourceTableNames) as { id: string; name: string }[]
        
        let edgesAdded = 0
        for (const st of sourceTables) {
          const existing = db.prepare(
            'SELECT id FROM lineage_edge WHERE source_id = ? AND target_id = ?'
          ).get(st.id, table.id)
          
          if (!existing) {
            db.prepare(
              'INSERT INTO lineage_edge (id, source_id, target_id, type) VALUES (?, ?, ?, ?)'
            ).run(uuidv4(), st.id, table.id, 'data_flow')
            edgesAdded++
          }
        }
        
        db.prepare(`
          INSERT INTO sql_parse_log (id, target_table_id, sql_content, source_tables, parse_status, new_edges_count, error_message, parsed_at)
          VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        `).run(uuidv4(), table.id, sampleSql, sourceTables.map(t => t.name).join(','), 'success', edgesAdded, null, now)
        
        results.push({ table_name: table.name, status: 'success', edges_added: edgesAdded })
      } catch (e) {
        results.push({ table_name: table.name, status: 'failed', edges_added: 0 })
      }
    }
    
    const totalEdges = results.reduce((sum, r) => sum + r.edges_added, 0)
    
    res.json({
      success: true,
      discovered_count: results.length,
      new_edges_count: totalEdges,
      message: `自动发现完成，处理 ${results.length} 个表，新增 ${totalEdges} 条血缘边`,
      results
    })
  } catch (error) {
    console.error('Failed to auto discover:', error)
    res.status(500).json({ error: 'Failed to auto discover lineage' })
  }
})

export default router
