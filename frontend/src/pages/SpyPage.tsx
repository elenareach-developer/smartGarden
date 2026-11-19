import { useEffect, useRef, useState } from 'react';
import {
  Alert, Avatar, Box, Button, Card, CardActionArea, CardContent, Chip, Grid2 as Grid, LinearProgress, MenuItem, Stack,
  TextField, ToggleButton, ToggleButtonGroup, Tooltip, Typography,
} from '@mui/material';
import TravelExploreIcon from '@mui/icons-material/TravelExplore';
import AddPhotoAlternateOutlinedIcon from '@mui/icons-material/AddPhotoAlternateOutlined';
import CollectionsOutlinedIcon from '@mui/icons-material/CollectionsOutlined';
import ShieldOutlinedIcon from '@mui/icons-material/ShieldOutlined';
import { api, errorMessage } from '../api/client';
import type { SpyInvestigation } from '../api/types';
import { usePlants } from '../context/PlantContext';
import { useAsync } from '../utils/useAsync';
import { fmtDateTime } from '../utils/format';
import { PageHeader } from '../components/PageHeader';
import { ErrorBox } from '../components/States';
import { PlantPhoto, isIllustration } from '../components/PlantPhoto';
import { SpyDossier } from '../components/SpyDossier';

const STEPS = ['Снимаем отпечатки листьев…', 'Допрашиваем пиксели…', 'Сверяем алиби с датчиками…', 'Листаем ботанический справочник…', 'Составляем досье…'];

