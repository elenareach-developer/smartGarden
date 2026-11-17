import { useEffect, useState } from 'react';
import {
  Alert, Box, Button, Card, CardContent, Chip, Divider, FormControlLabel, Grid2 as Grid, List, ListItem, ListItemText,
  MenuItem, Radio, RadioGroup, Stack, TextField, Typography,
} from '@mui/material';
import ScienceOutlinedIcon from '@mui/icons-material/ScienceOutlined';
import { api, errorMessage } from '../api/client';
import type { FertilizerIn, FertilizerResult, Plant, Stage } from '../api/types';
import { useAsync } from '../utils/useAsync';
import { fmtDate, STAGES } from '../utils/format';
import { KindChip } from './Chips';
import { ErrorBox } from './States';

const EMPTY: FertilizerIn = {
  name: '', manufacturer: null, npk_n: null, npk_p: null, npk_k: null, micronutrients: null, concentration: null,
  form: null, labeled_for_orchids: null, manufacturer_instructions: null,
};
const VERDICT_COLOR = { suitable: 'success', conditional: 'warning', not_now: 'error', insufficient_data: 'info' } as const;

export function FertilizerAdvisor({ plant, onAskAI }: { plant: Plant; onAskAI: (fertilizerId: number, name: string) => void }) {
  const lib = useAsync(() => api.fertilizers(plant.id), [plant.id]);
  const [mode, setMode] = useState<'library' | 'new'>('library');
  const [selected, setSelected] = useState<number | ''>('');
  const [form, setForm] = useState<FertilizerIn>(EMPTY);
  const [stage, setStage] = useState<Stage>(plant.stage);
  const [lastDate, setLastDate] = useState('');
  const [result, setResult] = useState<FertilizerResult | null>(null);
  const [dilution, setDilution] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState<string | null>(null);

  useEffect(() => { setStage(plant.stage); setResult(null); setSaved(null); }, [plant.id, plant.stage]);
  useEffect(() => { if (lib.data?.library.length && selected === '') setSelected(lib.data.library[0].id); }, [lib.data, selected]);

  const setF = (k: keyof FertilizerIn, num = false) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value === '' ? null : num ? Number(e.target.value) : e.target.value }));

  async function evaluate(record = false) {
    setBusy(true);
    setError(null);
    setSaved(null);
    try {
      const base = record && result
        ? { fertilizer_id: result.fertilizer.id }
        : mode === 'library' ? { fertilizer_id: Number(selected) } : { fertilizer: form };
      if (!record && mode === 'new' && !form.name.trim()) throw new Error('Укажите название удобрения');
      const r = await api.adviseFertilizer(plant.id, {
        ...base, stage, last_fertilized_at: lastDate ? new Date(lastDate).toISOString() : undefined,
        record_application: record, dilution: record ? dilution || undefined : undefined,
      });
      setResult(r);
      if (record) { setSaved(`Подкормка «${r.fertilizer.name}» записана в журнал.`); void lib.reload(); }
      else if (mode === 'new') { setMode('library'); setSelected(r.fertilizer.id); setForm(EMPTY); void lib.reload(); }
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  const a = result?.assessment;
  return (
    <Grid container spacing={3}>
      <Grid size={{ xs: 12, md: 5 }}>
        <Card>
          <CardContent>
            <Stack direction="row" spacing={1} alignItems="center"><ScienceOutlinedIcon color="primary" /><Typography variant="h6">Fertilizer Advisor</Typography></Stack>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              Укажите удобрение, которое у вас есть. Помощник оценит, подходит ли оно {plant.name} сейчас. Он не назначает препарат
              и не рассчитывает дозировку: дозу определяет инструкция производителя.
            </Typography>
            <RadioGroup row value={mode} onChange={(e) => setMode(e.target.value as 'library' | 'new')} sx={{ mt: 1 }}>
              <FormControlLabel value="library" control={<Radio />} label="Из моих удобрений" />
              <FormControlLabel value="new" control={<Radio />} label="Новое" />
            </RadioGroup>
            <Stack spacing={2} sx={{ mt: 1 }}>
              {mode === 'library' ? (
                <TextField select label="Удобрение" value={selected} onChange={(e) => setSelected(Number(e.target.value))}>
                  {(lib.data?.library ?? []).map((f) => (
                    <MenuItem key={f.id} value={f.id}>{f.name}{f.npk_n != null ? ` · NPK ${f.npk_n}-${f.npk_p}-${f.npk_k}` : ''}</MenuItem>
                  ))}
                </TextField>
              ) : (
                <>
                  <TextField label="Название" required value={form.name} onChange={setF('name')} />
                  <TextField label="Производитель" value={form.manufacturer ?? ''} onChange={setF('manufacturer')} />
                  <Stack direction="row" spacing={1}>
                    <TextField label="N, %" type="number" value={form.npk_n ?? ''} onChange={setF('npk_n', true)} />
                    <TextField label="P, %" type="number" value={form.npk_p ?? ''} onChange={setF('npk_p', true)} />
                    <TextField label="K, %" type="number" value={form.npk_k ?? ''} onChange={setF('npk_k', true)} />
                  </Stack>
                  <TextField label="Микроэлементы" placeholder="как на этикетке: Fe, Mg, B…" value={form.micronutrients ?? ''} onChange={setF('micronutrients')} />
                  <TextField label="Концентрация / форма выпуска" value={form.concentration ?? ''} onChange={setF('concentration')} />
                  <TextField select label="Предназначено для орхидей?" value={form.labeled_for_orchids === null ? '' : String(form.labeled_for_orchids)}
                    onChange={(e) => setForm((f) => ({ ...f, labeled_for_orchids: e.target.value === '' ? null : e.target.value === 'true' }))}>
                    <MenuItem value="">Не знаю</MenuItem><MenuItem value="true">Да, указано на упаковке</MenuItem><MenuItem value="false">Нет</MenuItem>
                  </TextField>
                  <TextField label="Инструкция производителя" multiline minRows={2} placeholder="Перепишите разведение и частоту с этикетки"
                    value={form.manufacturer_instructions ?? ''} onChange={setF('manufacturer_instructions')} />
                </>
              )}
              <TextField select label="Стадия развития" value={stage} onChange={(e) => setStage(e.target.value as Stage)}>
                {STAGES.map(([v, l]) => <MenuItem key={v} value={v}>{l}</MenuItem>)}
              </TextField>
              <TextField type="date" label="Дата последней подкормки (если журнал неточен)" InputLabelProps={{ shrink: true }}
                value={lastDate} onChange={(e) => setLastDate(e.target.value)}
                helperText={lib.data?.last_fertilized_at ? `По журналу: ${fmtDate(lib.data.last_fertilized_at)}` : 'В журнале нет подкормок'} />
              {error && <Alert severity="error">{error}</Alert>}
              <Button variant="contained" onClick={() => evaluate(false)} disabled={busy || (mode === 'library' && selected === '')}>Оценить применимость</Button>
            </Stack>
          </CardContent>
        </Card>
      </Grid>
      <Grid size={{ xs: 12, md: 7 }}>
        {lib.error && <ErrorBox message={lib.error} onRetry={lib.reload} />}
        {!a && (
          <Alert severity="info" variant="outlined">Выберите удобрение и нажмите «Оценить применимость».
            {lib.data?.next_window && <><br /><b>{lib.data.next_window.title}:</b> {lib.data.next_window.explanation}</>}
          </Alert>
        )}
        {a && result && (
          <Card>
            <CardContent>
              <Stack direction="row" justifyContent="space-between" alignItems="center" spacing={1}>
                <Typography variant="h6">{result.fertilizer.name}</Typography>
                <KindChip kind={a.kind} />
              </Stack>
              <Stack direction="row" spacing={1} sx={{ mt: 1 }} flexWrap="wrap" useFlexGap>
                <Chip color={VERDICT_COLOR[a.verdict]} label={a.verdict_label} />
                {a.composition_type && <Chip variant="outlined" label={`Состав: ${a.composition_type}`} />}
              </Stack>
              {a.blockers.length > 0 && (
                <Alert severity="error" sx={{ mt: 2 }}>
                  <b>Почему не сейчас:</b>
                  <ul style={{ margin: '4px 0 0', paddingLeft: 18 }}>{a.blockers.map((x) => <li key={x}>{x}</li>)}</ul>
                </Alert>
              )}
              {a.reasons.length > 0 && <>
                <Typography fontWeight={700} sx={{ mt: 2 }}>Почему</Typography>
                <List dense disablePadding>{a.reasons.map((x) => <ListItem key={x} disableGutters><ListItemText primary={`• ${x}`} /></ListItem>)}</List>
              </>}
              <Typography fontWeight={700} sx={{ mt: 1.5 }}>Когда использовать</Typography>
              <Typography variant="body2">{a.when_to_use}</Typography>
              <Typography fontWeight={700} sx={{ mt: 1.5 }}>Меры предосторожности</Typography>
              <List dense disablePadding>{a.precautions.map((x) => <ListItem key={x} disableGutters><ListItemText primary={`• ${x}`} /></ListItem>)}</List>
              {a.questions.length > 0 && (
                <Alert severity="info" variant="outlined" sx={{ mt: 1.5 }}>
                  <b>Чтобы оценить точнее, уточните:</b>
                  <ul style={{ margin: '4px 0 0', paddingLeft: 18 }}>{a.questions.map((x) => <li key={x}>{x}</li>)}</ul>
                </Alert>
              )}
              <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1.5 }}>Учтено: {a.data_used.join(' · ')}</Typography>
              <Divider sx={{ my: 2 }} />
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} alignItems={{ sm: 'center' }}>
                <Button variant="outlined" onClick={() => onAskAI(result.fertilizer.id, result.fertilizer.name)}>Попросить AI объяснить</Button>
                <Box sx={{ flexGrow: 1 }} />
                <TextField size="small" label="Фактическое разведение" placeholder="по инструкции производителя" value={dilution} onChange={(e) => setDilution(e.target.value)} />
                <Button variant="contained" color={a.verdict === 'not_now' ? 'warning' : 'primary'} disabled={busy}
                  onClick={() => { if (a.verdict !== 'not_now' || window.confirm('Помощник не рекомендует подкормку сейчас. Всё равно записать, что подкормка уже сделана?')) void evaluate(true); }}>
                  Записать подкормку
                </Button>
              </Stack>
              {saved && <Alert severity="success" sx={{ mt: 2 }}>{saved}</Alert>}
            </CardContent>
          </Card>
        )}
        {lib.data && lib.data.applications.length > 0 && (
          <Card sx={{ mt: 3 }}>
            <CardContent>
              <Typography variant="h6">История подкормок</Typography>
              <List dense>
                {lib.data.applications.slice(0, 8).map((x) => (
                  <ListItem key={x.id} disableGutters secondaryAction={x.source === 'demo' ? <Chip size="small" label="DEMO" variant="outlined" color="warning" /> : undefined}>
                    <ListItemText primary={`${fmtDate(x.applied_at)} — ${x.fertilizer.name}`}
                      secondary={[x.dilution && `разведение: ${x.dilution}`, x.notes].filter(Boolean).join(' · ') || undefined} />
                  </ListItem>
                ))}
              </List>
            </CardContent>
          </Card>
        )}
      </Grid>
    </Grid>
  );
}
