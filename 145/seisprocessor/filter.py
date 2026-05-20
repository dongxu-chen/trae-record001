import numpy as np
from obspy import Stream, Trace
from scipy.signal import butter, filtfilt


class Steim2Decoder:
    def __init__(self):
        self.frames = []
        
    def decode_frame(self, frame_data):
        if len(frame_data) < 64:
            frame_data = np.pad(frame_data, (0, 64 - len(frame_data)), 'constant')
        
        frame_data = frame_data[:64]
        samples = []
        dn = np.int32(0)
        
        for i in range(0, 64, 4):
            if i + 4 > len(frame_data):
                break
            word = np.frombuffer(frame_data[i:i+4], dtype=np.int32)[0]
            
            ctrl = (word >> 30) & 0x03
            
            if ctrl == 0:
                diffs = []
                mask = 0x3FFFFFFF
                for j in range(15):
                    shift = 28 - j * 2
                    diff = (word >> shift) & 0x03
                    if diff == 2:
                        diff = -2
                    diffs.append(diff)
                for d in diffs:
                    dn += d
                    samples.append(dn)
                    
            elif ctrl == 1:
                diffs = []
                for j in range(7):
                    shift = 26 - j * 4
                    diff = (word >> shift) & 0x0F
                    if diff >= 8:
                        diff -= 16
                    diffs.append(diff)
                for d in diffs:
                    dn += d
                    samples.append(dn)
                    
            elif ctrl == 2:
                diffs = []
                for j in range(3):
                    shift = 22 - j * 8
                    diff = (word >> shift) & 0xFF
                    if diff >= 128:
                        diff -= 256
                    diffs.append(diff)
                for d in diffs:
                    dn += d
                    samples.append(dn)
                    
            elif ctrl == 3:
                diff = word & 0x3FFFFFFF
                if diff >= 0x20000000:
                    diff -= 0x40000000
                dn += diff
                samples.append(dn)
        
        return np.array(samples, dtype=np.int32)
    
    def decode_stream(self, compressed_data, frame_size=64):
        n_frames = len(compressed_data) // frame_size
        all_samples = []
        
        for i in range(n_frames):
            start = i * frame_size
            end = start + frame_size
            frame = compressed_data[start:end]
            samples = self.decode_frame(frame)
            all_samples.extend(samples)
        
        return np.array(all_samples, dtype=np.float64)
    
    def validate_alignment(self, compressed_data, frame_size=64):
        remainder = len(compressed_data) % frame_size
        if remainder != 0:
            padding = frame_size - remainder
            compressed_data = np.pad(compressed_data, (0, padding), 'constant')
        return compressed_data


class WaveformFilter:
    def __init__(self, sampling_rate=None):
        self.sampling_rate = sampling_rate

    def _get_sampling_rate(self, trace):
        if self.sampling_rate is not None:
            return self.sampling_rate
        return trace.stats.sampling_rate

    def butter_lowpass(self, cutoff, fs, order=4):
        nyquist = 0.5 * fs
        normal_cutoff = cutoff / nyquist
        b, a = butter(order, normal_cutoff, btype="low", analog=False)
        return b, a

    def butter_highpass(self, cutoff, fs, order=4):
        nyquist = 0.5 * fs
        normal_cutoff = cutoff / nyquist
        b, a = butter(order, normal_cutoff, btype="high", analog=False)
        return b, a

    def butter_bandpass(self, lowcut, highcut, fs, order=4):
        nyquist = 0.5 * fs
        low = lowcut / nyquist
        high = highcut / nyquist
        b, a = butter(order, [low, high], btype="band", analog=False)
        return b, a

    def lowpass_filter(self, data, cutoff, fs, order=4):
        b, a = self.butter_lowpass(cutoff, fs, order=order)
        y = filtfilt(b, a, data)
        return y

    def highpass_filter(self, data, cutoff, fs, order=4):
        b, a = self.butter_highpass(cutoff, fs, order=order)
        y = filtfilt(b, a, data)
        return y

    def bandpass_filter(self, data, lowcut, highcut, fs, order=4):
        b, a = self.butter_bandpass(lowcut, highcut, fs, order=order)
        y = filtfilt(b, a, data)
        return y

    def filter_trace(self, trace, filter_type="bandpass", **kwargs):
        fs = self._get_sampling_rate(trace)
        data = trace.data.copy()

        if filter_type == "lowpass":
            cutoff = kwargs.get("cutoff", 1.0)
            order = kwargs.get("order", 4)
            filtered_data = self.lowpass_filter(data, cutoff, fs, order)
        elif filter_type == "highpass":
            cutoff = kwargs.get("cutoff", 0.1)
            order = kwargs.get("order", 4)
            filtered_data = self.highpass_filter(data, cutoff, fs, order)
        elif filter_type == "bandpass":
            lowcut = kwargs.get("lowcut", 0.1)
            highcut = kwargs.get("highcut", 10.0)
            order = kwargs.get("order", 4)
            filtered_data = self.bandpass_filter(data, lowcut, highcut, fs, order)
        else:
            raise ValueError(f"Unsupported filter type: {filter_type}")

        filtered_trace = trace.copy()
        filtered_trace.data = filtered_data
        return filtered_trace

    def filter_stream(self, stream, filter_type="bandpass", **kwargs):
        filtered_stream = Stream()
        for trace in stream:
            filtered_trace = self.filter_trace(trace, filter_type, **kwargs)
            filtered_stream.append(filtered_trace)
        return filtered_stream

    def detrend(self, trace, type="linear"):
        detrended_trace = trace.copy()
        detrended_trace.detrend(type)
        return detrended_trace

    def remove_response(self, trace, pre_filt=(0.005, 0.01, 10, 20)):
        resp_removed_trace = trace.copy()
        resp_removed_trace.remove_response(pre_filt=pre_filt)
        return resp_removed_trace
