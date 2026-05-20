import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.patches as mpatches


class AlignmentReport:
    def __init__(self):
        self.amino_acid_colors = {
            'A': '#8dd3c7', 'R': '#bebada', 'N': '#fb8072', 'D': '#80b1d3',
            'C': '#fdb462', 'Q': '#b3de69', 'E': '#fccde5', 'G': '#d9d9d9',
            'H': '#bc80bd', 'I': '#ccebc5', 'L': '#ffed6f', 'K': '#1f78b4',
            'M': '#33a02c', 'F': '#e31a1c', 'P': '#fdbf6f', 'S': '#ff7f00',
            'T': '#cab2d6', 'W': '#6a3d9a', 'Y': '#b15928', 'V': '#b2df8a',
            '-': '#ffffff'
        }
        
        self.dna_colors = {
            'A': '#4CAF50', 'T': '#F44336', 'U': '#F44336',
            'C': '#2196F3', 'G': '#FF9800', '-': '#ffffff', 'N': '#9E9E9E'
        }

    def _get_color(self, residue, seq_type='protein'):
        colors = self.amino_acid_colors if seq_type == 'protein' else self.dna_colors
        return colors.get(residue.upper(), '#cccccc')

    def create_alignment_page(self, aligned_sequences, names=None, 
                              title='Sequence Alignment', seq_type='protein',
                              line_width=50):
        n_seqs = len(aligned_sequences)
        if n_seqs == 0:
            return None
        
        if names is None:
            names = [f'seq_{i}' for i in range(n_seqs)]
        
        alignment_length = len(aligned_sequences[0])
        max_name_len = max(len(name) for name in names)
        
        n_lines = (alignment_length + line_width - 1) // line_width
        fig_height = min(11, 2 + n_seqs * n_lines * 0.4)
        
        fig, ax = plt.subplots(figsize=(12, fig_height))
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        
        ax.text(0.5, 0.98, title, fontsize=14, ha='center', va='top', fontweight='bold')
        
        char_width = 0.8 / line_width
        char_height = 0.7 / (n_seqs * n_lines)
        
        for line in range(n_lines):
            start = line * line_width
            end = min(start + line_width, alignment_length)
            
            line_y = 0.9 - line * (n_seqs + 1) * char_height
            
            for seq_idx in range(n_seqs):
                seq_y = line_y - seq_idx * char_height
                
                ax.text(0.01, seq_y + char_height/3, names[seq_idx], 
                       fontsize=8, ha='right', va='center', fontweight='bold')
                
                for pos in range(start, end):
                    char = aligned_sequences[seq_idx][pos]
                    x = 0.02 + (pos - start) * char_width
                    
                    color = self._get_color(char, seq_type)
                    rect = mpatches.Rectangle(
                        (x - char_width/2, seq_y), char_width, char_height * 0.8,
                        facecolor=color, edgecolor='gray', linewidth=0.3, alpha=0.8
                    )
                    ax.add_patch(rect)
                    
                    ax.text(x, seq_y + char_height/3, char, fontsize=7, 
                           ha='center', va='center', fontfamily='monospace')
            
            consensus_y = line_y - n_seqs * char_height
            for pos in range(start, end):
                residues = [aligned_sequences[i][pos] for i in range(n_seqs) 
                           if aligned_sequences[i][pos] != '-']
                if residues:
                    most_common = max(set(residues), key=residues.count)
                    count = residues.count(most_common)
                    if count / n_seqs >= 0.7:
                        x = 0.02 + (pos - start) * char_width
                        color = '#4CAF50'
                    elif count / n_seqs >= 0.4:
                        x = 0.02 + (pos - start) * char_width
                        color = '#FFC107'
                    else:
                        continue
                    
                    rect = mpatches.Rectangle(
                        (x - char_width/2, consensus_y), char_width, char_height * 0.6,
                        facecolor=color, edgecolor='none', alpha=0.6
                    )
                    ax.add_patch(rect)
        
        return fig

    def create_conservation_page(self, aligned_sequences, title='Conservation Analysis'):
        if not aligned_sequences:
            return None
        
        n_seqs = len(aligned_sequences)
        length = len(aligned_sequences[0])
        
        conservation = []
        for pos in range(length):
            residues = [seq[pos] for seq in aligned_sequences if seq[pos] != '-']
            if not residues:
                conservation.append(0.0)
            else:
                most_common = max(set(residues), key=residues.count)
                conservation.append(residues.count(most_common) / len(residues))
        
        fig, axes = plt.subplots(2, 1, figsize=(12, 8))
        
        ax1 = axes[0]
        ax1.plot(range(length), conservation, color='#2196F3', linewidth=1.5)
        ax1.fill_between(range(length), conservation, alpha=0.3, color='#2196F3')
        ax1.set_title('Position-wise Conservation', fontsize=12, fontweight='bold')
        ax1.set_xlabel('Position', fontsize=10)
        ax1.set_ylabel('Conservation Score', fontsize=10)
        ax1.set_ylim(0, 1.05)
        ax1.grid(True, alpha=0.3)
        ax1.axhline(y=0.7, color='red', linestyle='--', alpha=0.5, label='High Conservation (70%)')
        ax1.legend()
        
        ax2 = axes[1]
        window_size = min(20, length // 10)
        if window_size > 0:
            smoothed = np.convolve(conservation, np.ones(window_size)/window_size, mode='same')
            im = ax2.imshow(smoothed.reshape(1, -1), aspect='auto', cmap='RdYlGn', 
                           vmin=0, vmax=1, extent=[0, length, 0, 1])
            ax2.set_title('Conservation Heatmap (Smoothed)', fontsize=12, fontweight='bold')
            ax2.set_xlabel('Position', fontsize=10)
            ax2.set_yticks([])
            
            cbar = plt.colorbar(im, ax=ax2, orientation='horizontal', pad=0.2)
            cbar.set_label('Conservation', fontsize=9)
        
        fig.suptitle(title, fontsize=14, fontweight='bold', y=0.98)
        plt.tight_layout()
        return fig

    def create_similarity_matrix_page(self, similarity_matrix, names=None, 
                                       title='Sequence Similarity Matrix'):
        n = similarity_matrix.shape[0]
        if names is None:
            names = [f'seq_{i}' for i in range(n)]
        
        fig, ax = plt.subplots(figsize=(10, 8))
        
        im = ax.imshow(similarity_matrix, cmap='YlGnBu', vmin=0, vmax=1, aspect='equal')
        
        ax.set_xticks(range(n))
        ax.set_yticks(range(n))
        ax.set_xticklabels(names, rotation=45, ha='right', fontsize=9)
        ax.set_yticklabels(names, fontsize=9)
        
        for i in range(n):
            for j in range(n):
                color = 'white' if similarity_matrix[i, j] > 0.6 else 'black'
                ax.text(j, i, f'{similarity_matrix[i, j]:.2f}', 
                       ha='center', va='center', color=color, fontsize=8)
        
        cbar = plt.colorbar(im, ax=ax, shrink=0.8)
        cbar.set_label('Similarity', fontsize=10)
        
        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
        
        plt.tight_layout()
        return fig

    def create_blast_results_page(self, hits, query_id, title='BLAST Search Results'):
        if not hits:
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.text(0.5, 0.5, 'No significant hits found', ha='center', va='center', fontsize=14)
            ax.axis('off')
            ax.set_title(title, fontsize=14, fontweight='bold')
            return fig
        
        fig, axes = plt.subplots(2, 1, figsize=(12, 10))
        
        ax1 = axes[0]
        ax1.axis('off')
        
        ax1.text(0.5, 0.95, f'{title} - Query: {query_id}', 
                ha='center', va='top', fontsize=14, fontweight='bold')
        
        headers = ['Subject ID', 'Score', 'E-value', 'Identity', 'Positions']
        header_y = 0.85
        col_x = [0.1, 0.3, 0.45, 0.6, 0.75]
        
        for i, header in enumerate(headers):
            ax1.text(col_x[i], header_y, header, fontsize=10, fontweight='bold', ha='center')
        
        max_display = min(5, len(hits))
        for idx, hit in enumerate(hits[:max_display]):
            row_y = header_y - (idx + 1) * 0.06
            
            ax1.text(col_x[0], row_y, hit.subject_id[:15], fontsize=9, ha='center')
            ax1.text(col_x[1], row_y, str(hit.alignment_score), fontsize=9, ha='center')
            ax1.text(col_x[2], row_y, f'{hit.e_value:.2e}', fontsize=9, ha='center')
            ax1.text(col_x[3], row_y, f'{hit.identity:.1%}', fontsize=9, ha='center')
            ax1.text(col_x[4], row_y, f'{hit.subject_start}-{hit.subject_end}', fontsize=9, ha='center')
        
        ax2 = axes[1]
        scores = [hit.alignment_score for hit in hits[:20]]
        identities = [hit.identity for hit in hits[:20]]
        
        ax2.scatter(scores, identities, s=100, alpha=0.6, color='#2196F3', edgecolors='black')
        ax2.set_xlabel('Alignment Score', fontsize=11)
        ax2.set_ylabel('Identity', fontsize=11)
        ax2.set_title('Score vs Identity Distribution (Top 20 Hits)', fontsize=12, fontweight='bold')
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        return fig

    def create_phylogenetic_tree_page(self, tree_builder, title='Phylogenetic Tree'):
        fig, ax = plt.subplots(figsize=(10, 8))
        tree_builder.draw_tree(ax=ax, show_labels=True, show_distances=True, title=title)
        plt.tight_layout()
        return fig

    def create_summary_page(self, stats_dict, title='Analysis Summary'):
        fig, ax = plt.subplots(figsize=(10, 8))
        ax.axis('off')
        
        ax.text(0.5, 0.95, title, ha='center', va='top', 
               fontsize=16, fontweight='bold')
        
        y_pos = 0.8
        for category, items in stats_dict.items():
            ax.text(0.1, y_pos, f'{category}:', fontsize=12, fontweight='bold')
            y_pos -= 0.05
            
            for key, value in items.items():
                ax.text(0.15, y_pos, f'• {key}: {value}', fontsize=10)
                y_pos -= 0.035
            
            y_pos -= 0.02
        
        ax.text(0.5, 0.05, 'Generated by Sequence Alignment Toolkit', 
               ha='center', va='bottom', fontsize=9, color='gray')
        
        return fig

    def generate_full_report(self, filename, aligned_sequences=None, names=None,
                            similarity_matrix=None, blast_hits=None, query_id=None,
                            phylogenetic_tree=None, seq_type='protein'):
        with PdfPages(filename) as pdf:
            stats = {}
            
            if aligned_sequences is not None:
                stats['Sequence Alignment'] = {
                    'Number of sequences': len(aligned_sequences),
                    'Alignment length': len(aligned_sequences[0]) if aligned_sequences else 0
                }
                
                fig1 = self.create_alignment_page(aligned_sequences, names, seq_type=seq_type)
                if fig1:
                    pdf.savefig(fig1)
                    plt.close(fig1)
                
                fig2 = self.create_conservation_page(aligned_sequences)
                if fig2:
                    pdf.savefig(fig2)
                    plt.close(fig2)
            
            if similarity_matrix is not None:
                stats['Similarity Analysis'] = {
                    'Average similarity': f'{np.mean(similarity_matrix[np.triu_indices_from(similarity_matrix, 1)]):.2f}',
                    'Max similarity': f'{np.max(similarity_matrix):.2f}'
                }
                
                fig3 = self.create_similarity_matrix_page(similarity_matrix, names)
                if fig3:
                    pdf.savefig(fig3)
                    plt.close(fig3)
            
            if blast_hits is not None:
                stats['BLAST Search'] = {
                    'Total hits found': len(blast_hits)
                }
                if blast_hits:
                    stats['BLAST Search']['Best hit score'] = blast_hits[0].alignment_score
                    stats['BLAST Search']['Best hit identity'] = f'{blast_hits[0].identity:.1%}'
                
                fig4 = self.create_blast_results_page(blast_hits, query_id)
                if fig4:
                    pdf.savefig(fig4)
                    plt.close(fig4)
            
            if phylogenetic_tree is not None:
                stats['Phylogenetic Analysis'] = {
                    'Method': 'Neighbor-Joining',
                    'Newick format': 'See tree visualization'
                }
                
                fig5 = self.create_phylogenetic_tree_page(phylogenetic_tree)
                if fig5:
                    pdf.savefig(fig5)
                    plt.close(fig5)
            
            fig_summary = self.create_summary_page(stats)
            pdf.savefig(fig_summary)
            plt.close(fig_summary)
        
        print(f'Report successfully generated: {filename}')
        return True


class FastaWriter:
    @staticmethod
    def write_alignment(aligned_sequences, names, filename):
        with open(filename, 'w') as f:
            for name, seq in zip(names, aligned_sequences):
                f.write(f'>{name}\n')
                f.write(f'{seq}\n')
        print(f'Alignment saved to: {filename}')

    @staticmethod
    def read_fasta(filename):
        sequences = []
        names = []
        current_seq = []
        current_name = None
        
        with open(filename, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('>'):
                    if current_name is not None:
                        names.append(current_name)
                        sequences.append(''.join(current_seq))
                    current_name = line[1:]
                    current_seq = []
                elif line:
                    current_seq.append(line.upper())
            
            if current_name is not None:
                names.append(current_name)
                sequences.append(''.join(current_seq))
        
        return names, sequences
