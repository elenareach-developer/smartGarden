export type DataKind = 'measured' | 'derived' | 'forecast' | 'hypothesis' | 'observation';
export type Status = 'ok' | 'low' | 'high' | 'no_data' | 'stale' | 'night';
export type Attention = 'ok' | 'attention' | 'critical';
export type Stage = 'vegetative' | 'spike' | 'blooming' | 'resting' | 'recovery';
export type RootStatus = 'healthy' | 'dry' | 'damaged' | 'rotting' | 'unknown';
export type LeafStatus = 'healthy' | 'wrinkled' | 'yellowing' | 'spots' | 'unknown';
export type CareType = 'watering' | 'fertilizing' | 'misting' | 'repotting' | 'inspection' | 'treatment' | 'other';
export type Period = '24h' | '7d' | '30d';
export type Horizon = 3 | 7 | 14;
export type Topic = 'feeding' | 'watering' | 'yellow_leaves' | 'no_bloom' | 'roots' | 'disease' | 'conditions' | 'fertilizer' | 'general';
export type MetricKey = 'temperature' | 'air_humidity' | 'light' | 'substrate_moisture' | 'pot_weight';

export interface Targets {
  temp_min: number; temp_max: number;
  humidity_min: number; humidity_max: number;
  light_min: number; light_max: number;
  photoperiod_min: number; photoperiod_max: number;
  substrate_min: number; substrate_max: number;
  pot_weight_dry: number | null; pot_weight_wet: number | null;
  watering_interval_days: number; fertilizing_interval_days: number;
}

export interface Plant {
  id: number; name: string; species: string; variety: string | null; photo_url: string | null;
  stage: Stage; stage_label: string; location: string | null; pot: string | null; substrate: string | null;
  notes: string | null; acquired_at: string | null;
  root_status: RootStatus; root_label: string; leaf_status: LeafStatus; leaf_label: string;
  observed_at: string | null; data_source: 'demo' | 'iot'; targets: Targets;
  created_at: string; updated_at: string;
}

export interface PlantCard {
  plant: Plant; summary: string; attention: Attention; attention_reasons: string[];
  last_watering: string | null; last_fertilizing: string | null; sensors: string[];
}

export type PlantUpdate = Partial<Omit<Plant, 'id' | 'stage_label' | 'root_label' | 'leaf_label' | 'created_at' | 'updated_at' | 'observed_at' | 'acquired_at'>>;

export interface Reading { value: number; unit: string; timestamp: string; source: 'demo' | 'iot' | 'manual'; quality: string }

export interface MetricState {
  metric: string; label: string; unit: string; kind: DataKind; available: boolean;
  current: Reading | null; manual_latest: Reading | null;
  target_min: number | null; target_max: number | null;
  status: Status; status_text: string; note: string | null; sparkline: number[];
}

export interface Observation {
  key: 'root_status' | 'leaf_status'; label: string; value: string; value_label: string;
  kind: DataKind; observed_at: string | null; status: 'ok' | 'attention' | 'critical' | 'unknown';
}

export interface Monitoring {
  plant_id: number; data_source: 'demo' | 'iot'; is_demo: boolean; generated_at: string;
  metrics: MetricState[]; observations: Observation[]; attention: Attention; attention_reasons: string[];
}

export interface HistoryPoint { t: string; value: number; min?: number | null; max?: number | null }
export interface HistorySeries {
  metric: string; label: string; unit: string; kind: DataKind; source: string; bucket_minutes: number;
  target_min: number | null; target_max: number | null; points: HistoryPoint[];
  stats: Record<string, number | null>;
}
export interface History { plant_id: number; period: Period; start: string; end: string; series: HistorySeries[]; manual: HistorySeries[] }

export interface ForecastPoint { t: string; value: number; low: number; high: number }
export interface MetricForecast {
  metric: string; label: string; unit: string; kind: DataKind; method: string;
  trend_per_day: number | null; current_mean: number | null; expected_mean: number | null;
  points: ForecastPoint[]; history: HistoryPoint[];
  confidence: number | null; confidence_label: string; explanation: string;
}
export interface WateringForecast {
  kind: DataKind; next_check_at: string | null; method: string; based_on: string;
  confidence: number | null; confidence_label: string; explanation: string;
}
export interface Risk {
  code: string; title: string; level: 'low' | 'medium' | 'high'; kind: DataKind;
  explanation: string; based_on: string[]; suggestion: string;
}
export interface Dynamics { kind: DataKind; trajectory: 'improving' | 'stable' | 'declining' | 'uncertain'; title: string; explanation: string; factors: string[] }
export interface DerivedValue { key: string; label: string; kind: DataKind; value: number | null; value_end?: number; unit: string; explanation: string }
export interface Forecast {
  plant_id: number; horizon_days: Horizon; generated_at: string; data_source: string; is_demo: boolean;
  method_summary: string; metrics: MetricForecast[]; derived: DerivedValue[]; watering: WateringForecast;
  risks: Risk[]; dynamics: Dynamics; disclaimer: string; forecast_id: number | null;
}

