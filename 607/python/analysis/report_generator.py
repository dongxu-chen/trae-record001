import pandas as pd
import numpy as np
from datetime import datetime
from scipy import stats


class ReportGenerator:
    def __init__(self, analysis_result, method, treatment, outcome, covariates, sample_size):
        self.result = analysis_result
        self.method = method
        self.treatment = treatment
        self.outcome = outcome
        self.covariates = covariates
        self.sample_size = sample_size

    def format_number(self, num, decimals=4):
        if num is None:
            return 'N/A'
        return f"{float(num):.{decimals}f}"

    def get_p_value_stars(self, p_value):
        if p_value < 0.01:
            return '***'
        elif p_value < 0.05:
            return '**'
        elif p_value < 0.1:
            return '*'
        else:
            return ''

    def get_significance_label(self, p_value):
        if p_value < 0.01:
            return '极显著 (p<0.01)'
        elif p_value < 0.05:
            return '显著 (p<0.05)'
        elif p_value < 0.1:
            return '边缘显著 (p<0.10)'
        else:
            return '不显著'

    def generate_html_report(self):
        method_name = '倾向性匹配 (PSM)' if self.method == 'psm' else '双重差分 (DID)'
        analysis_date = datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')
        
        ate = self.result.get('ate', {})
        att = self.result.get('att', {})
        
        html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>因果推断分析报告</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 900px;
            margin: 0 auto;
            padding: 40px;
            background: #fafafa;
        }}
        .header {{
            text-align: center;
            padding: 40px 0;
            border-bottom: 3px solid #1e3a5f;
            margin-bottom: 40px;
        }}
        .header h1 {{
            font-size: 32px;
            color: #1e3a5f;
            margin-bottom: 10px;
        }}
        .header .subtitle {{
            color: #666;
            font-size: 14px;
        }}
        .section {{
            margin-bottom: 40px;
        }}
        .section-title {{
            font-size: 20px;
            color: #1e3a5f;
            border-left: 4px solid #d4a855;
            padding-left: 12px;
            margin-bottom: 20px;
        }}
        .info-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 20px;
            margin-bottom: 20px;
        }}
        .info-item {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            border-left: 3px solid #1e3a5f;
        }}
        .info-label {{
            color: #666;
            font-size: 13px;
            margin-bottom: 5px;
        }}
        .info-value {{
            font-size: 16px;
            font-weight: 600;
            color: #1e3a5f;
        }}
        .result-cards {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 20px;
            margin-bottom: 30px;
        }}
        .result-card {{
            background: linear-gradient(135deg, #1e3a5f, #152a43);
            color: white;
            padding: 25px;
            border-radius: 12px;
            text-align: center;
        }}
        .result-card.accent {{
            background: linear-gradient(135deg, #d4a855, #b88430);
        }}
        .result-label {{
            font-size: 14px;
            opacity: 0.9;
            margin-bottom: 10px;
        }}
        .result-value {{
            font-size: 36px;
            font-weight: 700;
            margin-bottom: 10px;
        }}
        .result-stats {{
            font-size: 12px;
            opacity: 0.8;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
            background: white;
        }}
        th {{
            background: #1e3a5f;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }}
        td {{
            padding: 12px;
            border-bottom: 1px solid #e5e7eb;
        }}
        tr:nth-child(even) {{
            background: #f8f9fa;
        }}
        .interpretation {{
            background: #f0f7ff;
            border-left: 4px solid #1e3a5f;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 0 8px 8px 0;
        }}
        .interpretation h4 {{
            color: #1e3a5f;
            margin-bottom: 10px;
        }}
        .interpretation p {{
            color: #4a5568;
            line-height: 1.8;
        }}
        .warning {{
            background: #fffbeb;
            border-left: 4px solid #f59e0b;
            padding: 15px;
            border-radius: 0 8px 8px 0;
            margin-bottom: 20px;
        }}
        .warning p {{
            color: #92400e;
        }}
        .success {{
            background: #ecfdf5;
            border-left: 4px solid #10b981;
            padding: 15px;
            border-radius: 0 8px 8px 0;
            margin-bottom: 20px;
        }}
        .success p {{
            color: #065f46;
        }}
        .footer {{
            text-align: center;
            padding-top: 30px;
            border-top: 1px solid #e5e7eb;
            margin-top: 50px;
            color: #9ca3af;
            font-size: 12px;
        }}
        .tag-list {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }}
        .tag {{
            background: #e5e7eb;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 13px;
            color: #374151;
        }}
        .robustness-score {{
            display: inline-block;
            padding: 8px 20px;
            border-radius: 20px;
            font-weight: 600;
            color: white;
        }}
        .robustness-high {{ background: #10b981; }}
        .robustness-medium {{ background: #f59e0b; }}
        .robustness-low {{ background: #ef4444; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>因果推断分析报告</h1>
        <div class="subtitle">
            分析方法: {method_name} | 生成时间: {analysis_date}
        </div>
    </div>

    <div class="section">
        <h2 class="section-title">1. 分析设置</h2>
        <div class="info-grid">
            <div class="info-item">
                <div class="info-label">处理变量 (Treatment)</div>
                <div class="info-value">{self.treatment}</div>
            </div>
            <div class="info-item">
                <div class="info-label">结果变量 (Outcome)</div>
                <div class="info-value">{self.outcome}</div>
            </div>
            <div class="info-item">
                <div class="info-label">样本量</div>
                <div class="info-value">{self.sample_size.get('total', 'N/A'):,}</div>
            </div>
            <div class="info-item">
                <div class="info-label">协变量数量</div>
                <div class="info-value">{len(self.covariates)}</div>
            </div>
        </div>
        
        <div style="margin-top: 20px;">
            <div class="info-label" style="margin-bottom: 10px;">控制变量:</div>
            <div class="tag-list">
                {''.join([f'<span class="tag">{cov}</span>' for cov in self.covariates])}
            </div>
        </div>
    </div>

    <div class="section">
        <h2 class="section-title">2. 因果效应估计</h2>
        
        <div class="result-cards">
            <div class="result-card">
                <div class="result-label">平均处理效应 (ATE)</div>
                <div class="result-value">{self.format_number(ate.get('estimate'))}{self.get_p_value_stars(ate.get('pValue', 1))}</div>
                <div class="result-stats">
                    SE: {self.format_number(ate.get('stdError'))} | p-value: {self.format_number(ate.get('pValue'), 4)}
                </div>
                <div class="result-stats">
                    95% CI: [{self.format_number(ate.get('confidenceInterval', [0,0])[0])}, {self.format_number(ate.get('confidenceInterval', [0,0])[1])}]
                </div>
            </div>
            <div class="result-card accent">
                <div class="result-label">处理组平均效应 (ATT)</div>
                <div class="result-value">{self.format_number(att.get('estimate'))}{self.get_p_value_stars(att.get('pValue', 1))}</div>
                <div class="result-stats">
                    SE: {self.format_number(att.get('stdError'))} | p-value: {self.format_number(att.get('pValue'), 4)}
                </div>
                <div class="result-stats">
                    95% CI: [{self.format_number(att.get('confidenceInterval', [0,0])[0])}, {self.format_number(att.get('confidenceInterval', [0,0])[1])}]
                </div>
            </div>
        </div>

        <table>
            <thead>
                <tr>
                    <th>指标</th>
                    <th>估计值</th>
                    <th>标准误</th>
                    <th>p值</th>
                    <th>95%置信区间</th>
                    <th>显著性</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td><strong>ATE</strong></td>
                    <td>{self.format_number(ate.get('estimate'))}</td>
                    <td>{self.format_number(ate.get('stdError'))}</td>
                    <td>{self.format_number(ate.get('pValue'), 4)}</td>
                    <td>[{self.format_number(ate.get('confidenceInterval', [0,0])[0])}, {self.format_number(ate.get('confidenceInterval', [0,0])[1])}]</td>
                    <td>{self.get_significance_label(ate.get('pValue', 1))}</td>
                </tr>
                <tr>
                    <td><strong>ATT</strong></td>
                    <td>{self.format_number(att.get('estimate'))}</td>
                    <td>{self.format_number(att.get('stdError'))}</td>
                    <td>{self.format_number(att.get('pValue'), 4)}</td>
                    <td>[{self.format_number(att.get('confidenceInterval', [0,0])[0])}, {self.format_number(att.get('confidenceInterval', [0,0])[1])}]</td>
                    <td>{self.get_significance_label(att.get('pValue', 1))}</td>
                </tr>
            </tbody>
        </table>

        <div class="interpretation">
            <h4>结果解释</h4>
            <p>
                <strong>ATE ({self.format_number(ate.get('estimate'))})</strong> 表示平均而言，处理使结果变量变化了{self.format_number(ate.get('estimate'))}单位。
                该效应在统计上{self.get_significance_label(ate.get('pValue', 1))}。
            </p>
            <p style="margin-top: 10px;">
                <strong>ATT ({self.format_number(att.get('estimate'))})</strong> 表示对于实际接受处理的个体，处理使结果变量变化了{self.format_number(att.get('estimate'))}单位。
            </p>
        </div>
    </div>
"""

        robustness = self.result.get('robustnessTests', {})
        if robustness:
            sensitivity = robustness.get('sensitivityAnalysis')
            enhanced_placebo = robustness.get('enhancedPlacebo')
            different_methods = robustness.get('differentMethods')

            html_content += f"""
    <div class="section">
        <h2 class="section-title">3. 稳健性检验</h2>
"""

            if enhanced_placebo:
                combined = enhanced_placebo.get('combined', {})
                p_val = combined.get('p_value', 1)
                
                if p_val > 0.05:
                    html_content += f"""
        <div class="success">
            <p><strong>✓ 安慰剂检验通过:</strong> 安慰剂效应的p值为{self.format_number(p_val, 4)}，大于0.05，
            说明观测到的效应很可能是真实的因果效应，而非随机因素导致。</p>
        </div>
"""
                else:
                    html_content += f"""
        <div class="warning">
            <p><strong>⚠ 安慰剂检验警告:</strong> 安慰剂效应的p值为{self.format_number(p_val, 4)}，小于0.05，
            建议谨慎解释结果，可能存在其他混淆因素。</p>
        </div>
"""

            if sensitivity:
                sens_analysis = self.result.get('sensitivity_analysis', {})
                e_value = sens_analysis.get('e_value', {})
                rosenbaum = sens_analysis.get('rosenbaum_bounds', {})
                robustness_summary = sens_analysis.get('robustness_summary', {})
                
                overall_robust = robustness_summary.get('overall_robustness', 'low')
                robustness_class = f'robustness-{overall_robust}'
                robustness_text = {'high': '高', 'medium': '中', 'low': '低'}[overall_robust]

                html_content += f"""
        <div style="text-align: center; margin-bottom: 30px;">
            <span class="robustness-score {robustness_class}">整体稳健性: {robustness_text}</span>
        </div>
        
        <table>
            <thead>
                <tr>
                    <th>检验方法</th>
                    <th>指标</th>
                    <th>值</th>
                    <th>解释</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td><strong>E-value</strong></td>
                    <td>最小关联强度</td>
                    <td>{self.format_number(e_value.get('e_value'), 2)}</td>
                    <td>{e_value.get('interpretation', '')}</td>
                </tr>
                <tr>
                    <td><strong>Rosenbaum界限</strong></td>
                    <td>临界Γ值</td>
                    <td>{self.format_number(rosenbaum.get('critical_gamma'), 2)}</td>
                    <td>{rosenbaum.get('interpretation', '')}</td>
                </tr>
            </tbody>
        </table>
"""

            if different_methods:
                html_content += f"""
        <div style="margin-top: 30px;">
            <h4 style="margin-bottom: 15px; color: #1e3a5f;">多方法比较</h4>
            <table>
                <thead>
                    <tr>
                        <th>方法</th>
                        <th>估计值</th>
                        <th>标准误</th>
                        <th>显著性</th>
                    </tr>
                </thead>
                <tbody>
"""
                for method in different_methods:
                    p_val = 2 * (1 - stats.norm.cdf(abs(method.get('estimate', 0) / method.get('stdError', 1)))) if method.get('stdError', 0) > 0 else 1
                    html_content += f"""
                    <tr>
                        <td>{method.get('method', '')}</td>
                        <td>{self.format_number(method.get('estimate'))}</td>
                        <td>{self.format_number(method.get('stdError'))}</td>
                        <td>{self.get_significance_label(p_val)}</td>
                    </tr>
"""
                html_content += """
                </tbody>
            </table>
        </div>
"""

            html_content += """
    </div>
"""

        causal_graph = self.result.get('causal_graph')
        if causal_graph:
            html_content += f"""
    <div class="section">
        <h2 class="section-title">4. 因果图分析</h2>
        <div class="interpretation">
            <h4>变量关系网络</h4>
            <p>共识别出{len(causal_graph.get('nodes', []))}个变量和{len(causal_graph.get('edges', []))}条显著关联。</p>
        </div>
        <table>
            <thead>
                <tr>
                    <th>变量类型</th>
                    <th>变量名</th>
                </tr>
            </thead>
            <tbody>
"""
            for node in causal_graph.get('nodes', []):
                node_type = {'treatment': '处理变量', 'outcome': '结果变量', 'covariate': '协变量'}.get(node.get('type'), '变量')
                html_content += f"""
                <tr>
                    <td>{node_type}</td>
                    <td><strong>{node.get('label', '')}</strong></td>
                </tr>
"""
            
            html_content += """
            </tbody>
        </table>
    </div>
"""

        parallel_tests = self.result.get('parallelTrendTests')
        if parallel_tests:
            stat_test = parallel_tests.get('statistical', {})
            passed = stat_test.get('passed', False)
            
            html_content += f"""
    <div class="section">
        <h2 class="section-title">5. 平行趋势检验 (DID)</h2>
"""
            
            if passed:
                html_content += f"""
        <div class="success">
            <p><strong>✓ 平行趋势假设检验通过:</strong> F统计量为{self.format_number(stat_test.get('f_statistic'), 3)}，
            p值为{self.format_number(stat_test.get('p_value'), 4)}，大于0.05，
            支持平行趋势假设。</p>
        </div>
"""
            else:
                html_content += f"""
        <div class="warning">
            <p><strong>⚠ 平行趋势假设检验未通过:</strong> F统计量为{self.format_number(stat_test.get('f_statistic'), 3)}，
            p值为{self.format_number(stat_test.get('p_value'), 4)}，小于0.05，
            平行趋势假设可能不成立，建议谨慎解释DID结果。</p>
        </div>
"""
            
            html_content += """
    </div>
"""

        lasso_selection = self.result.get('lassoSelection')
        if lasso_selection:
            method_names = {
                'double_lasso': '双重LASSO',
                'treatment': '处理预测',
                'outcome': '结果预测',
                'perturbation': '扰动稳定选择'
            }
            method_used = lasso_selection.get('method_used', '')
            method_display = method_names.get(method_used, method_used)
            
            html_content += f"""
    <div class="section">
        <h2 class="section-title">6. LASSO变量选择</h2>
        <div class="info-item" style="margin-bottom: 20px;">
            <div class="info-label">选择方法</div>
            <div class="info-value">{method_display}</div>
        </div>
        <div style="margin-bottom: 15px;">
            <div class="info-label" style="margin-bottom: 10px;">最终选择的协变量 ({len(lasso_selection.get('selected_covariates', []))}个):</div>
            <div class="tag-list">
                {''.join([f'<span class="tag">{cov}</span>' for cov in lasso_selection.get('selected_covariates', [])])}
            </div>
        </div>
    </div>
"""

        method_text = '使用倾向性匹配方法' if self.method == 'psm' else '使用双重差分方法'
        robustness_display = robustness_text if 'robustness_text' in locals() else '待评估'
        
        html_content += f"""
    <div class="section">
        <h2 class="section-title">7. 结论与建议</h2>
        <div class="interpretation">
            <h4>主要发现</h4>
            <p>
                {method_text}分析结果显示，
                <strong>{self.treatment}</strong> 对 <strong>{self.outcome}</strong> 
                {self.get_significance_label(ate.get('pValue', 1))}的因果效应为
                <strong>{self.format_number(ate.get('estimate'))}</strong>。
            </p>
            <p style="margin-top: 15px;">
                稳健性检验结果表明，研究结论的整体稳健性为<strong>{robustness_display}</strong>。
            </p>
            <h4 style="margin-top: 20px;">研究局限</h4>
            <p>
                本分析基于观测数据，虽然控制了可观测的混淆变量，但仍可能存在未观测的混淆因素。
                敏感性分析显示，当未观测混杂的关联强度超过一定阈值时，结论可能受到影响。
                建议结合领域知识和其他研究方法进一步验证。
            </p>
        </div>
    </div>

    <div class="footer">
        <p>本报告由因果推断分析工具自动生成</p>
        <p style="margin-top: 5px;">生成时间: {analysis_date}</p>
    </div>
</body>
</html>
"""
        return html_content

    def generate_report(self, format='html'):
        if format == 'html':
            return self.generate_html_report()
        else:
            raise ValueError(f"Unsupported format: {format}")

    def save_report(self, output_path, format='html'):
        content = self.generate_report(format)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return output_path
