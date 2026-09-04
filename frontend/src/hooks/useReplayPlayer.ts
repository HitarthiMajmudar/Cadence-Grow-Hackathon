import { useCallback, useEffect, useMemo, useRef, useState } from "react";

const SPEEDS = [0.5, 1, 2, 4] as const;
export type Speed = (typeof SPEEDS)[number];

function prefersReducedMotion(): boolean {
  try {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  } catch {
    return false;
  }
}

export function useReplayPlayer(frameCount: number) {
  const [index, setIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState<Speed>(1);
  const reduced = useMemo(prefersReducedMotion, []);
  const raf = useRef<number | null>(null);
  const last = useRef<number>(0);

  // reset when a new replay loads
  useEffect(() => {
    setIndex(0);
    setPlaying(false);
  }, [frameCount]);

  useEffect(() => {
    if (!playing || frameCount === 0) return;
    const baseMs = reduced ? 90 : 260; // ms per frame at 1x
    const stepMs = baseMs / speed;

    const tick = (t: number) => {
      if (t - last.current >= stepMs) {
        last.current = t;
        setIndex((i) => {
          if (i >= frameCount - 1) {
            setPlaying(false);
            return i;
          }
          return i + 1;
        });
      }
      raf.current = requestAnimationFrame(tick);
    };
    raf.current = requestAnimationFrame(tick);
    return () => {
      if (raf.current) cancelAnimationFrame(raf.current);
    };
  }, [playing, speed, frameCount, reduced]);

  const play = useCallback(() => {
    setIndex((i) => (i >= frameCount - 1 ? 0 : i));
    last.current = 0;
    setPlaying(true);
  }, [frameCount]);

  const pause = useCallback(() => setPlaying(false), []);
  const restart = useCallback(() => {
    setIndex(0);
    last.current = 0;
    setPlaying(true);
  }, []);
  const stepForward = useCallback(() => {
    setPlaying(false);
    setIndex((i) => Math.min(frameCount - 1, i + 1));
  }, [frameCount]);
  const stepBack = useCallback(() => {
    setPlaying(false);
    setIndex((i) => Math.max(0, i - 1));
  }, []);
  const seek = useCallback(
    (i: number) => {
      setPlaying(false);
      setIndex(Math.max(0, Math.min(frameCount - 1, i)));
    },
    [frameCount],
  );

  return {
    index,
    playing,
    speed,
    speeds: SPEEDS,
    setSpeed,
    play,
    pause,
    restart,
    stepForward,
    stepBack,
    seek,
    reduced,
    atEnd: index >= frameCount - 1,
  };
}
