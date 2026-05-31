import argparse
import numpy as np
import time
import sys
import os
from beat_tracker import BeatTracker
from audio_input import AudioInput
from beat_lock import AdaptiveBeatLock
from visualization import BeatVisualizer, OfflineVisualizer
from dance_visualizer import DanceVisualizer, OfflineDanceAnimator
from midi_exporter import BeatMIDIExporter
from structure_analyzer import MusicStructureAnalyzer


class RealtimeBeatTracker:
    def __init__(
        self,
        sr=44100,
        hop_length=512,
        chunk_size=2048,
        style='generic',
        min_bpm=60,
        max_bpm=200,
        use_visualization=True,
        use_dance_visualization=False,
        device_index=None,
        streaming=True,
        analyze_structure=False,
    ):
        self.sr = sr
        self.hop_length = hop_length
        self.chunk_size = chunk_size
        self.style = style
        self.min_bpm = min_bpm
        self.max_bpm = max_bpm
        self.use_visualization = use_visualization
        self.use_dance_visualization = use_dance_visualization
        self.streaming = streaming
        self.analyze_structure = analyze_structure

        self.beat_tracker = BeatTracker(
            sr=sr,
            hop_length=hop_length,
            min_bpm=min_bpm,
            max_bpm=max_bpm,
            style=style,
            use_kalman=True,
            streaming=streaming,
        )

        self.beat_lock = AdaptiveBeatLock(
            sr=sr,
            lock_confidence_threshold=0.6,
            unlock_confidence_threshold=0.2,
        )

        self.audio_input = AudioInput(
            sr=sr,
            chunk_size=chunk_size,
            channels=1,
            buffer_seconds=10,
        )

        self.visualizer = None
        if use_visualization:
            self.visualizer = BeatVisualizer(
                sr=sr,
                hop_length=hop_length,
                window_duration=10,
            )
            self.visualizer.set_style(style)

        self.dance_visualizer = None
        if use_dance_visualization:
            self.dance_visualizer = DanceVisualizer(
                sr=sr,
                hop_length=hop_length,
                window_duration=10,
            )

        self.structure_analyzer = None
        if analyze_structure:
            self.structure_analyzer = MusicStructureAnalyzer(
                sr=sr,
                hop_length=hop_length,
            )

        self.midi_exporter = BeatMIDIExporter(
            sr=sr,
            hop_length=hop_length,
        )

        self.device_index = device_index
        self.is_running = False
        self.process_interval = 0.1
        self.last_process_time = 0.0
        self.start_time = 0.0

        self.total_beats_detected = 0
        self.last_beat_time = 0.0
        self.current_structure = None
        self.structure_segments = []

    def _audio_callback(self, audio_data):
        pass

    def _process_audio(self):
        current_time = time.time()
        if current_time - self.last_process_time < self.process_interval:
            return

        self.last_process_time = current_time

        audio_data = self.audio_input.get_recent_chunk(duration=3.0)
        if len(audio_data) < self.sr * 0.5:
            return

        result = self.beat_tracker.process_frame(audio_data)

        if result is None:
            return

        beat_times = result['beats']
        downbeat_times = result['downbeats']
        bpm = result['bpm']
        confidence = result['confidence']
        onset_env = result.get('onset_env', None)
        speed_changing = result.get('speed_changing', False)
        speed_change_magnitude = result.get('speed_change_magnitude', 0.0)

        bpm_velocity = self.beat_tracker.bpm_kf.get_bpm_velocity() if self.beat_tracker.use_kalman else 0.0
        bpm_acceleration = self.beat_tracker.bpm_kf.get_bpm_acceleration() if self.beat_tracker.use_kalman else 0.0

        elapsed_time = current_time - self.start_time

        is_locked, locked_bpm = self.beat_lock.update(
            beat_times, bpm, confidence, elapsed_time, style=self.style
        )

        beat_phase = self.beat_lock.get_beat_phase(elapsed_time)

        if len(beat_times) > 0 and beat_times[-1] > self.last_beat_time + 0.1:
            self.total_beats_detected += len(beat_times) - np.sum(np.array(beat_times) <= self.last_beat_time)
            self.last_beat_time = beat_times[-1]

        if self.visualizer is not None:
            self.visualizer.update_data(
                onset_env=onset_env,
                beat_times=beat_times,
                downbeat_times=downbeat_times,
                bpm=bpm,
                confidence=confidence,
                is_locked=is_locked,
                locked_bpm=locked_bpm,
                beat_phase=beat_phase,
            )

        if self.dance_visualizer is not None:
            self.dance_visualizer.update_data(
                onset_env=onset_env,
                beat_times=beat_times,
                downbeat_times=downbeat_times,
                bpm=bpm,
                confidence=confidence,
                is_locked=is_locked,
                beat_phase=beat_phase,
            )

        if self.structure_analyzer is not None and len(audio_data) >= self.sr * 2:
            structure_result = self.structure_analyzer.analyze_stream(
                audio_data, elapsed_time, beat_times, bpm
            )
            if structure_result is not None:
                self.current_structure = structure_result

        self._print_status(
            beat_times, downbeat_times, bpm, confidence,
            is_locked, locked_bpm, beat_phase, elapsed_time,
            speed_changing, speed_change_magnitude,
            bpm_velocity, bpm_acceleration
        )

    def _print_status(
        self, beat_times, downbeat_times, bpm, confidence,
        is_locked, locked_bpm, beat_phase, elapsed_time,
        speed_changing=False, speed_change_magnitude=0.0,
        bpm_velocity=0.0, bpm_acceleration=0.0
    ):
        status = 'LOCKED' if is_locked else 'UNLOCKED'
        status_color = '\033[92m' if is_locked else '\033[91m'
        reset_color = '\033[0m'

        speed_status = 'CHANGING' if speed_changing else 'STABLE'
        speed_color = '\033[93m' if speed_changing else '\033[94m'

        algo_status = 'ONLINE-VITERBI' if self.streaming else 'BATCH-DP'
        algo_color = '\033[96m'

        sys.stdout.write('\033[2J\033[H')
        print('=' * 60)
        print(f'  MUSIC BEAT TRACKER - REAL-TIME MODE')
        print(f'  Style: {self.style.upper()} | Algorithm: {algo_color}{algo_status}{reset_color}')
        print('=' * 60)
        print(f'  Time Elapsed:       {elapsed_time:6.1f} s')
        print(f'  Current BPM:        {bpm:6.1f}')
        print(f'  Locked BPM:         {locked_bpm:6.1f}')
        print(f'  BPM Velocity:       {bpm_velocity:6.2f} BPM/s')
        print(f'  BPM Acceleration:   {bpm_acceleration:6.2f} BPM/s²')
        print(f'  Speed Status:       {speed_color}{speed_status}{reset_color} (mag: {speed_change_magnitude:.2f})')
        print(f'  Confidence:         {confidence:6.2f}')
        print(f'  Beat Phase:         {beat_phase:6.2f}')
        print(f'  Status:             {status_color}[{status}]{reset_color}')
        print(f'  Total Beats:        {self.total_beats_detected}')
        print('-' * 60)

        if len(beat_times) > 0:
            recent_beats = beat_times[-5:]
            print(f'  Recent Beats:       {[f"{bt:5.2f}" for bt in recent_beats]}')

        if len(downbeat_times) > 0:
            recent_downbeats = downbeat_times[-3:]
            print(f'  Recent Downbeats:   {[f"{bt:5.2f}" for bt in recent_downbeats]}')

        if len(beat_times) > 1:
            intervals = np.diff(beat_times[-10:])
            print(f'  Beat Interval:      {np.mean(intervals):.3f} ± {np.std(intervals):.3f} s')

        if self.style in ['metal', 'heavymetal']:
            print(f'  Energy Peaks:       ENABLED (emphasis: {self.beat_tracker.style_params.get("peak_emphasis", 0):.1f})')

        if self.current_structure is not None:
            seg_type = self.current_structure.get('current_segment', 'unknown')
            seg_duration = self.current_structure.get('duration', 0)
            is_new = self.current_structure.get('new_segment', False)
            new_marker = ' [NEW]' if is_new else ''
            print(f'  Current Section:    {seg_type.upper()} ({seg_duration:.1f}s){new_marker}')

        print('-' * 60)
        print('  Press Ctrl+C to exit')
        print('=' * 60)

    def start(self):
        print('Starting real-time beat tracker...')
        print(f'Sample Rate: {self.sr} Hz')
        print(f'Hop Length: {self.hop_length}')
        print(f'Style: {self.style}')

        if self.device_index is not None:
            print(f'Using audio device index: {self.device_index}')
            self.audio_input.set_input_device(self.device_index)
        else:
            self.audio_input.start_stream(callback=self._audio_callback)

        self.start_time = time.time()
        self.is_running = True

        if self.visualizer is not None:
            self.visualizer.start(interval=50)

        if self.dance_visualizer is not None:
            self.dance_visualizer.start(interval=50)

        try:
            while self.is_running and self.audio_input.is_active():
                self._process_audio()
                time.sleep(0.01)

        except KeyboardInterrupt:
            print('\n\nStopping...')
        finally:
            self.stop()

    def stop(self):
        self.is_running = False
        if self.audio_input is not None:
            self.audio_input.stop_stream()
        if self.visualizer is not None:
            self.visualizer.close()
        if self.dance_visualizer is not None:
            self.dance_visualizer.close()

        print('\n' + '=' * 60)
        print('  SUMMARY')
        print('=' * 60)
        print(f'  Total Running Time: {time.time() - self.start_time:.1f} s')
        print(f'  Total Beats Detected: {self.total_beats_detected}')
        print(f'  Final BPM: {self.beat_tracker.get_bpm():.1f}')
        print(f'  Final Confidence: {self.beat_tracker.get_confidence():.2f}')
        lock_status = self.beat_lock.get_lock_status()
        if lock_status['is_locked']:
            print(f'  Lock Duration: {lock_status["lock_duration"]:.1f} s')
        print('=' * 60)

    def set_style(self, style):
        self.style = style
        self.beat_tracker.set_style(style)
        if self.visualizer is not None:
            self.visualizer.set_style(style)

    def list_devices(self):
        return self.audio_input.list_input_devices()