export interface CareEvent {
  id: number; plant_id: number; event_type: CareType; event_label: string; timestamp: string;
  amount_ml: number | null; method: string | null; notes: string | null; source: string;
}
export interface PlannedTask { task: string; title: string; due_at: string | null; kind: DataKind; explanation: string }
export interface Care { plant_id: number; events: CareEvent[]; planned: PlannedTask[] }
export interface CareEventIn {
  event_type: CareType; timestamp?: string; amount_ml?: number | null; method?: string | null; notes?: string | null;
  root_status?: RootStatus; leaf_status?: LeafStatus;
}

export interface Fertilizer {
  id: number; name: string; manufacturer: string | null; npk_n: number | null; npk_p: number | null; npk_k: number | null;
  micronutrients: string | null; concentration: string | null; form: string | null;
  labeled_for_orchids: boolean | null; manufacturer_instructions: string | null;
}
export type FertilizerIn = Omit<Fertilizer, 'id'>;
export interface Assessment {
  kind: DataKind; verdict: 'suitable' | 'conditional' | 'not_now' | 'insufficient_data'; verdict_label: string;
  composition_type: string | null; reasons: string[]; when_to_use: string; precautions: string[];
  blockers: string[]; questions: string[]; data_used: string[];
}
export interface Application {
  id: number; fertilizer: Fertilizer; applied_at: string; dilution: string | null;
  stage_at_application: string; notes: string | null; source: string;
}
export interface FertilizerResult { fertilizer: Fertilizer; assessment: Assessment; application: Application | null }
export interface Fertilizers {
  plant_id: number; library: Fertilizer[]; applications: Application[]; last_fertilized_at: string | null;
  next_window: PlannedTask | null;
}
export interface FertilizerRequest {
  fertilizer_id?: number; fertilizer?: FertilizerIn; stage?: Stage; last_fertilized_at?: string;
  record_application?: boolean; applied_at?: string; dilution?: string; notes?: string;
}

export interface ChatTurn { role: 'user' | 'assistant'; content: string }
export interface ConsultIn { plant_id: number; topic: Topic; question: string; history?: ChatTurn[]; fertilizer_id?: number; force_demo?: boolean }
export interface ConsultOut {
  consultation_id: number; plant_id: number; topic: Topic; mode: 'demo' | 'claude'; model: string | null;
  answer: string; clarifying_questions: string[]; data_used: string[]; missing_data: string[];
  warnings: string[]; created_at: string;
}
export interface Consultation { id: number; plant_id: number; topic: string; question: string; answer: string; mode: string; model: string | null; created_at: string }

export interface Sensor { id: number; plant_id: number; name: string; sensor_type: string; metrics: string[]; source: string; hardware_id: string | null; is_active: boolean }
export interface SensorIn { plant_id: number; name: string; sensor_type: string; hardware_id?: string | null }
export interface ReadingIn { plant_id: number; metric: MetricKey; value: number; timestamp?: string; source?: 'manual' | 'iot' }

export interface DashboardSummary {
  generated_at: string; plants_total: number; needs_attention: number; critical: number;
  ai_mode: 'demo' | 'claude'; data_sources: Record<string, number>;
  plants: { id: number; name: string; photo_url: string | null; attention: Attention; attention_reasons: string[]; summary: string }[];
  upcoming: (PlannedTask & { plant_id: number; plant_name: string })[];
  recent_events: { id: number; plant_id: number; plant_name: string; event_type: CareType; event_label: string; timestamp: string; notes: string | null; source: string }[];
}

export interface SystemStatus {
  app: string; database: string; ai_mode: 'demo' | 'claude'; ai_configured_mode: string; claude_model: string;
  api_key_configured: boolean; plants: number; readings_by_source: Record<string, number>; providers: string[];
}

// ---------- Botanical Spy ----------
export type SpyConfidence = 'высокая' | 'средняя' | 'низкая';
export type SpyDirection = 'climate' | 'scene' | 'biology' | 'owner';
export type SpyFactSource = 'photo' | 'pixel_stats' | 'profile' | 'sensor' | 'observation' | 'care_history' | 'knowledge';
export interface SpyFact { text: string; source: SpyFactSource }
export interface SpyHypothesis { text: string; confidence: SpyConfidence; evidence: string[]; how_to_verify: string }
export interface SpySection {
  direction: SpyDirection; title: string; facts: SpyFact[]; hypotheses: SpyHypothesis[];
  unknowns: string[]; data_needed: string[]; sensors: { sensor: string; purpose: string }[];
}
export interface SpyResult {
  codename: string; summary: string; identification: { name: string; confidence: SpyConfidence; basis: string };
  sections: SpySection[]; clues: string[]; to_check: string[];
  visual_estimates: { light_level: string; humidity_level: string; setting: string }; photo_note: string;
}
export interface SpyCrosscheck {
  metric: string; label: string; visual: string; measured: string | null; measured_at: string | null;
  source: string | null; verdict: 'consistent' | 'contradicts' | 'no_data'; note: string;
}
export interface SpyInvestigation {
  id: number; plant_id: number | null; plant_name: string | null; photo_url: string | null;
  photo_source: 'upload' | 'collection' | 'illustration' | 'none'; codename: string; mode: 'demo' | 'claude';
  model: string | null; result: SpyResult; crosscheck: SpyCrosscheck[]; image_stats: Record<string, unknown> | null;
  warnings: string[]; created_at: string;
}
export interface SpyBrief {
  id: number; plant_id: number | null; plant_name: string | null; photo_url: string | null; photo_source: string;
  codename: string; summary: string; mode: string; created_at: string;
}
