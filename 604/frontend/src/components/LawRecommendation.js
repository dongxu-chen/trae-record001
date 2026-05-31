import React from 'react';
import {
  Paper,
  Typography,
  Box,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
  Chip,
} from '@mui/material';
import GavelIcon from '@mui/icons-material/Gavel';

function LawRecommendation({ laws }) {
  if (!laws || laws.length === 0) return null;

  const getRelevanceColor = (relevance) => {
    if (relevance >= 0.6) return 'success';
    if (relevance >= 0.4) return 'primary';
    return 'default';
  };

  return (
    <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
      <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <GavelIcon color="secondary" />
        法条推荐
      </Typography>
      <List>
        {laws.map((law, index) => (
          <React.Fragment key={index}>
            {index > 0 && <Divider variant="inset" />}
            <ListItem alignItems="flex-start">
              <ListItemIcon>
                <Chip
                  label={`相关度 ${(law.relevance * 100).toFixed(0)}%
                  size="small"
                  color={getRelevanceColor(law.relevance)}
                />
              </ListItemIcon>
              <ListItemText
                  primary={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography variant="subtitle1" fontWeight="medium">
                        {law.law_id}
                      </Typography>
                    </Box>
                  }
                  secondary={
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                      {law.content}
                    </Typography>
                  }
                />
              </ListItem>
            </React.Fragment>
          ))}
        </List>
    </Paper>
  );
}

export default LawRecommendation;
