import numpy as np
from sequence_alignment import GAP, DIAG, UP, LEFT

def print_score_matrix(aligner, show_traceback=False):
    if aligner.score_matrix is None:
        print("\n[注意] 滚动数组模式下未保存完整得分矩阵。")
        print("如需查看完整矩阵，请使用 use_rolling=False 重新计算。")
        return
    
    seq1 = ' ' + aligner.seq1
    seq2 = ' ' + aligner.seq2
    
    print("\n=== 得分矩阵 ===")
    
    header = "       "
    for base in seq2:
        header += f"{base:>5s}"
    print(header)
    print(" " + "-" * (5 * (len(seq2) + 1)))
    
    for i in range(len(seq1)):
        row = f"{seq1[i]:>3s} |"
        for j in range(len(seq2)):
            if show_traceback and hasattr(aligner, 'traceback_matrix'):
                direction = aligner.traceback_matrix[i, j]
                arrows = []
                if direction & DIAG:
                    arrows.append('↘')
                if direction & UP:
                    arrows.append('↑')
                if direction & LEFT:
                    arrows.append('←')
                arrow_str = ''.join(arrows) if arrows else ''
                row += f"{aligner.score_matrix[i, j]:>4d}{arrow_str}"
            else:
                row += f"{aligner.score_matrix[i, j]:>5d}"
        print(row)
    print()

def print_alignment(aligner, alignment_type="Global", line_width=60, show_all=False):
    print(f"\n=== {alignment_type}比对结果 ===")
    print(f"序列1: {aligner.seq1}")
    print(f"序列2: {aligner.seq2}")
    print(f"最优比对得分: {aligner.alignment_score}")
    print(f"找到的最优解数量: {len(aligner.alignment_results)}")
    print()
    
    if not aligner.alignment_results:
        print("未找到有效比对结果。")
        return
    
    results_to_show = aligner.alignment_results if show_all else [aligner.alignment_results[0]]
    
    for idx, result in enumerate(results_to_show, 1):
        if show_all:
            print(f"--- 解 {idx}/{len(aligner.alignment_results)} ---")
        
        aligned1 = result.aligned_seq1
        aligned2 = result.aligned_seq2
        match_line = aligner.get_match_line(result)
        
        total_len = len(aligned1)
        for i in range(0, total_len, line_width):
            end = min(i + line_width, total_len)
            print(f"Seq1: {aligned1[i:end]}")
            print(f"      {match_line[i:end]}")
            print(f"Seq2: {aligned2[i:end]}")
            print()
        
        identity = sum(1 for a, b in zip(aligned1, aligned2) if a == b and a != GAP)
        positives = sum(1 for a, b in zip(aligned1, aligned2) 
                       if a != GAP and b != GAP and aligner.sub_matrix.get_score(a, b) > 0)
        gaps = sum(1 for a, b in zip(aligned1, aligned2) if a == GAP or b == GAP)
        
        aligned_length = len(aligned1)
        print(f"一致性: {identity}/{aligned_length} ({100*identity/aligned_length:.1f}%)")
        print(f"相似性: {positives}/{aligned_length} ({100*positives/aligned_length:.1f}%)")
        print(f"缺口:   {gaps}/{aligned_length} ({100*gaps/aligned_length:.1f}%)")
        print()

def print_multiple_alignment(msa, line_width=60, show_consensus=True, show_conservation=True):
    print("\n=== 多序列比对结果 ===")
    print(f"序列数量: {msa.get_statistics()['n_sequences']}")
    print(f"比对长度: {msa.get_statistics()['aligned_length']}")
    print()
    
    aligned_seqs = msa.aligned_sequences
    if not aligned_seqs:
        print("未找到比对结果。")
        return
    
    names = list(aligned_seqs.keys())
    aligned_length = len(aligned_seqs[names[0]])
    conservation = msa.get_conservation_scores()
    
    for start in range(0, aligned_length, line_width):
        end = min(start + line_width, aligned_length)
        
        max_name_len = max(len(name) for name in names)
        for name in names:
            seq = aligned_seqs[name]
            display_seq = seq[start:end]
            colored_seq = []
            for pos, char in enumerate(display_seq):
                abs_pos = start + pos
                if char == GAP:
                    colored_seq.append(f"\033[90m{char}\033[0m")
                elif conservation and conservation[abs_pos] >= 0.9:
                    colored_seq.append(f"\033[92m{char}\033[0m")
                elif conservation and conservation[abs_pos] >= 0.7:
                    colored_seq.append(f"\033[93m{char}\033[0m")
                else:
                    colored_seq.append(char)
            print(f"{name:>{max_name_len}s}: {''.join(colored_seq)}")
        
        if show_conservation and conservation:
            cons_bar = []
            for pos in range(start, end):
                if pos < len(conservation):
                    if conservation[pos] >= 0.9:
                        cons_bar.append('*')
                    elif conservation[pos] >= 0.7:
                        cons_bar.append(':')
                    elif conservation[pos] >= 0.5:
                        cons_bar.append('.')
                    else:
                        cons_bar.append(' ')
                else:
                    cons_bar.append(' ')
            print(f"{'':>{max_name_len}s}  {''.join(cons_bar)}")
        
        print()
    
    if show_consensus and msa.consensus:
        print(f"一致性序列: {msa.consensus}")
        print()

