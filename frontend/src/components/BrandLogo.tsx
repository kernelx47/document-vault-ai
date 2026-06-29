"use client";

import clsx from "clsx";
import { useId } from "react";

type BrandLogoProps = {
  size?: number;
  className?: string;
};

/** VaultMind mark — clean monogram on soft violet tile */
export function BrandLogo({ size = 32, className }: BrandLogoProps) {
  const uid = useId().replace(/:/g, "");
  const bgId = `vm-bg-${uid}`;

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={clsx("shrink-0", className)}
      aria-hidden
    >
      <defs>
        <linearGradient id={bgId} x1="8" y1="6" x2="24" y2="26" gradientUnits="userSpaceOnUse">
          <stop stopColor="#7c3aed" />
          <stop offset="1" stopColor="#6d28d9" />
        </linearGradient>
      </defs>
      <rect x="1" y="1" width="30" height="30" rx="8" fill={`url(#${bgId})`} />
      <path
        d="M10 10.5 16 23 22 10.5"
        stroke="white"
        strokeWidth="3.25"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function BrandWordmark({ className }: { className?: string }) {
  return (
    <span
      className={clsx("font-semibold tracking-[-0.02em] text-[var(--deep-ink)]", className)}
      style={{ fontFamily: "'Source Serif 4', serif" }}
    >
      Vault<span className="bg-gradient-to-r from-[var(--electric-violet)] to-purple-500 bg-clip-text text-transparent">Mind</span>
    </span>
  );
}

/** Compact mark for assistant avatar */
export function BrandAvatar({ size = 28 }: { size?: number }) {
  return (
    <div
      className="flex shrink-0 items-center justify-center rounded-full shadow-sm shadow-purple-300/30"
      style={{
        width: size,
        height: size,
        background: "linear-gradient(145deg, #7c3aed 0%, #6d28d9 100%)",
      }}
    >
      <svg
        width={size * 0.46}
        height={size * 0.46}
        viewBox="0 0 16 16"
        fill="none"
        aria-hidden
      >
        <path
          d="M4.5 5 8 12.5 11.5 5"
          stroke="white"
          strokeWidth="2.2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </div>
  );
}
