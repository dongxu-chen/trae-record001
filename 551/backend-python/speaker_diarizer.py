import numpy as np
from collections import defaultdict

try:
    from sklearn.cluster import AgglomerativeClustering
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

try:
    from scipy.spatial.distance import cosine
    from scipy.signal import medfilt
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False


class SpeakerEmbedding:
    def __init__(self, sample_rate=16000, n_mfcc=13, n_mel=26):
        self.sample_rate = sample_rate
        self.n_mfcc = n_mfcc
        self.n_mel = n_mel
    
    def extract_mfcc(self, audio_data):
        if isinstance(audio_data, np.ndarray):
            signal = audio_data.astype(np.float32)
        else:
            try:
                signal = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)
            except:
                return np.zeros(self.n_mfcc * 3)
        
        if len(signal) < self.sample_rate * 0.1:
            return np.zeros(self.n_mfcc * 3)
        
        max_val = np.max(np.abs(signal))
        if max_val > 0:
            signal = signal / max_val
        
        pre_emphasis = 0.97
        emphasized = np.append(signal[0], signal[1:] - pre_emphasis * signal[:-1])
        
        frame_length = int(0.025 * self.sample_rate)
        frame_step = int(0.01 * self.sample_rate)
        
        signal_length = len(emphasized)
        num_frames = max(1, int(np.ceil(float(np.abs(signal_length - frame_length)) / frame_step)))
        
        pad_length = num_frames * frame_step + frame_length
        padded = np.append(emphasized, np.zeros(pad_length - signal_length))
        
        indices = (np.arange(0, frame_length)[np.newaxis, :] +
                   np.arange(0, num_frames * frame_step, frame_step)[:, np.newaxis])
        frames = padded[indices]
        
        frames *= np.hamming(frame_length)
        
        NFFT = 512
        mag_frames = np.absolute(np.fft.rfft(frames, NFFT))
        pow_frames = ((1.0 / NFFT) * ((mag_frames) ** 2))
        
        low_freq = 0
        high_freq = self.sample_rate / 2
        mel_points = self._hz_to_mel(np.linspace(low_freq, high_freq, self.n_mel + 2))
        bin_points = np.floor((NFFT + 1) * self._mel_to_hz(mel_points) / self.sample_rate).astype(int)
        
        fbank = np.zeros((self.n_mel, int(NFFT / 2 + 1)))
        for i in range(self.n_mel):
            for j in range(bin_points[i], bin_points[i + 1]):
                fbank[i, j] = (j - bin_points[i]) / (bin_points[i + 1] - bin_points[i] + 1e-10)
            for j in range(bin_points[i + 1], bin_points[i + 2]):
                fbank[i, j] = (bin_points[i + 2] - j) / (bin_points[i + 2] - bin_points[i + 1] + 1e-10)
        
        filter_banks = np.dot(pow_frames, fbank.T)
        filter_banks = np.where(filter_banks == 0, np.finfo(float).eps, filter_banks)
        filter_banks = 20 * np.log10(filter_banks)
        
        dct_matrix = self._dct(self.n_mfcc, self.n_mel)
        mfcc = np.dot(filter_banks, dct_matrix)
        
        mfcc_mean = np.mean(mfcc, axis=0)
        mfcc_std = np.std(mfcc, axis=0)
        mfcc_delta = np.mean(np.diff(mfcc, axis=0), axis=0) if len(mfcc) > 1 else np.zeros(self.n_mfcc)
        
        embedding = np.concatenate([mfcc_mean, mfcc_std, mfcc_delta])
        
        embedding = np.nan_to_num(embedding, nan=0.0, posinf=0.0, neginf=0.0)
        
        return embedding
    
    def _hz_to_mel(self, hz):
        return 2595 * np.log10(1 + hz / 700.0)
    
    def _mel_to_hz(self, mel):
        return 700 * (10 ** (mel / 2595.0) - 1)
    
    def _dct(self, n_mfcc, n_filters):
        dct = np.zeros((n_mfcc, n_filters))
        for i in range(n_mfcc):
            for j in range(n_filters):
                dct[i, j] = np.cos(np.pi * i * (j + 0.5) / n_filters)
        return dct * np.sqrt(2.0 / n_filters)


