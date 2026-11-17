import { useState } from 'react';
import {
  Alert, Box, Card, CardContent, Chip, Grid2 as Grid, Stack, ToggleButton, ToggleButtonGroup, Typography,
} from '@mui/material';
import WaterDropOutlinedIcon from '@mui/icons-material/WaterDropOutlined';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import TrendingDownIcon from '@mui/icons-material/TrendingDown';
import TrendingFlatIcon from '@mui/icons-material/TrendingFlat';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import { api } from '../api/client';
import type { Horizon, Plant } from '../api/types';
import { useAsync } from '../utils/useAsync';
import { usePlantParam } from '../components/usePlantParam';
import { usePlants } from '../context/PlantContext';
import { PageHeader, PlantSelector } from '../components/PageHeader';
import { ConfidenceChip, KindChip } from '../components/Chips';
import { ErrorBox, Loading } from '../components/States';
import { ForecastChart } from '../components/ForecastChart';
import { fmtDateTime, fmtValue, unitLabel, untilText } from '../utils/format';

const LEVEL = { high: { label: 'высокий', color: 'error' }, medium: { label: 'средний', color: 'warning' }, low: { label: 'низкий', color: 'info' } } as const;
const TRAJ = {
  improving: { icon: <TrendingUpIcon color="success" />, label: 'улучшение' },
  stable: { icon: <TrendingFlatIcon color="success" />, label: 'стабильно' },
  declining: { icon: <TrendingDownIcon color="error" />, label: 'ухудшение' },
  uncertain: { icon: <HelpOutlineIcon color="warning" />, label: 'неопределённо' },
};

function targetFor(p: Plant | undefined, metric: string): [number | null, number | null] | undefined {
  if (!p) return undefined;
  const t = p.targets;
  return ({ temperature: [t.temp_min, t.temp_max], air_humidity: [t.humidity_min, t.humidity_max], light: [t.light_min, t.light_max] } as Record<string, [number, number]>)[metric];
}

