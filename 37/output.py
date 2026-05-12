import datetime


def generate_sam_header(reference_id, reference_length, program_name="simple_sw", program_version="1.0"):
    headers = []
    
    headers.append(f"@HD\tVN:1.6\tSO:unsorted")
    headers.append(f"@SQ\tSN:{reference_id}\tLN:{reference_length}")
    headers.append(f"@PG\tID:{program_name}\tPN:{program_name}\tVN:{program_version}\tCL:smith_waterman_alignment")
    
    return headers


def alignment_to_sam(query_id, query_seq, query_qual, alignment_result, reference_id, mapq=255):
    is_unmapped = alignment_result.score == 0
    
    flag = 4 if is_unmapped else 0
    
    if is_unmapped:
        rname = '*'
        pos = 0
        mapq_val = 0
        cigar = '*'
        rnext = '*'
        pnext = 0
        tlen = 0
        seq = query_seq if query_seq else '*'
        qual = query_qual if query_qual else '*'
    else:
        rname = reference_id
        pos = alignment_result.start_ref + 1
        mapq_val = mapq
        cigar = alignment_result.cigar
        rnext = '*'
        pnext = 0
        tlen = 0
        seq = query_seq
        qual = query_qual if query_qual else '*'
    
    tags = []
    if not is_unmapped:
        tags.append(f"AS:i:{alignment_result.score}")
    
    fields = [
        query_id,
        str(flag),
        rname,
        str(pos),
        str(mapq_val),
        cigar,
        rnext,
        str(pnext),
        str(tlen),
        seq,
        qual,
    ]
    fields.extend(tags)
    
    return '\t'.join(fields)


def write_sam(file_path, query_sequences, reference_sequences, alignments, program_name="simple_sw", program_version="1.0"):
    ref = reference_sequences[0] if reference_sequences else None
    
    with open(file_path, 'w') as f:
        if ref:
            headers = generate_sam_header(ref.id, len(ref.seq), program_name, program_version)
            for header in headers:
                f.write(header + '\n')
        
        for i, (query, alignment) in enumerate(zip(query_sequences, alignments)):
            ref_id = ref.id if ref else '*'
            sam_line = alignment_to_sam(
                query_id=query.id,
                query_seq=query.seq,
                query_qual=query.quality,
                alignment_result=alignment,
                reference_id=ref_id
            )
            f.write(sam_line + '\n')


def print_alignment(alignment_result, query_id, ref_id):
    print(f"\n=== Alignment Result ===")
    print(f"Query: {query_id}")
    print(f"Reference: {ref_id}")
    print(f"Score: {alignment_result.score}")
    print(f"CIGAR: {alignment_result.cigar}")
    print(f"Query range: [{alignment_result.start_query}, {alignment_result.end_query}]")
    print(f"Reference range: [{alignment_result.start_ref}, {alignment_result.end_ref}]")
    print()
    print(f"Query: {alignment_result.query_aligned}")
    print(f"Ref:   {alignment_result.ref_aligned}")
    print()
