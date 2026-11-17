import { useMemo, useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import {
  Alert, Avatar, Box, Button, Card, CardContent, Chip, Grid2 as Grid, List, ListItem, ListItemAvatar, ListItemText,
  MenuItem, Stack, TextField, Typography,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import WaterDropOutlinedIcon from '@mui/icons-material/WaterDropOutlined';
import ScienceOutlinedIcon from '@mui/icons-material/ScienceOutlined';
import SearchIcon from '@mui/icons-material/Search';
import SpaIcon from '@mui/icons-material/Spa';
import { api } from '../api/client';
import type { CareEvent } from '../api/types';
import { usePlants } from '../context/PlantContext';
import { useAsync } from '../utils/useAsync';
import { PageHeader } from '../components/PageHeader';
import { KindChip } from '../components/Chips';
import { ErrorBox, Loading } from '../components/States';
import { CareEventDialog } from '../components/CareEventDialog';
import { fmtDateTime, untilText } from '../utils/format';

const ICONS: Record<string, JSX.Element> = {
  watering: <WaterDropOutlinedIcon />, watering_check: <WaterDropOutlinedIcon />, fertilizing: <ScienceOutlinedIcon />,
  inspection: <SearchIcon />,
};

export default function CalendarPage() {
  const { plants } = usePlants();
  const [filter, setFilter] = useState<number | 'all'>('all');
  const [addFor, setAddFor] = useState<number | null>(null);
  const dash = useAsync(() => api.dashboard(), []);
  const events = useAsync(async () => {
    const all = await Promise.all(plants.map((p) => api.care(p.plant.id)));
    return all.flatMap((c) => c.events);
  }, [plants.length]);
  const names = Object.fromEntries(plants.map((p) => [p.plant.id, p.plant.name]));
  const reload = () => { void dash.reload(); void events.reload(); };

  const grouped = useMemo(() => {
    const list = (events.data ?? []).filter((e) => filter === 'all' || e.plant_id === filter)
      .sort((a, b) => b.timestamp.localeCompare(a.timestamp)).slice(0, 80);
    const g = new Map<string, CareEvent[]>();
    for (const e of list) {
      const day = new Date(e.timestamp).toLocaleDateString('ru-RU', { weekday: 'long', day: 'numeric', month: 'long' });
      g.set(day, [...(g.get(day) ?? []), e]);
    }
    return [...g.entries()];
  }, [events.data, filter]);

  const upcoming = (dash.data?.upcoming ?? []).filter((u) => filter === 'all' || u.plant_id === filter);

  return (
    <>
      <PageHeader title="Календарь ухода" subtitle="Ближайшие задачи и журнал всех событий"
        actions={<>
          <TextField select size="small" value={filter} onChange={(e) => setFilter(e.target.value === 'all' ? 'all' : Number(e.target.value))} sx={{ minWidth: 180, bgcolor: 'background.paper' }}>
            <MenuItem value="all">Все орхидеи</MenuItem>
            {plants.map((p) => <MenuItem key={p.plant.id} value={p.plant.id}>{p.plant.name}</MenuItem>)}
          </TextField>
          <Button variant="contained" startIcon={<AddIcon />} disabled={!plants.length}
            onClick={() => setAddFor(filter === 'all' ? plants[0].plant.id : filter)}>Событие</Button>
        </>} />
      <Grid container spacing={3}>
        <Grid size={{ xs: 12, md: 5 }}>
          <Card>
            <CardContent>
              <Typography variant="h6">Ближайшие 7 дней</Typography>
              {dash.error && <ErrorBox message={dash.error} onRetry={dash.reload} />}
              {dash.loading && !dash.data ? <Loading rows={2} /> : (
                <List>
                  {upcoming.map((u, i) => (
                    <ListItem key={i} alignItems="flex-start" disableGutters>
                      <ListItemAvatar><Avatar sx={{ bgcolor: u.due_at ? 'primary.light' : 'grey.400' }}>{ICONS[u.task] ?? <SpaIcon />}</Avatar></ListItemAvatar>
                      <ListItemText
                        primary={<Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
                          <Typography fontWeight={700}>{u.plant_name}: {u.title}</Typography><KindChip kind={u.kind} />
                        </Stack>}
                        secondary={<>
                          <Typography variant="body2" component="span" fontWeight={600} color="text.primary">
                            {u.due_at ? `${untilText(u.due_at)} · ${fmtDateTime(u.due_at)}` : 'не запланировано'}
                          </Typography><br />{u.explanation}
                        </>} />
                    </ListItem>
                  ))}
                  {!upcoming.length && <Alert severity="success">Задач на ближайшую неделю нет.</Alert>}
                </List>
              )}
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, md: 7 }}>
          <Card>
            <CardContent>
              <Typography variant="h6">Журнал ухода</Typography>
              {events.error && <ErrorBox message={events.error} onRetry={events.reload} />}
              {events.loading && !events.data ? <Loading rows={3} /> : grouped.map(([day, list]) => (
                <Box key={day} sx={{ mt: 2 }}>
                  <Typography variant="overline" color="text.secondary">{day}</Typography>
                  <List dense disablePadding>
                    {list.map((e) => (
                      <ListItem key={e.id} disableGutters secondaryAction={e.source === 'demo' ? <Chip size="small" label="DEMO" variant="outlined" color="warning" /> : <Chip size="small" label="вы" variant="outlined" />}>
                        <ListItemAvatar><Avatar sx={{ width: 32, height: 32, bgcolor: '#eef5f0', color: 'primary.main' }}>{ICONS[e.event_type] ?? <SpaIcon fontSize="small" />}</Avatar></ListItemAvatar>
                        <ListItemText sx={{ pr: 8 }}
                          primary={<><Button component={RouterLink} to={`/plants/${e.plant_id}`} size="small" sx={{ p: 0, minWidth: 0, mr: 1 }}>{names[e.plant_id]}</Button>
                            {e.event_label} · {new Date(e.timestamp).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}{e.amount_ml ? ` · ${e.amount_ml} мл` : ''}</>}
                          secondary={[e.method, e.notes].filter(Boolean).join(' — ') || undefined} />
                      </ListItem>
                    ))}
                  </List>
                </Box>
              ))}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
      {addFor !== null && (
        <Box>
          <CareEventDialog plantId={addFor} open onClose={() => setAddFor(null)} onSaved={reload} />
        </Box>
      )}
    </>
  );
}
