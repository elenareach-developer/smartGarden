import { useState } from 'react';
import {
  Alert, Box, Card, CardContent, Chip, Divider, Grid2 as Grid, List, ListItem, ListItemIcon, ListItemText, Stack, Tab,
  Tabs, Tooltip, Typography,
} from '@mui/material';
import ThermostatOutlinedIcon from '@mui/icons-material/ThermostatOutlined';
import WindowOutlinedIcon from '@mui/icons-material/WindowOutlined';
import BugReportOutlinedIcon from '@mui/icons-material/BugReportOutlined';
import PersonSearchOutlinedIcon from '@mui/icons-material/PersonSearchOutlined';
import SearchIcon from '@mui/icons-material/Search';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import CompareArrowsIcon from '@mui/icons-material/CompareArrows';
import RemoveCircleOutlineIcon from '@mui/icons-material/RemoveCircleOutline';
import SensorsIcon from '@mui/icons-material/Sensors';
import TaskAltIcon from '@mui/icons-material/TaskAlt';
import type { SpyConfidence, SpyFactSource, SpyInvestigation, SpySection } from '../api/types';
import { fmtDateTime } from '../utils/format';
import { KindChip, SourceChip } from './Chips';
import { PlantPhoto } from './PlantPhoto';

const DIR_ICON = { climate: <ThermostatOutlinedIcon />, scene: <WindowOutlinedIcon />, biology: <BugReportOutlinedIcon />, owner: <PersonSearchOutlinedIcon /> };
const DIR_EN = { climate: 'Climate Intelligence', scene: 'Scene Investigation', biology: 'Biological Investigation', owner: 'Owner Profile' };
const SOURCE: Record<SpyFactSource, { label: string; hint: string }> = {
  photo: { label: 'Фото', hint: 'Видно на снимке или в его метаданных' },
  pixel_stats: { label: 'Пиксели', hint: 'Измерено по пикселям снимка' },
  profile: { label: 'Профиль', hint: 'Из профиля растения' },
  sensor: { label: 'Датчик', hint: 'Показание датчика с датой' },
  observation: { label: 'Наблюдение', hint: 'Осмотр, внесённый владельцем' },
  care_history: { label: 'Журнал', hint: 'Журнал ухода' },
  knowledge: { label: 'Справочник', hint: 'Общие ботанические сведения о роде/виде' },
};
const CONF_COLOR: Record<SpyConfidence, 'success' | 'warning' | 'error'> = { 'высокая': 'success', 'средняя': 'warning', 'низкая': 'error' };

function Heading({ children, extra }: { children: string; extra?: React.ReactNode }) {
  return (
    <Stack direction="row" spacing={1} alignItems="center" sx={{ mt: 2.5, mb: 1 }}>
      <Typography variant="overline" sx={{ fontWeight: 800, letterSpacing: 1.5, color: 'primary.dark' }}>{children}</Typography>
      {extra}
    </Stack>
  );
}

