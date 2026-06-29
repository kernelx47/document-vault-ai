"use client";

import { Area, AreaChart, ResponsiveContainer } from "recharts";

export function Sparkline({
  data,
  color = "#7c3aed",
  height = 44,
}: {
  data: number[];
  color?: string;
  height?: number;
}) {
  if (data.length < 2) return null;

  const chartData = data.map((value, index) => ({ index, value }));
  const gradientId = `spark-${color.replace("#", "")}`;

  return (
    <div className="mt-3 -mx-1" style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={chartData} margin={{ top: 2, right: 0, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.35} />
              <stop offset="100%" stopColor={color} stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <Area
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={2}
            fill={`url(#${gradientId})`}
            isAnimationActive
            dot={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
