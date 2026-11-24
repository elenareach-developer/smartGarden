import { useState } from 'react';
import {
  Alert, Box, Button, Card, CardContent, Chip, Divider, Grid2 as Grid, List, ListItem, ListItemText, MenuItem, Stack,
  TextField, ToggleButton, ToggleButtonGroup, Typography,
} from '@mui/material';
import RestartAltIcon from '@mui/icons-material/RestartAlt';
import RouterOutlinedIcon from '@mui/icons-material/RouterOutlined';
import { api, errorMessage } from '../api/client';
import { usePlants } from '../context/PlantContext';
import { useAsync } from '../utils/useAsync';
import { PageHeader } from '../components/PageHeader';
import { ErrorBox, Loading } from '../components/States';

const SENSOR_TYPES = [
  ['SHT31', 'SHT31 — температура и влажность'], ['DHT11', 'DHT11 — температура и влажность'], ['DHT22', 'DHT22 — температура и влажность'],
  ['BH1750', 'BH1750 — освещённость'], ['HX711', 'HX711 — весы (масса горшка)'],
  ['CAPACITIVE_SOIL', 'Ёмкостный датчик влажности субстрата'],
];

const ESP32_EXAMPLE = `POST /api/sensors/readings
{
  "readings": [
    {"plant_id": 1, "metric": "temperature", "value": 22.8,
     "source": "iot", "hardware_id": "esp32-orchid-dht11"},
    {"plant_id": 1, "metric": "air_humidity", "value": 58,
     "source": "iot", "hardware_id": "esp32-orchid-dht11"}
  ]
}`;

