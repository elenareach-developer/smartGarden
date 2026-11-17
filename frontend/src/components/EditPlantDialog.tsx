import { useEffect, useState } from 'react';
import {
  Alert, Box, Button, Dialog, DialogActions, DialogContent, DialogTitle, Grid2 as Grid, MenuItem, Stack, Tab, Tabs,
  TextField, Typography,
} from '@mui/material';
import UploadIcon from '@mui/icons-material/Upload';
import { api, errorMessage } from '../api/client';
import type { Plant, PlantUpdate, Targets } from '../api/types';
import { LEAVES, ROOTS, STAGES } from '../utils/format';
import { PlantPhoto } from './PlantPhoto';

const TARGET_FIELDS: [keyof Targets, keyof Targets, string, string][] = [
  ['temp_min', 'temp_max', 'Температура', '°C'],
  ['humidity_min', 'humidity_max', 'Влажность воздуха', '%'],
  ['light_min', 'light_max', 'Средняя дневная освещённость', 'лк'],
  ['photoperiod_min', 'photoperiod_max', 'Световой день', 'ч'],
  ['substrate_min', 'substrate_max', 'Влажность субстрата', '%'],
];

export function EditPlantDialog({ plant, open, onClose, onSaved }:
  { plant: Plant; open: boolean; onClose: () => void; onSaved: () => void }) {
  const [tab, setTab] = useState(0);
  const [form, setForm] = useState<PlantUpdate>({});
  const [targets, setTargets] = useState<Targets>(plant.targets);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [photo, setPhoto] = useState(plant.photo_url);

  useEffect(() => {
    if (open) {
      setForm({ name: plant.name, species: plant.species, variety: plant.variety, stage: plant.stage, location: plant.location,
        pot: plant.pot, substrate: plant.substrate, notes: plant.notes, root_status: plant.root_status, leaf_status: plant.leaf_status,
        photo_url: plant.photo_url });
      setTargets(plant.targets);
      setPhoto(plant.photo_url);
      setError(null);
      setTab(0);
    }
  }, [open, plant]);

  const set = (k: keyof PlantUpdate) => (e: React.ChangeEvent<HTMLInputElement>) => setForm((f) => ({ ...f, [k]: e.target.value }));
  const setT = (k: keyof Targets) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setTargets((t) => ({ ...t, [k]: e.target.value === '' ? null : Number(e.target.value) }));

  async function save() {
    setBusy(true);
    setError(null);
    try {
      const body: PlantUpdate = { ...form, targets };
      if (body.root_status === plant.root_status && body.leaf_status === plant.leaf_status) {
        delete body.root_status;
        delete body.leaf_status;
      }
      await api.updatePlant(plant.id, body);
      onSaved();
      onClose();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  async function upload(file: File) {
    setBusy(true);
    setError(null);
    try {
      const p = await api.uploadPhoto(plant.id, file);
      setPhoto(p.photo_url);
      setForm((f) => ({ ...f, photo_url: p.photo_url }));
      onSaved();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="md">
      <DialogTitle>Редактировать: {plant.name}</DialogTitle>
      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ px: 3 }}>
        <Tab label="Паспорт" /><Tab label="Условия содержания" /><Tab label="Фото" />
      </Tabs>
      <DialogContent dividers>
        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
        {tab === 0 && (
          <Grid container spacing={2}>
            <Grid size={{ xs: 12, sm: 6 }}><TextField label="Имя" fullWidth required value={form.name ?? ''} onChange={set('name')} /></Grid>
            <Grid size={{ xs: 12, sm: 6 }}>
              <TextField select label="Стадия развития" fullWidth value={form.stage ?? ''} onChange={set('stage')}>
                {STAGES.map(([v, l]) => <MenuItem key={v} value={v}>{l}</MenuItem>)}
              </TextField>
            </Grid>
            <Grid size={{ xs: 12, sm: 6 }}><TextField label="Вид / род" fullWidth required value={form.species ?? ''} onChange={set('species')} /></Grid>
            <Grid size={{ xs: 12, sm: 6 }}><TextField label="Сорт / гибрид" fullWidth value={form.variety ?? ''} onChange={set('variety')} /></Grid>
            <Grid size={12}><TextField label="Место" fullWidth value={form.location ?? ''} onChange={set('location')} /></Grid>
            <Grid size={{ xs: 12, sm: 6 }}><TextField label="Горшок" fullWidth value={form.pot ?? ''} onChange={set('pot')} /></Grid>
            <Grid size={{ xs: 12, sm: 6 }}><TextField label="Субстрат" fullWidth value={form.substrate ?? ''} onChange={set('substrate')} /></Grid>
            <Grid size={{ xs: 12, sm: 6 }}>
              <TextField select label="Корни (наблюдение)" fullWidth value={form.root_status ?? ''} onChange={set('root_status')}>
                {ROOTS.map(([v, l]) => <MenuItem key={v} value={v}>{l}</MenuItem>)}
              </TextField>
            </Grid>
            <Grid size={{ xs: 12, sm: 6 }}>
              <TextField select label="Листья (наблюдение)" fullWidth value={form.leaf_status ?? ''} onChange={set('leaf_status')}>
                {LEAVES.map(([v, l]) => <MenuItem key={v} value={v}>{l}</MenuItem>)}
              </TextField>
            </Grid>
            <Grid size={12}><TextField label="Заметки" fullWidth multiline minRows={3} value={form.notes ?? ''} onChange={set('notes')} /></Grid>
          </Grid>
        )}
        {tab === 1 && (
          <Stack spacing={2}>
            <Typography variant="body2" color="text.secondary">Индивидуальные целевые диапазоны — по ним оцениваются статусы, прогноз и риски.</Typography>
            {TARGET_FIELDS.map(([lo, hi, label, unit]) => (
              <Grid container spacing={2} key={lo} alignItems="center">
                <Grid size={{ xs: 12, sm: 4 }}><Typography fontWeight={600}>{label}, {unit}</Typography></Grid>
                <Grid size={{ xs: 6, sm: 4 }}><TextField size="small" type="number" label="от" fullWidth value={targets[lo] ?? ''} onChange={setT(lo)} /></Grid>
                <Grid size={{ xs: 6, sm: 4 }}><TextField size="small" type="number" label="до" fullWidth value={targets[hi] ?? ''} onChange={setT(hi)} /></Grid>
              </Grid>
            ))}
            <Grid container spacing={2}>
              <Grid size={{ xs: 6, sm: 3 }}><TextField size="small" type="number" label="Интервал полива, дн." fullWidth value={targets.watering_interval_days} onChange={setT('watering_interval_days')} /></Grid>
              <Grid size={{ xs: 6, sm: 3 }}><TextField size="small" type="number" label="Интервал подкормки, дн." fullWidth value={targets.fertilizing_interval_days} onChange={setT('fertilizing_interval_days')} /></Grid>
              <Grid size={{ xs: 6, sm: 3 }}><TextField size="small" type="number" label="Сухой горшок, г" fullWidth value={targets.pot_weight_dry ?? ''} onChange={setT('pot_weight_dry')} /></Grid>
              <Grid size={{ xs: 6, sm: 3 }}><TextField size="small" type="number" label="После полива, г" fullWidth value={targets.pot_weight_wet ?? ''} onChange={setT('pot_weight_wet')} /></Grid>
            </Grid>
          </Stack>
        )}
        {tab === 2 && (
          <Grid container spacing={2}>
            <Grid size={{ xs: 12, sm: 6 }}><PlantPhoto url={photo} name={plant.name} height={260} showBadge /></Grid>
            <Grid size={{ xs: 12, sm: 6 }}>
              <Stack spacing={2}>
                <Typography variant="body2" color="text.secondary">Загрузите настоящую фотографию растения (JPEG, PNG или WebP до 5 МБ). Она сохранится на сервере.</Typography>
                <Button component="label" variant="contained" startIcon={<UploadIcon />} disabled={busy}>
                  Загрузить фото
                  <input hidden type="file" accept="image/jpeg,image/png,image/webp"
                    onChange={(e) => { const f = e.target.files?.[0]; if (f) void upload(f); e.target.value = ''; }} />
                </Button>
                <TextField label="или ссылка на фото" size="small" value={form.photo_url ?? ''} onChange={(e) => { set('photo_url')(e as React.ChangeEvent<HTMLInputElement>); setPhoto(e.target.value || null); }} />
                <Box><Button size="small" onClick={() => { const def = `/photos/${['luna', 'caramel', 'emerald'][plant.id - 1] ?? 'placeholder'}.svg`; setForm((f) => ({ ...f, photo_url: def })); setPhoto(def); }}>Вернуть иллюстрацию</Button></Box>
              </Stack>
            </Grid>
          </Grid>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Отмена</Button>
        <Button variant="contained" onClick={save} disabled={busy}>Сохранить</Button>
      </DialogActions>
    </Dialog>
  );
}
