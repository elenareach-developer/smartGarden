import { useState } from 'react';
import { Link as RouterLink, useParams } from 'react-router-dom';
import {
  Alert, Box, Button, Card, CardContent, Chip, Divider, Grid2 as Grid, List, ListItem, ListItemText, Stack, Typography,
} from '@mui/material';
import EditOutlinedIcon from '@mui/icons-material/EditOutlined';
import WaterDropOutlinedIcon from '@mui/icons-material/WaterDropOutlined';
import SearchIcon from '@mui/icons-material/Search';
import MonitorHeartOutlinedIcon from '@mui/icons-material/MonitorHeartOutlined';
import QueryStatsIcon from '@mui/icons-material/QueryStats';
import AutoAwesomeOutlinedIcon from '@mui/icons-material/AutoAwesomeOutlined';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import { api } from '../api/client';
import { usePlants } from '../context/PlantContext';
import { useAsync } from '../utils/useAsync';
import { AttentionChip, KindChip, SourceChip } from '../components/Chips';
import { PlantPhoto } from '../components/PlantPhoto';
import { ErrorBox, Loading } from '../components/States';
import { EditPlantDialog } from '../components/EditPlantDialog';
import { CareEventDialog } from '../components/CareEventDialog';
import type { CareType } from '../api/types';
import { fmtDate, fmtDateTime, relDays, untilText } from '../utils/format';

function Row({ label, value }: { label: string; value?: string | null }) {
  return (
    <Box sx={{ py: 0.75 }}>
      <Typography variant="caption" color="text.secondary">{label}</Typography>
      <Typography>{value || '—'}</Typography>
    </Box>
  );
}

