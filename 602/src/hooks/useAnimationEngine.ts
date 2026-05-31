import { useEffect, useRef, useCallback } from 'react';
import gsap from 'gsap';
import type { Project, AnimationTrack } from '@/types';

interface AnimationEngineOptions {
  project: Project;
  currentTime: number;
  isPlaying: boolean;
}

export const useAnimationEngine = ({ project, currentTime, isPlaying }: AnimationEngineOptions) => {
  const timelineRef = useRef<gsap.core.Timeline | null>(null);
  const targetsRef = useRef<Map<string, any>>(new Map());

  const registerTarget = useCallback((id: string, element: any) => {
    targetsRef.current.set(id, element);
  }, []);

  const unregisterTarget = useCallback((id: string) => {
    targetsRef.current.delete(id);
  }, []);

  const buildAnimation = useCallback((track: AnimationTrack, target: any): gsap.core.Tween | null => {
    if (!target) return null;

    const { property, keyframes, easing, duration, delay, type, motionPath } = track;

    if (type === 'motionPath' && motionPath) {
      return gsap.to(target, {
        motionPath: {
          path: motionPath.path,
          align: motionPath.align,
          alignToSelf: motionPath.alignToSelf,
          start: motionPath.start || 0,
          end: motionPath.end || 1,
          autoRotate: motionPath.orient === 'auto',
        },
        duration,
        delay,
        ease: easing,
        paused: true,
      });
    }

    if (keyframes.length >= 2) {
      const kfValues = keyframes.map(kf => ({
        [property]: kf.value,
        duration: (kf.time - (keyframes[0]?.time || 0)) / keyframes.length,
        ease: kf.easing || easing,
      }));

      return gsap.to(target, {
        keyframes: kfValues,
        duration,
        delay,
        paused: true,
      });
    }

    if (keyframes.length === 1) {
      return gsap.to(target, {
        [property]: keyframes[0].value,
        duration,
        delay,
        ease: easing,
        paused: true,
      });
    }

    return null;
  }, []);

  const rebuildTimeline = useCallback(() => {
    if (timelineRef.current) {
      timelineRef.current.kill();
    }

    const tl = gsap.timeline({ paused: true });

    project.tracks.forEach(track => {
      const target = targetsRef.current.get(track.elementId);
      if (target) {
        const animation = buildAnimation(track, target);
        if (animation) {
          tl.add(animation, track.delay);
        }
      }
    });

    timelineRef.current = tl;
  }, [project.tracks, buildAnimation]);

  useEffect(() => {
    rebuildTimeline();
  }, [rebuildTimeline]);

  useEffect(() => {
    if (timelineRef.current && !isPlaying) {
      const totalDuration = timelineRef.current.duration();
      const progress = totalDuration > 0 ? currentTime / totalDuration : 0;
      timelineRef.current.progress(Math.min(1, Math.max(0, progress)));
    }
  }, [currentTime, isPlaying]);

  return {
    registerTarget,
    unregisterTarget,
    rebuildTimeline,
  };
};