class SpeakerDiarizer:
    def __init__(self, max_speakers=6, min_speakers=2, sample_rate=16000):
        self.max_speakers = max_speakers
        self.min_speakers = min_speakers
        self.sample_rate = sample_rate
        self.embedding_extractor = SpeakerEmbedding(sample_rate=sample_rate)
        
        self.speaker_profiles = {}
        self.speaker_embeddings = defaultdict(list)
        self.speaker_colors = {}
        self.speaker_names = {}
        self.next_speaker_id = 0
        
        self.color_palette = [
            '#00d4ff', '#7c3aed', '#10b981', '#f59e0b', '#ef4444',
            '#ec4899', '#8b5cf6', '#06b6d4', '#84cc16', '#f97316'
        ]
        
        self.distance_threshold = 0.65
        self.min_segment_samples = sample_rate * 0.5
        self.segment_buffer = []
        self.segment_embeddings = []
        
        if SKLEARN_AVAILABLE:
            self.scaler = StandardScaler()
            self.clustering = AgglomerativeClustering(
                n_clusters=None,
                distance_threshold=self.distance_threshold,
                linkage='average',
                metric='cosine'
            )
    
    def process_audio_segment(self, audio_data, timestamp=None):
        if isinstance(audio_data, np.ndarray):
            signal = audio_data
        else:
            try:
                signal = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)
            except:
                return 'speaker_0', 0.0
        
        energy = np.sqrt(np.mean(signal ** 2))
        if energy < 100:
            return None, 0.0
        
        if len(signal) < self.min_segment_samples:
            self.segment_buffer.append(signal)
            signal = np.concatenate(self.segment_buffer)
            self.segment_buffer = []
        
        embedding = self.embedding_extractor.extract_mfcc(signal)
        
        if np.all(embedding == 0):
            return 'speaker_0', 0.0
        
        speaker_id, confidence = self._identify_speaker(embedding)
        
        self.speaker_embeddings[speaker_id].append(embedding)
        
        if len(self.speaker_embeddings[speaker_id]) > 20:
            self.speaker_embeddings[speaker_id] = self.speaker_embeddings[speaker_id][-20:]
        
        self._update_speaker_profile(speaker_id)
        
        return speaker_id, confidence
    
    def _identify_speaker(self, embedding):
        if not self.speaker_profiles:
            speaker_id = self._create_new_speaker()
            return speaker_id, 1.0
        
        similarities = {}
        for sid, profile in self.speaker_profiles.items():
            sim = self._cosine_similarity(embedding, profile)
            similarities[sid] = sim
        
        best_speaker = max(similarities, key=similarities.get)
        best_similarity = similarities[best_speaker]
        
        if best_similarity > (1 - self.distance_threshold):
            return best_speaker, best_similarity
        
        if len(self.speaker_profiles) < self.max_speakers:
            speaker_id = self._create_new_speaker()
            return speaker_id, 0.5
        
        return best_speaker, best_similarity
    
    def _create_new_speaker(self):
        speaker_id = f'speaker_{self.next_speaker_id}'
        self.next_speaker_id += 1
        
        color_idx = (self.next_speaker_id - 1) % len(self.color_palette)
        self.speaker_colors[speaker_id] = self.color_palette[color_idx]
        self.speaker_names[speaker_id] = f'说话人{self.next_speaker_id}'
        
        self.speaker_profiles[speaker_id] = None
        self.speaker_embeddings[speaker_id] = []
        
        print(f"New speaker detected: {speaker_id} ({self.speaker_names[speaker_id]})")
        
        return speaker_id
    
    def _update_speaker_profile(self, speaker_id):
        embeddings = self.speaker_embeddings[speaker_id]
        if embeddings:
            self.speaker_profiles[speaker_id] = np.mean(embeddings, axis=0)
    
    def _cosine_similarity(self, a, b):
        if a is None or b is None:
            return 0.0
        
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return np.dot(a, b) / (norm_a * norm_b)
    
    def set_speaker_name(self, speaker_id, name):
        if speaker_id in self.speaker_names:
            self.speaker_names[speaker_id] = name
            return True
        return False
    
    def get_speaker_info(self, speaker_id):
        return {
            'id': speaker_id,
            'name': self.speaker_names.get(speaker_id, speaker_id),
            'color': self.speaker_colors.get(speaker_id, '#888'),
            'segment_count': len(self.speaker_embeddings.get(speaker_id, []))
        }
    
    def get_all_speakers(self):
        return {
            sid: self.get_speaker_info(sid)
            for sid in self.speaker_profiles
        }
    
    def reset(self):
        self.speaker_profiles = {}
        self.speaker_embeddings = defaultdict(list)
        self.next_speaker_id = 0
        self.segment_buffer = []
    
    def recluster(self):
        if not SKLEARN_AVAILABLE:
            print("Warning: sklearn not available for reclustering")
            return
        
        all_embeddings = []
        all_speaker_ids = []
        
        for sid, embeddings in self.speaker_embeddings.items():
            for emb in embeddings:
                all_embeddings.append(emb)
                all_speaker_ids.append(sid)
        
        if len(all_embeddings) < self.min_speakers:
            return
        
        X = np.array(all_embeddings)
        
        try:
            X = self.scaler.fit_transform(X)
            
            n_clusters = min(self.max_speakers, max(self.min_speakers, len(set(all_speaker_ids))))
            
            clusterer = AgglomerativeClustering(
                n_clusters=n_clusters,
                linkage='average',
                metric='cosine'
            )
            
            labels = clusterer.fit_predict(X)
            
            new_mapping = {}
            for old_id, label in zip(all_speaker_ids, labels):
                if old_id not in new_mapping:
                    new_mapping[old_id] = f'speaker_{label}'
            
            new_embeddings = defaultdict(list)
            for old_id, emb in zip(all_speaker_ids, all_embeddings):
                new_id = new_mapping.get(old_id, old_id)
                new_embeddings[new_id].append(emb)
            
            self.speaker_embeddings = new_embeddings
            for sid, embeddings in new_embeddings.items():
                self.speaker_profiles[sid] = np.mean(embeddings, axis=0)
                if sid not in self.speaker_names:
                    idx = int(sid.split('_')[-1]) + 1
                    self.speaker_names[sid] = f'说话人{idx}'
                    self.speaker_colors[sid] = self.color_palette[idx % len(self.color_palette)]
            
            print(f"Reclustered into {len(set(labels))} speakers")
            
        except Exception as e:
            print(f"Reclustering failed: {e}")