def print_alignment_statistics(msa):
    stats = msa.get_statistics()
    
    print("\n=== 比对统计信息 ===")
    print(f"序列数量: {stats['n_sequences']}")
    print(f"比对长度: {stats['aligned_length']}")
    print(f"平均保守度: {stats['average_conservation']:.3f}")
    print(f"完全一致位点: {stats['identity_positions']} ({100*stats['identity_positions']/stats['aligned_length']:.1f}%)")
    print(f"保守位点(≥70%): {stats['conserved_positions']} ({100*stats['conserved_positions']/stats['aligned_length']:.1f}%)")
    print(f"缺口比例: {stats['gap_percentage']:.1f}%")
    print(f"保守区域数量: {stats['n_conserved_regions']}")
    
    if stats['conserved_regions']:
        print("\n保守区域:")
        for i, (start, end) in enumerate(stats['conserved_regions'], 1):
            print(f"  区域{i}: 位置 {start}-{end} (长度 {end-start+1})")
    print()

def print_search_results(results, alignment_type="全局"):
    if not results:
        print("未找到匹配序列。")
        return
    
    print(f"\n=== 数据库{alignment_type}比对搜索结果 ===")
    print(f"排名{'':<2s}序列名称{'':<10s}得分{'':<5s}匹配度")
    print("-" * 50)
    
    for i, (name, score, aligned1, aligned2, aligner) in enumerate(results, 1):
        identity = sum(1 for a, b in zip(aligned1, aligned2) if a == b and a != GAP)
        length = len(aligned1)
        identity_pct = 100 * identity / length if length > 0 else 0
        print(f"{i:<6d}{name:<18s}{score:<10d}{identity_pct:.1f}%")
    print()

def print_detailed_alignment(name, aligned1, aligned2, aligner, line_width=60):
    print(f"\n--- {name} 详细比对 ---")
    match_line = aligner.get_match_line()
    
    total_len = len(aligned1)
    for i in range(0, total_len, line_width):
        end = min(i + line_width, total_len)
        print(f"Query:  {aligned1[i:end]}")
        print(f"        {match_line[i:end]}")
        print(f"Target: {aligned2[i:end]}")
        print()

def print_all_alignments_summary(aligner, max_display=10):
    if not aligner.alignment_results:
        print("没有找到比对结果。")
        return
    
    print(f"\n=== 全部 {len(aligner.alignment_results)} 个最优比对摘要 ===")
    print(f"比对得分: {aligner.alignment_score}")
    print()
    
    display_count = min(max_display, len(aligner.alignment_results))
    
    for i in range(display_count):
        result = aligner.alignment_results[i]
        print(f"[{i+1}] {result.aligned_seq1}")
        print(f"     {result.aligned_seq2}")
        print()
    
    if len(aligner.alignment_results) > max_display:
        print(f"... 还有 {len(aligner.alignment_results) - max_display} 个解未显示")

def print_local_alignment_details(aligner):
    if hasattr(aligner, 'start_pos') and hasattr(aligner, 'end_pos'):
        print("\n=== 局部比对详细信息 ===")
        print(f"起始位置 (序列1, 序列2): ({aligner.start_pos[0]}, {aligner.start_pos[1]})")
        print(f"结束位置 (序列1, 序列2): ({aligner.end_pos[0]}, {aligner.end_pos[1]})")
        if aligner.alignment_results:
            print(f"匹配区域长度: {len(aligner.alignment_results[0].aligned_seq1)}")
    if hasattr(aligner, 'max_positions') and len(aligner.max_positions) > 1:
        print(f"最高分位置数量: {len(aligner.max_positions)}")