export default function PlantProfilePage() {
  const id = Number(useParams().plantId);
  const { reload: reloadAll } = usePlants();
  const plant = useAsync(() => api.plant(id), [id]);
  const care = useAsync(() => api.care(id), [id]);
  const [edit, setEdit] = useState(false);
  const [event, setEvent] = useState<CareType | null>(null);
  const refresh = () => { void plant.reload(); void care.reload(); void reloadAll(); };

  if (plant.error) return <ErrorBox message={plant.error} onRetry={plant.reload} />;
  if (!plant.data) return <Loading />;
  const c = plant.data;
  const p = c.plant;
  const t = p.targets;

  return (
    <>
      <Button component={RouterLink} to="/" startIcon={<ArrowBackIcon />} sx={{ mb: 2 }}>Все орхидеи</Button>
      <Grid container spacing={3}>
        <Grid size={{ xs: 12, md: 5 }}>
          <Card>
            <PlantPhoto url={p.photo_url} name={p.name} height={340} rounded={false} showBadge />
            <CardContent>
              <Stack direction="row" justifyContent="space-between" alignItems="flex-start" spacing={1}>
                <Box>
                  <Typography variant="h4" component="h1">{p.name}</Typography>
                  <Typography color="text.secondary">{p.species}</Typography>
                </Box>
                <AttentionChip level={c.attention} size="medium" />
              </Stack>
              <Stack direction="row" spacing={1} sx={{ mt: 1.5 }} flexWrap="wrap" useFlexGap>
                <Chip label={p.stage_label} color="primary" variant="outlined" size="small" />
                <SourceChip source={p.data_source} />
              </Stack>
              {c.attention_reasons.length > 0 && (
                <Alert severity={c.attention === 'critical' ? 'error' : 'warning'} sx={{ mt: 2 }}>
                  <ul style={{ margin: 0, paddingLeft: 18 }}>{c.attention_reasons.map((r) => <li key={r}>{r}</li>)}</ul>
                </Alert>
              )}
              <Stack direction="row" spacing={1} sx={{ mt: 2 }} flexWrap="wrap" useFlexGap>
                <Button variant="contained" startIcon={<WaterDropOutlinedIcon />} onClick={() => setEvent('watering')}>Записать полив</Button>
                <Button variant="outlined" startIcon={<SearchIcon />} onClick={() => setEvent('inspection')}>Осмотр</Button>
                <Button startIcon={<EditOutlinedIcon />} onClick={() => setEdit(true)}>Редактировать</Button>
              </Stack>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, md: 7 }}>
          <Stack spacing={3}>
            <Grid container spacing={2}>
              {[
                { to: `/monitoring/${p.id}`, icon: <MonitorHeartOutlinedIcon />, title: 'Мониторинг', text: 'Текущее состояние и графики' },
                { to: `/forecast/${p.id}`, icon: <QueryStatsIcon />, title: 'Прогноз', text: 'На 3, 7 и 14 дней' },
                { to: `/assistant/${p.id}`, icon: <AutoAwesomeOutlinedIcon />, title: 'AI-помощник', text: 'Советы и подкормка' },
              ].map((x) => (
                <Grid key={x.to} size={{ xs: 12, sm: 4 }}>
                  <Button component={RouterLink} to={x.to} fullWidth variant="outlined"
                    sx={{ py: 2, flexDirection: 'column', alignItems: 'flex-start', textAlign: 'left', gap: 0.5, bgcolor: 'background.paper' }}>
                    {x.icon}
                    <Typography fontWeight={700} color="text.primary">{x.title}</Typography>
                    <Typography variant="caption" color="text.secondary">{x.text}</Typography>
                  </Button>
                </Grid>
              ))}
            </Grid>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>Паспорт растения</Typography>
                <Grid container columnSpacing={3}>
                  <Grid size={{ xs: 12, sm: 6 }}>
                    <Row label="Сорт / гибрид" value={p.variety} />
                    <Row label="Место" value={p.location} />
                    <Row label="Горшок" value={p.pot} />
                    <Row label="Субстрат" value={p.substrate} />
                  </Grid>
                  <Grid size={{ xs: 12, sm: 6 }}>
                    <Row label="В коллекции с" value={fmtDate(p.acquired_at)} />
                    <Row label="Последний полив" value={`${relDays(c.last_watering)} (${fmtDateTime(c.last_watering)})`} />
                    <Row label="Последняя подкормка" value={`${relDays(c.last_fertilizing)} (${fmtDateTime(c.last_fertilizing)})`} />
                    <Row label="Датчики" value={c.sensors.join(', ') || 'нет'} />
                  </Grid>
                </Grid>
                {p.notes && <><Divider sx={{ my: 1.5 }} /><Typography variant="body2">{p.notes}</Typography></>}
              </CardContent>
            </Card>
            <Card>
              <CardContent>
                <Stack direction="row" justifyContent="space-between" alignItems="center">
                  <Typography variant="h6">Наблюдения</Typography>
                  <KindChip kind="observation" />
                </Stack>
                <Grid container spacing={2} sx={{ mt: 0.5 }}>
                  <Grid size={{ xs: 12, sm: 6 }}><Row label="Корни" value={p.root_label} /></Grid>
                  <Grid size={{ xs: 12, sm: 6 }}><Row label="Листья" value={p.leaf_label} /></Grid>
                </Grid>
                <Typography variant="caption" color="text.secondary">Последний осмотр: {fmtDateTime(p.observed_at)}</Typography>
              </CardContent>
            </Card>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>Индивидуальные условия</Typography>
                <Grid container spacing={1}>
                  {[
                    ['Температура', `${t.temp_min}–${t.temp_max} °C`],
                    ['Влажность воздуха', `${t.humidity_min}–${t.humidity_max} %`],
                    ['Освещённость днём', `${t.light_min.toLocaleString('ru-RU')}–${t.light_max.toLocaleString('ru-RU')} лк`],
                    ['Световой день', `${t.photoperiod_min}–${t.photoperiod_max} ч`],
                    ['Полив', `ориентир раз в ${t.watering_interval_days} дн.`],
                    ['Подкормка', `не чаще раза в ${t.fertilizing_interval_days} дн.`],
                  ].map(([k, v]) => (
                    <Grid key={k} size={{ xs: 6, sm: 4 }}>
                      <Typography variant="caption" color="text.secondary">{k}</Typography>
                      <Typography fontWeight={600}>{v}</Typography>
                    </Grid>
                  ))}
                </Grid>
              </CardContent>
            </Card>
            <Card>
              <CardContent>
                <Typography variant="h6">План и история ухода</Typography>
                {care.error && <ErrorBox message={care.error} onRetry={care.reload} />}
                {care.data && (
                  <>
                    <List dense>
                      {care.data.planned.map((x) => (
                        <ListItem key={x.task} disableGutters secondaryAction={<KindChip kind={x.kind} />}>
                          <ListItemText primary={`${x.title}: ${x.due_at ? `${untilText(x.due_at)} (${fmtDateTime(x.due_at)})` : 'не запланировано'}`}
                            secondary={x.explanation} sx={{ pr: 12 }} />
                        </ListItem>
                      ))}
                    </List>
                    <Divider sx={{ my: 1 }} />
                    <List dense>
                      {care.data.events.slice(0, 8).map((e) => (
                        <ListItem key={e.id} disableGutters>
                          <ListItemText primary={`${e.event_label} · ${fmtDateTime(e.timestamp)}${e.amount_ml ? ` · ${e.amount_ml} мл` : ''}`}
                            secondary={[e.method, e.notes].filter(Boolean).join(' — ') || undefined} />
                          {e.source === 'demo' && <Chip size="small" label="DEMO" variant="outlined" color="warning" />}
                        </ListItem>
                      ))}
                    </List>
                    <Button component={RouterLink} to="/calendar" size="small">Весь календарь ухода</Button>
                  </>
                )}
              </CardContent>
            </Card>
          </Stack>
        </Grid>
      </Grid>
      <EditPlantDialog plant={p} open={edit} onClose={() => setEdit(false)} onSaved={refresh} />
      {event && <CareEventDialog plantId={p.id} open initialType={event} onClose={() => setEvent(null)} onSaved={refresh} />}
    </>
  );
}
