import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Alert, Box, Button, Card, CardActionArea, CardActions, CardContent, Chip, Grid2 as Grid, Stack, Tooltip, Typography,
} from '@mui/material';
import WaterDropOutlinedIcon from '@mui/icons-material/WaterDropOutlined';
import ScienceOutlinedIcon from '@mui/icons-material/ScienceOutlined';
import EditOutlinedIcon from '@mui/icons-material/EditOutlined';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import { usePlants } from '../context/PlantContext';
import { AttentionChip } from '../components/Chips';
import { PageHeader } from '../components/PageHeader';
import { PlantPhoto } from '../components/PlantPhoto';
import { ErrorBox, Loading } from '../components/States';
import { EditPlantDialog } from '../components/EditPlantDialog';
import { CareEventDialog } from '../components/CareEventDialog';
import type { PlantCard } from '../api/types';
import { fmtDate, relDays } from '../utils/format';

const ICON = { ok: <CheckCircleOutlineIcon color="success" />, attention: <WarningAmberIcon color="warning" />, critical: <ErrorOutlineIcon color="error" /> };

function OrchidCard({ card, onEdit, onWater }: { card: PlantCard; onEdit: () => void; onWater: () => void }) {
  const navigate = useNavigate();
  const { select } = usePlants();
  const p = card.plant;
  const open = () => { select(p.id); navigate(`/plants/${p.id}`); };
  return (
    <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <CardActionArea onClick={open} sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column', alignItems: 'stretch' }}>
        <Box sx={{ position: 'relative' }}>
          <PlantPhoto url={p.photo_url} name={p.name} height={220} rounded={false} showBadge />
          <Box sx={{ position: 'absolute', top: 12, right: 12 }}><AttentionChip level={card.attention} /></Box>
          {p.data_source === 'demo' && (
            <Chip size="small" icon={<ScienceOutlinedIcon />} label="DEMO" color="warning"
              sx={{ position: 'absolute', top: 12, left: 12 }} />
          )}
        </Box>
        <CardContent sx={{ flexGrow: 1 }}>
          <Typography variant="h5">{p.name}</Typography>
          <Typography color="text.secondary" variant="body2">{p.species}{p.variety ? ` · ${p.variety}` : ''}</Typography>
          <Chip size="small" variant="outlined" label={p.stage_label} sx={{ mt: 1.5 }} />
          <Stack direction="row" spacing={1} alignItems="flex-start" sx={{ mt: 2 }}>
            {ICON[card.attention]}
            <Box>
              <Typography fontWeight={650}>{card.summary}</Typography>
              {card.attention_reasons.length > 1 && (
                <Typography variant="caption" color="text.secondary">{card.attention_reasons.slice(1, 3).join(' · ')}</Typography>
              )}
            </Box>
          </Stack>
          <Grid container spacing={1} sx={{ mt: 2 }}>
            <Grid size={6}>
              <Typography variant="caption" color="text.secondary">Последний полив</Typography>
              <Tooltip title={fmtDate(card.last_watering)}><Typography fontWeight={600}>{relDays(card.last_watering)}</Typography></Tooltip>
            </Grid>
            <Grid size={6}>
              <Typography variant="caption" color="text.secondary">Последняя подкормка</Typography>
              <Tooltip title={fmtDate(card.last_fertilizing)}><Typography fontWeight={600}>{relDays(card.last_fertilizing)}</Typography></Tooltip>
            </Grid>
          </Grid>
        </CardContent>
      </CardActionArea>
      <CardActions sx={{ px: 2, pb: 2 }}>
        <Button size="small" variant="outlined" startIcon={<WaterDropOutlinedIcon />} onClick={onWater}>Полив</Button>
        <Button size="small" startIcon={<EditOutlinedIcon />} onClick={onEdit}>Редактировать</Button>
        <Box sx={{ flexGrow: 1 }} />
        <Button size="small" variant="contained" onClick={open}>Открыть</Button>
      </CardActions>
    </Card>
  );
}

export default function OrchidsPage() {
  const { plants, loading, error, reload } = usePlants();
  const [edit, setEdit] = useState<PlantCard | null>(null);
  const [water, setWater] = useState<number | null>(null);
  const attention = plants.filter((p) => p.attention !== 'ok').length;

  return (
    <>
      <PageHeader title="Мои орхидеи" subtitle="Коллекция и состояние каждого растения. Выберите орхидею, чтобы открыть её кабинет." />
      {error && <ErrorBox message={error} onRetry={reload} />}
      {loading ? <Loading /> : (
        <>
          {attention > 0 && (
            <Alert severity="warning" sx={{ mb: 3 }}>
              {attention} из {plants.length} растений требуют внимания. Подробности — в карточках и на экране мониторинга.
            </Alert>
          )}
          <Grid container spacing={3}>
            {plants.map((c) => (
              <Grid key={c.plant.id} size={{ xs: 12, sm: 6, lg: 4 }}>
                <OrchidCard card={c} onEdit={() => setEdit(c)} onWater={() => setWater(c.plant.id)} />
              </Grid>
            ))}
          </Grid>
        </>
      )}
      {edit && <EditPlantDialog plant={edit.plant} open onClose={() => setEdit(null)} onSaved={reload} />}
      {water !== null && <CareEventDialog plantId={water} open initialType="watering" onClose={() => setWater(null)} onSaved={reload} />}
    </>
  );
}
