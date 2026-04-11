/**
 * Reusable stats card component for dashboard metrics.
 */

import React from 'react';
import { Box, Typography, alpha } from '@mui/material';
import { TrendingUp, TrendingDown } from '@mui/icons-material';
import { colors } from '@/theme/theme';

interface StatsCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ReactNode;
  trend?: {
    value: number;
    isPositive: boolean;
  };
  color?: 'primary' | 'secondary' | 'success' | 'warning' | 'error';
  onClick?: () => void;
}

const colorMap = {
  primary: colors.primary.main,
  secondary: colors.secondary.main,
  success: colors.success.main,
  warning: colors.warning.main,
  error: colors.error.main,
};

const StatsCard: React.FC<StatsCardProps> = ({
  title,
  value,
  subtitle,
  icon,
  trend,
  color = 'primary',
  onClick,
}) => {
  const accentColor = colorMap[color];

  return (
    <Box
      onClick={onClick}
      sx={{
        width: '100%',
        minHeight: 176,
        p: 3,
        borderRadius: 3,
        bgcolor: 'background.paper',
        border: `1px solid ${alpha(accentColor, 0.2)}`,
        cursor: onClick ? 'pointer' : 'default',
        transition: 'all 0.3s ease',
        position: 'relative',
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
        '&:hover': onClick
          ? {
              transform: 'translateY(-4px)',
              borderColor: alpha(accentColor, 0.4),
              boxShadow: `0 12px 40px ${alpha(accentColor, 0.2)}`,
            }
          : {},
        '&::before': {
          content: '""',
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          height: 4,
          background: `linear-gradient(90deg, ${accentColor} 0%, ${alpha(accentColor, 0.5)} 100%)`,
        },
      }}
    >
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
        <Box
          sx={{
            width: 48,
            height: 48,
            borderRadius: 2,
            bgcolor: alpha(accentColor, 0.15),
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: accentColor,
          }}
        >
          {icon}
        </Box>
        {trend && (
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              gap: 0.5,
              px: 1,
              py: 0.5,
              borderRadius: 1,
              bgcolor: alpha(trend.isPositive ? colors.success.main : colors.error.main, 0.1),
              color: trend.isPositive ? colors.success.main : colors.error.main,
            }}
          >
            {trend.isPositive ? (
              <TrendingUp sx={{ fontSize: 16 }} />
            ) : (
              <TrendingDown sx={{ fontSize: 16 }} />
            )}
            <Typography variant="caption" sx={{ fontWeight: 600 }}>
              {trend.value}%
            </Typography>
          </Box>
        )}
      </Box>

      <Typography variant="h4" sx={{ fontWeight: 700, mb: 0.5, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
        {value}
      </Typography>
      <Typography variant="body2" sx={{ color: 'text.secondary', fontWeight: 500, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
        {title}
      </Typography>
      {subtitle && (
        <Typography variant="caption" sx={{ color: 'text.disabled', mt: 1, display: 'block' }}>
          {subtitle}
        </Typography>
      )}
    </Box>
  );
};

export default StatsCard;
