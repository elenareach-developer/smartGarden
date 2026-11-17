import { useEffect, useState } from 'react';
import { Alert, Button, Dialog, DialogActions, DialogContent, DialogTitle, InputAdornment, MenuItem, Stack, TextField } from '@mui/material';
import { api, errorMessage } from '../api/client';
import type { MetricKey } from '../api/types';
import { METRIC_OPTIONS, unitLabel } from '../utils/format';

export function ManualReadingDialog({ plantId, open, onClose, onSaved, initialMetric = 'temperature' }:
  { plantId: number; open: boolean; onClose: () => void; onSaved: () => void; initialMetric?: MetricKey }) {
  const [metric, setMetric] = useState<MetricKey>(initialMetric);
  const [value, setValue] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => { if (open) { setMetric(initialMetric); setValue(''); setError(null); } }, [open, initialMetric]);
  const unit = METRIC_OPTIONS.find((m) => m[0] === metric)![2];

  async function save() {
    if (value === '' || Number.isNaN(Number(value))) { setError('Введите числовое значение'); return; }
    setBusy(true);
    setError(null);
    try {
      await api.addReading({ plant_id: plantId, metric, value: Number(value), source: 'manual' });
      onSaved();
      onClose();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="xs">
      <DialogTitle>Ручное измерение</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ mt: 1 }}>
          <Alert severity="info" variant="outlined">Ручные измерения хранятся отдельно (источник «Вручную») и не смешиваются с DEMO-рядом.</Alert>
          {error && <Alert severity="error">{error}</Alert>}
          <TextField select label="Показатель" value={metric} onChange={(e) => setMetric(e.target.value as MetricKey)}>
            {METRIC_OPTIONS.map(([v, l]) => <MenuItem key={v} value={v}>{l}</MenuItem>)}
          </TextField>
          <TextField autoFocus type="number" label="Значение" value={value} onChange={(e) => setValue(e.target.value)}
            InputProps={{ endAdornment: <InputAdornment position="end">{unitLabel(unit)}</InputAdornment> }}
            onKeyDown={(e) => { if (e.key === 'Enter') void save(); }} />
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Отмена</Button>
        <Button variant="contained" onClick={save} disabled={busy}>Сохранить</Button>
      </DialogActions>
    </Dialog>
  );
}
