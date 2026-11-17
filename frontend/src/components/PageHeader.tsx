import type { ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { Avatar, Box, MenuItem, Select, Stack, Typography } from '@mui/material';
import { usePlants } from '../context/PlantContext';

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: ReactNode; actions?: ReactNode }) {
  return (
    <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} alignItems={{ sm: 'center' }} justifyContent="space-between" sx={{ mb: 3 }}>
      <Box>
        <Typography variant="h4" component="h1">{title}</Typography>
        {subtitle && <Typography color="text.secondary" sx={{ mt: 0.5 }}>{subtitle}</Typography>}
      </Box>
      {actions && <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>{actions}</Stack>}
    </Stack>
  );
}

/** Выбор орхидеи для экранов Monitoring / Forecast / AI. Меняет URL. */
export function PlantSelector({ value, basePath }: { value: number; basePath: string }) {
  const { plants, select } = usePlants();
  const navigate = useNavigate();
  return (
    <Select size="small" value={value} sx={{ minWidth: 220, bgcolor: 'background.paper' }} aria-label="Выбор орхидеи"
      onChange={(e) => { const id = Number(e.target.value); select(id); navigate(`${basePath}/${id}`); }}
      renderValue={(id) => {
        const p = plants.find((x) => x.plant.id === id);
        return p ? (
          <Stack direction="row" spacing={1} alignItems="center">
            <Avatar src={p.plant.photo_url ?? undefined} sx={{ width: 24, height: 24 }} />
            <span>{p.plant.name}</span>
          </Stack>
        ) : '';
      }}>
      {plants.map((p) => (
        <MenuItem key={p.plant.id} value={p.plant.id}>
          <Stack direction="row" spacing={1.5} alignItems="center">
            <Avatar src={p.plant.photo_url ?? undefined} sx={{ width: 28, height: 28 }} />
            <Box>
              <Typography fontWeight={650}>{p.plant.name}</Typography>
              <Typography variant="caption" color="text.secondary">{p.plant.species}</Typography>
            </Box>
          </Stack>
        </MenuItem>
      ))}
    </Select>
  );
}
