import { Chip, Tooltip, type ChipProps } from '@mui/material';
import SensorsIcon from '@mui/icons-material/Sensors';
import CalculateOutlinedIcon from '@mui/icons-material/CalculateOutlined';
import TimelineIcon from '@mui/icons-material/Timeline';
import PsychologyOutlinedIcon from '@mui/icons-material/PsychologyOutlined';
import VisibilityOutlinedIcon from '@mui/icons-material/VisibilityOutlined';
import ScienceOutlinedIcon from '@mui/icons-material/ScienceOutlined';
import RouterOutlinedIcon from '@mui/icons-material/RouterOutlined';
import EditNoteIcon from '@mui/icons-material/EditNote';
import type { Attention, DataKind, Status } from '../api/types';

const KIND: Record<DataKind, { label: string; color: ChipProps['color']; icon: JSX.Element; hint: string }> = {
  measured: { label: 'Измерено', color: 'success', icon: <SensorsIcon />, hint: 'Значение получено от датчика или введено вручную' },
  derived: { label: 'Расчёт', color: 'info', icon: <CalculateOutlinedIcon />, hint: 'Вычислено из измерений по формуле' },
  forecast: { label: 'Прогноз', color: 'secondary', icon: <TimelineIcon />, hint: 'Ожидаемое значение по модели прогноза' },
  hypothesis: { label: 'AI-гипотеза', color: 'warning', icon: <PsychologyOutlinedIcon />, hint: 'Предположение на основе правил или AI; требует проверки' },
  observation: { label: 'Наблюдение', color: 'primary', icon: <VisibilityOutlinedIcon />, hint: 'Результат осмотра, внесённый пользователем' },
};

export function KindChip({ kind, size = 'small' }: { kind: DataKind; size?: ChipProps['size'] }) {
  const k = KIND[kind];
  return (
    <Tooltip title={k.hint}>
      <Chip size={size} variant="outlined" color={k.color} icon={k.icon} label={k.label} sx={{ height: 24 }} />
    </Tooltip>
  );
}

export function SourceChip({ source }: { source: string }) {
  if (source === 'demo')
    return <Tooltip title="Демонстрационные данные: смоделированы DemoDataProvider"><Chip size="small" color="warning" icon={<ScienceOutlinedIcon />} label="DEMO" sx={{ height: 24 }} /></Tooltip>;
  if (source === 'iot')
    return <Chip size="small" color="info" icon={<RouterOutlinedIcon />} label="IoT" sx={{ height: 24 }} />;
  return <Chip size="small" color="default" icon={<EditNoteIcon />} label="Вручную" sx={{ height: 24 }} />;
}

const ATT: Record<Attention, { label: string; color: ChipProps['color'] }> = {
  ok: { label: 'Всё хорошо', color: 'success' },
  attention: { label: 'Нужно внимание', color: 'warning' },
  critical: { label: 'Срочно', color: 'error' },
};

export function AttentionChip({ level, size = 'small' }: { level: Attention; size?: ChipProps['size'] }) {
  return <Chip size={size} color={ATT[level].color} label={ATT[level].label} />;
}

const ST: Record<Status, { label: string; color: ChipProps['color'] }> = {
  ok: { label: 'Норма', color: 'success' },
  low: { label: 'Ниже нормы', color: 'warning' },
  high: { label: 'Выше нормы', color: 'error' },
  no_data: { label: 'Нет данных', color: 'default' },
  stale: { label: 'Устарело', color: 'default' },
  night: { label: 'Ночь', color: 'default' },
};

export function StatusChip({ status }: { status: Status }) {
  return <Chip size="small" color={ST[status].color} variant={status === 'ok' ? 'outlined' : 'filled'} label={ST[status].label} sx={{ height: 22 }} />;
}

export const confidenceColor = (c: number | null): ChipProps['color'] =>
  c === null ? 'default' : c >= 0.7 ? 'success' : c >= 0.45 ? 'warning' : 'error';

export function ConfidenceChip({ value, label }: { value: number | null; label: string }) {
  return (
    <Tooltip title="Уверенность рассчитывается из объёма данных, качества подгонки модели и горизонта прогноза">
      <Chip size="small" variant="outlined" color={confidenceColor(value)}
        label={`Уверенность: ${label}${value !== null ? ` (${Math.round(value * 100)}%)` : ''}`} sx={{ height: 24 }} />
    </Tooltip>
  );
}
