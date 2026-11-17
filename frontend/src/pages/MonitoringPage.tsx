import { useState } from 'react';
import {
  Alert, Box, Button, Card, CardContent, Chip, Grid2 as Grid, Stack, Tab, Tabs, ToggleButton, ToggleButtonGroup, Typography,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import RefreshIcon from '@mui/icons-material/Refresh';
import { api } from '../api/client';
import type { MetricKey, MetricState, Period } from '../api/types';
import { useAsync } from '../utils/useAsync';
import { usePlantParam } from '../components/usePlantParam';
import { PageHeader, PlantSelector } from '../components/PageHeader';
import { KindChip, SourceChip, StatusChip } from '../components/Chips';
import { RangeBar } from '../components/RangeBar';
import { Sparkline } from '../components/Sparkline';
import { ErrorBox, Loading } from '../components/States';
import { HistoryChart } from '../components/HistoryChart';
import { ManualReadingDialog } from '../components/ManualReadingDialog';
import { fmtDateTime, fmtValue, unitLabel } from '../utils/format';

const COLORS: Record<string, string> = {
  temperature: '#d0743c', air_humidity: '#3d7ea6', light: '#c9a21d', photoperiod: '#8a6fb0',
  substrate_moisture: '#2e6b4a', pot_weight: '#6d5a48',
};

function MetricCard({ m, onAdd }: { m: MetricState; onAdd: () => void }) {
  return (
    <Card sx={{ height: '100%', opacity: m.available ? 1 : 0.85 }}>
      <CardContent>
        <Stack direction="row" justifyContent="space-between" alignItems="center" spacing={1}>
          <Typography fontWeight={700}>{m.label}</Typography>
          <KindChip kind={m.kind} />
        </Stack>
        {m.current ? (
          <>
            <Stack direction="row" alignItems="baseline" spacing={1} sx={{ mt: 1 }}>
              <Typography variant="h4" sx={{ color: COLORS[m.metric] }}>{fmtValue(m.current.value, m.unit)}</Typography>
              <Typography color="text.secondary">{unitLabel(m.unit)}</Typography>
            </Stack>
            <Stack direction="row" spacing={1} alignItems="center" sx={{ mt: 0.5 }} flexWrap="wrap" useFlexGap>
              <StatusChip status={m.status} />
              <SourceChip source={m.current.source} />
              <Typography variant="caption" color="text.secondary">{fmtDateTime(m.current.timestamp)}</Typography>
            </Stack>
            {m.metric !== 'light' && <RangeBar value={m.current.value} min={m.target_min} max={m.target_max} unit={m.unit} />}
            {m.metric === 'light' && m.target_min != null && (
              <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
                цель днём {fmtValue(m.target_min, 'lx')}–{fmtValue(m.target_max, 'lx')} лк
              </Typography>
            )}
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>{m.status_text}</Typography>
            {m.sparkline.length > 1 && <Box sx={{ mt: 1 }}><Sparkline data={m.sparkline} color={COLORS[m.metric]} /></Box>}
          </>
        ) : (
          <Box sx={{ mt: 1.5 }}>
            <StatusChip status="no_data" />
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>{m.status_text}</Typography>
          </Box>
        )}
        {m.note && <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>{m.note}</Typography>}
        {m.manual_latest && (
          <Alert severity="info" variant="outlined" sx={{ mt: 1.5, py: 0 }} icon={false}>
            Вручную: <b>{fmtValue(m.manual_latest.value, m.unit)} {unitLabel(m.unit)}</b> · {fmtDateTime(m.manual_latest.timestamp)}
          </Alert>
        )}
        {m.kind === 'measured' && (
          <Button size="small" startIcon={<AddIcon />} onClick={onAdd} sx={{ mt: 1, ml: -1 }}>Внести вручную</Button>
        )}
      </CardContent>
    </Card>
  );
}

export default function MonitoringPage() {
  const id = usePlantParam('/monitoring');
  const [period, setPeriod] = useState<Period>('24h');
  const [metric, setMetric] = useState<string>('temperature');
  const [manual, setManual] = useState<MetricKey | null>(null);
  const mon = useAsync(() => (id && id > 0 ? api.monitoring(id) : Promise.resolve(null)), [id]);
  const hist = useAsync(() => (id && id > 0 ? api.history(id, period) : Promise.resolve(null)), [id, period]);

  if (id === -1) return <ErrorBox message="Растение не найдено" />;
  if (!id) return <Loading />;
  const refresh = () => { void mon.reload(); void hist.reload(); };
  const series = hist.data?.series ?? [];
  const current = series.find((s) => s.metric === metric) ?? series[0];
  const manualSeries = hist.data?.manual.find((s) => s.metric === current?.metric);

  return (
    <>
      <PageHeader title="Мониторинг" subtitle="Текущее состояние и история измерений"
        actions={<>
          <PlantSelector value={id} basePath="/monitoring" />
          <Button variant="outlined" startIcon={<AddIcon />} onClick={() => setManual('temperature')}>Измерение</Button>
          <Button startIcon={<RefreshIcon />} onClick={refresh}>Обновить</Button>
        </>} />
      {mon.error && <ErrorBox message={mon.error} onRetry={mon.reload} />}
      {mon.loading && !mon.data ? <Loading rows={4} /> : mon.data && (
        <>
          {mon.data.is_demo && (
            <Alert severity="warning" variant="outlined" sx={{ mb: 2 }}>
              <b>DEMO-режим.</b> Физических датчиков пока нет: измерения смоделированы DemoDataProvider (суточный ход, длина дня,
              высыхание после поливов из журнала). Данные обновляются со временем. Ручные измерения хранятся отдельно.
            </Alert>
          )}
          <Grid container spacing={2}>
            {mon.data.metrics.map((m) => (
              <Grid key={m.metric} size={{ xs: 12, sm: 6, lg: 4 }}>
                <MetricCard m={m} onAdd={() => setManual(m.metric as MetricKey)} />
              </Grid>
            ))}
            {mon.data.observations.map((o) => (
              <Grid key={o.key} size={{ xs: 12, sm: 6, lg: 4 }}>
                <Card sx={{ height: '100%' }}>
                  <CardContent>
                    <Stack direction="row" justifyContent="space-between" alignItems="center">
                      <Typography fontWeight={700}>{o.label}</Typography>
                      <KindChip kind="observation" />
                    </Stack>
                    <Typography variant="h6" sx={{ mt: 1 }}>{o.value_label}</Typography>
                    <Chip size="small" sx={{ mt: 1 }} label={{ ok: 'Норма', attention: 'Внимание', critical: 'Критично', unknown: 'Неизвестно' }[o.status]}
                      color={{ ok: 'success', attention: 'warning', critical: 'error', unknown: 'default' }[o.status] as 'success'} />
                    <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
                      Осмотр: {fmtDateTime(o.observed_at)}. Обновляется при записи осмотра в профиле растения.
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </>
      )}

      <Card sx={{ mt: 3 }}>
        <CardContent>
          <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" spacing={2} alignItems={{ sm: 'center' }}>
            <Typography variant="h6">История измерений</Typography>
            <ToggleButtonGroup size="small" exclusive value={period} onChange={(_, v) => v && setPeriod(v)}>
              <ToggleButton value="24h">24 часа</ToggleButton>
              <ToggleButton value="7d">7 дней</ToggleButton>
              <ToggleButton value="30d">30 дней</ToggleButton>
            </ToggleButtonGroup>
          </Stack>
          {hist.error && <ErrorBox message={hist.error} onRetry={hist.reload} />}
          {series.length > 0 && current && (
            <>
              <Tabs value={current.metric} onChange={(_, v) => setMetric(v)} variant="scrollable" sx={{ mt: 1 }}>
                {series.map((s) => <Tab key={s.metric} value={s.metric} label={s.label} />)}
              </Tabs>
              <Stack direction="row" spacing={1} sx={{ my: 1.5 }} flexWrap="wrap" useFlexGap alignItems="center">
                <KindChip kind={current.kind} />
                <SourceChip source={current.source} />
                <Typography variant="body2" color="text.secondary">
                  мин {fmtValue(current.stats.min, current.unit)} · сред {fmtValue(current.stats.avg, current.unit)} · макс {fmtValue(current.stats.max, current.unit)} {unitLabel(current.unit)}
                  {current.bucket_minutes > 30 && current.bucket_minutes < 1440 && ` · усреднение по ${current.bucket_minutes / 60} ч`}
                </Typography>
              </Stack>
              <HistoryChart series={current} manual={manualSeries} period={period} />
              <Typography variant="caption" color="text.secondary">Зелёная полоса — целевой диапазон растения.</Typography>
            </>
          )}
          {!hist.loading && series.length === 0 && !hist.error && (
            <Alert severity="info" sx={{ mt: 2 }}>Нет измерений за период.</Alert>
          )}
        </CardContent>
      </Card>
      {manual && <ManualReadingDialog plantId={id} open initialMetric={manual} onClose={() => setManual(null)} onSaved={refresh} />}
    </>
  );
}
