"use client";

import React, { useEffect, useState, useRef, useMemo } from "react";

export interface EyeProps {
  cursorX?: number;
  cursorY?: number;
  isClosed?: boolean;
  isPeeking?: boolean;
  variant?: "sclera" | "beady";
  size?: "xs" | "sm" | "md" | "lg";
  pupilColor?: string;
  scleraColor?: string;
  gap?: number;
  className?: string;
}

export const CharacterEyes: React.FC<EyeProps> = ({
  cursorX = 0,
  cursorY = 0,
  isClosed = false,
  isPeeking = false,
  variant = "sclera",
  size = "sm",
  pupilColor = "#18181b",
  scleraColor = "#ffffff",
  gap = 6,
  className = "",
}) => {
  const leftEyeRef = useRef<HTMLDivElement>(null);
  const rightEyeRef = useRef<HTMLDivElement>(null);

  const [leftOffset, setLeftOffset] = useState({ x: 0, y: 0 });
  const [rightOffset, setRightOffset] = useState({ x: 0, y: 0 });
  const [isBlinking, setIsBlinking] = useState(false);

  // Dimensions based on size and variant
  const dim = useMemo(() => {
    if (variant === "beady") {
      switch (size) {
        case "xs":
          return { eyeW: 6, eyeH: 6, pupilSize: 6, maxRadius: 2.5 };
        case "sm":
          return { eyeW: 7.5, eyeH: 8, pupilSize: 7.5, maxRadius: 3.5 };
        case "lg":
          return { eyeW: 12, eyeH: 13, pupilSize: 12, maxRadius: 5 };
        case "md":
        default:
          return { eyeW: 9, eyeH: 10, pupilSize: 9, maxRadius: 4 };
      }
    } else {
      // Sclera white eyeball with inner pupil
      switch (size) {
        case "xs":
          return { eyeW: 11, eyeH: 13, pupilSize: 5.5, maxRadius: 3 };
        case "sm":
          return { eyeW: 15, eyeH: 17, pupilSize: 7, maxRadius: 4 };
        case "lg":
          return { eyeW: 22, eyeH: 25, pupilSize: 10, maxRadius: 6 };
        case "md":
        default:
          return { eyeW: 17, eyeH: 20, pupilSize: 8, maxRadius: 5 };
      }
    }
  }, [size, variant]);

  // Subtle natural blink
  useEffect(() => {
    if (isClosed) return;

    let timer: NodeJS.Timeout;
    const blink = () => {
      setIsBlinking(true);
      setTimeout(() => setIsBlinking(false), 140);
      timer = setTimeout(blink, 4000 + Math.random() * 3000);
    };

    timer = setTimeout(blink, 2500 + Math.random() * 2000);
    return () => clearTimeout(timer);
  }, [isClosed]);

  // Calculate pupil tracking
  useEffect(() => {
    if (isClosed) {
      setLeftOffset({ x: 0, y: 0 });
      setRightOffset({ x: 0, y: 0 });
      return;
    }

    const calc = (el: HTMLDivElement | null) => {
      if (!el) return { x: 0, y: 0 };
      const rect = el.getBoundingClientRect();
      const cx = rect.left + rect.width / 2;
      const cy = rect.top + rect.height / 2;

      const dx = cursorX - cx;
      const dy = cursorY - cy;
      const dist = Math.hypot(dx, dy);
      if (dist < 1) return { x: 0, y: 0 };

      const maxDist = 450;
      const norm = Math.min(dist / maxDist, 1);
      const pupilDist = norm * dim.maxRadius;
      const angle = Math.atan2(dy, dx);

      return {
        x: Math.cos(angle) * pupilDist,
        y: Math.sin(angle) * pupilDist,
      };
    };

    setLeftOffset(calc(leftEyeRef.current));
    setRightOffset(calc(rightEyeRef.current));
  }, [cursorX, cursorY, isClosed, dim.maxRadius]);

  const shouldClose = isClosed || isBlinking;

  return (
    <div
      className={`inline-flex items-center justify-center select-none ${className}`}
      style={{ gap: `${gap}px` }}
      aria-hidden="true"
    >
      {/* Left Eye */}
      <div
        ref={leftEyeRef}
        className="relative overflow-hidden rounded-full flex items-center justify-center transition-all duration-150"
        style={{
          width: `${dim.eyeW}px`,
          height: `${dim.eyeH}px`,
          backgroundColor: variant === "sclera" ? scleraColor : "transparent",
        }}
      >
        {/* Open State (Pupil / Beady Eye) */}
        <div
          className={`absolute inset-0 flex items-center justify-center transition-all duration-150 ${
            shouldClose ? "opacity-0 scale-y-0" : "opacity-100 scale-y-100"
          }`}
        >
          <div
            className="rounded-full relative transition-transform duration-75 ease-out"
            style={{
              width: `${dim.pupilSize * (isPeeking ? 1.2 : 1)}px`,
              height: `${dim.pupilSize * (isPeeking ? 1.2 : 1)}px`,
              backgroundColor: pupilColor,
              transform: `translate3d(${leftOffset.x}px, ${leftOffset.y}px, 0)`,
            }}
          >
            {/* Minimal subtle catchlight */}
            <div
              className="absolute rounded-full bg-white/90"
              style={{
                top: "18%",
                left: "22%",
                width: `${Math.max(dim.pupilSize * 0.28, 1.5)}px`,
                height: `${Math.max(dim.pupilSize * 0.28, 1.5)}px`,
              }}
            />
          </div>
        </div>

        {/* Closed Curved Arc State */}
        <div
          className={`absolute inset-0 flex items-center justify-center transition-all duration-150 ${
            shouldClose ? "opacity-100 scale-100" : "opacity-0 scale-50 pointer-events-none"
          }`}
        >
          <svg
            viewBox="0 0 16 10"
            className="w-full h-auto text-neutral-900"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.2"
            strokeLinecap="round"
          >
            <path d="M 2 7 C 5 2.5, 11 2.5, 14 7" />
          </svg>
        </div>
      </div>

      {/* Right Eye */}
      <div
        ref={rightEyeRef}
        className="relative overflow-hidden rounded-full flex items-center justify-center transition-all duration-150"
        style={{
          width: `${dim.eyeW}px`,
          height: `${dim.eyeH}px`,
          backgroundColor: variant === "sclera" ? scleraColor : "transparent",
        }}
      >
        {/* Open State (Pupil / Beady Eye) */}
        <div
          className={`absolute inset-0 flex items-center justify-center transition-all duration-150 ${
            shouldClose ? "opacity-0 scale-y-0" : "opacity-100 scale-y-100"
          }`}
        >
          <div
            className="rounded-full relative transition-transform duration-75 ease-out"
            style={{
              width: `${dim.pupilSize * (isPeeking ? 1.2 : 1)}px`,
              height: `${dim.pupilSize * (isPeeking ? 1.2 : 1)}px`,
              backgroundColor: pupilColor,
              transform: `translate3d(${rightOffset.x}px, ${rightOffset.y}px, 0)`,
            }}
          >
            {/* Minimal subtle catchlight */}
            <div
              className="absolute rounded-full bg-white/90"
              style={{
                top: "18%",
                left: "22%",
                width: `${Math.max(dim.pupilSize * 0.28, 1.5)}px`,
                height: `${Math.max(dim.pupilSize * 0.28, 1.5)}px`,
              }}
            />
          </div>
        </div>

        {/* Closed Curved Arc State */}
        <div
          className={`absolute inset-0 flex items-center justify-center transition-all duration-150 ${
            shouldClose ? "opacity-100 scale-100" : "opacity-0 scale-50 pointer-events-none"
          }`}
        >
          <svg
            viewBox="0 0 16 10"
            className="w-full h-auto text-neutral-900"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.2"
            strokeLinecap="round"
          >
            <path d="M 2 7 C 5 2.5, 11 2.5, 14 7" />
          </svg>
        </div>
      </div>
    </div>
  );
};
