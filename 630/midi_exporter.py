import numpy as np
import struct
from collections import namedtuple


MIDIEvent = namedtuple('MIDIEvent', ['time', 'status', 'data1', 'data2'])
MIDIMetaEvent = namedtuple('MIDIMetaEvent', ['time', 'meta_type', 'data'])


class MIDIFile:
    def __init__(self, format=1, ticks_per_beat=480):
        self.format = format
        self.ticks_per_beat = ticks_per_beat
        self.tracks = []

    def add_track(self, track):
        self.tracks.append(track)

    def _write_variable_length(self, value):
        result = []
        value = int(value)
        if value == 0:
            return bytes([0])
        while value > 0:
            result.append(value & 0x7F)
            value >>= 7
        result.reverse()
        for i in range(len(result) - 1):
            result[i] |= 0x80
        return bytes(result)

    def _write_header(self):
        header = b'MThd'
        header += struct.pack('>I', 6)
        header += struct.pack('>HHH', self.format, len(self.tracks), self.ticks_per_beat)
        return header

    def _write_track(self, track):
        track_data = bytearray()
        last_status = None

        for event in track:
            delta_time = int(event.time)
            track_data.extend(self._write_variable_length(delta_time))

            if isinstance(event, MIDIMetaEvent):
                track_data.append(0xFF)
                track_data.append(event.meta_type)
                track_data.extend(self._write_variable_length(len(event.data)))
                track_data.extend(event.data)
                last_status = None
            else:
                if event.status != last_status or (event.status & 0xF0) == 0xF0:
                    track_data.append(event.status)
                    last_status = event.status

                track_data.append(event.data1)
                if (event.status & 0xF0) not in (0xC0, 0xD0):
                    track_data.append(event.data2)

        track_data.extend(self._write_variable_length(0))
        track_data.append(0xFF)
        track_data.append(0x2F)
        track_data.append(0x00)

        track_header = b'MTrk'
        track_header += struct.pack('>I', len(track_data))
        return track_header + bytes(track_data)

    def save(self, filepath):
        with open(filepath, 'wb') as f:
            f.write(self._write_header())
            for track in self.tracks:
                f.write(self._write_track(track))


