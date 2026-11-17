import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { api, errorMessage } from '../api/client';
import type { PlantCard } from '../api/types';

interface Ctx {
  plants: PlantCard[];
  loading: boolean;
  error: string | null;
  reload: () => Promise<void>;
  selectedId: number | null;
  select: (id: number) => void;
  byId: (id: number | null | undefined) => PlantCard | undefined;
}

const PlantContext = createContext<Ctx | null>(null);
const KEY = 'smartOrchid.selectedPlant';

function readSaved(): number | null {
  try {
    const v = localStorage.getItem(KEY);
    return v ? Number(v) : null;
  } catch {
    return null;
  }
}

export function PlantProvider({ children }: { children: ReactNode }) {
  const [plants, setPlants] = useState<PlantCard[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(readSaved);

  const reload = useCallback(async () => {
    setError(null);
    try {
      const list = await api.plants();
      setPlants(list);
      setSelectedId((cur) => (cur && list.some((p) => p.plant.id === cur) ? cur : list[0]?.plant.id ?? null));
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void reload(); }, [reload]);

  const select = useCallback((id: number) => {
    setSelectedId(id);
    try { localStorage.setItem(KEY, String(id)); } catch { /* приватный режим */ }
  }, []);

  const value = useMemo<Ctx>(() => ({
    plants, loading, error, reload, selectedId, select,
    byId: (id) => plants.find((p) => p.plant.id === id),
  }), [plants, loading, error, reload, selectedId, select]);

  return <PlantContext.Provider value={value}>{children}</PlantContext.Provider>;
}

export function usePlants() {
  const ctx = useContext(PlantContext);
  if (!ctx) throw new Error('usePlants вне PlantProvider');
  return ctx;
}
