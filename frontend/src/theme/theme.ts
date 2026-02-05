/**
 * C-OCR Dark Theme Configuration
 * Modern, professional dark theme with vibrant accents
 */

import { createTheme, alpha } from '@mui/material/styles';

// Color palette
const colors = {
  // Primary backgrounds
  background: {
    default: '#0a1929',
    paper: '#0d2137',
    card: '#132f4c',
    elevated: '#173a5e',
  },
  // Primary brand colors
  primary: {
    main: '#5c9ce6',
    light: '#7eb8ff',
    dark: '#3d7cc4',
    contrastText: '#ffffff',
  },
  // Secondary accent (teal)
  secondary: {
    main: '#00d4aa',
    light: '#5fffdc',
    dark: '#00a17b',
    contrastText: '#000000',
  },
  // Status colors
  success: {
    main: '#2dd36f',
    light: '#6ff79e',
    dark: '#00a042',
  },
  warning: {
    main: '#ffc409',
    light: '#ffd74a',
    dark: '#c79400',
  },
  error: {
    main: '#ff4961',
    light: '#ff7b8f',
    dark: '#c50036',
  },
  info: {
    main: '#5c9ce6',
    light: '#8cc4ff',
    dark: '#2176d2',
  },
  // Text colors
  text: {
    primary: '#ffffff',
    secondary: 'rgba(255, 255, 255, 0.7)',
    disabled: 'rgba(255, 255, 255, 0.4)',
  },
  // Divider
  divider: 'rgba(255, 255, 255, 0.12)',
  // Action colors
  action: {
    active: 'rgba(255, 255, 255, 0.7)',
    hover: 'rgba(255, 255, 255, 0.08)',
    selected: 'rgba(92, 156, 230, 0.16)',
    disabled: 'rgba(255, 255, 255, 0.26)',
    disabledBackground: 'rgba(255, 255, 255, 0.12)',
  },
};