export default function ForecastPage() {
  const id = usePlantParam('/forecast');
  const { byId } = usePlants();
  const [horizon, setHorizon] = useState<Horizon>(7);
  const fc = useAsync(() => (id && id > 0 ? api.forecast(id, horizon) : Promise.resolve(null)), [id, horizon]);
  if (id === -1) return <ErrorBox message="Растение не найдено" />;
  if (!id) return <Loading />;
  const plant = byId(id)?.plant;
  const f = fc.data;

  return (
    <>
      <PageHeader title="Прогноз" subtitle="Ожидаемые условия, время проверки полива и риски"
        actions={<>
          <PlantSelector value={id} basePath="/forecast" />
          <ToggleButtonGroup size="small" exclusive value={horizon} onChange={(_, v) => v && setHorizon(v)} sx={{ bgcolor: 'background.paper' }}>
            <ToggleButton value={3}>3 дня</ToggleButton>
            <ToggleButton value={7}>7 дней</ToggleButton>
            <ToggleButton value={14}>14 дней</ToggleButton>
          </ToggleButtonGroup>
        </>} />

      <Card variant="outlined" sx={{ mb: 2, bgcolor: '#fafbf8' }}>
        <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap alignItems="center">
            <Typography variant="body2" fontWeight={650} sx={{ mr: 1 }}>Типы данных:</Typography>
            <KindChip kind="measured" /><KindChip kind="derived" /><KindChip kind="forecast" /><KindChip kind="hypothesis" /><KindChip kind="observation" />
          </Stack>
        </CardContent>
      </Card>

      {fc.error && <ErrorBox message={fc.error} onRetry={fc.reload} />}
      {fc.loading && !f ? <Loading rows={4} /> : f && (
        <Stack spacing={3}>
          <Alert severity={f.is_demo ? 'warning' : 'info'} variant="outlined">
            <b>{f.disclaimer}</b><br />
            <Typography variant="body2" component="span">Методика: {f.method_summary}</Typography>
          </Alert>

          <Grid container spacing={2}>
            <Grid size={{ xs: 12, md: 6 }}>
              <Card sx={{ height: '100%', borderColor: 'primary.light' }}>
                <CardContent>
                  <Stack direction="row" justifyContent="space-between" alignItems="center">
                    <Stack direction="row" spacing={1} alignItems="center"><WaterDropOutlinedIcon color="primary" /><Typography variant="h6">Следующая проверка полива</Typography></Stack>
                    <KindChip kind="forecast" />
                  </Stack>
                  <Typography variant="h4" sx={{ mt: 1.5 }}>{untilText(f.watering.next_check_at)}</Typography>
                  <Typography color="text.secondary">{fmtDateTime(f.watering.next_check_at)} · по данным: {f.watering.based_on}</Typography>
                  <Box sx={{ mt: 1 }}><ConfidenceChip value={f.watering.confidence} label={f.watering.confidence_label} /></Box>
                  <Typography variant="body2" sx={{ mt: 1.5 }}>{f.watering.explanation}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid size={{ xs: 12, md: 6 }}>
              <Card sx={{ height: '100%' }}>
                <CardContent>
                  <Stack direction="row" justifyContent="space-between" alignItems="center">
                    <Typography variant="h6">Динамика состояния растения</Typography>
                    <KindChip kind={f.dynamics.kind} />
                  </Stack>
                  <Stack direction="row" spacing={1} alignItems="center" sx={{ mt: 1.5 }}>
                    {TRAJ[f.dynamics.trajectory].icon}
                    <Typography variant="h5">{f.dynamics.title}</Typography>
                  </Stack>
                  <Typography variant="body2" sx={{ mt: 1 }}>{f.dynamics.explanation}</Typography>
                  {f.dynamics.factors.length > 0 && (
                    <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mt: 1.5 }}>
                      {f.dynamics.factors.map((x) => <Chip key={x} size="small" label={x} />)}
                    </Stack>
                  )}
                  <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1.5 }}>
                    Это гипотеза на основе правил: она не является диагнозом и требует наблюдения за растением.
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          <Box>
            <Typography variant="h6" gutterBottom>Возможные риски</Typography>
            {f.risks.length === 0 ? <Alert severity="success">Значимых рисков в горизонте {f.horizon_days} дн. не обнаружено.</Alert> : (
              <Grid container spacing={2}>
                {f.risks.map((r) => (
                  <Grid key={r.code} size={{ xs: 12, md: 6 }}>
                    <Card sx={{ height: '100%', borderLeft: 4, borderLeftColor: `${LEVEL[r.level].color}.main` }}>
                      <CardContent>
                        <Stack direction="row" justifyContent="space-between" spacing={1} alignItems="center">
                          <Typography fontWeight={750}>{r.title}</Typography>
                          <Stack direction="row" spacing={1}>
                            <Chip size="small" color={LEVEL[r.level].color} label={`риск ${LEVEL[r.level].label}`} />
                            <KindChip kind={r.kind} />
                          </Stack>
                        </Stack>
                        <Typography variant="body2" sx={{ mt: 1 }}>{r.explanation}</Typography>
                        <Typography variant="body2" sx={{ mt: 1 }}><b>Что сделать:</b> {r.suggestion}</Typography>
                        {r.based_on.length > 0 && <Typography variant="caption" color="text.secondary">Основание: {r.based_on.join(', ')}</Typography>}
                      </CardContent>
                    </Card>
                  </Grid>
                ))}
              </Grid>
            )}
          </Box>

          <Box>
            <Typography variant="h6" gutterBottom>Прогноз условий на {f.horizon_days} дн.</Typography>
            {f.metrics.length === 0 && <Alert severity="info">Нет датчиков климата — прогнозировать нечего. Добавьте ручные измерения или подключите датчики.</Alert>}
            <Grid container spacing={2}>
              {f.metrics.map((m) => {
                const delta = m.expected_mean != null && m.current_mean != null ? m.expected_mean - m.current_mean : null;
                return (
                  <Grid key={m.metric} size={{ xs: 12, lg: 6 }}>
                    <Card>
                      <CardContent>
                        <Stack direction="row" justifyContent="space-between" alignItems="center" spacing={1}>
                          <Typography fontWeight={750}>{m.label}</Typography>
                          <Stack direction="row" spacing={1}><KindChip kind="forecast" /><ConfidenceChip value={m.confidence} label={m.confidence_label} /></Stack>
                        </Stack>
                        {m.current_mean != null && (
                          <Stack direction="row" spacing={3} sx={{ mt: 1 }}>
                            <Box><Typography variant="caption" color="text.secondary">Сейчас (среднее 3 дня)</Typography>
                              <Typography variant="h6">{fmtValue(m.current_mean, m.unit)} {unitLabel(m.unit)}</Typography></Box>
                            <Box><Typography variant="caption" color="text.secondary">Через {f.horizon_days} дн.</Typography>
                              <Typography variant="h6">{fmtValue(m.expected_mean, m.unit)} {unitLabel(m.unit)}</Typography></Box>
                            <Box><Typography variant="caption" color="text.secondary">Изменение</Typography>
                              <Typography variant="h6">{delta != null ? `${delta > 0 ? '+' : ''}${fmtValue(delta, m.unit)}` : '—'}</Typography></Box>
                          </Stack>
                        )}
                        {m.points.length > 0 && <ForecastChart f={m} target={targetFor(plant, m.metric)} />}
                        <Typography variant="body2" color="text.secondary">{m.explanation}</Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                );
              })}
            </Grid>
          </Box>

          <Box>
            <Typography variant="h6" gutterBottom>Расчётные показатели</Typography>
            <Grid container spacing={2}>
              {f.derived.map((d) => (
                <Grid key={d.key} size={{ xs: 12, sm: 6, md: 4 }}>
                  <Card sx={{ height: '100%' }}>
                    <CardContent>
                      <Stack direction="row" justifyContent="space-between"><Typography fontWeight={700}>{d.label}</Typography><KindChip kind={d.kind} /></Stack>
                      <Typography variant="h5" sx={{ mt: 1 }}>
                        {fmtValue(d.value, d.unit)} {unitLabel(d.unit)}
                        {d.value_end != null && <Typography component="span" color="text.secondary"> → {fmtValue(d.value_end, d.unit)} {unitLabel(d.unit)}</Typography>}
                      </Typography>
                      <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>{d.explanation}</Typography>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          </Box>
          <Typography variant="caption" color="text.secondary">Прогноз рассчитан {fmtDateTime(f.generated_at)}{f.forecast_id ? ` · сохранён как #${f.forecast_id}` : ''}</Typography>
        </Stack>
      )}
    </>
  );
}
