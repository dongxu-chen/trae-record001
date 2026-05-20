import json
from config import Config

class DependencyGraph:
    def __init__(self):
        self.nodes = []
        self.edges = []
        self.node_positions = {}
    
    def build_graph_from_deadlock(self, deadlock_data):
        transactions = deadlock_data.get('transactions', [])
        
        for txn in transactions:
            txn_id = txn.get('transaction_id', 'unknown')
            node_label = f"Txn {txn_id}"
            thread_id = txn.get('thread_id', 'N/A')
            queries = txn.get('queries', [])
            holds = txn.get('holds', [])
            waiting = txn.get('waiting_for', {})
            
            self.nodes.append({
                'id': txn_id,
                'label': node_label,
                'thread_id': thread_id,
                'queries': queries,
                'holds_count': len(holds),
                'waiting_for': waiting.get('table', 'None') if waiting else 'None',
                'waiting_mode': waiting.get('mode', 'N/A') if waiting else 'N/A',
                'holds': holds
            })
        
        for i, txn1 in enumerate(transactions):
            txn1_id = txn1.get('transaction_id', 'unknown')
            waiting1 = txn1.get('waiting_for', {})
            
            if waiting1:
                table1 = waiting1.get('table')
                mode1 = waiting1.get('mode', 'N/A')
                
                for j, txn2 in enumerate(transactions):
                    if i != j:
                        txn2_id = txn2.get('transaction_id', 'unknown')
                        holds2 = txn2.get('holds', [])
                        
                        for hold in holds2:
                            if hold.get('table') == table1:
                                edge_label = f"{mode1} → {table1}"
                                self.edges.append({
                                    'source': txn1_id,
                                    'target': txn2_id,
                                    'label': edge_label,
                                    'table': table1,
                                    'mode': mode1
                                })
        
        self._calculate_positions()
    
    def _calculate_positions(self):
        n = len(self.nodes)
        if n == 0:
            return
        
        center_x = 400
        center_y = 300
        radius = 200
        
        for i, node in enumerate(self.nodes):
            angle = (2 * 3.14159 * i) / n - 3.14159 / 2
            x = center_x + radius * 0.8 * 3.14159
            y = center_y + radius * 0.8 * 3.14159
            
            x = center_x + radius * 0.6 * (1 + 0.3 * (i % 2)) * 1.0
            y = center_y + (i - n/2) * 100
            
            self.node_positions[node['id']] = {
                'x': 100 + (i % 3) * 250,
                'y': 100 + (i // 3) * 150
            }
    
    def generate_html_svg(self, output_file=None):
        if not output_file:
            output_file = Config.DEPENDENCY_GRAPH_FILE
        
        nodes_json = json.dumps(self.nodes, ensure_ascii=False)
        edges_json = json.dumps(self.edges, ensure_ascii=False)
        positions_json = json.dumps(self.node_positions, ensure_ascii=False)
        
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>死锁依赖关系图</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            text-align: center;
        }}
        .header h1 {{
            font-size: 28px;
            margin-bottom: 10px;
        }}
        .controls {{
            padding: 15px 25px;
            background: #f8f9fa;
            border-bottom: 1px solid #e9ecef;
            display: flex;
            gap: 15px;
            align-items: center;
        }}
        .btn {{
            padding: 8px 16px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.3s;
        }}
        .btn-primary {{
            background: #667eea;
            color: white;
        }}
        .btn-primary:hover {{
            background: #5a67d8;
        }}
        .btn-secondary {{
            background: #e2e8f0;
            color: #4a5568;
        }}
        .btn-secondary:hover {{
            background: #cbd5e0;
        }}
        .graph-container {{
            padding: 20px;
            position: relative;
            overflow: auto;
        }}
        #graph-svg {{
            width: 100%;
            min-height: 500px;
            background: #fafafa;
            border-radius: 10px;
            border: 2px solid #e2e8f0;
        }}
        .node {{
            cursor: pointer;
            transition: all 0.3s ease;
        }}
        .node:hover circle {{
            filter: brightness(1.1);
            transform-origin: center;
        }}
        .node circle {{
            stroke-width: 3px;
            transition: all 0.3s ease;
        }}
        .node text {{
            font-family: 'Segoe UI', sans-serif;
            font-size: 12px;
            font-weight: 600;
            fill: #2d3748;
            pointer-events: none;
            text-anchor: middle;
        }}
        .edge path {{
            fill: none;
            stroke: #e53e3e;
            stroke-width: 2.5px;
            marker-end: url(#arrowhead);
            transition: all 0.3s ease;
        }}
        .edge path:hover {{
            stroke: #c53030;
            stroke-width: 3.5px;
        }}
        .edge text {{
            font-family: 'Segoe UI', sans-serif;
            font-size: 11px;
            fill: #e53e3e;
            font-weight: 500;
        }}
        .tooltip {{
            position: absolute;
            background: rgba(45, 55, 72, 0.95);
            color: white;
            padding: 15px;
            border-radius: 8px;
            font-size: 13px;
            max-width: 400px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            z-index: 1000;
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.3s ease;
        }}
        .tooltip.visible {{
            opacity: 1;
        }}
        .tooltip h4 {{
            margin-bottom: 10px;
            color: #63b3ed;
            font-size: 14px;
        }}
        .tooltip .section {{
            margin-bottom: 8px;
        }}
        .tooltip .label {{
            color: #a0aec0;
            font-size: 11px;
            text-transform: uppercase;
        }}
        .tooltip .value {{
            color: #e2e8f0;
        }}
        .legend {{
            padding: 20px 25px;
            background: #f8f9fa;
            border-top: 1px solid #e9ecef;
        }}
        .legend h3 {{
            color: #2d3748;
            margin-bottom: 15px;
            font-size: 16px;
        }}
        .legend-items {{
            display: flex;
            gap: 30px;
            flex-wrap: wrap;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .legend-color {{
            width: 20px;
            height: 20px;
            border-radius: 50%;
        }}
        .legend-line {{
            width: 30px;
            height: 3px;
            background: #e53e3e;
        }}
        .stats {{
            padding: 20px 25px;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
        }}
        .stat-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px;
            border-radius: 10px;
            text-align: center;
        }}
        .stat-value {{
            font-size: 28px;
            font-weight: bold;
        }}
        .stat-label {{
            font-size: 12px;
            opacity: 0.9;
        }}
        #arrowhead {{
            fill: #e53e3e;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔗 死锁依赖关系图</h1>
            <p>交互式可视化 - 悬停查看详情，拖动移动节点</p>
        </div>
        
        <div class="controls">
            <button class="btn btn-primary" onclick="resetView()">重置视图</button>
            <button class="btn btn-secondary" onclick="toggleLabels()">切换标签</button>
            <button class="btn btn-secondary" onclick="zoomIn()">放大 +</button>
            <button class="btn btn-secondary" onclick="zoomOut()">缩小 -</button>
        </div>
        
        <div class="graph-container">
            <svg id="graph-svg" viewBox="0 0 800 600">
                <defs>
                    <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
                        <polygon points="0 0, 10 3.5, 0 7" />
                    </marker>
                    <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
                        <feDropShadow dx="2" dy="2" stdDeviation="3" flood-opacity="0.3"/>
                    </filter>
                </defs>
                <g id="edges-group"></g>
                <g id="nodes-group"></g>
            </svg>
        </div>
        
        <div class="tooltip" id="tooltip"></div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-value" id="node-count">0</div>
                <div class="stat-label">事务数量</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="edge-count">0</div>
                <div class="stat-label">等待关系</div>
            </div>
        </div>
        
        <div class="legend">
            <h3>📖 图例</h3>
            <div class="legend-items">
                <div class="legend-item">
                    <div class="legend-color" style="background: #4299e1;"></div>
                    <span>事务节点</span>
                </div>
                <div class="legend-item">
                    <div class="legend-line"></div>
                    <span>等待关系</span>
                </div>
            </div>
        </div>
    </div>

    <script>
        const nodes = {nodes_json};
        const edges = {edges_json};
        const positions = {positions_json};
        
        let showLabels = true;
        let currentScale = 1;
        let draggedNode = null;
        let dragOffset = {{ x: 0, y: 0 }};
        
        document.addEventListener('DOMContentLoaded', function() {{
            renderGraph();
            updateStats();
        }});
        
        function renderGraph() {{
            const nodesGroup = document.getElementById('nodes-group');
            const edgesGroup = document.getElementById('edges-group');
            nodesGroup.innerHTML = '';
            edgesGroup.innerHTML = '';
            
            edges.forEach(edge => {{
                const sourcePos = positions[edge.source] || {{ x: 100, y: 100 }};
                const targetPos = positions[edge.target] || {{ x: 300, y: 300 }};
                
                const dx = targetPos.x - sourcePos.x;
                const dy = targetPos.y - sourcePos.y;
                const dist = Math.sqrt(dx * dx + dy * dy);
                
                const startX = sourcePos.x + (dx / dist) * 35;
                const startY = sourcePos.y + (dy / dist) * 35;
                const endX = targetPos.x - (dx / dist) * 40;
                const endY = targetPos.y - (dy / dist) * 40;
                
                const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                path.setAttribute('d', `M ${{startX}} ${{startY}} L ${{endX}} ${{endY}}`);
                path.setAttribute('class', 'edge-path');
                
                const edgeGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
                edgeGroup.setAttribute('class', 'edge');
                edgeGroup.appendChild(path);
                
                if (showLabels) {{
                    const midX = (startX + endX) / 2;
                    const midY = (startY + endY) / 2;
                    const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                    text.setAttribute('x', midX);
                    text.setAttribute('y', midY - 8);
                    text.setAttribute('text-anchor', 'middle');
                    text.textContent = edge.label;
                    edgeGroup.appendChild(text);
                }}
                
                edgesGroup.appendChild(edgeGroup);
            }});
            
            nodes.forEach(node => {{
                const pos = positions[node.id] || {{ x: 100, y: 100 }};
                
                const nodeGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
                nodeGroup.setAttribute('class', 'node');
                nodeGroup.setAttribute('data-id', node.id);
                nodeGroup.setAttribute('transform', `translate(${{pos.x}}, ${{pos.y}})`);
                
                const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
                circle.setAttribute('r', '35');
                circle.setAttribute('fill', node.holds_count > 0 ? '#f6ad55' : '#4299e1');
                circle.setAttribute('stroke', node.waiting_for !== 'None' ? '#e53e3e' : '#2b6cb0');
                circle.setAttribute('filter', 'url(#shadow)');
                
                const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                label.setAttribute('y', '5');
                label.textContent = node.label;
                
                const subLabel = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                subLabel.setAttribute('y', '20');
                subLabel.setAttribute('font-size', '10');
                subLabel.setAttribute('fill', '#718096');
                subLabel.textContent = `锁: ${{node.holds_count}}`;
                
                nodeGroup.appendChild(circle);
                nodeGroup.appendChild(label);
                nodeGroup.appendChild(subLabel);
                
                nodeGroup.addEventListener('mouseenter', function(e) {{
                    showTooltip(e, node);
                }});
                
                nodeGroup.addEventListener('mouseleave', function() {{
                    hideTooltip();
                }});
                
                nodeGroup.addEventListener('mousedown', function(e) {{
                    startDrag(e, node.id);
                }});
                
                nodesGroup.appendChild(nodeGroup);
            }});
        }}
        
        function showTooltip(e, node) {{
            const tooltip = document.getElementById('tooltip');
            const queries = node.queries.length > 0 ? 
                node.queries.map(q => `<code style="display:block; margin:5px 0; padding:5px; background:rgba(255,255,255,0.1); border-radius:3px; word-break:break-all;">${{q.substring(0, 100)}}${{q.length > 100 ? '...' : ''}}</code>`).join('') :
                '<em>无查询语句</em>';
            
            const holdsInfo = node.holds && node.holds.length > 0 ?
                node.holds.map(h => `<div>• ${{h.mode || '?'}} on ${{h.table || '?'}} (${{h.index || '?'}})</div>`).join('') :
                '<em>无持有锁</em>';
            
            tooltip.innerHTML = `
                <h4>🔹 ${{node.label}}</h4>
                <div class="section">
                    <div class="label">线程ID</div>
                    <div class="value">${{node.thread_id}}</div>
                </div>
                <div class="section">
                    <div class="label">等待锁</div>
                    <div class="value">${{node.waiting_mode}} on ${{node.waiting_for}}</div>
                </div>
                <div class="section">
                    <div class="label">持有锁 (${{node.holds_count}})</div>
                    <div class="value">${{holdsInfo}}</div>
                </div>
                <div class="section">
                    <div class="label">执行SQL</div>
                    <div class="value">${{queries}}</div>
                </div>
            `;
            
            tooltip.style.left = (e.pageX + 15) + 'px';
            tooltip.style.top = (e.pageY + 15) + 'px';
            tooltip.classList.add('visible');
        }}
        
        function hideTooltip() {{
            const tooltip = document.getElementById('tooltip');
            tooltip.classList.remove('visible');
        }}
        
        function startDrag(e, nodeId) {{
            draggedNode = nodeId;
            const nodeElement = document.querySelector(`[data-id="${{nodeId}}"]`);
            const transform = nodeElement.getAttribute('transform');
            const match = transform.match(/translate\(([^,]+),\s*([^)]+)\)/);
            
            if (match) {{
                dragOffset.x = e.clientX - parseFloat(match[1]);
                dragOffset.y = e.clientY - parseFloat(match[2]);
            }}
            
            document.addEventListener('mousemove', onDrag);
            document.addEventListener('mouseup', stopDrag);
        }}
        
        function onDrag(e) {{
            if (!draggedNode) return;
            
            const nodeElement = document.querySelector(`[data-id="${{draggedNode}}"]`);
            const newX = e.clientX - dragOffset.x;
            const newY = e.clientY - dragOffset.y;
            
            nodeElement.setAttribute('transform', `translate(${{newX}}, ${{newY}})`);
            positions[draggedNode] = {{ x: newX, y: newY }};
            
            updateEdges();
        }}
        
        function stopDrag() {{
            draggedNode = null;
            document.removeEventListener('mousemove', onDrag);
            document.removeEventListener('mouseup', stopDrag);
        }}
        
        function updateEdges() {{
            const edgesGroup = document.getElementById('edges-group');
            const edgeElements = edgesGroup.querySelectorAll('.edge');
            
            edges.forEach((edge, index) => {{
                if (edgeElements[index]) {{
                    const sourcePos = positions[edge.source] || {{ x: 100, y: 100 }};
                    const targetPos = positions[edge.target] || {{ x: 300, y: 300 }};
                    
                    const dx = targetPos.x - sourcePos.x;
                    const dy = targetPos.y - sourcePos.y;
                    const dist = Math.sqrt(dx * dx + dy * dy) || 1;
                    
                    const startX = sourcePos.x + (dx / dist) * 35;
                    const startY = sourcePos.y + (dy / dist) * 35;
                    const endX = targetPos.x - (dx / dist) * 40;
                    const endY = targetPos.y - (dy / dist) * 40;
                    
                    const path = edgeElements[index].querySelector('path');
                    path.setAttribute('d', `M ${{startX}} ${{startY}} L ${{endX}} ${{endY}}`);
                    
                    const text = edgeElements[index].querySelector('text');
                    if (text) {{
                        text.setAttribute('x', (startX + endX) / 2);
                        text.setAttribute('y', (startY + endY) / 2 - 8);
                    }}
                }}
            }});
        }}
        
        function updateStats() {{
            document.getElementById('node-count').textContent = nodes.length;
            document.getElementById('edge-count').textContent = edges.length;
        }}
        
        function resetView() {{
            currentScale = 1;
            document.getElementById('graph-svg').style.transform = `scale(${{currentScale}})`;
            self._calculate_positions();
            renderGraph();
        }}
        
        function toggleLabels() {{
            showLabels = !showLabels;
            renderGraph();
        }}
        
        function zoomIn() {{
            currentScale *= 1.2;
            document.getElementById('graph-svg').style.transform = `scale(${{currentScale}})`;
        }}
        
        function zoomOut() {{
            currentScale /= 1.2;
            document.getElementById('graph-svg').style.transform = `scale(${{currentScale}})`;
        }}
    </script>
</body>
</html>
        """
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return output_file
    
    def clear(self):
        self.nodes = []
        self.edges = []
        self.node_positions = {}
