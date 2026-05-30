import { useEffect, useRef, useCallback, useState } from 'react';
import { useLEDStore } from '../store/ledStore';

const CHANNEL_NAME = 'led-sync-channel';

export function useMultiScreenSync() {
  const channelRef = useRef<BroadcastChannel | null>(null);
  const [isSyncing, setIsSyncing] = useState(false);
  const [screenCount, setScreenCount] = useState(1);
  const screenIdRef = useRef(Math.random().toString(36).substr(2, 9));

  const { applyPreset, lines, font, scroll, background, isPlaying } = useLEDStore();

  const initChannel = useCallback(() => {
    if (channelRef.current) {
      channelRef.current.close();
    }

    const channel = new BroadcastChannel(CHANNEL_NAME);

    channel.onmessage = (event) => {
      const message = event.data;

      switch (message.type) {
        case 'screen_announce':
          setScreenCount(message.payload.screenCount);
          break;

        case 'sync_subtitle':
          if (message.screenId !== screenIdRef.current) {
            applyPreset({
              name: '多屏同步',
              lines: message.payload.lines,
              font: message.payload.font,
              scroll: message.payload.scroll,
              background: message.payload.background
            });
          }
          break;

        case 'sync_play_state':
          if (message.screenId !== screenIdRef.current) {
            const currentState = useLEDStore.getState().isPlaying;
            if (currentState !== message.payload.isPlaying) {
              useLEDStore.getState().togglePlaying();
            }
          }
          break;

        case 'screen_ping':
          if (message.screenId !== screenIdRef.current) {
            channel.postMessage({
              type: 'screen_pong',
              screenId: screenIdRef.current,
              payload: { screenCount: message.payload.screenCount + 1 }
            });
          }
          break;

        case 'screen_pong':
          setScreenCount(message.payload.screenCount);
          break;

        case 'screen_leave':
          setScreenCount((prev) => Math.max(1, prev - 1));
          break;
      }
    };

    channelRef.current = channel;

    channel.postMessage({
      type: 'screen_ping',
      screenId: screenIdRef.current,
      payload: { screenCount: 1 }
    });
  }, [applyPreset]);

  const broadcastState = useCallback(() => {
    if (!channelRef.current || !isSyncing) return;

    channelRef.current.postMessage({
      type: 'sync_subtitle',
      screenId: screenIdRef.current,
      payload: {
        lines: lines.map((l) => ({ text: l.text, color: l.color })),
        font,
        scroll,
        background
      }
    });
  }, [lines, font, scroll, background, isSyncing]);

  const broadcastPlayState = useCallback(() => {
    if (!channelRef.current || !isSyncing) return;

    channelRef.current.postMessage({
      type: 'sync_play_state',
      screenId: screenIdRef.current,
      payload: { isPlaying }
    });
  }, [isPlaying, isSyncing]);

  const toggleSync = useCallback(() => {
    const newState = !isSyncing;
    setIsSyncing(newState);

    if (newState) {
      initChannel();
    } else {
      if (channelRef.current) {
        channelRef.current.postMessage({
          type: 'screen_leave',
          screenId: screenIdRef.current
        });
        channelRef.current.close();
        channelRef.current = null;
      }
      setScreenCount(1);
    }
  }, [isSyncing, initChannel]);

  useEffect(() => {
    return () => {
      if (channelRef.current) {
        channelRef.current.postMessage({
          type: 'screen_leave',
          screenId: screenIdRef.current
        });
        channelRef.current.close();
      }
    };
  }, []);

  return {
    isSyncing,
    screenCount,
    screenId: screenIdRef.current,
    toggleSync,
    broadcastState,
    broadcastPlayState
  };
}
