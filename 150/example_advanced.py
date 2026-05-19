#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MS Peak Detector - 高级功能示例
展示谱库搜索、PTM鉴定、TMT定量和标准格式输出
"""

import numpy as np
import sys
sys.path.insert(0, '.')

from ms_peak_detector import (
    # 谱库搜索
    SpectralLibrary,
    SpectralMatcher,
    create_example_library,
    
    # PTM鉴定
    PTMDatabase,
    PeptideFragmenter,
    PTMIdentifier,
    
    # 定量分析
    ReporterIonQuantitation,
    PeptideQuantitation,
    ProteinQuantitation,
    RatioCalculation,
    QuantitationPipeline,
    
    # 文件输出
    SimpleFileWriter,
    ResultExporter
)


def example_1_spectral_library_search():
    """示例1: 谱库搜索"""
    print("=" * 70)
    print("示例1: 谱库搜索 - 与已知谱图比对")
    print("=" * 70)
    
    # 创建示例谱库
    lib = create_example_library()
    
    # 查看库统计
    stats = lib.get_library_stats()
    print(f"谱库统计:")
    print(f"  - 总条目数: {stats['total_entries']}")
    print(f"  - 电荷分布: {stats.get('charge_distribution', {})}")
    
    # 生成查询谱图
    mz = np.array([50.5, 72.04, 103.05, 171.11, 205.1, 246.11, 286.17, 330.20])
    intensity = np.array([50, 80, 100, 150, 120, 60, 90, 70])
    
    print(f"\n查询谱图包含 {len(mz)} 个峰")
    
    # 搜索谱库
    results = lib.search_spectrum(mz, intensity, top_n=5)
    
    print(f"\n搜索结果 (Top 5):")
    for i, result in enumerate(results):
        entry = result['entry']
        print(f"  匹配 {i+1}: {entry['name']}")
        print(f"    序列: {entry.get('sequence', 'N/A')}")
        print(f"    前体m/z: {entry['precursor_mz']:.4f}")
        print(f"    匹配分数: {result['score']:.4f}")
    
    # 使用SpectralMatcher
    matcher = SpectralMatcher(lib)
    match_result = matcher.match_ms2_spectrum(
        mz, intensity, precursor_mz=246.1145, precursor_charge=2, score_threshold=0.1
    )
    
    if match_result['best_match']:
        print(f"\n最佳匹配: {match_result['best_match']['entry']['name']}")
        print(f"匹配分数: {match_result['best_match']['score']:.4f}")
    
    print()
    return True


def example_2_ptm_identification():
    """示例2: 翻译后修饰(PTM)鉴定"""
    print("=" * 70)
    print("示例2: 翻译后修饰(PTM)鉴定")
    print("=" * 70)
    
    # 查看支持的PTM类型
    ptm_db = PTMDatabase()
    all_mods = ptm_db.get_all_modifications()
    
    print(f"支持的PTM类型 (共{len(all_mods)}种):")
    for mod in all_mods[:10]:
        print(f"  - {mod['name']}: {mod['mass_shift']:.4f} Da")
    if len(all_mods) > 10:
        print(f"  ... 还有 {len(all_mods) - 10} 种")
    
    # 肽段碎裂
    fragmenter = PeptideFragmenter()
    sequence = "ACDEFGHIK"
    
    # 未修饰肽段
    fragments_unmodified = fragmenter.fragment_peptide(sequence, charge=2)
    print(f"\n肽段 '{sequence}' 碎裂结果:")
    print(f"  前体m/z: {fragments_unmodified['precursor_mz']:.4f}")
    print(f"  b离子数: {len(fragments_unmodified['b_ions'])}")
    print(f"  y离子数: {len(fragments_unmodified['y_ions'])}")
    
    # 生成带修饰的模拟谱图 (模拟磷酸化)
    phospho_mass = 79.966331
    mz_values = []
    intensity_values = []
    
    for ion in fragments_unmodified['b_ions'][:10]:
        if ion['position'] > 2:
            mz_values.append(ion['mz'] + phospho_mass / 2)
        else:
            mz_values.append(ion['mz'])
        intensity_values.append(np.random.uniform(50, 200))
    
    for ion in fragments_unmodified['y_ions'][:10]:
        mz_values.append(ion['mz'])
        intensity_values.append(np.random.uniform(30, 150))
    
    mz = np.array(mz_values)
    intensity = np.array(intensity_values)
    
    # PTM鉴定
    ptm_id = PTMIdentifier()
    ptm_results = ptm_id.identify_ptms(
        mz, intensity, sequence, charge=2,
        mods_to_check=["phosphorylation", "acetylation"]
    )
    
    print(f"\nPTM鉴定结果:")
    for i, result in enumerate(ptm_results[:5]):
        mod = result['modification']
        print(f"  {i+1}. {mod['name']} 位置 {mod['position']} ({mod['amino_acid']})")
        print(f"     Delta分数: {result['delta_score']:.4f}, 分数比: {result['score_ratio']:.4f}")
    
    # 定位分数
    if ptm_results:
        best_mod = ptm_results[0]['modification']
        loc_score = ptm_id.get_localization_score(
            sequence, best_mod['position'], mz, intensity, best_mod['mass_shift'], charge=2
        )
        print(f"\n最佳修饰定位分数: {loc_score['localization_score']:.4f}")
        print(f"匹配离子数: {loc_score['matched_ions']}/{loc_score['total_expected_ions']}")
    
    print()
    return True


def example_3_tmt_quantitation():
    """示例3: TMT/iTRAQ定量分析"""
    print("=" * 70)
    print("示例3: TMT/iTRAQ定量分析")
    print("=" * 70)
    
    # 报告离子定量
    reporter_quant = ReporterIonQuantitation()
    
    # 查看TMT-10plex报告离子
    tmt_ions = reporter_quant.get_reporter_ions("TMT_10plex")
    print(f"TMT-10plex 报告离子:")
    for name, mz in tmt_ions.items():
        print(f"  - {name}: {mz:.4f} Da")
    
    # 生成模拟MS2谱图，包含报告离子峰
    mz_values = []
    intensity_values = []
    
    # 添加报告离子峰
    for name, mz in tmt_ions.items():
        mz_values.append(mz + np.random.normal(0, 0.005))
        intensity_values.append(np.random.uniform(500, 2000))
    
    # 添加一些碎片离子
    for i in range(50):
        mz_values.append(np.random.uniform(100, 1500))
        intensity_values.append(np.random.uniform(50, 500))
    
    mz = np.array(mz_values)
    intensity = np.array(intensity_values)
    
    # 定量单个谱图
    quant_result = reporter_quant.quantitate_spectrum(mz, intensity, kit="TMT_10plex", method="max")
    
    print(f"\n报告离子定量结果:")
    for channel, value in quant_result.items():
        print(f"  {channel}: {value:.2f}")
    
    # 模拟多个PSM并进行肽段/蛋白定量
    print(f"\n模拟批量定量分析...")
    
    # 生成多个MS2谱图
    ms2_spectra = []
    for i in range(20):
        mz_values = []
        intensity_values = []
        for name, mz in tmt_ions.items():
            mz_values.append(mz + np.random.normal(0, 0.005))
            intensity_values.append(np.random.uniform(300, 2500))
        ms2_spectra.append({
            "mz": np.array(mz_values),
            "intensity": np.array(intensity_values),
            "id": f"spec_{i}"
        })
    
    # 生成PSM分配
    psm_assignments = []
    peptides = ["ACDEFGHIK", "LMNOPQRST", "UVWXYZA", "BCDEFGHIJ", "KLMNOPQ"]
    for i in range(20):
        psm_assignments.append({
            "sequence": peptides[i % len(peptides)],
            "protein": f"P{i % 3:06d}",
            "score": np.random.uniform(0.5, 1.0)
        })
    
    # 生成肽段到蛋白的映射
    peptide_to_protein = {
        "ACDEFGHIK": ["P00000", "P00001"],
        "LMNOPQRST": ["P00000"],
        "UVWXYZA": ["P00001", "P00002"],
        "BCDEFGHIJ": ["P00002"],
        "KLMNOPQ": ["P00000", "P00002"]
    }
    
    # 运行完整定量流程
    quant_pipeline = QuantitationPipeline()
    full_quant = quant_pipeline.run_full_quantitation(
        ms2_spectra, psm_assignments, peptide_to_protein,
        kit="TMT_10plex", reference_channel="TMT126"
    )
    
    print(f"\n肽段定量结果 ({len(full_quant['peptide_quantitation'])} 个肽段):")
    for peptide, data in list(full_quant['peptide_quantitation'].items())[:3]:
        print(f"  {peptide}:")
        print(f"    PSM数: {data['n_psms']}")
        for ch, val in list(data['mean'].items())[:5]:
            print(f"    {ch}: {val:.2f}")
        if 'log2_ratios' in data:
            for ch, val in list(data['log2_ratios'].items())[:3]:
                if ch != "TMT126":
                    print(f"    log2({ch}/126): {val:.4f}")
    
    print(f"\n蛋白定量结果 ({len(full_quant['protein_quantitation'])} 个蛋白):")
    for protein, data in full_quant['protein_quantitation'].items():
        print(f"  {protein}: {data['n_peptides']} 个肽段")
    
    print()
    return True


def example_4_file_export():
    """示例4: 标准格式输出 (mzML, mzTab, CSV/TSV)"""
    print("=" * 70)
    print("示例4: 标准格式输出 (mzML, mzTab, CSV/TSV)")
    print("=" * 70)
    
    # 生成模拟质谱数据
    print("生成模拟谱图数据...")
    spectra = []
    for i in range(5):
        mz = np.linspace(100, 1500, 1000)
        intensity = np.zeros_like(mz)
        
        for j in range(50):
            peak_pos = np.random.uniform(100, 1500)
            peak_height = np.random.uniform(100, 5000)
            intensity += peak_height * np.exp(-(mz - peak_pos)**2 / (2 * 0.1**2))
        
        spectra.append({
            "mz": mz,
            "intensity": intensity,
            "ms_level": 1 if i < 3 else 2
        })
    
    # 写入mzML
    import os
    if not os.path.exists("output"):
        os.makedirs("output")
    
    mzml_path = "output/example_data.mzML"
    writer = SimpleFileWriter()
    writer.mzml_writer.write_mzml(spectra, mzml_path, instrument="Orbitrap Fusion", sample_name="Sample_A")
    print(f"✓ mzML文件已写入: {mzml_path}")
    
    # 写入谱图CSV
    csv_path = "output/spectrum_0.csv"
    writer.write_spectrum_csv(spectra[0]["mz"], spectra[0]["intensity"], csv_path)
    print(f"✓ 谱图CSV已写入: {csv_path}")
    
    # 模拟定量数据
    quant_data = {
        "protein_quantitation": {
            "P00001": {
                "n_peptides": 5,
                "mean": {f"TMT{i}": np.random.uniform(1000, 5000) for i in range(10)}
            },
            "P00002": {
                "n_peptides": 3,
                "mean": {f"TMT{i}": np.random.uniform(800, 4000) for i in range(10)}
            }
        },
        "peptide_quantitation": {
            "ACDEFGHIK": {
                "n_psms": 3,
                "mean": {f"TMT{i}": np.random.uniform(500, 2000) for i in range(10)}
            }
        }
    }
    
    # 写入mzTab
    mztab_path = "output/example_quant.mzTab"
    writer.mztab_writer.write_mztab(quant_data, mztab_path)
    print(f"✓ mzTab文件已写入: {mztab_path}")
    
    # 写入定量TSV
    tsv_path = "output/protein_quant.tsv"
    writer.write_quantification_tsv(quant_data["protein_quantitation"], tsv_path, "protein")
    print(f"✓ 蛋白定量TSV已写入: {tsv_path}")
    
    # 使用ResultExporter批量导出
    print("\n使用ResultExporter批量导出...")
    exporter = ResultExporter(output_dir="output")
    
    ptm_results = [
        {
            "modification": {"name": "phosphorylation", "position": 2, "amino_acid": "S"},
            "delta_score": 0.5,
            "score_ratio": 1.5
        }
    ]
    
    export_results = {
        "peak_data": [{"mz": 500.0, "intensity": 1000.0, "charge": 2, "score": 0.9}],
        "quantification": quant_data,
        "ptm_results": ptm_results,
        "mztab_data": quant_data
    }
    
    exported_files = exporter.export_all(export_results, prefix="full_export")
    
    print("批量导出文件:")
    for file_type, path in exported_files.items():
        print(f"  {file_type}: {path}")
    
    print()
    return True


def main():
    print("MS Peak Detector v0.2 - 高级功能示例")
    print("=" * 70)
    print("包含功能: 谱库搜索、PTM鉴定、TMT定量、标准格式输出\n")
    
    examples = [
        example_1_spectral_library_search,
        example_2_ptm_identification,
        example_3_tmt_quantitation,
        example_4_file_export
    ]
    
    passed = 0
    failed = 0
    
    for example in examples:
        try:
            if example():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ 示例执行失败: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("=" * 70)
    print(f"执行总结: {passed}/{passed + failed} 个示例成功")
    print("=" * 70)
    
    if failed == 0:
        print("\n所有示例执行成功! ✓")
        print("\n新功能总览:")
        print("  1. 谱库搜索 - 基于余弦相似度的谱图匹配")
        print("  2. PTM鉴定 - 支持16种常见修饰，包含定位分数")
        print("  3. 定量分析 - TMT/iTRAQ报告离子定量，支持肽段/蛋白水平汇总")
        print("  4. 格式输出 - mzML、mzTab、CSV/TSV标准格式")
        return 0
    else:
        print("\n部分示例执行失败! ✗")
        return 1


if __name__ == "__main__":
    sys.exit(main())
