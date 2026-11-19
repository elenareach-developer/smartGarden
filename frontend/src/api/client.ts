import axios, { AxiosError } from 'axios';
import type * as T from './types';

export const http = axios.create({ baseURL: import.meta.env.VITE_API_URL ?? '', timeout: 120_000 });

interface ApiErrorBody { detail?: string | { msg: string }[]; errors?: { field: string; message: string }[] }

/** Человекочитаемое сообщение об ошибке API. */
export function errorMessage(e: unknown): string {
  const err = e as AxiosError<ApiErrorBody>;
  if (err?.isAxiosError) {
    if (!err.response) return 'Сервер недоступен. Запущен ли backend на порту 8000?';
    const body = err.response.data;
    if (body?.errors?.length) return body.errors.map((x) => `${x.field || 'данные'}: ${x.message}`).join('; ');
    if (typeof body?.detail === 'string') return body.detail;
    return `Ошибка ${err.response.status}`;
  }
  return e instanceof Error ? e.message : 'Неизвестная ошибка';
}

const get = <R,>(url: string, params?: object) => http.get<R>(url, { params }).then((r) => r.data);
const post = <R,>(url: string, body?: unknown) => http.post<R>(url, body).then((r) => r.data);
const put = <R,>(url: string, body: unknown) => http.put<R>(url, body).then((r) => r.data);

export const api = {
  plants: () => get<T.PlantCard[]>('/api/plants'),
  plant: (id: number) => get<T.PlantCard>(`/api/plants/${id}`),
  updatePlant: (id: number, data: T.PlantUpdate) => put<T.Plant>(`/api/plants/${id}`, data),
  uploadPhoto: (id: number, file: File) => {
    const fd = new FormData();
    fd.append('file', file);
    return http.post<T.Plant>(`/api/plants/${id}/photo`, fd).then((r) => r.data);
  },
  monitoring: (id: number) => get<T.Monitoring>(`/api/plants/${id}/monitoring`),
  history: (id: number, period: T.Period) => get<T.History>(`/api/plants/${id}/history`, { period }),
  forecast: (id: number, horizon: T.Horizon) => get<T.Forecast>(`/api/plants/${id}/forecast`, { horizon }),
  care: (id: number) => get<T.Care>(`/api/plants/${id}/care`),
  addCare: (id: number, data: T.CareEventIn) => post<T.CareEvent>(`/api/plants/${id}/care`, data),
  fertilizers: (id: number) => get<T.Fertilizers>(`/api/plants/${id}/fertilizers`),
  adviseFertilizer: (id: number, data: T.FertilizerRequest) => post<T.FertilizerResult>(`/api/plants/${id}/fertilizers`, data),
  consult: (data: T.ConsultIn) => post<T.ConsultOut>('/api/ai/consult', data),
  consultations: (id: number) => get<T.Consultation[]>(`/api/plants/${id}/consultations`),
  sensors: (plantId?: number) => get<T.Sensor[]>('/api/sensors', plantId ? { plant_id: plantId } : undefined),
  registerSensor: (data: T.SensorIn) => post<T.Sensor>('/api/sensors', data),
  addReading: (data: T.ReadingIn) => post<{ accepted: number }>('/api/sensors/readings', data),
  dashboard: () => get<T.DashboardSummary>('/api/dashboard/summary'),
  system: () => get<T.SystemStatus>('/api/system/status'),
  resetDemo: () => post<{ status: string }>('/api/system/reset-demo'),
  // Botanical Spy
  spyInvestigate: (opts: { file?: File | null; plantId?: number | null; usePlantPhoto?: boolean }) => {
    const fd = new FormData();
    if (opts.file) fd.append('file', opts.file);
    if (opts.plantId) fd.append('plant_id', String(opts.plantId));
    if (opts.usePlantPhoto) fd.append('use_plant_photo', 'true');
    return http.post<T.SpyInvestigation>('/api/spy/investigations', fd, { timeout: 240_000 }).then((r) => r.data);
  },
  spyHistory: (plantId?: number) => get<T.SpyBrief[]>('/api/spy/investigations', plantId ? { plant_id: plantId } : undefined),
  spyGet: (id: number) => get<T.SpyInvestigation>(`/api/spy/investigations/${id}`),
};