def print_substitution_matrix(sub_matrix):
    print(f"\n=== 替换矩阵: {sub_matrix.matrix_type.upper()} ===")
    print(f"序列类型: {sub_matrix.seq_type.upper()}")
    print(f"字母表大小: {len(sub_matrix.alphabet)}")
    print()
    
    alphabet = sub_matrix.alphabet[:20]
    header = "    "
    for aa in alphabet:
        header += f"{aa:>4s}"
    print(header)
    print("  " + "-" * (4 * len(alphabet) + 2))
    
    for i, aa1 in enumerate(alphabet):
        row = f"{aa1:>2s} |"
        for j, aa2 in enumerate(alphabet):
            row += f"{sub_matrix.matrix[i, j]:>4d}"
        print(row)
    print()
    
    if len(sub_matrix.alphabet) > 20:
        print(f"[注] 显示前20个标准氨基酸，完整字母表包含 {len(sub_matrix.alphabet)} 个字符:")
        print(f"     {''.join(sub_matrix.alphabet)}")

def print_memory_comparison(aligner):
    n, m = aligner.n, aligner.m
    full_matrix_bytes = (n + 1) * (m + 1) * 4
    rolling_bytes = (m + 1) * 4 * 2
    traceback_bytes = (n + 1) * (m + 1) * 1
    
    print("\n=== 内存使用对比 ===")
    print(f"序列长度: seq1={n}, seq2={m}")
    print(f"完整分数矩阵 (O(nm)): {full_matrix_bytes:,} 字节 ({full_matrix_bytes/1024:.2f} KB)")
    print(f"滚动数组 (O(n)):       {rolling_bytes:,} 字节 ({rolling_bytes/1024:.2f} KB)")
    print(f"回溯矩阵 (O(nm)):       {traceback_bytes:,} 字节 ({traceback_bytes/1024:.2f} KB)")
    if full_matrix_bytes > 0:
        print(f"分数矩阵内存节省: {(1 - rolling_bytes/full_matrix_bytes)*100:.1f}%")
    print()

