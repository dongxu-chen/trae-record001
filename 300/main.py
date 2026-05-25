import argparse
import sys
from sequence_alignment import NeedlemanWunsch, SmithWaterman
from substitution_matrices import SubstitutionMatrix
from multiple_alignment import ProgressiveAlignment, SequenceDatabase
from visualization import (
    print_score_matrix, 
    print_alignment, 
    print_multiple_alignment,
    print_alignment_statistics,
    print_search_results,
    print_detailed_alignment,
    print_all_alignments_summary,
    print_local_alignment_details,
    print_substitution_matrix,
    print_memory_comparison,
    create_html_visualization,
    create_msa_html_visualization
)

def run_demo():
    print("=" * 60)
    print("生物序列比对算法演示 (增强版)")
    print("=" * 60)
    print("新增功能:")
    print("  ✅ 渐进式多序列比对")
    print("  ✅ 序列数据库搜索")
    print("  ✅ 比对统计与保守区域分析")
    print("=" * 60)
    
    print("\n" + "=" * 60)
    print("1. 多序列比对演示")
    print("=" * 60)
    
    protein_sequences = {
        'Seq1': 'MVLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSHGSAQVKGHGKKVADALTNAVAHVDDMPNALSALSDLHAHKLRVDPVNFKLLSHCLLVTLAAHLPAEFTPAVHASLDKFLASVSTVLTSKYR',
        'Seq2': 'MVLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSHGSAQVKGHGKKVADALTNAVAHVDDMPNALSALSDLHAHKLRVDPVNFKLLSHCLLVTLAAHLPAEFTPAVHASLDKFLASVSTVLTSKYR',
        'Seq3': 'MVLSAADKTNVKAAWSKVGGHAGEYGAEALERMFLGFPTTKTYFPHFDLSHGSAQVKAHGKKVGDALTLAVGHLDDLPGALSNLSDLHAHKLRVDPVNFKLLSHCLLSTLAVHLPNDFTPAVHASLDKFLSTVSTVLTSKYR',
        'Seq4': 'HVVDADEEKALLKLWKKVGEHARDIAAELERLFPILTIKTYFAHLDSSGSQVLKSHGKKVSEVLKAVGTILKDLPGVLSTIGAISARVQVDPANFKILYNICILVAIASHFPDDFTPEVHIAVDKFLTNLSRVMREYFA',
    }
    
    msa = ProgressiveAlignment(seq_type='protein', gap_penalty=-2, matrix_type='blosum62')
    msa.add_sequences(protein_sequences)
    msa.align()
    
    print_multiple_alignment(msa, line_width=60)
    print_alignment_statistics(msa)
    create_msa_html_visualization(msa, "msa_protein.html")
    
    print("\n" + "=" * 60)
    print("2. 序列数据库搜索演示")
    print("=" * 60)
    
    db = SequenceDatabase(seq_type='protein')
    db.add_sequences({
        'Hemoglobin_A': 'MVLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSHGSAQVKGHGKKVADALTNAVAHVDDMPNALSALSDLHAHKLRVDPVNFKLLSHCLLVTLAAHLPAEFTPAVHASLDKFLASVSTVLTSKYR',
        'Hemoglobin_B': 'MVHLTPEEKSAVTALWGKVNVDEVGGEALGRLLVVYPWTQRFFESFGDLSTPDAVMGNPKVKAHGKKVLGAFSDGLAHLDNLKGTFATLSELHCDKLHVDPENFRLLGNVLVCVLAHHFGKEFTPPVQAAYQKVVAGVANALAHKYH',
        'Myoglobin': 'MGLSDGEWQLVLNVWGKVEADIPGHGQEVLIRLFKGHPETLEKFDKFKHLKSEDEMKASEDLKKHGATVLTALGGILKKKGHHEAEIKPLAQSHATKHKIPVKYLEFISECIIQVLQSKHPGDFGADAQGAMNKALELFRKDMASNYKELGFQG',
        'Insulin': 'MALWMRLLPLLALLALWGPDPAAAFVNQHLCGSHLVEALYLVCGERGFFYTPKTRREAEDLQVGQVELGGGPGAGSLQPLALEGSLQKRGIVEQCCTSICSLYQLENYCN',
        'Cytochrome_C': 'MGDVEKGKKIFIMKCSQCHTVEKGGKHKTGPNLHGLFGRKTGQAPGYSYTAANKNKGIIWGEDTLMEYLENPKKYIPGTKMIFVGIKKKEERADLIAYLKKATNE',
    })
    
    query = 'MVLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHF'
    print(f"查询序列: {query}")
    print()
    
    results = db.search(query, top_k=3, gap_penalty=-2)
    print_search_results(results, "全局")
    
    for name, score, aligned1, aligned2, aligner in results[:1]:
        print_detailed_alignment(name, aligned1, aligned2, aligner)
    
    print("\n" + "=" * 60)
    print("3. DNA多序列比对与统计")
    print("=" * 60)
    
    dna_sequences = {
        'DNA1': 'ATCGATCGATCGATCG',
        'DNA2': 'ATCGATCGATCGATGG',
        'DNA3': 'ATCGATCGTTAGATCG',
        'DNA4': 'ATCGTTCGATCGATCG',
    }
    
    dna_msa = ProgressiveAlignment(seq_type='dna', gap_penalty=-1, matrix_type='dna')
    dna_msa.add_sequences(dna_sequences)
    dna_msa.align()
    
    print_multiple_alignment(dna_msa, line_width=50)
    print_alignment_statistics(dna_msa)
    create_msa_html_visualization(dna_msa, "msa_dna.html")
    
    print("\n" + "=" * 60)
    print("4. 双序列比对 - 多解模式")
    print("=" * 60)
    
    nw_multi = NeedlemanWunsch('ABC', 'AC', gap_penalty=-1,
                               matrix_type='blosum62', seq_type='protein',
                               use_rolling=True, find_all_solutions=True, max_solutions=100)
    nw_multi.align()
    print_memory_comparison(nw_multi)
    print_all_alignments_summary(nw_multi)
    
    print("\n" + "=" * 60)
    print("演示完成！生成的HTML文件:")
    print("- msa_protein.html (蛋白质多序列比对)")
    print("- msa_dna.html (DNA多序列比对)")
    print("=" * 60)

