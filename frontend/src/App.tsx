import { Navigate, Route, Routes } from 'react-router-dom';
import { Layout } from './components/Layout';
import OrchidsPage from './pages/OrchidsPage';
import PlantProfilePage from './pages/PlantProfilePage';
import MonitoringPage from './pages/MonitoringPage';
import ForecastPage from './pages/ForecastPage';
import AssistantPage from './pages/AssistantPage';
import CalendarPage from './pages/CalendarPage';
import SettingsPage from './pages/SettingsPage';
import { usePlants } from './context/PlantContext';
import { ErrorBox } from './components/States';

export default function App() {
  const { error, reload, plants } = usePlants();
  return (
    <Layout>
      {error && !plants.length ? <ErrorBox message={error} onRetry={reload} /> : (
        <Routes>
          <Route path="/" element={<OrchidsPage />} />
          <Route path="/plants/:plantId" element={<PlantProfilePage />} />
          <Route path="/monitoring/:plantId?" element={<MonitoringPage />} />
          <Route path="/forecast/:plantId?" element={<ForecastPage />} />
          <Route path="/assistant/:plantId?" element={<AssistantPage />} />
          <Route path="/calendar" element={<CalendarPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      )}
    </Layout>
  );
}
