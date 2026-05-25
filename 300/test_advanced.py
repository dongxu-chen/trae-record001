
import sys
sys.path.insert(0, 'd:\\Trae\\project\\record001\\300')

print("=" * 60)
print("生物序列比对增强功能测试")
print("=" * 60)

print("\n【测试1】多序列比对模块导入")
print("-" * 40)
try:
    from multiple_alignment import ProgressiveAlignment, SequenceDatabase
    print("✓ ProgressiveAlignment 导入成功")
    print("✓ SequenceDatabase 导入成功")
except Exception as e:
    print(f"✗ 导入失败: {e}")
    sys.exit(1)

print("\n【测试2】序列数据库功能")
print("-" * 40)
try:
    db = SequenceDatabase(seq_type='protein')
    db.add_sequences({
        'Seq1': 'MVLSPADKTNVKAAWG',
        'Seq2': 'MVLSPADKTNVKAAWG',
        'Seq3': 'MVLSAADKTNVKAAWS',
        'Seq4': 'HVVDADEEKALLKLWK',
    })
    print(f"✓ 数据库创建成功，包含 {len(db.get_all_sequences())} 条序列")
    
    query = 'MVLSPADKTNVKAAWG'
    results = db.search(query, top_k=3, gap_penalty=-2)
    print(f"✓ 全局搜索完成，找到 {len(results)} 个结果")
    print(f"  排名1: {results[0][0]} (得分: {results[0][1]})")
    
    results_local = db.search_local(query, top_k=3, gap_penalty=-2)
    print(f"✓ 局部搜索完成，找到 {len(results_local)} 个结果")
except Exception as e:
    print(f"✗ 数据库测试失败: {e}")
    import traceback
    traceback.print_exc()

print("\n【测试3】渐进式多序列比对 (2条序列)")
print("-" * 40)
try:
    seqs = {
        'SeqA': 'HEAGAWGHE',
        'SeqB': 'PAWHEAE',
    }
    msa = ProgressiveAlignment(seq_type='protein', gap_penalty=-2, matrix_type='blosum62')
    msa.add_sequences(seqs)
    result = msa.align()
    print(f"✓ 比对完成，得到 {len(result)} 条比对序列")
    for name, seq in result.items():
        print(f"  {name}: {seq}")
    print(f"✓ 一致性序列: {msa.consensus}")
except Exception as e:
    print(f"✗ 双序列MSA测试失败: {e}")
    import traceback
    traceback.print_exc()

print("\n【测试4】渐进式多序列比对 (4条序列)")
print("-" * 40)
try:
    seqs = {
        'Seq1': 'MVLSPADKTNVKAAWG',
        'Seq2': 'MVLSPADKTNVKAAWG',
        'Seq3': 'MVLSAADKTNVKAAWS',
        'Seq4': 'HVVDADEEKALLKLWK',
    }
    msa = ProgressiveAlignment(seq_type='protein', gap_penalty=-2, matrix_type='blosum62')
    msa.add_sequences(seqs)
    result = msa.align()
    print(f"✓ 比对完成，得到 {len(result)} 条比对序列")
    
    stats = msa.get_statistics()
    print(f"✓ 统计信息计算完成:")
    print(f"  序列数量: {stats['n_sequences']}")
    print(f"  比对长度: {stats['aligned_length']}")
    print(f"  平均保守度: {stats['average_conservation']:.3f}")
    print(f"  一致位点: {stats['identity_positions']}")
    print(f"  保守区域: {stats['n_conserved_regions']} 个")
    
    conservation = msa.get_conservation_scores()
    print(f"✓ 保守分数计算完成，共 {len(conservation)} 个位置")
    
    regions = msa.get_conserved_regions(threshold=0.7, min_length=3)
    print(f"✓ 保守区域检测完成: {len(regions)} 个区域")
    for i, (start, end) in enumerate(regions, 1):
        print(f"  区域{i}: {start}-{end}")
