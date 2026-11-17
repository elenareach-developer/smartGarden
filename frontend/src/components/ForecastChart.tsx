import { Area, CartesianGrid, ComposedChart, Legend, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import type { MetricForecast } from '../api/types';
import { fmtValue, unitLabel } from '../utils/format';

export function ForecastChart({ f, target }: { f: MetricForecast; target?: [number | null, number | null] }) {
  const hist = f.history.map((p) => ({ t: new Date(p.t).getTime(), measured: p.value }));
  // Прогноз сводится к суткам (как и история): среднее и диапазон «суточные колебания + неопределённость».
  const days = new Map<string, { t: number; vals: number[]; lo: number; hi: number }>();
  for (const p of f.points) {
    const d = new Date(p.t);
    const key = d.toDateString();
    const noon = new Date(d.getFullYear(), d.getMonth(), d.getDate(), 12).getTime();
    const cur = days.get(key) ?? { t: noon, vals: [], lo: Infinity, hi: -Infinity };
    cur.vals.push(p.value);
    cur.lo = Math.min(cur.lo, p.low);
    cur.hi = Math.max(cur.hi, p.high);
    days.set(key, cur);
  }
  const fc = [...days.values()].filter((d) => d.vals.length >= 3).map((d) => ({
    t: d.t, forecast: d.vals.reduce((a, b) => a + b, 0) / d.vals.length, band: [d.lo, d.hi],
  }));
  const lastHist = hist[hist.length - 1];
  if (lastHist && fc.length) fc.unshift({ t: lastHist.t, forecast: lastHist.measured, band: [lastHist.measured, lastHist.measured] });
  const data = [...hist, ...fc].sort((a, b) => a.t - b.t);
  const now = Date.now();
  const unit = unitLabel(f.unit);
  return (
    <ResponsiveContainer width="100%" height={260}>
      <ComposedChart data={data} margin={{ top: 10, right: 12, left: 0, bottom: 0 }}>
        <CartesianGrid stroke="#eef1ec" vertical={false} />
        <XAxis dataKey="t" type="number" scale="time" domain={['dataMin', 'dataMax']}
          tickFormatter={(t: number) => new Date(t).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' })}
          tick={{ fontSize: 12, fill: '#5d6b62' }} minTickGap={30} />
        <YAxis width={56} tick={{ fontSize: 12, fill: '#5d6b62' }} domain={['auto', 'auto']} tickFormatter={(v: number) => fmtValue(v, f.unit)} />
        <Tooltip labelFormatter={(t: number) => new Date(t).toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}
          formatter={(v: number | number[], name: string) => [Array.isArray(v) ? `${fmtValue(v[0], f.unit)}–${fmtValue(v[1], f.unit)} ${unit}` : `${fmtValue(v, f.unit)} ${unit}`, name]} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        {target?.[0] != null && <ReferenceLine y={target[0]} stroke="#c9851d" strokeDasharray="4 4" label={{ value: 'мин', fontSize: 11, fill: '#c9851d', position: 'insideTopLeft' }} />}
        {target?.[1] != null && <ReferenceLine y={target[1]} stroke="#c0453a" strokeDasharray="4 4" label={{ value: 'макс', fontSize: 11, fill: '#c0453a', position: 'insideBottomLeft' }} />}
        <ReferenceLine x={now} stroke="#5d6b62" label={{ value: 'сейчас', fontSize: 11, fill: '#5d6b62', position: 'top' }} />
        <Area dataKey="band" name="диапазон за сутки (~90%)" stroke="none" fill="#8a6fb0" fillOpacity={0.15} isAnimationActive={false} connectNulls />
        <Line dataKey="measured" name="измерено (среднее за сутки)" stroke="#2e6b4a" strokeWidth={2} dot isAnimationActive={false} connectNulls />
        <Line dataKey="forecast" name="прогноз (среднее за сутки)" stroke="#8a6fb0" strokeWidth={2} strokeDasharray="6 4" dot={{ r: 2.5 }} isAnimationActive={false} connectNulls />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
