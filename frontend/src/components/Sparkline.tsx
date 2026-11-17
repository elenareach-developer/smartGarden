import { Line, LineChart, ResponsiveContainer, YAxis } from 'recharts';

export function Sparkline({ data, color = '#2e6b4a' }: { data: number[]; color?: string }) {
  if (data.length < 2) return null;
  return (
    <ResponsiveContainer width="100%" height={36}>
      <LineChart data={data.map((v, i) => ({ i, v }))} margin={{ top: 4, bottom: 4, left: 0, right: 0 }}>
        <YAxis hide domain={['dataMin', 'dataMax']} />
        <Line type="monotone" dataKey="v" stroke={color} strokeWidth={1.8} dot={false} isAnimationActive={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}