class OfflineBeatTracker:
    def __init__(
        self,
        sr=44100,
        hop_length=512,
        style='generic',
        min_bpm=60,
        max_bpm=200,
        analyze_structure=False,
    ):
        self.sr = sr
        self.hop_length = hop_length
        self.style = style
        self.min_bpm = min_bpm
        self.max_bpm = max_bpm
        self.analyze_structure = analyze_structure

        self.beat_tracker = BeatTracker(
            sr=sr,
            hop_length=hop_length,
            min_bpm=min_bpm,
            max_bpm=max_bpm,
            style=style,
            use_kalman=True,
        )

        self.visualizer = OfflineVisualizer(sr=sr, hop_length=hop_length)
        self.dance_animator = OfflineDanceAnimator(sr=sr, hop_length=hop_length)
        self.midi_exporter = BeatMIDIExporter(sr=sr, hop_length=hop_length)
        self.structure_analyzer = MusicStructureAnalyzer(sr=sr, hop_length=hop_length) if analyze_structure else None

    def process_file(self, audio_path, show_plot=True, save_plot=None, output_file=None,
                     export_midi=None, midi_mode='complete', export_dance=None,
                     analyze_structure=None, structure_plot=None):
        import librosa

        print(f'Loading audio file: {audio_path}')
        y, sr = librosa.load(audio_path, sr=self.sr)
        duration = len(y) / sr
        print(f'Audio loaded: {duration:.2f} seconds, {sr} Hz')

        print(f'Processing with style: {self.style}')
        result = self.beat_tracker.process_frame(y)

        if result is None:
            print('No beats detected!')
            return None

        beat_times = result['beats']
        downbeat_times = result['downbeats']
        bpm = result['bpm']
        confidence = result['confidence']
        onset_env = result.get('onset_env', None)

        print('\n' + '=' * 60)
        print('  OFFLINE BEAT TRACKING RESULTS')
        print('=' * 60)
        print(f'  File: {os.path.basename(audio_path)}')
        print(f'  Duration: {duration:.2f} s')
        print(f'  Style: {self.style}')
        print(f'  Detected BPM: {bpm:.1f}')
        print(f'  Confidence: {confidence:.2f}')
        print(f'  Total Beats: {len(beat_times)}')
        print(f'  Total Downbeats: {len(downbeat_times)}')

        if len(beat_times) > 1:
            intervals = np.diff(beat_times)
            print(f'  Mean Beat Interval: {np.mean(intervals):.3f} s')
            print(f'  Beat Interval Std: {np.std(intervals):.3f} s')

        print('-' * 60)
        print('  Beat Sequence (first 20):')
        for i, bt in enumerate(beat_times[:20]):
            is_downbeat = bt in downbeat_times
            marker = '▼' if is_downbeat else '|'
            print(f'    Beat {i+1:3d}: {bt:7.3f} s {marker}')

        if len(beat_times) > 20:
            print(f'    ... and {len(beat_times) - 20} more')

        print('=' * 60)

        structure_segments = None
        if self.structure_analyzer is not None or analyze_structure:
            print('\nAnalyzing music structure...')
            if self.structure_analyzer is None:
                self.structure_analyzer = MusicStructureAnalyzer(sr=self.sr, hop_length=self.hop_length)
            structure_segments = self.structure_analyzer.analyze_offline(
                y, beat_times, downbeat_times, bpm
            )
            self.structure_analyzer.print_structure(structure_segments)

            if structure_plot is not None:
                import matplotlib.pyplot as plt
                fig, ax = plt.subplots(figsize=(14, 4))
                self.structure_analyzer.visualize_structure(structure_segments, y, self.sr, ax)
                plt.tight_layout()
                plt.savefig(structure_plot, dpi=150, bbox_inches='tight')
                print(f'Structure plot saved to: {structure_plot}')
                plt.close()

        if output_file is not None:
            self._save_results(output_file, beat_times, downbeat_times, bpm, confidence, duration, structure_segments)
            print(f'Results saved to: {output_file}')

        if export_midi is not None:
            print(f'\nExporting MIDI ({midi_mode} mode)...')
            if midi_mode == 'beats':
                midi_info = self.midi_exporter.export_beats(
                    beat_times, downbeat_times, bpm, export_midi, duration
                )
            elif midi_mode == 'melody':
                midi_info = self.midi_exporter.export_melody(
                    beat_times, downbeat_times, bpm, export_midi, duration=duration
                )
            elif midi_mode == 'structure' and structure_segments is not None:
                midi_info = self.midi_exporter.export_structure(
                    beat_times, downbeat_times, bpm, structure_segments, export_midi, duration
                )
            else:
                midi_info = self.midi_exporter.export_complete(
                    beat_times, downbeat_times, bpm, export_midi, duration
                )
            self.midi_exporter.print_midi_info(midi_info)

        if export_dance is not None:
            print(f'\nGenerating dance animation...')
            try:
                fig, anim = self.dance_animator.animate(
                    beat_times, downbeat_times, bpm, duration, export_dance
                )
            except Exception as e:
                print(f'Dance animation video export failed: {e}')
                print('Try installing ffmpeg: conda install ffmpeg')

        if show_plot or save_plot is not None:
            fig = self.visualizer.plot_results(
                y, onset_env, beat_times, downbeat_times, bpm, confidence
            )

            if structure_segments is not None and len(structure_segments) > 0:
                axes = fig.axes
                if len(axes) > 0:
                    self.structure_analyzer.visualize_structure(
                        structure_segments, None, None, axes[0]
                    )

            if save_plot is not None:
                self.visualizer.save(save_plot)
                print(f'Plot saved to: {save_plot}')

            if show_plot:
                self.visualizer.show()

        return {
            'beat_times': beat_times,
            'downbeat_times': downbeat_times,
            'bpm': bpm,
            'confidence': confidence,
            'duration': duration,
            'onset_env': onset_env,
            'structure_segments': structure_segments,
        }

    def _save_results(self, output_file, beat_times, downbeat_times, bpm, confidence, duration, structure_segments=None):
        with open(output_file, 'w') as f:
            f.write('# Music Beat Tracking Results\n')
            f.write(f'# Style: {self.style}\n')
            f.write(f'# Duration: {duration:.2f} s\n')
            f.write(f'# BPM: {bpm:.1f}\n')
            f.write(f'# Confidence: {confidence:.2f}\n')
            f.write(f'# Total Beats: {len(beat_times)}\n')
            f.write(f'# Total Downbeats: {len(downbeat_times)}\n')

            if structure_segments is not None and len(structure_segments) > 0:
                f.write(f'# Total Segments: {len(structure_segments)}\n')
                f.write('#\n')
                f.write('# Structure Segments:\n')
                f.write('# start(s),end(s),type,confidence\n')
                for seg in structure_segments:
                    f.write(f'# {seg["start"]:.2f},{seg["end"]:.2f},{seg["type"]},{seg.get("confidence", 0):.2f}\n')

            f.write('\n')
            f.write('time(s),type\n')
            for bt in beat_times:
                beat_type = 'downbeat' if bt in downbeat_times else 'beat'
                f.write(f'{bt:.4f},{beat_type}\n')

    def set_style(self, style):
        self.style = style
        self.beat_tracker.set_style(style)