function SectionView({ s }: { s: SpySection }) {
  return (
    <Box>
      <Heading extra={<Tooltip title="То, что видно на фото или есть в данных. Не догадки."><Chip size="small" label="только проверяемое" variant="outlined" /></Tooltip>}>Факты</Heading>
      {s.facts.length === 0 ? <Typography color="text.secondary" variant="body2">Достоверных фактов по этому направлению нет.</Typography> : (
        <Stack spacing={0.75}>
          {s.facts.map((f, i) => (
            <Stack key={i} direction="row" spacing={1} alignItems="flex-start">
              <Tooltip title={SOURCE[f.source].hint}><Chip size="small" label={SOURCE[f.source].label} sx={{ minWidth: 104, flexShrink: 0, height: 22 }} color={f.source === 'sensor' ? 'success' : f.source === 'knowledge' ? 'info' : 'default'} variant="outlined" /></Tooltip>
              <Typography variant="body2">{f.text}</Typography>
            </Stack>
          ))}
        </Stack>
      )}
      <Heading extra={<KindChip kind="hypothesis" />}>Гипотезы</Heading>
      <Grid container spacing={1.5}>
        {s.hypotheses.map((h, i) => (
          <Grid key={i} size={{ xs: 12, md: 4 }}>
            <Box sx={{ p: 1.5, height: '100%', borderRadius: 2, border: '1px dashed', borderColor: 'divider', bgcolor: '#fffdf7' }}>
              <Stack direction="row" justifyContent="space-between" alignItems="center" flexWrap="wrap" useFlexGap spacing={0.5} sx={{ mb: 0.75 }}>
                <Typography variant="caption" sx={{ fontFamily: 'ui-monospace, monospace', color: 'text.secondary', whiteSpace: 'nowrap' }}>№{i + 1}</Typography>
                <Chip size="small" color={CONF_COLOR[h.confidence]} variant="outlined" label={h.confidence} sx={{ height: 22 }} />
              </Stack>
              <Typography fontWeight={650} variant="body2">{h.text}</Typography>
              {h.evidence.length > 0 && <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.75 }}>Улики: {h.evidence.join('; ')}</Typography>}
              <Typography variant="caption" display="block" sx={{ mt: 0.5 }}><b>Проверка:</b> {h.how_to_verify}</Typography>
            </Box>
          </Grid>
        ))}
      </Grid>
      <Grid container spacing={2} sx={{ mt: 0.5 }}>
        <Grid size={{ xs: 12, md: 4 }}>
          <Heading>Не определить по фото</Heading>
          <List dense disablePadding>{s.unknowns.map((u) => <ListItem key={u} disableGutters><ListItemIcon sx={{ minWidth: 28 }}><HelpOutlineIcon fontSize="small" color="disabled" /></ListItemIcon><ListItemText primary={u} /></ListItem>)}</List>
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <Heading>Нужны данные</Heading>
          <List dense disablePadding>{s.data_needed.map((u) => <ListItem key={u} disableGutters><ListItemIcon sx={{ minWidth: 28 }}><SearchIcon fontSize="small" color="action" /></ListItemIcon><ListItemText primary={u} /></ListItem>)}</List>
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <Heading>Датчики для проверки</Heading>
          <List dense disablePadding>{s.sensors.map((x) => <ListItem key={x.sensor} disableGutters><ListItemIcon sx={{ minWidth: 28 }}><SensorsIcon fontSize="small" color="primary" /></ListItemIcon><ListItemText primary={x.sensor} secondary={x.purpose} /></ListItem>)}</List>
        </Grid>
      </Grid>
    </Box>
  );
}

const VERDICT = {
  consistent: { icon: <CheckCircleOutlineIcon color="success" />, label: 'подтверждено датчиком' },
  contradicts: { icon: <CompareArrowsIcon color="warning" />, label: 'расходится с датчиком' },
  no_data: { icon: <RemoveCircleOutlineIcon color="disabled" />, label: 'нечем проверить' },
};

