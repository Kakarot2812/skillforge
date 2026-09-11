"use client";

import React from "react";
import { CharacterEyes } from "./AnimatedEyes";

export interface InteractiveCharacterProps {
  cursorX?: number;
  cursorY?: number;
  isPasswordFocused?: boolean;
  isTypingPassword?: boolean;
  isPasswordVisible?: boolean;
  className?: string;
}

export const InteractiveCharacter: React.FC<InteractiveCharacterProps> = ({
  cursorX = 0,
  cursorY = 0,
  isPasswordFocused = false,
  isTypingPassword = false,
  isPasswordVisible = false,
  className = "",
}) => {
  const isClosed = (isPasswordFocused || isTypingPassword) && !isPasswordVisible;
  const isPeeking = (isPasswordFocused || isTypingPassword) && isPasswordVisible;

  return (
    <div
      className={`relative w-full h-full min-h-[380px] sm:min-h-[460px] flex items-end justify-center select-none overflow-hidden pb-4 sm:pb-6 ${className}`}
    >
      {/* Group Container */}
      <div className="relative w-full max-w-[420px] sm:max-w-[460px] h-[350px] sm:h-[400px] flex items-end justify-center">
        {/* --- CHARACTER 1: TALL PURPLE RECTANGLE (Back Center-Left) --- */}
        <div
          className={`absolute left-[24%] sm:left-[26%] bottom-0 w-[110px] sm:w-[130px] h-[250px] sm:h-[285px] rounded-[2.2rem] bg-[#6e38e0] z-10 flex flex-col items-center pt-8 transition-all duration-200 ${
            isClosed ? "scale-[0.99] translate-y-1" : ""
          }`}
        >
          {/* Sclera White Eyes with tracking pupils */}
          <div className="mt-1">
            <CharacterEyes
              cursorX={cursorX}
              cursorY={cursorY}
              isClosed={isClosed}
              isPeeking={isPeeking}
              variant="sclera"
              size="sm"
              gap={10}
            />
          </div>

          {/* Cute subtle smile */}
          <div className="mt-2.5">
            {isClosed ? (
              <div className="w-2.5 h-1 border-b-[2px] border-neutral-900 rounded-full" />
            ) : isPeeking ? (
              <div className="w-3.5 h-2 rounded-b-full bg-neutral-900" />
            ) : (
              <div className="w-3 h-1.5 border-b-[2px] border-neutral-900 rounded-b-full" />
            )}
          </div>
        </div>

        {/* --- CHARACTER 2: HOT PINK / MAGENTA SLENDER CAPSULE (Middle Right) --- */}
        <div
          className={`absolute left-[47%] sm:left-[49%] bottom-0 w-[80px] sm:w-[90px] h-[195px] sm:h-[225px] rounded-[2rem] bg-[#e62575] z-12 flex flex-col items-center pt-6 transition-all duration-200 ${
            isClosed ? "scale-[0.99] translate-y-1" : ""
          }`}
        >
          {/* Sclera White Eyes with tracking pupils */}
          <div className="mt-0.5">
            <CharacterEyes
              cursorX={cursorX}
              cursorY={cursorY}
              isClosed={isClosed}
              isPeeking={isPeeking}
              variant="sclera"
              size="xs"
              gap={6}
            />
          </div>

          {/* Subtle tiny expression */}
          <div className="mt-2">
            {isClosed ? (
              <div className="w-2 h-1 border-b-[2px] border-neutral-900 rounded-full" />
            ) : isPeeking ? (
              <div className="w-2.5 h-1.5 rounded-b-full bg-neutral-900" />
            ) : null}
          </div>
        </div>

        {/* --- CHARACTER 3: GOLDEN YELLOW CYLINDER (Front Right) --- */}
        <div
          className={`absolute left-[64%] sm:left-[66%] bottom-0 w-[95px] sm:w-[110px] h-[160px] sm:h-[185px] rounded-t-[3.2rem] rounded-b-[1.2rem] bg-[#f7c728] z-20 flex flex-col items-center pt-7 transition-all duration-200 ${
            isClosed ? "scale-[0.99]" : ""
          }`}
        >
          {/* Deadpan / Cool Beady Eyes */}
          <div className="mt-1 flex items-center justify-center">
            <CharacterEyes
              cursorX={cursorX}
              cursorY={cursorY}
              isClosed={isClosed}
              isPeeking={isPeeking}
              variant="beady"
              size="xs"
              gap={8}
            />
          </div>

          {/* Iconic Deadpan Straight Line Mouth */}
          <div className="mt-4">
            <div className="w-10 sm:w-12 h-[3px] bg-neutral-900 rounded-full" />
          </div>
        </div>

        {/* --- CHARACTER 4: ORANGE ROUNDED DOME / MOUND (Front Left) --- */}
        <div
          className={`absolute left-[4%] sm:left-[6%] bottom-0 w-[200px] sm:w-[240px] h-[125px] sm:h-[145px] rounded-t-[6.5rem] sm:rounded-t-[8rem] rounded-b-[1.5rem] bg-[#f77526] z-30 flex flex-col items-center pt-8 transition-all duration-200 ${
            isClosed ? "scale-[0.99] translate-y-0.5" : ""
          }`}
        >
          {/* Beady Black Eyes with cursor tracking */}
          <div className="mt-1">
            <CharacterEyes
              cursorX={cursorX}
              cursorY={cursorY}
              isClosed={isClosed}
              isPeeking={isPeeking}
              variant="beady"
              size="sm"
              gap={26}
            />
          </div>

          {/* Cute Happy Open Smile Mouth `D` from the reference */}
          <div className="mt-2.5">
            {isClosed ? (
              <div className="w-4 h-2 border-b-[2.5px] border-neutral-900 rounded-full" />
            ) : (
              <div
                className={`w-6 h-4 bg-neutral-900 rounded-b-full border-2 border-neutral-900 flex items-end justify-center overflow-hidden transition-all duration-150 ${
                  isPeeking ? "scale-105" : ""
                }`}
              >
                {/* Tongue */}
                <div className="w-3.5 h-1.5 bg-[#f472b6] rounded-t-full" />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
