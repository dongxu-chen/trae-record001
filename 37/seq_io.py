import gzip


class Sequence:
    def __init__(self, identifier, sequence, quality=None, description=""):
        self.id = identifier
        self.seq = sequence
        self.quality = quality
        self.description = description

    def __len__(self):
        return len(self.seq)

    def __repr__(self):
        return f"Sequence(id={self.id}, len={len(self)})"


def _open_file(file_path, mode='rt'):
    if file_path.endswith('.gz'):
        return gzip.open(file_path, mode, encoding='utf-8')
    else:
        return open(file_path, mode, encoding='utf-8')


def _detect_format_from_content(lines):
    if not lines:
        return None
    first_line = lines[0]
    if first_line.startswith('>'):
        return 'fasta'
    elif first_line.startswith('@'):
        return 'fastq'
    return None


def read_fasta(file_path):
    sequences = []
    current_id = None
    current_desc = ""
    current_seq = []

    with _open_file(file_path, 'rt') as f:
        for line in f:
            line = line.rstrip('\n\r')
            if not line:
                continue
            if line.startswith('>'):
                if current_id is not None:
                    sequences.append(Sequence(
                        identifier=current_id,
                        sequence=''.join(current_seq),
                        description=current_desc
                    ))
                parts = line[1:].split(None, 1)
                current_id = parts[0]
                current_desc = parts[1] if len(parts) > 1 else ""
                current_seq = []
            else:
                current_seq.append(line)
        
        if current_id is not None:
            sequences.append(Sequence(
                identifier=current_id,
                sequence=''.join(current_seq),
                description=current_desc
            ))
    
    return sequences


def read_fastq(file_path):
    sequences = []
    
    with _open_file(file_path, 'rt') as f:
        while True:
            header = f.readline()
            if not header:
                break
            header = header.rstrip('\n\r')
            if not header.startswith('@'):
                raise ValueError(f"Expected FASTQ header starting with '@', got: {header}")
            
            seq_line = f.readline().rstrip('\n\r')
            plus_line = f.readline()
            qual_line = f.readline().rstrip('\n\r')
            
            parts = header[1:].split(None, 1)
            seq_id = parts[0]
            desc = parts[1] if len(parts) > 1 else ""
            
            sequences.append(Sequence(
                identifier=seq_id,
                sequence=seq_line,
                quality=qual_line,
                description=desc
            ))
    
    return sequences


def read_sequence_file(file_path):
    base_path = file_path[:-3] if file_path.endswith('.gz') else file_path
    
    if base_path.endswith('.fastq') or base_path.endswith('.fq'):
        return read_fastq(file_path)
    elif base_path.endswith('.fasta') or base_path.endswith('.fa'):
        return read_fasta(file_path)
    else:
        try:
            return read_fasta(file_path)
        except Exception:
            try:
                return read_fastq(file_path)
            except Exception:
                raise ValueError(f"Unable to determine file format for: {file_path}")


def read_fasta_gzip(file_path):
    return read_fasta(file_path)


def read_fastq_gzip(file_path):
    return read_fastq(file_path)


def write_fasta(file_path, sequences, line_width=60):
    with _open_file(file_path, 'wt') as f:
        for seq in sequences:
            header = f">{seq.id}"
            if seq.description:
                header += f" {seq.description}"
            f.write(header + '\n')
            for i in range(0, len(seq.seq), line_width):
                f.write(seq.seq[i:i+line_width] + '\n')


def write_fastq(file_path, sequences):
    with _open_file(file_path, 'wt') as f:
        for seq in sequences:
            header = f"@{seq.id}"
            if seq.description:
                header += f" {seq.description}"
            f.write(header + '\n')
            f.write(seq.seq + '\n')
            f.write('+\n')
            qual = seq.quality if seq.quality else 'I' * len(seq.seq)
            f.write(qual + '\n')
