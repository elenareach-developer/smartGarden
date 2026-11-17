import { useEffect, useRef, useState } from 'react';
import {
  Alert, Avatar, Box, Button, Card, CardContent, Chip, Collapse, Grid2 as Grid, IconButton, List, ListItemButton,
  ListItemText, Paper, Stack, Tab, Tabs, TextField, Tooltip, Typography,
} from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import PersonIcon from '@mui/icons-material/Person';
import DeleteSweepOutlinedIcon from '@mui/icons-material/DeleteSweepOutlined';
import HistoryIcon from '@mui/icons-material/History';
import { api, errorMessage } from '../api/client';
import type { ConsultOut, Topic } from '../api/types';
import { usePlantParam } from '../components/usePlantParam';
import { usePlants } from '../context/PlantContext';
import { PageHeader, PlantSelector } from '../components/PageHeader';
import { ErrorBox, Loading, Spinner } from '../components/States';
import { Markdown } from '../components/Markdown';
import { FertilizerAdvisor } from '../components/FertilizerAdvisor';
import { useAsync } from '../utils/useAsync';
import { fmtDateTime } from '../utils/format';

const QUICK: [Topic, string][] = [
  ['feeding', 'Чем подкормить?'], ['watering', 'Когда поливать?'], ['yellow_leaves', 'Почему желтеют листья?'],
  ['no_bloom', 'Почему не цветёт?'], ['roots', 'Как стимулировать рост корней?'], ['disease', 'Есть ли признаки заболевания?'],
  ['conditions', 'Как изменить условия ухода?'],
];

interface Msg { role: 'user' | 'assistant'; content: string; meta?: ConsultOut }

