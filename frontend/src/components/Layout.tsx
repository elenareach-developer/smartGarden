import { useState, type ReactNode } from 'react';
import { Link as RouterLink, useLocation, useNavigate } from 'react-router-dom';
import {
  AppBar, BottomNavigation, BottomNavigationAction, Box, Chip, Divider, Drawer, IconButton, List, ListItemButton,
  ListItemIcon, ListItemText, Paper, Toolbar, Typography, useMediaQuery, useTheme,
} from '@mui/material';
import LocalFloristOutlinedIcon from '@mui/icons-material/LocalFloristOutlined';
import MonitorHeartOutlinedIcon from '@mui/icons-material/MonitorHeartOutlined';
import QueryStatsIcon from '@mui/icons-material/QueryStats';
import AutoAwesomeOutlinedIcon from '@mui/icons-material/AutoAwesomeOutlined';
import CalendarMonthOutlinedIcon from '@mui/icons-material/CalendarMonthOutlined';
import SettingsOutlinedIcon from '@mui/icons-material/SettingsOutlined';
import TravelExploreIcon from '@mui/icons-material/TravelExplore';
import MenuIcon from '@mui/icons-material/Menu';
import { usePlants } from '../context/PlantContext';

const WIDTH = 252;

export function useNavItems() {
  const { selectedId } = usePlants();
  const sel = selectedId ? `/${selectedId}` : '';
  return [
    { key: 'orchids', label: 'My Orchids', ru: 'Мои орхидеи', short: 'Орхидеи', to: '/', icon: <LocalFloristOutlinedIcon />, match: (p: string) => p === '/' || p.startsWith('/plants') },
    { key: 'monitoring', label: 'Monitoring', ru: 'Мониторинг', short: 'Мониторинг', to: `/monitoring${sel}`, icon: <MonitorHeartOutlinedIcon />, match: (p: string) => p.startsWith('/monitoring') },
    { key: 'forecast', label: 'Forecast', ru: 'Прогноз', short: 'Прогноз', to: `/forecast${sel}`, icon: <QueryStatsIcon />, match: (p: string) => p.startsWith('/forecast') },
    { key: 'assistant', label: 'AI Assistant', ru: 'AI-помощник', short: 'AI', to: `/assistant${sel}`, icon: <AutoAwesomeOutlinedIcon />, match: (p: string) => p.startsWith('/assistant') },
    { key: 'spy', label: 'Botanical Spy', ru: 'Ботаническая разведка', short: 'Разведка', to: '/spy', icon: <TravelExploreIcon />, match: (p: string) => p.startsWith('/spy') },
    { key: 'calendar', label: 'Care Calendar', ru: 'Календарь ухода', short: 'Календарь', to: '/calendar', icon: <CalendarMonthOutlinedIcon />, match: (p: string) => p.startsWith('/calendar') },
    { key: 'settings', label: 'Settings', ru: 'Настройки', short: 'Настройки', to: '/settings', icon: <SettingsOutlinedIcon />, match: (p: string) => p.startsWith('/settings') },
  ];
}

function Brand() {
  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.25, px: 1 }}>
      <Box component="img" src="/favicon.svg" alt="" sx={{ width: 34, height: 34 }} />
      <Box>
        <Typography fontWeight={800} lineHeight={1.1}>Smart Orchid</Typography>
        <Typography variant="caption" color="text.secondary">ботаническая лаборатория</Typography>
      </Box>
    </Box>
  );
}

function NavList({ onNavigate }: { onNavigate?: () => void }) {
  const items = useNavItems();
  const { pathname } = useLocation();
  const { plants, selectedId } = usePlants();
  const sel = plants.find((p) => p.plant.id === selectedId);
  return (
    <Box sx={{ p: 2, display: 'flex', flexDirection: 'column', height: '100%' }}>
      <Brand />
      <List sx={{ mt: 3 }}>
        {items.map((it) => (
          <ListItemButton key={it.key} component={RouterLink} to={it.to} selected={it.match(pathname)} onClick={onNavigate} sx={{ mb: 0.5 }}>
            <ListItemIcon sx={{ minWidth: 38 }}>{it.icon}</ListItemIcon>
            <ListItemText primary={it.label} secondary={it.ru} primaryTypographyProps={{ fontWeight: 650 }} secondaryTypographyProps={{ fontSize: 11.5 }} />
          </ListItemButton>
        ))}
      </List>
      <Box sx={{ flexGrow: 1 }} />
      {sel && (
        <Paper variant="outlined" sx={{ p: 1.5, bgcolor: '#f8faf6' }}>
          <Typography variant="caption" color="text.secondary">Выбрана орхидея</Typography>
          <Typography fontWeight={700}>{sel.plant.name}</Typography>
          <Typography variant="caption" color="text.secondary" display="block">{sel.plant.species}</Typography>
          {sel.plant.data_source === 'demo' && <Chip size="small" color="warning" label="DEMO-данные" sx={{ mt: 1 }} />}
        </Paper>
      )}
    </Box>
  );
}

export function Layout({ children }: { children: ReactNode }) {
  const theme = useTheme();
  const desktop = useMediaQuery(theme.breakpoints.up('md'));
  const [open, setOpen] = useState(false);
  const items = useNavItems();
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const mobileMain = items.slice(0, 4);
  const current = mobileMain.findIndex((i) => i.match(pathname));

  if (desktop) {
    return (
      <Box sx={{ display: 'flex', minHeight: '100vh' }}>
        <Drawer variant="permanent" sx={{ width: WIDTH, '& .MuiDrawer-paper': { width: WIDTH, borderRight: '1px solid', borderColor: 'divider' } }}>
          <NavList />
        </Drawer>
        <Box component="main" sx={{ flexGrow: 1, minWidth: 0, p: { md: 3, lg: 4 }, maxWidth: 1400 }}>{children}</Box>
      </Box>
    );
  }
  return (
    <Box sx={{ minHeight: '100vh', pb: 9 }}>
      <AppBar position="sticky" color="inherit" elevation={0} sx={{ borderBottom: '1px solid', borderColor: 'divider' }}>
        <Toolbar sx={{ gap: 1 }}>
          <IconButton edge="start" onClick={() => setOpen(true)} aria-label="Открыть меню"><MenuIcon /></IconButton>
          <Brand />
        </Toolbar>
      </AppBar>
      <Drawer open={open} onClose={() => setOpen(false)} sx={{ '& .MuiDrawer-paper': { width: WIDTH } }}>
        <NavList onNavigate={() => setOpen(false)} />
      </Drawer>
      <Box component="main" sx={{ p: 2 }}>{children}</Box>
      <Paper sx={{ position: 'fixed', bottom: 0, left: 0, right: 0, zIndex: 10, borderRadius: 0 }} elevation={3}>
        <Divider />
        <BottomNavigation showLabels value={current} onChange={(_, i: number) => navigate(mobileMain[i].to)}>
          {mobileMain.map((it) => <BottomNavigationAction key={it.key} label={it.short} icon={it.icon} />)}
        </BottomNavigation>
      </Paper>
    </Box>
  );
}
