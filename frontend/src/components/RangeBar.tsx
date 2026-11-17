import { Box, Tooltip, Typography } from '@mui/material';
import { fmtValue, unitLabel } from '../utils/format';

/** Шкала: целевой диапазон (зелёный) и маркер текущего значения. */
export function RangeBar({ value, min, max, unit }: { value: number | null; min: number | null; max: number | null; unit: string }) {
  if (min === null || max === null) return null;
  const span = max - min || 1;
  const lo = Math.min(min - span * 0.5, value ?? min);
  const hi = Math.max(max + span * 0.5, value ?? max);
  const pct = (v: number) => ((v - lo) / (hi - lo)) * 100;
  const inRange = value !== null && value >= min && value <= max;
  return (
    <Box sx={{ mt: 1.5 }}>
      <Box sx={{ position: 'relative', height: 8, borderRadius: 4, bgcolor: '#eef1ec' }}>
        <Tooltip title={`Целевой диапазон ${fmtValue(min, unit)}–${fmtValue(max, unit)} ${unitLabel(unit)}`}>
          <Box sx={{ position: 'absolute', left: `${pct(min)}%`, width: `${pct(max) - pct(min)}%`, top: 0, bottom: 0, borderRadius: 4, bgcolor: 'rgba(63,143,91,.35)' }} />
        </Tooltip>
        {value !== null && (
          <Box sx={{
            position: 'absolute', left: `calc(${pct(value)}% - 7px)`, top: -3, width: 14, height: 14, borderRadius: '50%',
            bgcolor: inRange ? 'success.main' : 'warning.main', border: '2px solid #fff', boxShadow: '0 1px 3px rgba(0,0,0,.25)',
          }} />
        )}
      </Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 0.5 }}>
        <Typography variant="caption" color="text.secondary">цель {fmtValue(min, unit)}–{fmtValue(max, unit)} {unitLabel(unit)}</Typography>
      </Box>
    </Box>
  );
}