class BeatMIDIExporter:
    def __init__(self, sr=44100, hop_length=512, ticks_per_beat=480):
        self.sr = sr
        self.hop_length = hop_length
        self.ticks_per_beat = ticks_per_beat

        self.drum_notes = {
            'kick': 36,
            'snare': 38,
            'hihat_closed': 42,
            'hihat_open': 46,
            'tom_low': 41,
            'tom_mid': 45,
            'tom_high': 48,
            'crash': 49,
            'ride': 51,
            'clap': 39,
        }

        self.note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

    def _time_to_ticks(self, time_sec, bpm):
        beat_duration = 60.0 / bpm if bpm > 0 else 0.5
        beats = time_sec / beat_duration
        return int(beats * self.ticks_per_beat)

    def _freq_to_midi(self, freq):
        if freq <= 0:
            return 60
        midi = int(69 + 12 * np.log2(freq / 440.0))
        return max(0, min(127, midi))

    def _midi_to_note_name(self, midi_note):
        octave = midi_note // 12 - 1
        note = self.note_names[midi_note % 12]
        return f'{note}{octave}'

    def export_beats(self, beat_times, downbeat_times, bpm, output_file,
                     duration=None, time_signature=(4, 4), velocity=100):
        if duration is None and len(beat_times) > 0:
            duration = beat_times[-1] + 2.0
        elif duration is None:
            duration = 10.0

        midi_file = MIDIFile(format=1, ticks_per_beat=self.ticks_per_beat)

        tempo_track = []
        tempo = int(60000000 / bpm) if bpm > 0 else 500000
        tempo_bytes = struct.pack('>I', tempo)[1:]
        tempo_track.append(MIDIMetaEvent(time=0, meta_type=0x51, data=tempo_bytes))

        numerator, denominator = time_signature
        denom_log = int(np.log2(denominator))
        time_sig_data = bytes([numerator, denom_log, 24, 8])
        tempo_track.append(MIDIMetaEvent(time=0, meta_type=0x58, data=time_sig_data))

        midi_file.add_track(tempo_track)

        beat_track = []
        prev_ticks = 0

        for i, bt in enumerate(beat_times):
            ticks = self._time_to_ticks(bt, bpm)
            delta = max(0, ticks - prev_ticks)

            is_downbeat = any(abs(bt - dbt) < 0.01 for dbt in downbeat_times)

            if is_downbeat:
                note = self.drum_notes['kick']
                vel = min(127, velocity + 20)
            else:
                beat_in_bar = i % time_signature[0]
                if beat_in_bar == 2:
                    note = self.drum_notes['snare']
                    vel = velocity
                else:
                    note = self.drum_notes['hihat_closed']
                    vel = max(40, velocity - 20)

            beat_track.append(MIDIEvent(
                time=delta,
                status=0x99,
                data1=note,
                data2=vel,
            ))

            note_duration_ticks = int(self.ticks_per_beat * 0.25)
            beat_track.append(MIDIEvent(
                time=note_duration_ticks,
                status=0x89,
                data1=note,
                data2=0,
            ))

            prev_ticks = ticks + note_duration_ticks

        end_ticks = self._time_to_ticks(duration, bpm)
        if end_ticks > prev_ticks:
            beat_track.append(MIDIEvent(
                time=end_ticks - prev_ticks,
                status=0x89,
                data1=0,
                data2=0,
            ))

        midi_file.add_track(beat_track)
        midi_file.save(output_file)

        return {
            'file': output_file,
            'bpm': bpm,
            'total_beats': len(beat_times),
            'total_downbeats': len(downbeat_times),
            'duration': duration,
            'ticks_per_beat': self.ticks_per_beat,
        }

    def export_melody(self, beat_times, downbeat_times, bpm, output_file,
                      key='C', scale='major', duration=None, velocity=80):
        if duration is None and len(beat_times) > 0:
            duration = beat_times[-1] + 2.0
        elif duration is None:
            duration = 10.0

        scales = {
            'major': [0, 2, 4, 5, 7, 9, 11],
            'minor': [0, 2, 3, 5, 7, 8, 10],
            'pentatonic': [0, 2, 4, 7, 9],
            'blues': [0, 3, 5, 6, 7, 10],
        }

        key_offsets = {'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'F': 5,
                       'F#': 6, 'G': 7, 'G#': 8, 'A': 9, 'A#': 10, 'B': 11}

        base_note = 60 + key_offsets.get(key.upper(), 0)
        scale_notes = scales.get(scale.lower(), scales['major'])

        midi_file = MIDIFile(format=1, ticks_per_beat=self.ticks_per_beat)

        tempo_track = []
        tempo = int(60000000 / bpm) if bpm > 0 else 500000
        tempo_bytes = struct.pack('>I', tempo)[1:]
        tempo_track.append(MIDIMetaEvent(time=0, meta_type=0x51, data=tempo_bytes))
        midi_file.add_track(tempo_track)

        melody_track = []
        prev_ticks = 0

        np.random.seed(42)

        for i, bt in enumerate(beat_times):
            ticks = self._time_to_ticks(bt, bpm)
            delta = max(0, ticks - prev_ticks)

            is_downbeat = any(abs(bt - dbt) < 0.01 for dbt in downbeat_times)

            if is_downbeat:
                note_idx = 0
                octave_shift = 0
            else:
                note_idx = np.random.randint(0, len(scale_notes))
                octave_shift = np.random.choice([0, 0, 12, -12], p=[0.5, 0.3, 0.15, 0.05])

            midi_note = base_note + scale_notes[note_idx] + octave_shift
            midi_note = max(36, min(84, midi_note))

            note_duration = 0.5 if is_downbeat else 0.25
            note_duration_ticks = int(self.ticks_per_beat * note_duration)

            melody_track.append(MIDIEvent(
                time=delta,
                status=0x90,
                data1=midi_note,
                data2=velocity,
            ))

            melody_track.append(MIDIEvent(
                time=note_duration_ticks,
                status=0x80,
                data1=midi_note,
                data2=0,
            ))

            prev_ticks = ticks + note_duration_ticks

        midi_file.add_track(melody_track)
        midi_file.save(output_file)

        return {
            'file': output_file,
            'bpm': bpm,
            'key': key,
            'scale': scale,
            'total_notes': len(beat_times),
            'duration': duration,
        }

    def export_complete(self, beat_times, downbeat_times, bpm, output_file,
                        duration=None, time_signature=(4, 4),
                        drum_velocity=100, melody_velocity=80,
                        key='C', scale='major'):
        if duration is None and len(beat_times) > 0:
            duration = beat_times[-1] + 2.0
        elif duration is None:
            duration = 10.0

        midi_file = MIDIFile(format=1, ticks_per_beat=self.ticks_per_beat)

        tempo_track = []
        tempo = int(60000000 / bpm) if bpm > 0 else 500000
        tempo_bytes = struct.pack('>I', tempo)[1:]
        tempo_track.append(MIDIEvent(time=0, status=0xFF, data1=0x51, data2=0x03))
        midi_file.add_track(tempo_track)

        drum_track = []
        prev_ticks = 0

        for i, bt in enumerate(beat_times):
            ticks = self._time_to_ticks(bt, bpm)
            delta = max(0, ticks - prev_ticks)

            is_downbeat = any(abs(bt - dbt) < 0.01 for dbt in downbeat_times)
            beat_in_bar = i % time_signature[0]

            if is_downbeat:
                notes = [(self.drum_notes['kick'], min(127, drum_velocity + 20))]
            elif beat_in_bar == 2:
                notes = [(self.drum_notes['snare'], drum_velocity)]
            else:
                notes = [(self.drum_notes['hihat_closed'], max(40, drum_velocity - 20))]

            if beat_in_bar % 2 == 1:
                notes.append((self.drum_notes['hihat_closed'], max(30, drum_velocity - 40)))

            note_duration_ticks = int(self.ticks_per_beat * 0.25)

            for j, (note, vel) in enumerate(notes):
                if j == 0:
                    drum_track.append(MIDIEvent(
                        time=delta,
                        status=0x99,
                        data1=note,
                        data2=vel,
                    ))
                else:
                    drum_track.append(MIDIEvent(
                        time=0,
                        status=0x99,
                        data1=note,
                        data2=vel,
                    ))

            for j, (note, vel) in enumerate(notes):
                if j == 0:
                    drum_track.append(MIDIEvent(
                        time=note_duration_ticks,
                        status=0x89,
                        data1=note,
                        data2=0,
                    ))
                else:
                    drum_track.append(MIDIEvent(
                        time=0,
                        status=0x89,
                        data1=note,
                        data2=0,
                    ))

            prev_ticks = ticks + note_duration_ticks

        midi_file.add_track(drum_track)

        scales = {
            'major': [0, 2, 4, 5, 7, 9, 11],
            'minor': [0, 2, 3, 5, 7, 8, 10],
            'pentatonic': [0, 2, 4, 7, 9],
            'blues': [0, 3, 5, 6, 7, 10],
        }

        key_offsets = {'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'F': 5,
                       'F#': 6, 'G': 7, 'G#': 8, 'A': 9, 'A#': 10, 'B': 11}

        base_note = 60 + key_offsets.get(key.upper(), 0)
        scale_notes = scales.get(scale.lower(), scales['major'])

        melody_track = []
        prev_ticks = 0
        np.random.seed(42)

        for i, bt in enumerate(beat_times):
            ticks = self._time_to_ticks(bt, bpm)
            delta = max(0, ticks - prev_ticks)

            is_downbeat = any(abs(bt - dbt) < 0.01 for dbt in downbeat_times)

            if is_downbeat:
                note_idx = 0
                octave_shift = 0
            else:
                note_idx = np.random.randint(0, len(scale_notes))
                octave_shift = np.random.choice([0, 0, 12, -12], p=[0.5, 0.3, 0.15, 0.05])

            midi_note = base_note + scale_notes[note_idx] + octave_shift
            midi_note = max(36, min(84, midi_note))

            note_duration = 0.5 if is_downbeat else 0.25
            note_duration_ticks = int(self.ticks_per_beat * note_duration)

            melody_track.append(MIDIEvent(
                time=delta,
                status=0x90,
                data1=midi_note,
                data2=melody_velocity,
            ))

            melody_track.append(MIDIEvent(
                time=note_duration_ticks,
                status=0x80,
                data1=midi_note,
                data2=0,
            ))

            prev_ticks = ticks + note_duration_ticks

        midi_file.add_track(melody_track)
        midi_file.save(output_file)

        return {
            'file': output_file,
            'bpm': bpm,
            'key': key,
            'scale': scale,
            'time_signature': f'{time_signature[0]}/{time_signature[1]}',
            'total_beats': len(beat_times),
            'total_downbeats': len(downbeat_times),
            'duration': duration,
            'tracks': ['tempo', 'drums', 'melody'],
        }

    def export_structure(self, beat_times, downbeat_times, bpm, structure_segments,
                         output_file, duration=None, time_signature=(4, 4), velocity=90):
        if duration is None and len(beat_times) > 0:
            duration = beat_times[-1] + 2.0
        elif duration is None:
            duration = 10.0

        section_instruments = {
            'intro': 48,
            'verse': 1,
            'chorus': 30,
            'bridge': 35,
            'outro': 56,
            'breakdown': 29,
            'pre_chorus': 6,
            'solo': 27,
        }

        midi_file = MIDIFile(format=1, ticks_per_beat=self.ticks_per_beat)

        tempo_track = []
        tempo = int(60000000 / bpm) if bpm > 0 else 500000
        tempo_bytes = struct.pack('>I', tempo)[1:]
        tempo_track.append(MIDIMetaEvent(time=0, meta_type=0x51, data=tempo_bytes))
        midi_file.add_track(tempo_track)

        for segment in structure_segments:
            track = []
            seg_type = segment['type']
            seg_start = segment['start']
            seg_end = segment['end']
            instrument = section_instruments.get(seg_type, 1)

            track.append(MIDIEvent(time=0, status=0xC0, data1=instrument, data2=0))

            seg_beats = [bt for bt in beat_times if seg_start <= bt <= seg_end]
            seg_downbeats = [dbt for dbt in downbeat_times if seg_start <= dbt <= seg_end]

            prev_ticks = 0

            for i, bt in enumerate(seg_beats):
                ticks = self._time_to_ticks(bt - seg_start, bpm)
                delta = max(0, ticks - prev_ticks)

                is_downbeat = any(abs(bt - dbt) < 0.01 for dbt in seg_downbeats)

                base_note = 48 if is_downbeat else 60
                note = base_note + (i % 7) * 2
                note = max(36, min(84, note))

                vel = min(127, velocity + (10 if is_downbeat else 0))
                note_duration = 0.5 if is_downbeat else 0.25
                note_duration_ticks = int(self.ticks_per_beat * note_duration)

                track.append(MIDIEvent(
                    time=delta,
                    status=0x90,
                    data1=note,
                    data2=vel,
                ))

                track.append(MIDIEvent(
                    time=note_duration_ticks,
                    status=0x80,
                    data1=note,
                    data2=0,
                ))

                prev_ticks = ticks + note_duration_ticks

            midi_file.add_track(track)

        midi_file.save(output_file)

        return {
            'file': output_file,
            'bpm': bpm,
            'total_segments': len(structure_segments),
            'segment_types': [s['type'] for s in structure_segments],
            'duration': duration,
        }

    def print_midi_info(self, midi_info):
        print('\n' + '=' * 60)
        print('  MIDI EXPORT SUMMARY')
        print('=' * 60)
        for key, value in midi_info.items():
            if isinstance(value, list):
                value_str = ', '.join(str(v) for v in value)
            else:
                value_str = str(value)
            print(f'  {key.replace("_", " ").title():<20}: {value_str}')
        print('=' * 60 + '\n')
