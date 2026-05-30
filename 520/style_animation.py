import torch
import cv2
import numpy as np
from PIL import Image
from style_mixer import StyleMixer


class StyleAnimationGenerator:
    def __init__(self, device='cpu'):
        self.device = device
        self.style_mixer = StyleMixer(device)

    def generate_interpolation_animation(self, content_img, style_img1, style_img2,
                                          num_frames=30, alpha=0.8, fps=15,
                                          hf_enhance=True, hf_strength=0.5,
                                          output_format='gif', output_path=None,
                                          progress_callback=None):
        frames_bgr = self.style_mixer.style_interpolation(
            content_img, style_img1, style_img2,
            interpolation_steps=num_frames, alpha=alpha,
            hf_enhance=hf_enhance, hf_strength=hf_strength
        )

        frames_rgb = [cv2.cvtColor(f, cv2.COLOR_BGR2RGB) for f in frames_bgr]
        pil_frames = [Image.fromarray(f) for f in frames_rgb]

        if progress_callback:
            progress_callback(num_frames, num_frames)

        if output_path is None:
            output_path = f'style_interpolation.{output_format}'

        if output_format == 'gif':
            pil_frames[0].save(
                output_path, save_all=True, append_images=pil_frames[1:],
                duration=int(1000 / fps), loop=0
            )
        elif output_format == 'mp4':
            self._write_mp4(frames_bgr, output_path, fps)

        return output_path, pil_frames

    def generate_multi_keyframe_animation(self, content_img, style_keyframes,
                                           num_frames_per_seg=10, alpha=0.8, fps=15,
                                           hf_enhance=True, hf_strength=0.5,
                                           output_format='gif', output_path=None,
                                           progress_callback=None):
        frames_bgr = self.style_mixer.multi_keyframe_interpolation(
            content_img, style_keyframes,
            num_frames_per_seg=num_frames_per_seg, alpha=alpha,
            hf_enhance=hf_enhance, hf_strength=hf_strength
        )

        frames_rgb = [cv2.cvtColor(f, cv2.COLOR_BGR2RGB) for f in frames_bgr]
        pil_frames = [Image.fromarray(f) for f in frames_rgb]

        if progress_callback:
            progress_callback(len(frames_bgr), len(frames_bgr))

        if output_path is None:
            output_path = f'multi_keyframe_animation.{output_format}'

        if output_format == 'gif':
            pil_frames[0].save(
                output_path, save_all=True, append_images=pil_frames[1:],
                duration=int(1000 / fps), loop=0
            )
        elif output_format == 'mp4':
            self._write_mp4(frames_bgr, output_path, fps)

        return output_path, pil_frames

    def generate_cyclic_animation(self, content_img, style_imgs, num_cycles=1,
                                   frames_per_style=10, alpha=0.8, fps=15,
                                   hf_enhance=True, hf_strength=0.5,
                                   output_format='gif', output_path=None,
                                   progress_callback=None):
        all_frames_bgr = []
        n = len(style_imgs)

        for cycle in range(num_cycles):
            for i in range(n):
                next_i = (i + 1) % n
                seg_frames = self.style_mixer.style_interpolation(
                    content_img, style_imgs[i], style_imgs[next_i],
                    interpolation_steps=frames_per_style, alpha=alpha,
                    hf_enhance=hf_enhance, hf_strength=hf_strength
                )
                if i < n - 1:
                    seg_frames = seg_frames[:-1]
                all_frames_bgr.extend(seg_frames)

                if progress_callback:
                    done = (cycle * n + i + 1)
                    total = num_cycles * n
                    progress_callback(done, total)

        frames_rgb = [cv2.cvtColor(f, cv2.COLOR_BGR2RGB) for f in all_frames_bgr]
        pil_frames = [Image.fromarray(f) for f in frames_rgb]

        if output_path is None:
            output_path = f'cyclic_animation.{output_format}'

        if output_format == 'gif':
            pil_frames[0].save(
                output_path, save_all=True, append_images=pil_frames[1:],
                duration=int(1000 / fps), loop=0
            )
        elif output_format == 'mp4':
            self._write_mp4(all_frames_bgr, output_path, fps)

        return output_path, pil_frames

    def generate_intensity_sweep_animation(self, content_img, style_img,
                                            num_frames=30, alpha_max=1.0,
                                            fps=15, ping_pong=True,
                                            hf_enhance=True, hf_strength=0.5,
                                            output_format='gif', output_path=None,
                                            progress_callback=None):
        alphas = np.linspace(0, alpha_max, num_frames)
        if ping_pong:
            alphas = np.concatenate([alphas, alphas[-2:0:-1]])

        frames_bgr = []
        for i, a in enumerate(alphas):
            frame = self.style_mixer.style_swap(
                content_img, style_img, alpha=a, method='adain',
                hf_enhance=hf_enhance, hf_strength=hf_strength * a
            )
            frames_bgr.append(frame)

            if progress_callback:
                progress_callback(i + 1, len(alphas))

        frames_rgb = [cv2.cvtColor(f, cv2.COLOR_BGR2RGB) for f in frames_bgr]
        pil_frames = [Image.fromarray(f) for f in frames_rgb]

        if output_path is None:
            output_path = f'intensity_sweep.{output_format}'

        if output_format == 'gif':
            pil_frames[0].save(
                output_path, save_all=True, append_images=pil_frames[1:],
                duration=int(1000 / fps), loop=0
            )
        elif output_format == 'mp4':
            self._write_mp4(frames_bgr, output_path, fps)

        return output_path, pil_frames

    def _write_mp4(self, frames_bgr, output_path, fps):
        if len(frames_bgr) == 0:
            return
        h, w = frames_bgr[0].shape[:2]
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (w, h))
        for frame in frames_bgr:
            out.write(frame)
        out.release()