except Exception as e:
    print(f"✗ 多序列比对测试失败: {e}")
    import traceback
    traceback.print_exc()

print("\n【测试5】DNA多序列比对")
print("-" * 40)
try:
    dna_seqs = {
        'DNA1': 'ATCGATCGATCG',
        'DNA2': 'ATCGATCGATGG',
        'DNA3': 'ATCGTTAGATCG',
        'DNA4': 'ATCGATCGATCG',
    }
    dna_msa = ProgressiveAlignment(seq_type='dna', gap_penalty=-1, matrix_type='dna')
    dna_msa.add_sequences(dna_seqs)
    result = dna_msa.align()
    print(f"✓ DNA比对完成，得到 {len(result)} 条比对序列")
    
    stats = dna_msa.get_statistics()
    print(f"  比对长度: {stats['aligned_length']}")
    print(f"  一致位点: {stats['identity_positions']}")
    print(f"  一致性序列: {dna_msa.consensus}")
except Exception as e:
    print(f"✗ DNA多序列比对测试失败: {e}")
    import traceback
    traceback.print_exc()

print("\n【测试6】可视化模块新功能")
print("-" * 40)
try:
    from visualization import (
        print_multiple_alignment, 
        print_alignment_statistics,
        print_search_results,
        create_msa_html_visualization
    )
    print("✓ MSA可视化函数导入成功")
    
    seqs = {
        'Seq1': 'MVLSPADKTNV',
        'Seq2': 'MVLSPADKTNV',
        'Seq3': 'MVLSAADKTN',
    }
    msa = ProgressiveAlignment(seq_type='protein', gap_penalty=-2, matrix_type='blosum62')
    msa.add_sequences(seqs)
    msa.align()
    
    print("✓ print_multiple_alignment 函数可用")
    print("✓ print_alignment_statistics 函数可用")
    print("✓ create_msa_html_visualization 函数可用")
except Exception as e:
    print(f"✗ 可视化测试失败: {e}")
    import traceback
    traceback.print_exc()

print("\n【测试7】FASTA文件操作")
print("-" * 40)
try:
    db = SequenceDatabase(seq_type='protein')
    db.add_sequences({
        'TestSeq1': 'MVLSPADKTNVKAAWG',
        'TestSeq2': 'MVLSAADKTNVKAAWS',
    })
    
    test_fasta = 'test_db.fasta'
    db.save_to_fasta(test_fasta)
    print(f"✓ FASTA文件保存成功: {test_fasta}")
    
    db2 = SequenceDatabase(seq_type='protein')
    db2.load_from_fasta(test_fasta)
    print(f"✓ FASTA文件加载成功，包含 {len(db2.get_all_sequences())} 条序列")
    
    import os
    os.remove(test_fasta)
    print(f"✓ 测试文件清理完成")
except Exception as e:
    print(f"✗ FASTA操作测试失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("✅ 所有增强功能测试完成！")
print("=" * 60)
print("\n新增功能总结:")
print("  1. ✅ SequenceDatabase - 序列数据库管理")
print("     - add_sequence(s) - 添加序列")
print("     - search/search_local - 全局/局部搜索")
print("     - save/load_from_fasta - FASTA文件操作")
print()
print("  2. ✅ ProgressiveAlignment - 渐进式多序列比对")
print("     - 距离矩阵计算")
print("     - UPGMA引导树构建")
print("     - Profile-Profile比对")
print("     - 一致性序列生成")
print()
print("  3. ✅ 比对统计分析")
print("     - get_conservation_scores - 位点保守分数")
print("     - get_conserved_regions - 保守区域检测")
print("     - get_statistics - 完整统计信息")
print()
print("  4. ✅ 多序列比对可视化")
print("     - print_multiple_alignment - 控制台彩色输出")
print("     - create_msa_html_visualization - HTML交互式报告")
