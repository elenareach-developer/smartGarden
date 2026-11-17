import { Alert, Box, Button, CircularProgress, Skeleton, Stack } from '@mui/material';

export function Loading({ rows = 3 }: { rows?: number }) {
  return (
    <Stack spacing={2} aria-busy="true">
      {Array.from({ length: rows }).map((_, i) => <Skeleton key={i} variant="rounded" height={i === 0 ? 120 : 80} />)}
    </Stack>
  );
}

export function Spinner() {
  return <Box sx={{ display: 'grid', placeItems: 'center', py: 6 }}><CircularProgress /></Box>;
}

export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <Alert severity="error" action={onRetry && <Button color="inherit" size="small" onClick={onRetry}>Повторить</Button>}>
      {message}
    </Alert>
  );
}
