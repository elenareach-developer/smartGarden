import { useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { usePlants } from '../context/PlantContext';

/** Возвращает id растения из URL; без id — перенаправляет на выбранное. */
export function usePlantParam(basePath: string): number | null {
  const { plantId } = useParams();
  const { selectedId, select, plants, loading } = usePlants();
  const navigate = useNavigate();
  const id = plantId ? Number(plantId) : null;

  useEffect(() => {
    if (!id && selectedId) navigate(`${basePath}/${selectedId}`, { replace: true });
    else if (id && id !== selectedId && plants.some((p) => p.plant.id === id)) select(id);
  }, [id, selectedId, basePath, navigate, select, plants]);

  if (!id) return null;
  if (!loading && plants.length && !plants.some((p) => p.plant.id === id)) return -1;
  return id;
}
