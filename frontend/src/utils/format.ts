const dtf = new Intl.DateTimeFormat('ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
const df = new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' });
const dshort = new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'short' });

export const fmtDateTime = (iso?: string | null) => (iso ? dtf.format(new Date(iso)) : '—');
export const fmtDate = (iso?: string | null) => (iso ? df.format(new Date(iso)) : '—');
export const fmtDayShort = (iso?: string | null) => (iso ? dshort.format(new Date(iso)) : '—');

export function relDays(iso?: string | null): string {
  if (!iso) return 'нет данных';
  const days = (Date.now() - new Date(iso).getTime()) / 86_400_000;
  if (days < -0.5) {
    const d = Math.round(-days);
    return d === 1 ? 'завтра' : `через ${d} ${plural(d, 'день', 'дня', 'дней')}`;
  }
  if (days < 0.5) return 'сегодня';
  if (days < 1.5) return 'вчера';
  const d = Math.round(days);
  return `${d} ${plural(d, 'день', 'дня', 'дней')} назад`;
}

export function untilText(iso?: string | null): string {
  if (!iso) return '—';
  const h = (new Date(iso).getTime() - Date.now()) / 3_600_000;
  if (h <= 1) return 'сейчас';
  if (h < 24) return `через ${Math.round(h)} ч`;
  const d = Math.round(h / 24);
  return `через ${d} ${plural(d, 'день', 'дня', 'дней')}`;
}

export function plural(n: number, one: string, few: string, many: string) {
  const a = Math.abs(n) % 100, b = a % 10;
  if (a > 10 && a < 20) return many;
  if (b > 1 && b < 5) return few;
  if (b === 1) return one;
  return many;
}

const UNIT: Record<string, string> = { h: 'ч', g: 'г', lx: 'лк' };
export const unitLabel = (u: string) => UNIT[u] ?? u;

export function fmtValue(v: number | null | undefined, unit: string): string {
  if (v === null || v === undefined) return '—';
  const digits = unit === 'lx' || unit === 'g' || unit === '%' ? 0 : 1;
  return v.toLocaleString('ru-RU', { maximumFractionDigits: digits, minimumFractionDigits: digits });
}

export const STAGES = [
  ['vegetative', 'Вегетация (рост листьев и корней)'],
  ['spike', 'Рост цветоноса'],
  ['blooming', 'Цветение'],
  ['resting', 'Период покоя'],
  ['recovery', 'Восстановление'],
] as const;
export const ROOTS = [
  ['healthy', 'Здоровые'], ['dry', 'Пересушены'], ['damaged', 'Повреждены'], ['rotting', 'Признаки гнили'], ['unknown', 'Не осматривались'],
] as const;
export const LEAVES = [
  ['healthy', 'Упругие'], ['wrinkled', 'Потеря тургора'], ['yellowing', 'Желтеют'], ['spots', 'Пятна'], ['unknown', 'Не осматривались'],
] as const;
export const METRIC_OPTIONS = [
  ['temperature', 'Температура', '°C'],
  ['air_humidity', 'Влажность воздуха', '%'],
  ['light', 'Освещённость', 'lx'],
  ['substrate_moisture', 'Влажность субстрата', '%'],
  ['pot_weight', 'Масса горшка', 'g'],
] as const;
