"use client";

import React from "react";

export const TechnicalWaveVisual: React.FC<{ className?: string }> = ({ className = "" }) => {
  // 14 harmonic wavy contour lines matching the editorial reference graphic
  const wavePaths = [
    "M -80,260 C 220,190 440,330 720,250 C 1000,170 1240,290 1520,220",
    "M -80,272 C 220,202 440,342 720,262 C 1000,182 1240,302 1520,232",
    "M -80,284 C 220,214 440,354 720,274 C 1000,194 1240,314 1520,244",
    "M -80,296 C 220,226 440,366 720,286 C 1000,206 1240,326 1520,256",
    "M -80,308 C 220,238 440,378 720,298 C 1000,218 1240,338 1520,268",
    "M -80,320 C 220,250 440,390 720,310 C 1000,230 1240,350 1520,280",
    "M -80,332 C 220,262 440,402 720,322 C 1000,242 1240,362 1520,292",
    "M -80,344 C 220,274 440,414 720,334 C 1000,254 1240,374 1520,304",
    "M -80,356 C 220,286 440,426 720,346 C 1000,266 1240,386 1520,316",
    "M -80,368 C 220,298 440,438 720,358 C 1000,278 1240,398 1520,328",
    "M -80,380 C 220,310 440,450 720,370 C 1000,290 1240,410 1520,340",
    "M -80,392 C 220,322 440,462 720,382 C 1000,302 1240,422 1520,352",
    "M -80,404 C 220,334 440,474 720,394 C 1000,314 1240,434 1520,364",
    "M -80,416 C 220,346 440,486 720,406 C 1000,326 1240,446 1520,376",
  ];

  return (
    <div
      aria-hidden="true"
      className={`absolute inset-0 overflow-hidden pointer-events-none select-none flex items-center justify-center -z-10 ${className}`}
    >
      <svg
        viewBox="0 0 1440 640"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="w-full h-full object-cover opacity-75 dark:opacity-40"
        preserveAspectRatio="xMidYMid slice"
      >
        {wavePaths.map((d, i) => (
          <path
            key={i}
            d={d}
            stroke="currentColor"
            strokeWidth="0.85"
            className="text-neutral-400/50 dark:text-neutral-600/40"
            vectorEffect="non-scaling-stroke"
          />
        ))}
      </svg>
    </div>
  );
};
