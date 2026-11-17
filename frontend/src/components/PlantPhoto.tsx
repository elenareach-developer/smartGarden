import { Box, Chip } from '@mui/material';

export function isIllustration(url?: string | null) {
  return !url || url.startsWith('/photos/');
}

export function PlantPhoto({ url, name, height = 180, rounded = true, showBadge = false }:
  { url: string | null; name: string; height?: number | string; rounded?: boolean; showBadge?: boolean }) {
  return (
    <Box sx={{ position: 'relative', height, overflow: 'hidden', borderRadius: rounded ? 3 : 0, bgcolor: '#e8efe6' }}>
      <Box component="img" src={url || '/photos/placeholder.svg'} alt={`Орхидея ${name}`}
        sx={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }} />
      {showBadge && isIllustration(url) && (
        <Chip size="small" label="Иллюстрация" sx={{ position: 'absolute', left: 8, bottom: 8, bgcolor: 'rgba(255,255,255,.85)' }} />
      )}
    </Box>
  );
}
