import os
import subprocess
from typing import Dict, Optional, Tuple, Union

import ffmpeg


def probe_video_info(file_path: str) -> Dict[str, Union[int, float]]:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    try:
        probe = ffmpeg.probe(file_path)
        video_stream = next(
            (stream for stream in probe['streams'] if stream['codec_type'] == 'video'),
            None
        )
        
        if video_stream is None:
            raise ValueError("No video stream found in the file")
        
        width = int(video_stream['width'])
        height = int(video_stream['height'])
        
        r_frame_rate = video_stream.get('r_frame_rate', '0/1')
        num, den = map(int, r_frame_rate.split('/'))
        fps = num / den if den != 0 else 0.0
        
        duration = float(probe['format'].get('duration', 0.0))
        
        return {
            'width': width,
            'height': height,
            'fps': fps,
            'duration': duration
        }
    except ffmpeg.Error as e:
        raise RuntimeError(f"FFmpeg probe error: {str(e)}") from e
    except (KeyError, ValueError) as e:
        raise RuntimeError(f"Failed to parse video info: {str(e)}") from e


def extract_frames_ffmpeg(
    input_path: str,
    output_dir: str,
    fps: float,
    frame_size: Optional[Tuple[int, int]] = None
) -> int:
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        output_pattern = os.path.join(output_dir, 'frame_%06d.jpg')
        
        stream = ffmpeg.input(input_path)
        
        if frame_size is not None:
            if not isinstance(frame_size, tuple) or len(frame_size) != 2:
                raise ValueError("frame_size must be a tuple of (width, height)")
            stream = stream.filter('scale', frame_size[0], frame_size[1])
        
        stream = stream.filter('fps', fps=fps)
        
        stream = stream.output(
            output_pattern,
            format='image2',
            vcodec='mjpeg',
            qscale=2,
            start_number=0
        )
        
        stream = stream.overwrite_output()
        
        cmd = stream.compile()
        subprocess.run(cmd, check=True, capture_output=True)
        
        frame_count = len([
            f for f in os.listdir(output_dir)
            if f.startswith('frame_') and f.endswith('.jpg')
        ])
        
        return frame_count
    except ffmpeg.Error as e:
        raise RuntimeError(f"FFmpeg error: {str(e)}") from e
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"FFmpeg process failed: {e.stderr.decode() if e.stderr else str(e)}") from e


def get_video_stream_pipeline(
    source: Union[str, int],
    fps: float,
    frame_size: Optional[Tuple[int, int]] = None
) -> subprocess.Popen:
    if isinstance(source, int):
        input_source = f'/dev/video{source}' if os.name != 'nt' else f'video={source}'
        input_format = 'v4l2' if os.name != 'nt' else 'dshow'
    elif isinstance(source, str):
        input_source = source
        input_format = None
    else:
        raise TypeError("source must be a string (file path) or integer (camera index)")
    
    try:
        cmd = ['ffmpeg']
        
        if input_format:
            cmd.extend(['-f', input_format])
        
        cmd.extend([
            '-i', input_source,
            '-r', str(fps),
            '-f', 'rawvideo',
            '-pix_fmt', 'bgr24'
        ])
        
        if frame_size is not None:
            if not isinstance(frame_size, tuple) or len(frame_size) != 2:
                raise ValueError("frame_size must be a tuple of (width, height)")
            cmd.extend([
                '-vf', f'scale={frame_size[0]}:{frame_size[1]}',
                '-s', f'{frame_size[0]}x{frame_size[1]}'
            ])
        
        cmd.append('-')
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=10**8
        )
        
        return process
    except Exception as e:
        raise RuntimeError(f"Failed to create video stream pipeline: {str(e)}") from e