def main():
    parser = argparse.ArgumentParser(
        description='生物序列比对工具 (增强版) - 支持多序列比对和数据库搜索',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  运行完整演示:
    python main.py --demo
  
  双序列全局比对:
    python main.py --seq1 HEAGAWGHE --seq2 PAWHEAE --global --type protein --matrix blosum62
  
  多序列比对:
    python main.py --msa seq1:HEAGAWGHE seq2:PAWHEAE seq3:PEAHEAE --type protein
  
  数据库搜索:
    python main.py --search --query HEAGAWGHE --db seq1:HEAGAWGHE seq2:PAWHEAE seq3:PEAHEAE --top 5
  
  生成HTML可视化:
    python main.py --msa seq1:ABC seq2:AC seq3:AC --type protein --html msa.html
        """
    )
    
    parser.add_argument('--demo', action='store_true', help='运行演示程序')
    parser.add_argument('--seq1', type=str, help='第一条序列 (双序列比对)')
    parser.add_argument('--seq2', type=str, help='第二条序列 (双序列比对)')
    parser.add_argument('--global', dest='global_align', action='store_true', help='使用Needleman-Wunsch全局比对')
    parser.add_argument('--local', action='store_true', help='使用Smith-Waterman局部比对')
    
    parser.add_argument('--msa', nargs='+', help='多序列比对，格式: name1:seq1 name2:seq2 ...')
    parser.add_argument('--search', action='store_true', help='数据库搜索模式')
    parser.add_argument('--query', type=str, help='查询序列 (数据库搜索)')
    parser.add_argument('--db', nargs='+', help='数据库序列，格式: name1:seq1 name2:seq2 ...')
    parser.add_argument('--top', type=int, default=5, help='显示Top K结果 (数据库搜索)')
    
    parser.add_argument('--type', type=str, default='protein', choices=['protein', 'dna'], help='序列类型 (protein/dna)')
    parser.add_argument('--matrix', type=str, default='blosum62', choices=['blosum62', 'pam250', 'dna'], help='替换矩阵类型')
    parser.add_argument('--gap', type=int, default=-2, help='缺口惩罚值')
    parser.add_argument('--no-rolling', dest='no_rolling', action='store_true', help='禁用滚动数组优化')
    parser.add_argument('--all', dest='find_all', action='store_true', help='查找所有最优解 (双序列比对)')
    parser.add_argument('--max-solutions', type=int, default=100, help='最大解数量')
    parser.add_argument('--show-matrix', action='store_true', help='显示得分矩阵')
    parser.add_argument('--show-traceback', action='store_true', help='显示回溯箭头')
    parser.add_argument('--show-all', dest='show_all_results', action='store_true', help='显示所有比对结果')
    parser.add_argument('--show-stats', action='store_true', help='显示比对统计信息')
    parser.add_argument('--show-submatrix', action='store_true', help='显示替换矩阵')
    parser.add_argument('--show-memory', action='store_true', help='显示内存对比')
    parser.add_argument('--html', type=str, help='生成HTML可视化文件')
    
    args = parser.parse_args()
    
    if args.demo:
        run_demo()
        return
    
    if args.msa:
        seq_dict = {}
        for item in args.msa:
            if ':' in item:
                name, seq = item.split(':', 1)
                seq_dict[name.strip()] = seq.strip()
        
        if len(seq_dict) < 2:
            print("错误: 多序列比对需要至少2条序列")
            return
        
        msa = ProgressiveAlignment(
            seq_type=args.type,
            gap_penalty=args.gap,
            matrix_type=args.matrix
        )
        msa.add_sequences(seq_dict)
        msa.align()
        
        print_multiple_alignment(msa)
        
        if args.show_stats:
            print_alignment_statistics(msa)
        
        if args.html:
            create_msa_html_visualization(msa, args.html)
        
        return
    
    if args.search:
        if not args.query:
            print("错误: 请提供查询序列 --query")
            return
        
        db = SequenceDatabase(seq_type=args.type)
        if args.db:
            seq_dict = {}
            for item in args.db:
                if ':' in item:
                    name, seq = item.split(':', 1)
                    seq_dict[name.strip()] = seq.strip()
            db.add_sequences(seq_dict)
        
        if not db.get_all_sequences():
            print("错误: 请提供数据库序列 --db")
            return
        
        results = db.search(args.query, top_k=args.top, gap_penalty=args.gap)
        print_search_results(results)
        
        for name, score, aligned1, aligned2, aligner in results[:1]:
            if args.show_all_results:
                print_detailed_alignment(name, aligned1, aligned2, aligner)
        
        return
    
    if not args.seq1 or not args.seq2:
        parser.print_help()
        return
    
    if not args.global_align and not args.local:
        print("请指定 --global 或 --local")
        return
    
    if args.show_submatrix:
        sub_matrix = SubstitutionMatrix(args.matrix, args.type)
        print_substitution_matrix(sub_matrix)
    
    use_rolling = not args.no_rolling
    
    if args.global_align:
        aligner = NeedlemanWunsch(
            args.seq1, args.seq2, 
            gap_penalty=args.gap,
            matrix_type=args.matrix,
            seq_type=args.type,
            use_rolling=use_rolling,
            find_all_solutions=args.find_all,
            max_solutions=args.max_solutions
        )
        aligner.align()
        
        if args.show_memory:
            print_memory_comparison(aligner)
        
        if args.show_matrix:
            print_score_matrix(aligner, show_traceback=args.show_traceback)
        
        print_alignment(aligner, "全局", show_all=args.show_all_results)
        
        if args.html:
            create_html_visualization(aligner, args.html, show_all=args.show_all_results)
    
    if args.local:
        aligner = SmithWaterman(
            args.seq1, args.seq2, 
            gap_penalty=args.gap,
            matrix_type=args.matrix,
            seq_type=args.type,
            use_rolling=use_rolling,
            find_all_solutions=args.find_all,
            max_solutions=args.max_solutions
        )
        aligner.align()
        
        if args.show_matrix:
            print_score_matrix(aligner, show_traceback=args.show_traceback)
        
        print_alignment(aligner, "局部", show_all=args.show_all_results)
        print_local_alignment_details(aligner)
        
        if args.html:
            create_html_visualization(aligner, args.html, show_all=args.show_all_results)

if __name__ == "__main__":
    main()