export default function AssistantPage() {
  const id = usePlantParam('/assistant');
  const { byId } = usePlants();
  const [tab, setTab] = useState(0);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showHistory, setShowHistory] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);
  const history = useAsync(() => (id && id > 0 ? api.consultations(id) : Promise.resolve([])), [id]);
  const status = useAsync(() => api.system(), []);

  useEffect(() => { setMsgs([]); setError(null); }, [id]);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }); }, [msgs, busy]);

  if (id === -1) return <ErrorBox message="Растение не найдено" />;
  if (!id) return <Loading />;
  const plant = byId(id)?.plant;

  async function ask(question: string, topic: Topic = 'general', fertilizerId?: number) {
    if (!question.trim() || !id) return;
    setBusy(true);
    setError(null);
    const prior = msgs.map((m) => ({ role: m.role, content: m.content })).slice(-10);
    setMsgs((m) => [...m, { role: 'user', content: question }]);
    setInput('');
    try {
      const r = await api.consult({ plant_id: id, topic, question, history: prior, fertilizer_id: fertilizerId });
      setMsgs((m) => [...m, { role: 'assistant', content: r.answer, meta: r }]);
      void history.reload();
    } catch (e) {
      setError(errorMessage(e));
      setMsgs((m) => m.slice(0, -1));
      setInput(question);
    } finally {
      setBusy(false);
    }
  }

  const aiMode = status.data?.ai_mode;
  return (
    <>
      <PageHeader title="AI-помощник" subtitle={plant ? `Консультации по уходу за ${plant.name} с учётом её данных` : undefined}
        actions={<>
          <PlantSelector value={id} basePath="/assistant" />
          {aiMode && (
            <Tooltip title={aiMode === 'demo' ? 'Ответы строятся по экспертным правилам без языковой модели. Для Claude задайте ANTHROPIC_API_KEY на сервере.' : `Claude API (${status.data?.claude_model}); ключ хранится на сервере`}>
              <Chip color={aiMode === 'demo' ? 'warning' : 'success'} icon={<AutoAwesomeIcon />} label={aiMode === 'demo' ? 'Demo AI Mode' : 'Claude'} />
            </Tooltip>
          )}
        </>} />
      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 2 }}>
        <Tab label="Консультация" />
        <Tab label="Fertilizer Advisor" />
      </Tabs>

      {tab === 1 && plant && (
        <FertilizerAdvisor plant={plant} onAskAI={(fid, name) => { setTab(0); void ask(`Объясни оценку удобрения «${name}» для этого растения`, 'fertilizer', fid); }} />
      )}

      {tab === 0 && (
        <Grid container spacing={3}>
          <Grid size={{ xs: 12, md: 8 }}>
            <Card sx={{ display: 'flex', flexDirection: 'column', minHeight: 520 }}>
              <CardContent sx={{ flexGrow: 1, overflowY: 'auto', maxHeight: '62vh' }}>
                {msgs.length === 0 && !busy && (
                  <Box sx={{ textAlign: 'center', py: 4, px: 2 }}>
                    <Avatar sx={{ bgcolor: 'primary.main', mx: 'auto', width: 56, height: 56 }}><AutoAwesomeIcon /></Avatar>
                    <Typography variant="h6" sx={{ mt: 2 }}>Спросите об уходе за {plant?.name}</Typography>
                    <Typography color="text.secondary" sx={{ maxWidth: 520, mx: 'auto', mt: 1 }}>
                      Помощник видит вид, стадию, измерения, наблюдения за корнями и листьями, историю поливов и подкормок.
                      Отсутствующие измерения он не додумывает.
                    </Typography>
                  </Box>
                )}
                <Stack spacing={2}>
                  {msgs.map((m, i) => (
                    <Stack key={i} direction="row" spacing={1.5} alignItems="flex-start" justifyContent={m.role === 'user' ? 'flex-end' : 'flex-start'}>
                      {m.role === 'assistant' && <Avatar sx={{ bgcolor: 'primary.main', width: 32, height: 32 }}><AutoAwesomeIcon fontSize="small" /></Avatar>}
                      <Paper variant="outlined" sx={{ p: 2, maxWidth: '88%', bgcolor: m.role === 'user' ? '#eef5f0' : 'background.paper' }}>
                        {m.role === 'user' ? <Typography>{m.content}</Typography> : <Markdown>{m.content}</Markdown>}
                        {m.meta && (
                          <>
                            {m.meta.warnings.filter((w) => w.startsWith('Claude')).map((w) => <Alert key={w} severity="warning" sx={{ mt: 1 }}>{w}</Alert>)}
                            <Stack direction="row" spacing={1} sx={{ mt: 1.5 }} flexWrap="wrap" useFlexGap alignItems="center">
                              <Chip size="small" label={m.meta.mode === 'demo' ? 'Demo AI' : `Claude · ${m.meta.model}`} color={m.meta.mode === 'demo' ? 'warning' : 'success'} variant="outlined" />
                              {m.meta.clarifying_questions.slice(0, 3).map((q) => (
                                <Chip key={q} size="small" label={q} onClick={() => setInput(q)} clickable />
                              ))}
                            </Stack>
                          </>
                        )}
                      </Paper>
                      {m.role === 'user' && <Avatar sx={{ width: 32, height: 32 }}><PersonIcon fontSize="small" /></Avatar>}
                    </Stack>
                  ))}
                  {busy && <Spinner />}
                  <div ref={endRef} />
                </Stack>
              </CardContent>
              {error && <Box sx={{ px: 2 }}><ErrorBox message={error} /></Box>}
              <Box sx={{ p: 2, borderTop: '1px solid', borderColor: 'divider' }}>
                <Stack direction="row" spacing={1} sx={{ mb: 1.5, overflowX: 'auto', pb: 0.5 }}>
                  {QUICK.map(([t, q]) => <Chip key={t} label={q} onClick={() => void ask(q, t)} disabled={busy} variant="outlined" color="primary" clickable sx={{ flexShrink: 0 }} />)}
                </Stack>
                <Stack direction="row" spacing={1}>
                  <TextField fullWidth size="small" placeholder="Задайте свой вопрос или ответьте на уточняющий…" value={input}
                    onChange={(e) => setInput(e.target.value)} disabled={busy} multiline maxRows={4}
                    onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); void ask(input); } }} />
                  <IconButton color="primary" onClick={() => void ask(input)} disabled={busy || !input.trim()} aria-label="Отправить"><SendIcon /></IconButton>
                  <Tooltip title="Очистить диалог"><span><IconButton onClick={() => setMsgs([])} disabled={busy || !msgs.length} aria-label="Очистить"><DeleteSweepOutlinedIcon /></IconButton></span></Tooltip>
                </Stack>
              </Box>
            </Card>
          </Grid>
          <Grid size={{ xs: 12, md: 4 }}>
            <Stack spacing={2}>
              <Card>
                <CardContent>
                  <Typography variant="h6">Как работает помощник</Typography>
                  <Typography variant="body2" sx={{ mt: 1 }}>
                    • Использует только данные выбранного растения.<br />
                    • Различает измерения, расчёты, прогнозы и гипотезы.<br />
                    • Учитывает сезон и стадию развития.<br />
                    • Не назначает удобрения и дозировки — для этого есть Fertilizer Advisor.<br />
                    • API-ключ Claude хранится только на сервере.
                  </Typography>
                </CardContent>
              </Card>
              <Card>
                <CardContent>
                  <Button startIcon={<HistoryIcon />} onClick={() => setShowHistory((s) => !s)}>История консультаций ({history.data?.length ?? 0})</Button>
                  <Collapse in={showHistory}>
                    <List dense>
                      {(history.data ?? []).slice(0, 15).map((c) => (
                        <ListItemButton key={c.id} onClick={() => setMsgs([{ role: 'user', content: c.question }, { role: 'assistant', content: c.answer }])}>
                          <ListItemText primary={c.question} secondary={`${fmtDateTime(c.created_at)} · ${c.mode}`} primaryTypographyProps={{ noWrap: true }} />
                        </ListItemButton>
                      ))}
                    </List>
                  </Collapse>
                </CardContent>
              </Card>
            </Stack>
          </Grid>
        </Grid>
      )}
    </>
  );
}
