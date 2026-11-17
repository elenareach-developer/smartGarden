import { alpha, createTheme } from '@mui/material/styles';

const green = '#2e6b4a';

export const theme = createTheme({
  palette: {
    mode: 'light',
    primary: { main: green, light: '#5a9a75', dark: '#1d4a32', contrastText: '#fff' },
    secondary: { main: '#8a6fb0' },
    success: { main: '#3f8f5b' },
    warning: { main: '#c9851d' },
    error: { main: '#c0453a' },
    info: { main: '#3d7ea6' },
    background: { default: '#f5f7f2', paper: '#ffffff' },
    text: { primary: '#1d2a22', secondary: '#5d6b62' },
    divider: '#e2e8df',
  },
  shape: { borderRadius: 14 },
  typography: {
    fontFamily: '"Manrope", "Segoe UI", Roboto, system-ui, sans-serif',
    h4: { fontWeight: 800, letterSpacing: -0.5 },
    h5: { fontWeight: 750 },
    h6: { fontWeight: 700 },
    subtitle1: { fontWeight: 600 },
    button: { textTransform: 'none', fontWeight: 650 },
  },
  components: {
    MuiCard: {
      defaultProps: { elevation: 0 },
      styleOverrides: {
        root: { border: '1px solid #e2e8df', boxShadow: '0 1px 2px rgba(29,42,34,.04), 0 6px 18px rgba(29,42,34,.04)' },
      },
    },
    MuiPaper: { styleOverrides: { rounded: { borderRadius: 14 } } },
    MuiButton: { defaultProps: { disableElevation: true }, styleOverrides: { root: { borderRadius: 10 } } },
    MuiChip: { styleOverrides: { root: { fontWeight: 600 } } },
    MuiListItemButton: {
      styleOverrides: {
        root: {
          borderRadius: 10,
          '&.Mui-selected': { backgroundColor: alpha(green, 0.1), color: green },
          '&.Mui-selected .MuiListItemIcon-root': { color: green },
        },
      },
    },
    MuiTooltip: { styleOverrides: { tooltip: { fontSize: 12.5 } } },
  },
});
