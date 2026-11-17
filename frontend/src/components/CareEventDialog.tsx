import { useEffect, useState } from 'react';
import { Alert, Button, Dialog, DialogActions, DialogContent, DialogTitle, MenuItem, Stack, TextField } from '@mui/material';
import { api, errorMessage } from '../api/client';
import type { CareEventIn, CareType, LeafStatus, RootStatus } from '../api/types';
import { LEAVES, ROOTS } from '../utils/format';

const TYPES: [CareType, string][] = [
  ['watering', 'Полив'], ['misting', 'Опрыскивание'], ['inspection', 'Осмотр'], ['repotting', 'Пересадка'],
  ['treatment', 'Обработка'], ['other', 'Другое'],
];

function localNow() {
  const d = new Date();
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 16);
}

export function CareEventDialog({ plantId, open, initialType = 'watering', onClose, onSaved }:
  { plantId: number; open: boolean; initialType?: CareType; onClose: () => void; onSaved: () => void }) {
  const [type, setType] = useState<CareType>(initialType);
  const [when, setWhen] = useState(localNow());
  const [amount, setAmount] = useState('');
  const [method, setMethod] = useState('');
  const [notes, setNotes] = useState('');
  const [roots, setRoots] = useState<RootStatus | ''>('');
  const [leaves, setLeaves] = useState<LeafStatus | ''>('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (open) { setType(initialType); setWhen(localNow()); setAmount(''); setMethod(''); setNotes(''); setRoots(''); setLeaves(''); setError(null); }
  }, [open, initialType]);

  async function save() {
    setBusy(true);
    setError(null);
    const body: CareEventIn = { event_type: type, timestamp: new Date(when).toISOString(), notes: notes || null, method: method || null };
    if (type === 'watering' && amount) body.amount_ml = Number(amount);
    if (type === 'inspection') { if (roots) body.root_status = roots; if (leaves) body.leaf_status = leaves; }
    try {
      await api.addCare(plantId, body);
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
      <DialogTitle>Событие ухода</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ mt: 1 }}>
          {error && <Alert severity="error">{error}</Alert>}
          <TextField select label="Тип" value={type} onChange={(e) => setType(e.target.value as CareType)}>
            {TYPES.map(([v, l]) => <MenuItem key={v} value={v}>{l}</MenuItem>)}
          </TextField>
          <TextField type="datetime-local" label="Когда" value={when} onChange={(e) => setWhen(e.target.value)} InputLabelProps={{ shrink: true }} />
          {type === 'watering' && <>
            <TextField type="number" label="Объём воды, мл" value={amount} onChange={(e) => setAmount(e.target.value)} />
            <TextField label="Способ" placeholder="погружение, полив сверху…" value={method} onChange={(e) => setMethod(e.target.value)} />
          </>}
          {type === 'inspection' && <>
            <TextField select label="Корни" value={roots} onChange={(e) => setRoots(e.target.value as RootStatus)}>
              <MenuItem value="">Не менять</MenuItem>{ROOTS.map(([v, l]) => <MenuItem key={v} value={v}>{l}</MenuItem>)}
            </TextField>
            <TextField select label="Листья" value={leaves} onChange={(e) => setLeaves(e.target.value as LeafStatus)}>
              <MenuItem value="">Не менять</MenuItem>{LEAVES.map(([v, l]) => <MenuItem key={v} value={v}>{l}</MenuItem>)}
            </TextField>
          </>}
          <TextField label="Заметка" multiline minRows={2} value={notes} onChange={(e) => setNotes(e.target.value)} />
          <Alert severity="info" variant="outlined">Подкормку записывайте через Fertilizer Advisor — так сохраняется состав удобрения.</Alert>
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Отмена</Button>
        <Button variant="contained" onClick={save} disabled={busy}>Сохранить</Button>
      </DialogActions>
    </Dialog>
  );
}
