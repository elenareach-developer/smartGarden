import {
  Area, CartesianGrid, ComposedChart, Legend, Line, ReferenceArea, ResponsiveContainer, Scatter, Tooltip, XAxis, YAxis,
} from 'recharts';
import type { HistorySeries, Period } from '../api/types';
import { fmtValue, unitLabel } from '../utils/format';

const tickFmt = (period: Period) => (t: number) => {
  const d = new Date(t);
  return period === '24h'
    ? d.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
    : d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' });
};

export function HistoryChart({ series, manual, period, height = 300 }:
  { series: HistorySeries; manual?: HistorySeries; period: Period; height?: number }) {
  const data = series.points.map((p) => ({
    t: new Date(p.t).getTime(), value: p.value, range: p.min != null && p.max != null ? [p.min, p.max] : undefined,
  }));
  const manualPts = (manual?.points ?? []).map((p) => ({ t: new Date(p.t).getTime(), manual: p.value }));
  const unit = unitLabel(series.unit);
  const showRange = series.bucket_minutes > 30;
  return (
    <ResponsiveContainer width="100%" height={height}>
      <ComposedChart data={data} margin={{ top: 10, right: 16, bottom: 0, left: 0 }}>
        <CartesianGrid stroke="#eef1ec" vertical={false} />
        <XAxis dataKey="t" type="number" domain={['dataMin', 'dataMax']} scale="time" tickFormatter={tickFmt(period)}
          tick={{ fontSize: 12, fill: '#5d6b62' }} minTickGap={28} />
        <YAxis tick={{ fontSize: 12, fill: '#5d6b62' }} width={56} domain={['auto', 'auto']}
          tickFormatter={(v: number) => fmtValue(v, series.unit)} />
        {series.target_min != null && series.target_max != null && (
          <ReferenceArea y1={series.target_min} y2={series.target_max} fill="#3f8f5b" fillOpacity={0.08}
            stroke="#3f8f5b" strokeOpacity={0.25} strokeDasharray="4 4" ifOverflow="extendDomain" />
        )}
        <Tooltip labelFormatter={(t: number) => new Date(t).toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}
          formatter={(v: number | number[], name: string) => [Array.isArray(v) ? `${fmtValue(v[0], series.unit)}–${fmtValue(v[1], series.unit)} ${unit}` : `${fmtValue(v, series.unit)} ${unit}`, name]} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        {showRange && <Area dataKey="range" name="мин–макс за интервал" stroke="none" fill="#2e6b4a" fillOpacity={0.12} isAnimationActive={false} />}
        <Line dataKey="value" name={series.kind === 'derived' ? 'расчёт' : series.source === 'demo' ? 'DEMO-датчик' : 'датчик'}
          stroke="#2e6b4a" strokeWidth={2} dot={series.points.length < 40} isAnimationActive={false} />
        {manualPts.length > 0 && <Scatter data={manualPts} dataKey="manual" name="вручную" fill="#8a6fb0" />}
      </ComposedChart>
    </ResponsiveContainer>
  );
}
