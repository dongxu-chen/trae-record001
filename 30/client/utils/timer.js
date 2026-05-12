export function formatTime(seconds) {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;

  const parts = [];
  if (hours > 0) {
    parts.push(hours.toString().padStart(2, '0'));
  }
  parts.push(minutes.toString().padStart(2, '0'));
  parts.push(secs.toString().padStart(2, '0'));

  return parts.join(':');
}

export function minutesToSeconds(minutes) {
  return minutes * 60;
}

export function secondsToMinutes(seconds) {
  return Math.ceil(seconds / 60);
}

export function isTimeUp(seconds) {
  return seconds <= 0;
}

export function getTimeStatus(seconds, totalSeconds) {
  const ratio = seconds / totalSeconds;
  if (ratio > 0.5) {
    return 'normal';
  } else if (ratio > 0.25) {
    return 'warning';
  }
  return 'danger';
}

export function createAccurateTimer(totalSeconds, onTick, onComplete) {
  const startTime = performance.now();
  const endTime = startTime + totalSeconds * 1000;
  let timerId = null;

  function tick() {
    const now = performance.now();
    const remaining = Math.max(0, Math.ceil((endTime - now) / 1000));

    onTick(remaining);

    if (remaining <= 0) {
      onComplete();
      return;
    }

    timerId = requestAnimationFrame(tick);
  }

  timerId = requestAnimationFrame(tick);

  return {
    stop: () => {
      if (timerId) {
        cancelAnimationFrame(timerId);
        timerId = null;
      }
    },
    getRemaining: () => {
      const now = performance.now();
      return Math.max(0, Math.ceil((endTime - now) / 1000));
    }
  };
}