export default function SpyPage() {
  const { plants, selectedId } = usePlants();
  const [source, setSource] = useState<'upload' | 'collection'>('upload');
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [plantId, setPlantId] = useState<number | ''>('');
  const [busy, setBusy] = useState(false);
  const [step, setStep] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [current, setCurrent] = useState<SpyInvestigation | null>(null);
  const [drag, setDrag] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const history = useAsync(() => api.spyHistory(), []);
  const status = useAsync(() => api.system(), []);

  useEffect(() => { if (source === 'collection' && plantId === '' && selectedId) setPlantId(selectedId); }, [source, plantId, selectedId]);
  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview); }, [preview]);
  useEffect(() => {
    if (!busy) return;
    const t = setInterval(() => setStep((s) => (s + 1) % STEPS.length), 1600);
    return () => clearInterval(t);
  }, [busy]);

  const chosen = plants.find((p) => p.plant.id === plantId)?.plant;
  const pick = (f: File | undefined) => {
    if (!f) return;
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(f.type)) { setError('Поддерживаются JPEG, PNG и WebP'); return; }
    setError(null);
    setFile(f);
    setPreview(URL.createObjectURL(f));
  };

  async function start() {
    setBusy(true); setStep(0); setError(null);
    try {
      const inv = await api.spyInvestigate(source === 'upload'
        ? { file, plantId: plantId || null }
        : { plantId: plantId || null, usePlantPhoto: true });
      setCurrent(inv);
      void history.reload();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  async function open(id: number) {
    setError(null);
    try { setCurrent(await api.spyGet(id)); window.scrollTo({ top: 0, behavior: 'smooth' }); } catch (e) { setError(errorMessage(e)); }
  }

  const canStart = source === 'upload' ? !!file : !!plantId;
  const mode = status.data?.ai_mode;
  return (
    <>
      <PageHeader title="Ботаническая разведка" subtitle="Что можно узнать об окружающем мире по фотографии одного растения?"
        actions={mode && (
          <Tooltip title={mode === 'claude' ? 'Claude анализирует фото (vision)' : 'Без API-ключа агент не распознаёт объекты на фото, а работает с пикселями, профилем и датчиками'}>
            <Chip icon={<TravelExploreIcon />} color={mode === 'claude' ? 'success' : 'warning'} label={mode === 'claude' ? 'Агент Claude' : 'Агент Demo'} />
          </Tooltip>
        )} />
      <Grid container spacing={3}>
        <Grid size={{ xs: 12, md: 4 }}>
          <Card>
            <CardContent>
              <Typography variant="h6">Улика №1: фотография</Typography>
              <ToggleButtonGroup exclusive fullWidth size="small" value={source} onChange={(_, v) => v && setSource(v)} sx={{ mt: 1.5 }}>
                <ToggleButton value="upload"><AddPhotoAlternateOutlinedIcon fontSize="small" sx={{ mr: 0.5 }} />Загрузить</ToggleButton>
                <ToggleButton value="collection"><CollectionsOutlinedIcon fontSize="small" sx={{ mr: 0.5 }} />Из коллекции</ToggleButton>
              </ToggleButtonGroup>

              {source === 'upload' ? (
                <Box onClick={() => inputRef.current?.click()} role="button" tabIndex={0} aria-label="Выбрать фото"
                  onKeyDown={(e) => { if (e.key === 'Enter') inputRef.current?.click(); }}
                  onDragOver={(e) => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)}
                  onDrop={(e) => { e.preventDefault(); setDrag(false); pick(e.dataTransfer.files[0]); }}
                  sx={{ mt: 2, borderRadius: 3, border: '2px dashed', borderColor: drag ? 'primary.main' : 'divider', cursor: 'pointer',
                    bgcolor: drag ? '#eef5f0' : '#fafbf8', overflow: 'hidden', minHeight: 200, display: 'grid', placeItems: 'center' }}>
                  {preview ? <Box component="img" src={preview} alt="Выбранное фото" sx={{ width: '100%', maxHeight: 280, objectFit: 'cover', display: 'block' }} /> : (
                    <Stack alignItems="center" spacing={1} sx={{ p: 3, textAlign: 'center' }}>
                      <AddPhotoAlternateOutlinedIcon color="primary" sx={{ fontSize: 40 }} />
                      <Typography fontWeight={650}>Перетащите фото или нажмите</Typography>
                      <Typography variant="caption" color="text.secondary">JPEG, PNG, WebP до 10 МБ</Typography>
                    </Stack>
                  )}
                  <input ref={inputRef} hidden type="file" accept="image/jpeg,image/png,image/webp" onChange={(e) => { pick(e.target.files?.[0]); e.target.value = ''; }} />
                </Box>
              ) : (
                <Box sx={{ mt: 2 }}>
                  {chosen ? <PlantPhoto url={chosen.photo_url} name={chosen.name} height={200} showBadge /> : <Box sx={{ height: 200, bgcolor: '#f3f5f1', borderRadius: 3 }} />}
                  {chosen && isIllustration(chosen.photo_url) && (
                    <Alert severity="info" variant="outlined" sx={{ mt: 1 }}>У этого растения пока только иллюстрация. Агент изучит профиль и датчики, но пиксельных улик не будет. Фото можно загрузить в профиле растения.</Alert>
                  )}
                </Box>
              )}

              <TextField select fullWidth size="small" sx={{ mt: 2 }} value={plantId}
                label={source === 'upload' ? 'Связать с растением (необязательно)' : 'Растение из коллекции'}
                helperText={source === 'upload' ? 'Тогда агент использует профиль и сверит фото с датчиками' : undefined}
                onChange={(e) => setPlantId(e.target.value === '' ? '' : Number(e.target.value))}>
                {source === 'upload' && <MenuItem value="">Не связывать — чужое растение</MenuItem>}
                {plants.map((p) => (
                  <MenuItem key={p.plant.id} value={p.plant.id}>
                    <Stack direction="row" spacing={1} alignItems="center"><Avatar src={p.plant.photo_url ?? undefined} sx={{ width: 22, height: 22 }} /><span>{p.plant.name}</span></Stack>
                  </MenuItem>
                ))}
              </TextField>

              <Button fullWidth size="large" variant="contained" startIcon={<TravelExploreIcon />} sx={{ mt: 2 }} disabled={!canStart || busy} onClick={start}>
                Начать расследование
              </Button>
              {busy && (
                <Box sx={{ mt: 2 }}>
                  <LinearProgress />
                  <Typography variant="caption" color="text.secondary" sx={{ fontFamily: 'ui-monospace, monospace' }}>{STEPS[step]}</Typography>
                </Box>
              )}
              {error && <Box sx={{ mt: 2 }}><ErrorBox message={error} /></Box>}
              <Stack direction="row" spacing={1} alignItems="flex-start" sx={{ mt: 2 }}>
                <ShieldOutlinedIcon fontSize="small" color="action" />
                <Typography variant="caption" color="text.secondary">
                  Загруженные фото перекодируются без метаданных (EXIF, GPS). Агент отделяет факты от гипотез и не делает выводов о личности владельца.
                </Typography>
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, md: 8 }}>
          {current ? <SpyDossier key={current.id} inv={current} /> : (
            <Card sx={{ height: '100%', minHeight: 320, display: 'grid', placeItems: 'center', bgcolor: '#fbf9f3', borderStyle: 'dashed' }}>
              <CardContent sx={{ textAlign: 'center', maxWidth: 520 }}>
                <TravelExploreIcon sx={{ fontSize: 56, color: 'primary.light' }} />
                <Typography variant="h6" sx={{ mt: 1 }}>Досье пока пусто</Typography>
                <Typography color="text.secondary" sx={{ mt: 1 }}>
                  Агент изучит климат родины растения, окружение на снимке, биологические улики и организацию ухода.
                  Каждая гипотеза получит уровень уверенности и способ проверки.
                </Typography>
              </CardContent>
            </Card>
          )}
        </Grid>
      </Grid>

      <Typography variant="h6" sx={{ mt: 4, mb: 2 }}>Архив расследований</Typography>
      {history.error && <ErrorBox message={history.error} onRetry={history.reload} />}
      {history.data && history.data.length === 0 && <Alert severity="info">Расследований ещё не было.</Alert>}
      <Grid container spacing={2}>
        {(history.data ?? []).map((h) => (
          <Grid key={h.id} size={{ xs: 12, sm: 6, lg: 3 }}>
            <Card sx={{ height: '100%', outline: current?.id === h.id ? '2px solid' : 'none', outlineColor: 'primary.main' }}>
              <CardActionArea onClick={() => void open(h.id)} sx={{ height: '100%' }}>
                <PlantPhoto url={h.photo_url} name={h.plant_name ?? 'объект'} height={120} rounded={false} />
                <CardContent>
                  <Typography variant="caption" sx={{ fontFamily: 'ui-monospace, monospace' }} color="text.secondary">№{String(h.id).padStart(4, '0')} · {fmtDateTime(h.created_at)}</Typography>
                  <Typography fontWeight={700} noWrap>{h.codename}</Typography>
                  <Stack direction="row" spacing={0.5} sx={{ mt: 0.5 }}>
                    <Chip size="small" label={h.plant_name ?? 'без привязки'} variant="outlined" />
                    <Chip size="small" label={h.mode === 'claude' ? 'Claude' : 'Demo'} color={h.mode === 'claude' ? 'success' : 'warning'} variant="outlined" />
                  </Stack>
                </CardContent>
              </CardActionArea>
            </Card>
          </Grid>
        ))}
      </Grid>
    </>
  );
}