// Create the theme
const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: colors.primary,
    secondary: colors.secondary,
    success: colors.success,
    warning: colors.warning,
    error: colors.error,
    info: colors.info,
    background: {
      default: colors.background.default,
      paper: colors.background.paper,
    },
    text: colors.text,
    divider: colors.divider,
    action: colors.action,
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    h1: {
      fontSize: '2.5rem',
      fontWeight: 700,
      letterSpacing: '-0.02em',
    },
    h2: {
      fontSize: '2rem',
      fontWeight: 600,
      letterSpacing: '-0.01em',
    },
    h3: {
      fontSize: '1.75rem',
      fontWeight: 600,
    },
    h4: {
      fontSize: '1.5rem',
      fontWeight: 600,
    },
    h5: {
      fontSize: '1.25rem',
      fontWeight: 600,
    },
    h6: {
      fontSize: '1rem',
      fontWeight: 600,
    },
    subtitle1: {
      fontSize: '1rem',
      fontWeight: 500,
    },
    subtitle2: {
      fontSize: '0.875rem',
      fontWeight: 500,
    },
    body1: {
      fontSize: '1rem',
      lineHeight: 1.6,
    },
    body2: {
      fontSize: '0.875rem',
      lineHeight: 1.6,
    },
    button: {
      fontWeight: 600,
      textTransform: 'none',
    },
  },
  shape: {
    borderRadius: 12,
  },
  shadows: [
    'none',
    '0px 2px 4px rgba(0, 0, 0, 0.3)',
    '0px 4px 8px rgba(0, 0, 0, 0.3)',
    '0px 6px 12px rgba(0, 0, 0, 0.3)',
    '0px 8px 16px rgba(0, 0, 0, 0.3)',
    '0px 10px 20px rgba(0, 0, 0, 0.3)',
    '0px 12px 24px rgba(0, 0, 0, 0.3)',
    '0px 14px 28px rgba(0, 0, 0, 0.3)',
    '0px 16px 32px rgba(0, 0, 0, 0.3)',
    '0px 18px 36px rgba(0, 0, 0, 0.3)',
    '0px 20px 40px rgba(0, 0, 0, 0.3)',
    '0px 22px 44px rgba(0, 0, 0, 0.3)',
    '0px 24px 48px rgba(0, 0, 0, 0.3)',
    '0px 26px 52px rgba(0, 0, 0, 0.3)',
    '0px 28px 56px rgba(0, 0, 0, 0.3)',
    '0px 30px 60px rgba(0, 0, 0, 0.3)',
    '0px 32px 64px rgba(0, 0, 0, 0.3)',
    '0px 34px 68px rgba(0, 0, 0, 0.3)',
    '0px 36px 72px rgba(0, 0, 0, 0.3)',
    '0px 38px 76px rgba(0, 0, 0, 0.3)',
    '0px 40px 80px rgba(0, 0, 0, 0.3)',
    '0px 42px 84px rgba(0, 0, 0, 0.3)',
    '0px 44px 88px rgba(0, 0, 0, 0.3)',
    '0px 46px 92px rgba(0, 0, 0, 0.3)',
    '0px 48px 96px rgba(0, 0, 0, 0.3)',
  ],
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          scrollbarColor: `${colors.primary.main} ${colors.background.paper}`,
          '&::-webkit-scrollbar, & *::-webkit-scrollbar': {
            width: 8,
            height: 8,
          },
          '&::-webkit-scrollbar-track, & *::-webkit-scrollbar-track': {
            background: colors.background.paper,
          },
          '&::-webkit-scrollbar-thumb, & *::-webkit-scrollbar-thumb': {
            backgroundColor: colors.background.elevated,
            borderRadius: 4,
          },
          '&::-webkit-scrollbar-thumb:hover, & *::-webkit-scrollbar-thumb:hover': {
            backgroundColor: colors.primary.dark,
          },
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          padding: '10px 20px',
          fontWeight: 600,
          boxShadow: 'none',
          '&:hover': {
            boxShadow: 'none',
          },
        },
        contained: {
          background: `linear-gradient(135deg, ${colors.primary.main} 0%, ${colors.primary.dark} 100%)`,
          '&:hover': {
            background: `linear-gradient(135deg, ${colors.primary.light} 0%, ${colors.primary.main} 100%)`,
          },
        },
        containedSecondary: {
          background: `linear-gradient(135deg, ${colors.secondary.main} 0%, ${colors.secondary.dark} 100%)`,
          '&:hover': {
            background: `linear-gradient(135deg, ${colors.secondary.light} 0%, ${colors.secondary.main} 100%)`,
          },
        },
        outlined: {
          borderWidth: 2,
          '&:hover': {
            borderWidth: 2,
            backgroundColor: alpha(colors.primary.main, 0.08),
          },
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          backgroundColor: colors.background.card,
          backgroundImage: 'none',
          borderRadius: 16,
          border: `1px solid ${alpha(colors.primary.main, 0.1)}`,
          transition: 'transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease',
          '&:hover': {
            borderColor: alpha(colors.primary.main, 0.3),
            boxShadow: `0 8px 32px ${alpha(colors.primary.main, 0.15)}`,
          },
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
        },
        elevation1: {
          boxShadow: `0 4px 20px ${alpha('#000', 0.25)}`,
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            backgroundColor: alpha(colors.background.default, 0.5),
            '&:hover .MuiOutlinedInput-notchedOutline': {
              borderColor: colors.primary.main,
            },
            '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
              borderColor: colors.primary.main,
              boxShadow: `0 0 0 3px ${alpha(colors.primary.main, 0.2)}`,
            },
          },
        },
      },
    },
    MuiOutlinedInput: {
      styleOverrides: {
        root: {
          borderRadius: 10,
          '& .MuiOutlinedInput-notchedOutline': {
            borderColor: alpha(colors.text.primary, 0.2),
          },
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          fontWeight: 500,
        },
        colorPrimary: {
          backgroundColor: alpha(colors.primary.main, 0.15),
          color: colors.primary.light,
        },
        colorSecondary: {
          backgroundColor: alpha(colors.secondary.main, 0.15),
          color: colors.secondary.light,
        },
        colorSuccess: {
          backgroundColor: alpha(colors.success.main, 0.15),
          color: colors.success.light,
        },
        colorWarning: {
          backgroundColor: alpha(colors.warning.main, 0.15),
          color: colors.warning.light,
        },
        colorError: {
          backgroundColor: alpha(colors.error.main, 0.15),
          color: colors.error.light,
        },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        root: {
          borderColor: alpha(colors.text.primary, 0.08),
        },
        head: {
          fontWeight: 600,
          backgroundColor: colors.background.card,
          color: colors.text.secondary,
          textTransform: 'uppercase',
          fontSize: '0.75rem',
          letterSpacing: '0.05em',
        },
      },
    },
    MuiTableRow: {
      styleOverrides: {
        root: {
          '&:hover': {
            backgroundColor: alpha(colors.primary.main, 0.04),
          },
        },
      },
    },
    MuiDialog: {
      styleOverrides: {
        paper: {
          backgroundColor: colors.background.card,
          borderRadius: 16,
          border: `1px solid ${alpha(colors.primary.main, 0.1)}`,
        },
      },
    },
    MuiDialogTitle: {
      styleOverrides: {
        root: {
          fontWeight: 600,
        },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: {
          backgroundColor: colors.background.paper,
          borderRight: `1px solid ${alpha(colors.text.primary, 0.08)}`,
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundColor: colors.background.paper,
          backgroundImage: 'none',
          borderBottom: `1px solid ${alpha(colors.text.primary, 0.08)}`,
          boxShadow: 'none',
        },
      },
    },
    MuiListItemButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          margin: '4px 8px',
          '&.Mui-selected': {
            backgroundColor: alpha(colors.primary.main, 0.15),
            '&:hover': {
              backgroundColor: alpha(colors.primary.main, 0.2),
            },
            '&::before': {
              content: '""',
              position: 'absolute',
              left: 0,
              top: '50%',
              transform: 'translateY(-50%)',
              width: 4,
              height: '60%',
              backgroundColor: colors.primary.main,
              borderRadius: '0 4px 4px 0',
            },
          },
          '&:hover': {
            backgroundColor: alpha(colors.text.primary, 0.05),
          },
        },
      },
    },
    MuiAlert: {
      styleOverrides: {
        root: {
          borderRadius: 10,
        },
        standardSuccess: {
          backgroundColor: alpha(colors.success.main, 0.15),
          color: colors.success.light,
        },
        standardError: {
          backgroundColor: alpha(colors.error.main, 0.15),
          color: colors.error.light,
        },
        standardWarning: {
          backgroundColor: alpha(colors.warning.main, 0.15),
          color: colors.warning.light,
        },
        standardInfo: {
          backgroundColor: alpha(colors.info.main, 0.15),
          color: colors.info.light,
        },
      },
    },
    MuiTooltip: {
      styleOverrides: {
        tooltip: {
          backgroundColor: colors.background.elevated,
          fontSize: '0.8rem',
          borderRadius: 8,
          padding: '8px 12px',
        },
      },
    },
    MuiLinearProgress: {
      styleOverrides: {
        root: {
          borderRadius: 4,
          backgroundColor: alpha(colors.primary.main, 0.15),
        },
      },
    },
    MuiCircularProgress: {
      styleOverrides: {
        root: {
          color: colors.primary.main,
        },
      },
    },
    MuiTab: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          fontWeight: 500,
          '&.Mui-selected': {
            color: colors.primary.light,
          },
        },
      },
    },
    MuiTabs: {
      styleOverrides: {
        indicator: {
          backgroundColor: colors.primary.main,
          height: 3,
          borderRadius: '3px 3px 0 0',
        },
      },
    },
  },
});

// Export theme colors for use in custom components
export { colors };
export default theme;