export default function SettingsPage() {
  const { plants, reload } = usePlants();
  const status = useAsync(() => api.system(), []);
  const sensors = useAsync(() => api.sensors(), []);
  const [msg, setMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [form, setForm] = useState({ plant_id: plants[0]?.plant.id ?? 1, sensor_type: 'SHT31', name: '', hardware_id: '' });

  async function switchSource(id: number, source: 'demo' | 'iot') {
    try {
      await api.updatePlant(id, { data_source: source });
      await reload();
      setMsg({ type: 'success', text: source === 'iot' ? 'Источник переключён на IoT. Данные появятся, когда устройство начнёт отправлять измерения.' : 'Источник переключён на DEMO.' });
    } catch (e) { setMsg({ type: 'error', text: errorMessage(e) }); }
  }

  async function register() {
    try {
      await api.registerSensor({ plant_id: form.plant_id, sensor_type: form.sensor_type, name: form.name || form.sensor_type, hardware_id: form.hardware_id || null });
      setForm((f) => ({ ...f, name: '', hardware_id: '' }));
      void sensors.reload();
      setMsg({ type: 'success', text: 'IoT-датчик зарегистрирован.' });
    } catch (e) { setMsg({ type: 'error', text: errorMessage(e) }); }
  }

  async function reset() {
    if (!window.confirm('Пересоздать демонстрационные данные? Все ваши события, измерения и консультации будут удалены.')) return;
    try {
      await api.resetDemo();
      await reload();
      void status.reload(); void sensors.reload();
      setMsg({ type: 'success', text: 'Демо-данные пересозданы.' });
    } catch (e) { setMsg({ type: 'error', text: errorMessage(e) }); }
  }

  const s = status.data;
  return (
    <>
      <PageHeader title="Настройки" subtitle="Источники данных, датчики и AI" />
      {msg && <Alert severity={msg.type} onClose={() => setMsg(null)} sx={{ mb: 2 }}>{msg.text}</Alert>}
      <Grid container spacing={3}>
        <Grid size={{ xs: 12, md: 6 }}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Typography variant="h6">Система</Typography>
              {status.error && <ErrorBox message={status.error} onRetry={status.reload} />}
              {!s ? <Loading rows={1} /> : (
                <List dense>
                  <ListItem disableGutters><ListItemText primary="AI-режим" secondary={s.ai_mode === 'claude' ? `Claude API, модель ${s.claude_model}` : 'Demo AI Mode (экспертные правила)'} />
                    <Chip color={s.ai_mode === 'claude' ? 'success' : 'warning'} label={s.ai_mode === 'claude' ? 'Claude' : 'Demo'} /></ListItem>
                  <ListItem disableGutters><ListItemText primary="API-ключ Claude" secondary="Хранится только на сервере (backend/.env → ANTHROPIC_API_KEY); в браузер не передаётся" />
                    <Chip variant="outlined" label={s.api_key_configured ? 'задан' : 'не задан'} /></ListItem>
                  <ListItem disableGutters><ListItemText primary="База данных" secondary={`${s.database} · переход на PostgreSQL через DATABASE_URL`} /></ListItem>
                  <ListItem disableGutters><ListItemText primary="Измерения в базе"
                    secondary={Object.entries(s.readings_by_source).map(([k, v]) => `${k}: ${v.toLocaleString('ru-RU')}`).join(' · ') || 'нет'} /></ListItem>
                  <ListItem disableGutters><ListItemText primary="Провайдеры данных" secondary={s.providers.join(', ')} /></ListItem>
                </List>
              )}
              <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
                <Button href="/docs" target="_blank" variant="outlined">Swagger API</Button>
                <Button color="warning" startIcon={<RestartAltIcon />} onClick={reset}>Пересоздать DEMO</Button>
              </Stack>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Typography variant="h6">Источник данных растений</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                Сервис мониторинга работает одинаково для обоих источников. DEMO и IoT-измерения хранятся раздельно и не смешиваются.
              </Typography>
              {plants.map((p) => (
                <Stack key={p.plant.id} direction="row" alignItems="center" justifyContent="space-between" sx={{ py: 1 }}>
                  <Typography fontWeight={650}>{p.plant.name}</Typography>
                  <ToggleButtonGroup size="small" exclusive value={p.plant.data_source} onChange={(_, v) => v && void switchSource(p.plant.id, v)}>
                    <ToggleButton value="demo">DEMO</ToggleButton>
                    <ToggleButton value="iot">IoT</ToggleButton>
                  </ToggleButtonGroup>
                </Stack>
              ))}
            </CardContent>
          </Card>
        </Grid>
        <Grid size={12}>
          <Card>
            <CardContent>
              <Stack direction="row" spacing={1} alignItems="center"><RouterOutlinedIcon color="primary" /><Typography variant="h6">Датчики и подготовка к IoT</Typography></Stack>
              <Grid container spacing={3} sx={{ mt: 0.5 }}>
                <Grid size={{ xs: 12, md: 6 }}>
                  {sensors.error && <ErrorBox message={sensors.error} onRetry={sensors.reload} />}
                  <List dense>
                    {(sensors.data ?? []).map((x) => (
                      <ListItem key={x.id} disableGutters secondaryAction={<Chip size="small" label={x.source.toUpperCase()} color={x.source === 'iot' ? 'info' : x.source === 'demo' ? 'warning' : 'default'} variant="outlined" />}>
                        <ListItemText primary={`${plants.find((p) => p.plant.id === x.plant_id)?.plant.name ?? x.plant_id}: ${x.name}`}
                          secondary={`${x.sensor_type} · ${x.metrics.join(', ') || 'ручной ввод любых показателей'}${x.hardware_id ? ` · ${x.hardware_id}` : ''}`} />
                      </ListItem>
                    ))}
                  </List>
                </Grid>
                <Grid size={{ xs: 12, md: 6 }}>
                  <Typography fontWeight={700}>Зарегистрировать IoT-датчик</Typography>
                  <Stack spacing={1.5} sx={{ mt: 1 }}>
                    <TextField select size="small" label="Растение" value={form.plant_id} onChange={(e) => setForm({ ...form, plant_id: Number(e.target.value) })}>
                      {plants.map((p) => <MenuItem key={p.plant.id} value={p.plant.id}>{p.plant.name}</MenuItem>)}
                    </TextField>
                    <TextField select size="small" label="Тип" value={form.sensor_type} onChange={(e) => setForm({ ...form, sensor_type: e.target.value })}>
                      {SENSOR_TYPES.map(([v, l]) => <MenuItem key={v} value={v}>{l}</MenuItem>)}
                    </TextField>
                    <TextField size="small" label="Название" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
                    <TextField size="small" label="hardware_id (например, MAC ESP32 + канал)" value={form.hardware_id} onChange={(e) => setForm({ ...form, hardware_id: e.target.value })} />
                    <Box><Button variant="contained" onClick={register}>Зарегистрировать</Button></Box>
                  </Stack>
                  <Divider sx={{ my: 2 }} />
                  <Typography variant="body2" fontWeight={650}>Формат отправки с ESP32</Typography>
                  <Box component="pre" sx={{ fontSize: 12, bgcolor: '#f3f5f1', p: 1.5, borderRadius: 2, overflowX: 'auto' }}>{ESP32_EXAMPLE}</Box>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </>
  );
}
