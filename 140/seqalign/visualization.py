import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from collections import Counter


class AlignmentVisualizer:
    def __init__(self, figsize=(10, 8)):
        self.figsize = figsize
        self.amino_colors = {
            'A': '#8DD3C7', 'R': '#BEBADA', 'N': '#FB8072', 'D': '#80B1D3',
            'C': '#FDB462', 'Q': '#B3DE69', 'E': '#FCCDE5', 'G': '#D9D9D9',
            'H': '#BC80BD', 'I': '#CCEBC5', 'L': '#FFED6F', 'K': '#1F78B4',
            'M': '#33A02C', 'F': '#E31A1C', 'P': '#FDBF6F', 'S': '#FF7F00',
            'T': '#CAB2D6', 'W': '#6A3D9A', 'Y': '#B15928', 'V': '#B2DF8A',
            '-': '#FFFFFF'
        }
        self.dna_colors = {
            'A': '#4CAF50', 'T': '#F44336', 'U': '#F44336',
            'C': '#2196F3', 'G': '#FF9800', '-': '#FFFFFF',
            'N': '#9E9E9E'
        }

    def _get_color_map(self, sequence_type='protein'):
        return self.amino_colors if sequence_type == 'protein' else self.dna_colors

    def plot_score_matrix_heatmap(self, score_matrix, seq1, seq2, 
                                   title="Alignment Score Matrix", 
                                   show_traceback=False, traceback_path=None,
                                   cmap="viridis", save_path=None):
        fig, ax = plt.subplots(figsize=self.figsize)
        
        im = ax.imshow(score_matrix, cmap=cmap, aspect="auto", interpolation="nearest")
        
        ax.set_xticks(np.arange(len(seq2) + 1))
        ax.set_yticks(np.arange(len(seq1) + 1))
        ax.set_xticklabels([" "] + list(seq2), fontsize=9)
        ax.set_yticklabels([" "] + list(seq1), fontsize=9)
        
        ax.set_xlabel("Sequence 2", fontsize=12)
        ax.set_ylabel("Sequence 1", fontsize=12)
        
        cbar = plt.colorbar(im, ax=ax, shrink=0.8)
        cbar.set_label("Score", fontsize=11)
        
        if show_traceback and traceback_path is not None:
            path_i, path_j = zip(*traceback_path)
            ax.plot(path_j, path_i, color="red", linewidth=2.5, marker="o",
                   markersize=6, label="Traceback Path", alpha=0.8)
            ax.legend(loc="upper right")
        
        ax.set_title(title, fontsize=14, pad=20)
        ax.grid(True, alpha=0.3, linestyle="--")
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches="tight")
        
        plt.show()

    def plot_similarity_heatmap(self, similarity_matrix, sequence_names,
                                 title="Sequence Similarity Matrix",
                                 cmap="YlGnBu", annot=True, save_path=None):
        fig, ax = plt.subplots(figsize=self.figsize)
        
        im = ax.imshow(similarity_matrix, cmap=cmap, vmin=0, vmax=1,
                      aspect="equal", interpolation="nearest")
        
        ax.set_xticks(np.arange(len(sequence_names)))
        ax.set_yticks(np.arange(len(sequence_names)))
        ax.set_xticklabels(sequence_names, rotation=45, ha="right", fontsize=10)
        ax.set_yticklabels(sequence_names, fontsize=10)
        
        if annot:
            for i in range(similarity_matrix.shape[0]):
                for j in range(similarity_matrix.shape[1]):
                    color = "white" if similarity_matrix[i, j] > 0.6 else "black"
                    ax.text(j, i, f"{similarity_matrix[i, j]:.2f}",
                           ha="center", va="center", color=color, fontsize=9)
        
        cbar = plt.colorbar(im, ax=ax, shrink=0.8)
        cbar.set_label("Similarity", fontsize=11)
        
        ax.set_title(title, fontsize=14, pad=20)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches="tight")
        
        plt.show()

    def plot_sequence_logo(self, aligned_sequences, title="Sequence Logo",
                          sequence_type='protein', save_path=None):
        n_seqs = len(aligned_sequences)
        seq_length = len(aligned_sequences[0])
        
        color_map = self._get_color_map(sequence_type)
        
        position_counts = []
        for pos in range(seq_length):
            chars = [seq[pos] for seq in aligned_sequences]
            counts = Counter(chars)
            position_counts.append(counts)
        
        heights = []
        for counts in position_counts:
            total = sum(counts.values())
            freqs = {char: count / total for char, count in counts.items()}
            heights.append(freqs)
        
        fig, ax = plt.subplots(figsize=(max(12, seq_length * 0.3), 6))
        
        bar_width = 0.8
        for pos in range(seq_length):
            y_offset = 0
            sorted_chars = sorted(heights[pos].items(), key=lambda x: x[1])
            for char, height in sorted_chars:
                color = color_map.get(char.upper(), "#CCCCCC")
                ax.bar(pos, height, bar_width, bottom=y_offset,
                      color=color, edgecolor="white", linewidth=0.5)
                if height > 0.05:
                    ax.text(pos, y_offset + height / 2, char,
                           ha="center", va="center", fontsize=10,
                           color="black", fontweight="bold")
                y_offset += height
        
        ax.set_xlim(-0.5, seq_length - 0.5)
        ax.set_ylim(0, 1)
        ax.set_xlabel("Position", fontsize=12)
        ax.set_ylabel("Frequency", fontsize=12)
        ax.set_title(title, fontsize=14, pad=20)
        
        ax.set_xticks(np.arange(0, seq_length, max(1, seq_length // 20)))
        ax.set_xticklabels([str(i + 1) for i in range(0, seq_length, max(1, seq_length // 20))])
        
        ax.grid(axis="y", alpha=0.3, linestyle="--")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches="tight")
        
        plt.show()

    def plot_conservation_heatmap(self, aligned_sequences, title="Conservation Heatmap",
                                  sequence_type='protein', window_size=1, save_path=None):
        n_seqs = len(aligned_sequences)
        seq_length = len(aligned_sequences[0])
        
        conservation = np.zeros(seq_length)
        for pos in range(seq_length):
            chars = [seq[pos] for seq in aligned_sequences if seq[pos] != "-"]
            if len(chars) > 0:
                most_common = Counter(chars).most_common(1)[0][1]
                conservation[pos] = most_common / len(chars)
        
        if window_size > 1:
            kernel = np.ones(window_size) / window_size
            conservation = np.convolve(conservation, kernel, mode="same")
        
        fig, ax = plt.subplots(figsize=(max(14, seq_length * 0.2), 3))
        
        im = ax.imshow(conservation.reshape(1, -1), cmap="RdYlGn",
                      aspect="auto", vmin=0, vmax=1, interpolation="nearest")
        
        ax.set_yticks([])
        ax.set_xlabel("Position", fontsize=11)
        ax.set_title(title, fontsize=13, pad=15)
        
        cbar = plt.colorbar(im, ax=ax, shrink=0.8, orientation="horizontal", pad=0.2)
        cbar.set_label("Conservation", fontsize=10)
        
        ax.set_xticks(np.arange(0, seq_length, max(1, seq_length // 15)))
        ax.set_xticklabels([str(i + 1) for i in range(0, seq_length, max(1, seq_length // 15))])
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches="tight")
        
        plt.show()

    def plot_alignment_display(self, aligned_seq1, aligned_seq2, title="Sequence Alignment",
                              sequence_type='protein', show_numbers=True, save_path=None):
        seq_length = len(aligned_seq1)
        line_width = 60
        num_lines = (seq_length + line_width - 1) // line_width
        
        color_map = self._get_color_map(sequence_type)
        
        fig, axes = plt.subplots(num_lines, 1, figsize=(14, num_lines * 1.8 + 1),
                                squeeze=False)
        
        for line_num, ax in enumerate(axes.flat):
            start = line_num * line_width
            end = min(start + line_width, seq_length)
            line_len = end - start
            
            for pos in range(start, end):
                x_pos = pos - start
                
                color1 = color_map.get(aligned_seq1[pos].upper(), "#CCCCCC")
                color2 = color_map.get(aligned_seq2[pos].upper(), "#CCCCCC")
                
                rect1 = plt.Rectangle((x_pos, 1.6), 0.9, 0.8,
                                     facecolor=color1, edgecolor="gray", linewidth=0.5)
                rect2 = plt.Rectangle((x_pos, 0.6), 0.9, 0.8,
                                     facecolor=color2, edgecolor="gray", linewidth=0.5)
                ax.add_patch(rect1)
                ax.add_patch(rect2)
                
                ax.text(x_pos + 0.45, 2.0, aligned_seq1[pos],
                       ha="center", va="center", fontsize=10, fontfamily="monospace")
                ax.text(x_pos + 0.45, 1.0, aligned_seq2[pos],
                       ha="center", va="center", fontsize=10, fontfamily="monospace")
                
                if aligned_seq1[pos] == aligned_seq2[pos] and aligned_seq1[pos] != "-":
                    ax.text(x_pos + 0.45, 1.5, "|", color="#2E7D32",
                           ha="center", va="center", fontsize=12, fontweight="bold")
                elif aligned_seq1[pos] != "-" and aligned_seq2[pos] != "-":
                    ax.text(x_pos + 0.45, 1.5, ".", color="#FF9800",
                           ha="center", va="center", fontsize=12, fontweight="bold")
            
            if show_numbers:
                ax.text(-2, 2.0, f"Seq1 {start + 1}", ha="right", va="center", fontsize=9)
                ax.text(-2, 1.0, f"Seq2 {start + 1}", ha="right", va="center", fontsize=9)
            
            ax.set_xlim(-3, line_len)
            ax.set_ylim(0.3, 2.7)
            ax.set_xticks([])
            ax.set_yticks([])
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.spines["left"].set_visible(False)
            ax.spines["bottom"].set_visible(False)
        
        axes[0, 0].set_title(title, fontsize=14, pad=20)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches="tight")
        
        plt.show()

    def plot_similarity_histogram(self, similarity_matrix, title="Similarity Distribution",
                                  bins=10, show_stats=True, save_path=None):
        upper_triangle = similarity_matrix[np.triu_indices_from(similarity_matrix, k=1)]
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        n, bins, patches = ax.hist(upper_triangle, bins=bins, edgecolor="black",
                                  alpha=0.7, color="#2196F3")
        
        fracs = n / n.max()
        norm = plt.Normalize(fracs.min(), fracs.max())
        for thisfrac, thispatch in zip(fracs, patches):
            color = plt.cm.viridis(norm(thisfrac))
            thispatch.set_facecolor(color)
        
        if show_stats:
            mean_val = np.mean(upper_triangle)
            median_val = np.median(upper_triangle)
            std_val = np.std(upper_triangle)
            
            ax.axvline(mean_val, color="#E91E63", linestyle="--", linewidth=2,
                      label=f"Mean: {mean_val:.3f}")
            ax.axvline(median_val, color="#FF9800", linestyle="--", linewidth=2,
                      label=f"Median: {median_val:.3f}")
            
            stats_text = f"Mean: {mean_val:.3f}\nMedian: {median_val:.3f}\nStd: {std_val:.3f}\nN: {len(upper_triangle)}"
            ax.text(0.95, 0.95, stats_text, transform=ax.transAxes,
                   fontsize=10, verticalalignment="top", horizontalalignment="right",
                   bbox=dict(boxstyle="round", facecolor="white", alpha=0.8))
        
        ax.set_xlabel("Similarity Score", fontsize=12)
        ax.set_ylabel("Frequency", fontsize=12)
        ax.set_title(title, fontsize=14, pad=20)
        ax.legend(loc="upper left")
        ax.grid(axis="y", alpha=0.3, linestyle="--")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches="tight")
        
        plt.show()

    def plot_dotplot(self, seq1, seq2, window_size=1, title="Dot Plot", save_path=None):
        n, m = len(seq1), len(seq2)
        
        dot_matrix = np.zeros((n, m))
        
        for i in range(n):
            for j in range(m):
                if seq1[i] == seq2[j]:
                    dot_matrix[i, j] = 1
        
        if window_size > 1:
            from scipy.ndimage import convolve
            kernel = np.ones((window_size, window_size))
            dot_matrix = convolve(dot_matrix, kernel, mode="constant") / (window_size ** 2)
        
        fig, ax = plt.subplots(figsize=(self.figsize[0], self.figsize[0] * n / m))
        
        im = ax.imshow(dot_matrix, cmap="Blues", aspect="equal", vmin=0, vmax=1,
                      interpolation="nearest")
        
        ax.set_xticks(np.arange(0, m, max(1, m // 20)))
        ax.set_yticks(np.arange(0, n, max(1, n // 20)))
        ax.set_xticklabels([str(i + 1) for i in range(0, m, max(1, m // 20))], rotation=90)
        ax.set_yticklabels([str(i + 1) for i in range(0, n, max(1, n // 20))])
        
        ax.set_xlabel("Sequence 2 Position", fontsize=12)
        ax.set_ylabel("Sequence 1 Position", fontsize=12)
        ax.set_title(title, fontsize=14, pad=20)
        
        ax.plot([0, m], [0, n], "r--", alpha=0.5, label="Diagonal")
        ax.legend()
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches="tight")
        
        plt.show()