def create_html_visualization(aligner, output_file="alignment_visualization.html", show_all=False):
    if not aligner.alignment_results:
        print("没有比对结果可可视化。")
        return None
    
    seq1_display = ' ' + aligner.seq1
    seq2_display = ' ' + aligner.seq2
    
    html_content = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>序列比对可视化</title>
    <style>
        body {
            font-family: 'Courier New', monospace;
            margin: 20px;
            background-color: #f5f5f5;
        }
        h1, h2 {
            color: #333;
        }
        .info-box {
            background: white;
            padding: 15px;
            border-radius: 8px;
            margin: 10px 0;
        }
        .matrix-container {
            overflow-x: auto;
            margin: 20px 0;
            background: white;
            padding: 15px;
            border-radius: 8px;
        }
        table {
            border-collapse: collapse;
        }
        td {
            width: 45px;
            height: 45px;
            text-align: center;
            border: 1px solid #ddd;
            position: relative;
            font-size: 12px;
        }
        .header-cell {
            background-color: #4a90d9;
            color: white;
            font-weight: bold;
            font-size: 14px;
        }
        .diag-cell {
            background-color: #a8e6cf;
        }
        .up-cell {
            background-color: #ffd3b6;
        }
        .left-cell {
            background-color: #ffaaa5;
        }
        .multi-cell {
            background: linear-gradient(135deg, #a8e6cf 33%, #ffd3b6 66%, #ffaaa5 100%);
        }
        .zero-cell {
            background-color: #ff8b94;
        }
        .score {
            font-size: 14px;
            font-weight: bold;
            display: block;
        }
        .arrow {
            font-size: 10px;
            position: absolute;
            bottom: 1px;
            right: 2px;
            color: #555;
        }
        .alignment-result {
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
        }
        .alignment-result pre {
            font-size: 14px;
            line-height: 1.4;
        }
        .match {
            color: #2ecc71;
            font-weight: bold;
        }
        .positive {
            color: #f39c12;
        }
        .mismatch {
            color: #e74c3c;
        }
        .gap {
            color: #95a5a6;
        }
        .stats {
            margin-top: 15px;
            padding: 10px;
            background-color: #e8f4f8;
            border-radius: 5px;
        }
        .legend {
            display: flex;
            gap: 20px;
            margin: 10px 0;
            flex-wrap: wrap;
        }
        .legend-item {
            display: flex;
            align-items: center;
            gap: 5px;
        }
        .legend-box {
            width: 20px;
            height: 20px;
            border: 1px solid #ddd;
        }
        .solution-tabs {
            display: flex;
            gap: 5px;
            margin-bottom: 10px;
            flex-wrap: wrap;
        }
        .tab-btn {
            padding: 8px 16px;
            border: none;
            background: #ddd;
            cursor: pointer;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
        }
        .tab-btn.active {
            background: #4a90d9;
            color: white;
        }
        .solution-content {
            display: none;
        }
        .solution-content.active {
            display: block;
        }
    </style>
</head>
<body>
    <h1>序列比对可视化</h1>
    
    <div class="info-box">
        <h2>序列信息</h2>
        <p><strong>序列1:</strong> """ + aligner.seq1 + """</p>
        <p><strong>序列2:</strong> """ + aligner.seq2 + """</p>
        <p><strong>最优比对得分:</strong> """ + str(aligner.alignment_score) + """</p>
        <p><strong>最优解数量:</strong> """ + str(len(aligner.alignment_results)) + """</p>
    </div>
"""
    
    if aligner.score_matrix is not None:
        html_content += """
    <h2>得分矩阵</h2>
    <div class="legend">
        <div class="legend-item">
            <div class="legend-box" style="background-color: #a8e6cf;"></div>
            <span>对角线 (匹配)</span>
        </div>
        <div class="legend-item">
            <div class="legend-box" style="background-color: #ffd3b6;"></div>
            <span>向上 (seq2缺口)</span>
        </div>
        <div class="legend-item">
            <div class="legend-box" style="background-color: #ffaaa5;"></div>
            <span>向左 (seq1缺口)</span>
        </div>
        <div class="legend-item">
            <div class="legend-box" style="background: linear-gradient(135deg, #a8e6cf 33%, #ffd3b6 66%, #ffaaa5 100%);"></div>
            <span>多方向</span>
        </div>
    </div>
    
    <div class="matrix-container">
        <table>
"""
        html_content += "            <tr>"
        for j, base in enumerate(seq2_display):
            html_content += f'<td class="header-cell">{base}</td>'
        html_content += "</tr>\n"
        
        for i, base1 in enumerate(seq1_display):
            html_content += "            <tr>"
            html_content += f'<td class="header-cell">{base1}</td>'
            for j in range(1, len(seq2_display)):
                score = aligner.score_matrix[i, j]
                direction = aligner.traceback_matrix[i, j] if hasattr(aligner, 'traceback_matrix') else 0
                
                cell_class = ""
                dir_count = bin(direction).count('1')
                if dir_count > 1:
                    cell_class = "multi-cell"
                elif direction & DIAG:
                    cell_class = "diag-cell"
                elif direction & UP:
                    cell_class = "up-cell"
                elif direction & LEFT:
                    cell_class = "left-cell"
                elif score == 0:
                    cell_class = "zero-cell"
                
                arrows = []
                if direction & DIAG:
                    arrows.append('↘')
                if direction & UP:
                    arrows.append('↑')
                if direction & LEFT:
                    arrows.append('←')
                arrow_str = ''.join(arrows) if arrows else ''
                
                html_content += f'<td class="{cell_class}"><span class="score">{score}</span><span class="arrow">{arrow_str}</span></td>'
            html_content += "</tr>\n"
        
        html_content += """
        </table>
    </div>
"""
    else:
        html_content += """
    <div class="info-box">
        <p><em>滚动数组模式下未保存完整得分矩阵。如需可视化矩阵，请使用 use_rolling=False 重新计算。</em></p>
    </div>
"""
    
    html_content += """
    <h2>比对结果</h2>
    <div class="alignment-result">
"""
    
    if show_all and len(aligner.alignment_results) > 1:
        html_content += '<div class="solution-tabs">'
        for idx in range(len(aligner.alignment_results)):
            active_class = 'active' if idx == 0 else ''
            html_content += f'<button class="tab-btn {active_class}" onclick="showSolution({idx})">解 {idx+1}</button>'
        html_content += '</div>'
        
        for idx, result in enumerate(aligner.alignment_results):
            active_class = 'active' if idx == 0 else ''
            aligned1 = result.aligned_seq1
            aligned2 = result.aligned_seq2
            match_line = aligner.get_match_line(result)
            
            identity = sum(1 for a, b in zip(aligned1, aligned2) if a == b and a != GAP)
            positives = sum(1 for a, b in zip(aligned1, aligned2) 
                           if a != GAP and b != GAP and aligner.sub_matrix.get_score(a, b) > 0)
            gaps = sum(1 for a, b in zip(aligned1, aligned2) if a == GAP or b == GAP)
            aligned_length = len(aligned1)
            
            html_content += f'<div class="solution-content {active_class}" id="solution-{idx}">'
            html_content += f"<pre>"
            html_content += f"Seq1: {aligned1}\n"
            html_content += f"      {match_line}\n"
            html_content += f"Seq2: {aligned2}\n"
            html_content += "</pre>"
            html_content += f"""
            <div class="stats">
                <p><strong>一致性:</strong> {identity}/{aligned_length} ({100*identity/aligned_length:.1f}%)</p>
                <p><strong>相似性:</strong> {positives}/{aligned_length} ({100*positives/aligned_length:.1f}%)</p>
                <p><strong>缺口:</strong> {gaps}/{aligned_length} ({100*gaps/aligned_length:.1f}%)</p>
            </div>
            </div>
            """
        
        html_content += """
        <script>
        function showSolution(idx) {
            document.querySelectorAll('.solution-content').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
            document.getElementById('solution-' + idx).classList.add('active');
            event.target.classList.add('active');
        }
        </script>
        """
    else:
        result = aligner.alignment_results[0]
        aligned1 = result.aligned_seq1
        aligned2 = result.aligned_seq2
        match_line = aligner.get_match_line(result)
        
        identity = sum(1 for a, b in zip(aligned1, aligned2) if a == b and a != GAP)
        positives = sum(1 for a, b in zip(aligned1, aligned2) 
                       if a != GAP and b != GAP and aligner.sub_matrix.get_score(a, b) > 0)
        gaps = sum(1 for a, b in zip(aligned1, aligned2) if a == GAP or b == GAP)
        aligned_length = len(aligned1)
        
        html_content += f"<pre>"
        html_content += f"Seq1: {aligned1}\n"
        html_content += f"      {match_line}\n"
        html_content += f"Seq2: {aligned2}\n"
        html_content += "</pre>"
        html_content += f"""
        <div class="stats">
            <p><strong>一致性:</strong> {identity}/{aligned_length} ({100*identity/aligned_length:.1f}%)</p>
            <p><strong>相似性:</strong> {positives}/{aligned_length} ({100*positives/aligned_length:.1f}%)</p>
            <p><strong>缺口:</strong> {gaps}/{aligned_length} ({100*gaps/aligned_length:.1f}%)</p>
        </div>
        """
    
    html_content += """
    </div>
</body>
</html>
"""
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"\nHTML可视化已保存到: {output_file}")
    return output_file

def create_msa_html_visualization(msa, output_file="msa_visualization.html"):
    stats = msa.get_statistics()
    aligned_seqs = msa.aligned_sequences
    conservation = msa.get_conservation_scores()
    
    html_content = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>多序列比对可视化</title>
    <style>
        body {
            font-family: 'Courier New', monospace;
            margin: 20px;
            background-color: #f5f5f5;
        }
        h1, h2 {
            color: #333;
        }
        .info-box {
            background: white;
            padding: 15px;
            border-radius: 8px;
            margin: 10px 0;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 10px;
        }
        .stat-item {
            background: #e8f4f8;
            padding: 10px;
            border-radius: 5px;
            text-align: center;
        }
        .stat-value {
            font-size: 24px;
            font-weight: bold;
            color: #4a90d9;
        }
        .stat-label {
            font-size: 12px;
            color: #666;
        }
        .alignment-container {
            overflow-x: auto;
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
        }
        .alignment-row {
            display: flex;
            margin: 2px 0;
        }
        .seq-name {
            min-width: 120px;
            padding-right: 10px;
            text-align: right;
            font-weight: bold;
            color: #333;
        }
        .seq-content {
            letter-spacing: 2px;
        }
        .conserved-high {
            color: #27ae60;
            font-weight: bold;
            background-color: #d5f5e3;
        }
        .conserved-med {
            color: #f39c12;
            background-color: #fef9e7;
        }
        .conserved-low {
            color: #e74c3c;
        }
        .gap {
            color: #95a5a6;
        }
        .consensus-row {
            margin-top: 10px;
            padding-top: 10px;
            border-top: 2px solid #ddd;
        }
        .conservation-bar {
            display: flex;
            margin: 5px 0 0 130px;
        }
        .conservation-char {
            width: 14px;
            text-align: center;
            font-size: 12px;
        }
        .regions-container {
            background: white;
            padding: 15px;
            border-radius: 8px;
            margin: 20px 0;
        }
        .region-item {
            padding: 10px;
            margin: 5px 0;
            background: #e8f4f8;
            border-radius: 5px;
            border-left: 4px solid #4a90d9;
        }
    </style>
</head>
<body>
    <h1>多序列比对可视化</h1>
    
    <div class="info-box">
        <h2>比对统计</h2>
        <div class="stats-grid">
            <div class="stat-item">
                <div class="stat-value">""" + str(stats['n_sequences']) + """</div>
                <div class="stat-label">序列数量</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">""" + str(stats['aligned_length']) + """</div>
                <div class="stat-label">比对长度</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">""" + f"{stats['average_conservation']:.1%}" + """</div>
                <div class="stat-label">平均保守度</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">""" + str(stats['identity_positions']) + """</div>
                <div class="stat-label">完全一致位点</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">""" + str(stats['n_conserved_regions']) + """</div>
                <div class="stat-label">保守区域</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">""" + f"{stats['gap_percentage']:.1f}%" + """</div>
                <div class="stat-label">缺口比例</div>
            </div>
        </div>
    </div>
    
    <h2>比对结果</h2>
    <div class="alignment-container">
"""
    
    if aligned_seqs:
        names = list(aligned_seqs.keys())
        aligned_length = len(aligned_seqs[names[0]])
        
        for name in names:
            seq = aligned_seqs[name]
            html_content += f'<div class="alignment-row"><div class="seq-name">{name}</div><div class="seq-content">'
            
            for pos, char in enumerate(seq):
                if char == '-':
                    html_content += f'<span class="gap">{char}</span>'
                elif conservation and conservation[pos] >= 0.9:
                    html_content += f'<span class="conserved-high">{char}</span>'
                elif conservation and conservation[pos] >= 0.7:
                    html_content += f'<span class="conserved-med">{char}</span>'
                else:
                    html_content += char
            
            html_content += '</div></div>'
        
        if msa.consensus:
            html_content += f'<div class="alignment-row consensus-row"><div class="seq-name">Consensus</div><div class="seq-content">{msa.consensus}</div></div>'
        
        html_content += '<div class="conservation-bar">'
        for pos in range(aligned_length):
            if conservation and pos < len(conservation):
                if conservation[pos] >= 0.9:
                    html_content += '<span class="conservation-char">*</span>'
                elif conservation[pos] >= 0.7:
                    html_content += '<span class="conservation-char">:</span>'
                elif conservation[pos] >= 0.5:
                    html_content += '<span class="conservation-char">.</span>'
                else:
                    html_content += '<span class="conservation-char">&nbsp;</span>'
            else:
                html_content += '<span class="conservation-char">&nbsp;</span>'
        html_content += '</div>'
    
    html_content += """
    </div>
"""
    
    if stats['conserved_regions']:
        html_content += """
    <h2>保守区域</h2>
    <div class="regions-container">
"""
        for i, (start, end) in enumerate(stats['conserved_regions'], 1):
            if msa.consensus:
                region_seq = msa.consensus[start:end+1]
            else:
                region_seq = "N/A"
            html_content += f"""
        <div class="region-item">
            <strong>区域{i}:</strong> 位置 {start}-{end} (长度 {end-start+1})<br>
            <strong>序列:</strong> {region_seq}
        </div>
"""
        html_content += """
    </div>
"""
    
    html_content += """
</body>
</html>
"""
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"\n多序列比对HTML可视化已保存到: {output_file}")
    return output_file
