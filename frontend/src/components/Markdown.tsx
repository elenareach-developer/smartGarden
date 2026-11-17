import { Box } from '@mui/material';
import ReactMarkdown from 'react-markdown';

export function Markdown({ children }: { children: string }) {
  return (
    <Box sx={{
      '& h2': { fontSize: 18, fontWeight: 750, mt: 0, mb: 1 },
      '& h3': { fontSize: 15, fontWeight: 700, mt: 2, mb: 0.5, color: 'primary.dark' },
      '& p, & li': { fontSize: 14.5, lineHeight: 1.6 },
      '& ul, & ol': { pl: 2.5, my: 0.5 },
      '& blockquote': { m: 0, my: 1, px: 1.5, py: 1, bgcolor: '#fff7e8', borderLeft: '3px solid', borderColor: 'warning.main', borderRadius: 1 },
      '& blockquote p': { m: 0 },
      '& code': { fontSize: 12.5, bgcolor: '#eef1ec', px: 0.5, borderRadius: 0.5 },
    }}>
      <ReactMarkdown>{children}</ReactMarkdown>
    </Box>
  );
}