def process_multiple_styles(audio_path, styles=None, output_dir='results'):
    if styles is None:
        styles = ['generic', 'rock', 'jazz', 'electronic', 'classical', 'hiphop', 'metal', 'heavymetal']

    os.makedirs(output_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(audio_path))[0]

    results = {}
    for style in styles:
        print(f'\n{"="*60}')
        print(f'  PROCESSING WITH STYLE: {style.upper()}')
        print(f'{"="*60}\n')

        tracker = OfflineBeatTracker(style=style)
        result = tracker.process_file(
            audio_path,
            show_plot=False,
            save_plot=os.path.join(output_dir, f'{base_name}_{style}.png'),
            output_file=os.path.join(output_dir, f'{base_name}_{style}.csv'),
        )

        if result is not None:
            results[style] = result

    print('\n' + '=' * 60)
    print('  STYLE COMPARISON SUMMARY')
    print('=' * 60)
    print(f'  {"Style":<15} {"BPM":>8} {"Confidence":>12} {"Beats":>8}')
    print('-' * 60)
    for style, result in results.items():
        print(f'  {style:<15} {result["bpm"]:>8.1f} {result["confidence"]:>12.2f} {len(result["beat_times"]):>8}')
    print('=' * 60)

    return results


def main():
    parser = argparse.ArgumentParser(
        description='Music Beat Tracker - Detect beats, BPM, downbeats, and structure in music',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Real-time mode with microphone (Online Viterbi)
  python main.py --realtime

  # Real-time mode with dance visualization
  python main.py --realtime --dance --analyze-structure

  # Real-time mode with heavy metal style
  python main.py --realtime --style metal

  # Real-time mode with batch DP algorithm
  python main.py --realtime --no-streaming --style electronic

  # List audio devices
  python main.py --list-devices

  # Offline mode with audio file
  python main.py --file song.mp3

  # Offline mode with full analysis (structure + MIDI + dance)
  python main.py --file song.mp3 --analyze-structure --export-midi beats.mid --export-dance dance.mp4

  # Offline mode with MIDI export (drums only)
  python main.py --file song.wav --export-midi drums.mid --midi-mode beats

  # Offline mode with structure-based MIDI export
  python main.py --file song.wav --analyze-structure --export-midi structure.mid --midi-mode structure

  # Offline mode with multiple styles (including metal)
  python main.py --file song.mp3 --multi-style

  # Offline mode saving results
  python main.py --file song.wav --output beats.csv --plot beats.png --structure-plot structure.png
        """,
    )

    parser.add_argument('--realtime', action='store_true', help='Enable real-time microphone input mode')
    parser.add_argument('--file', type=str, help='Path to audio file for offline processing')
    parser.add_argument('--style', type=str, default='generic',
                        choices=['generic', 'rock', 'jazz', 'electronic', 'classical', 'hiphop', 'metal', 'heavymetal'],
                        help='Music style for optimized tracking (metal/heavymetal enable energy peak detection)')
    parser.add_argument('--min-bpm', type=int, default=60, help='Minimum BPM to detect')
    parser.add_argument('--max-bpm', type=int, default=200, help='Maximum BPM to detect')
    parser.add_argument('--sr', type=int, default=44100, help='Sample rate in Hz')
    parser.add_argument('--hop-length', type=int, default=512, help='Hop length for feature extraction')
    parser.add_argument('--no-visualization', action='store_true', help='Disable real-time visualization')
    parser.add_argument('--no-streaming', action='store_true', help='Use batch DP instead of online Viterbi')
    parser.add_argument('--device', type=int, help='Audio input device index')
    parser.add_argument('--list-devices', action='store_true', help='List available audio input devices')
    parser.add_argument('--output', type=str, help='Output file for beat tracking results (CSV)')
    parser.add_argument('--plot', type=str, help='Save visualization plot to file')
    parser.add_argument('--no-show', action='store_true', help='Do not display plot window')
    parser.add_argument('--multi-style', action='store_true', help='Process with all styles and compare')

    parser.add_argument('--dance', action='store_true', help='Enable 3D dance visualization (real-time)')
    parser.add_argument('--analyze-structure', action='store_true', help='Analyze music structure (verse/chorus/etc.)')
    parser.add_argument('--export-midi', type=str, help='Export beat sequence to MIDI file')
    parser.add_argument('--midi-mode', type=str, default='complete',
                        choices=['beats', 'melody', 'complete', 'structure'],
                        help='MIDI export mode: beats (drums only), melody, complete (drums + melody), structure')
    parser.add_argument('--export-dance', type=str, help='Export dance animation to video file (requires ffmpeg)')
    parser.add_argument('--structure-plot', type=str, help='Save structure visualization plot to file')

    args = parser.parse_args()

    if args.list_devices:
        print('Available audio input devices:')
        tracker = RealtimeBeatTracker()
        devices = tracker.list_devices()
        for dev in devices:
            print(f"  {dev['index']}: {dev['name']} (channels: {dev['channels']}, rate: {dev['sample_rate']})")
        return

    if args.realtime:
        tracker = RealtimeBeatTracker(
            sr=args.sr,
            hop_length=args.hop_length,
            style=args.style,
            min_bpm=args.min_bpm,
            max_bpm=args.max_bpm,
            use_visualization=not args.no_visualization,
            use_dance_visualization=args.dance,
            device_index=args.device,
            streaming=not args.no_streaming,
            analyze_structure=args.analyze_structure,
        )
        tracker.start()
        return

    if args.file:
        if not os.path.exists(args.file):
            print(f'Error: File not found: {args.file}')
            sys.exit(1)

        if args.multi_style:
            process_multiple_styles(args.file)
            return

        tracker = OfflineBeatTracker(
            sr=args.sr,
            hop_length=args.hop_length,
            style=args.style,
            min_bpm=args.min_bpm,
            max_bpm=args.max_bpm,
            analyze_structure=args.analyze_structure,
        )

        tracker.process_file(
            args.file,
            show_plot=not args.no_show,
            save_plot=args.plot,
            output_file=args.output,
            export_midi=args.export_midi,
            midi_mode=args.midi_mode,
            export_dance=args.export_dance,
            analyze_structure=args.analyze_structure,
            structure_plot=args.structure_plot,
        )
        return

    parser.print_help()


if __name__ == '__main__':
    main()