export function SpyDossier({ inv }: { inv: SpyInvestigation }) {
  const [tab, setTab] = useState(0);
  const r = inv.result;
  const section = r.sections[tab];
  return (
    <Card sx={{ position: 'relative', overflow: 'visible', bgcolor: '#fbf9f3', borderColor: '#e6dfcc' }}>
      <Box sx={{ position: 'absolute', top: 18, right: 18, transform: 'rotate(8deg)', border: '3px double', borderColor: 'error.main',
        color: 'error.main', px: 1.5, py: 0.25, borderRadius: 1, fontWeight: 900, letterSpacing: 3, fontSize: 13, opacity: 0.75,
        display: { xs: 'none', sm: 'block' } }}>СЕКРЕТНО</Box>
      <CardContent>
        <Typography variant="caption" sx={{ fontFamily: 'ui-monospace, monospace', color: 'text.secondary' }}>
          ДОСЬЕ №{String(inv.id).padStart(4, '0')} · {fmtDateTime(inv.created_at)} · агент: {inv.mode === 'claude' ? `Claude (${inv.model})` : 'Demo'}
        </Typography>
        <Typography variant="h5" sx={{ mt: 0.5, pr: { sm: 14 } }}>{r.codename}</Typography>
        {inv.warnings.map((w) => <Alert key={w} severity="warning" sx={{ mt: 1.5 }}>{w}</Alert>)}
        <Grid container spacing={2.5} sx={{ mt: 0.5 }}>
          <Grid size={{ xs: 12, sm: 4 }}>
            <PlantPhoto url={inv.photo_url} name={inv.plant_name ?? 'объект'} height={190} showBadge={inv.photo_source === 'illustration'} />
          </Grid>
          <Grid size={{ xs: 12, sm: 8 }}>
            <Typography variant="body2">{r.summary}</Typography>
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mt: 1.5 }}>
              <Chip label={`Объект: ${r.identification.name}`} color="primary" />
              <Chip variant="outlined" color={CONF_COLOR[r.identification.confidence]} label={`опознание: ${r.identification.confidence}`} />
              {inv.plant_name && <Chip variant="outlined" label={`Дело: ${inv.plant_name}`} />}
            </Stack>
            <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>Основание опознания: {r.identification.basis}</Typography>
            <Typography variant="caption" color="text.secondary" display="block">{r.photo_note}</Typography>
          </Grid>
        </Grid>

        <Heading>Улики</Heading>
        <Stack spacing={0.75}>
          {r.clues.map((c, i) => (
            <Typography key={i} variant="body2"><Box component="span" sx={{ fontFamily: 'ui-monospace, monospace', color: 'error.main', mr: 1 }}>#{i + 1}</Box>{c}</Typography>
          ))}
        </Stack>

        <Divider sx={{ my: 2 }} />
        <Tabs value={tab} onChange={(_, v) => setTab(v)} variant="scrollable" allowScrollButtonsMobile>
          {r.sections.map((s) => <Tab key={s.direction} icon={DIR_ICON[s.direction]} iconPosition="start" label={<Box textAlign="left"><div>{s.title}</div><Typography variant="caption" color="text.secondary">{DIR_EN[s.direction]}</Typography></Box>} sx={{ minHeight: 56 }} />)}
        </Tabs>
        {section && <SectionView s={section} />}
        {section?.direction === 'owner' && (
          <Alert severity="info" variant="outlined" sx={{ mt: 2 }}>
            Профиль владельца описывает только организацию ухода. Выводы о личности, характере, возрасте или семейном положении по фото не делаются.
          </Alert>
        )}

        <Divider sx={{ my: 2 }} />
        <Heading extra={<KindChip kind="measured" />}>Сверка с датчиками</Heading>
        <Stack spacing={1}>
          {inv.crosscheck.map((c) => (
            <Stack key={c.metric} direction="row" spacing={1.5} alignItems="flex-start">
              {VERDICT[c.verdict].icon}
              <Box>
                <Typography variant="body2" fontWeight={650}>
                  {c.label}: по фото — {c.visual}; датчик — {c.measured ?? 'нет данных'} <Typography component="span" variant="caption" color="text.secondary">({VERDICT[c.verdict].label})</Typography>
                </Typography>
                <Stack direction="row" spacing={1} alignItems="center">
                  {c.source && <SourceChip source={c.source} />}
                  <Typography variant="caption" color="text.secondary">{c.measured_at ? `${fmtDateTime(c.measured_at)} · ` : ''}{c.note}</Typography>
                </Stack>
              </Box>
            </Stack>
          ))}
        </Stack>

        <Heading>Что проверить</Heading>
        <List dense disablePadding>
          {r.to_check.map((t) => <ListItem key={t} disableGutters><ListItemIcon sx={{ minWidth: 28 }}><TaskAltIcon fontSize="small" color="primary" /></ListItemIcon><ListItemText primary={t} /></ListItem>)}
        </List>
      </CardContent>
    </Card>
  );
}
