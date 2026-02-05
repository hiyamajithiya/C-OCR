# C-OCR Frontend

React + TypeScript frontend for the C-OCR Document Processing Platform.

## Tech Stack

- **React 18** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **Material-UI (MUI)** - Component library
- **React Router** - Client-side routing
- **Axios** - HTTP client
- **React Dropzone** - File upload

## Prerequisites

- Node.js 18+ and npm
- Backend API running on `http://localhost:8000` (or configure `VITE_API_BASE_URL`)

## Installation

```bash
# Install dependencies
npm install
```

## Development

```bash
# Start dev server (with hot reload)
npm run dev
```

The application will be available at: http://localhost:3000

## Build

```bash
# Build for production
npm run build

# Preview production build
npm run preview
```

## Environment Variables

Create a `.env` file in the frontend directory (optional):

```env
VITE_API_BASE_URL=http://localhost:8000
```

If not set, it defaults to `http://localhost:8000`.

## Project Structure

```
frontend/
├── src/
│   ├── components/        # Reusable components
│   │   └── Layout.tsx     # Main layout with sidebar
│   ├── contexts/          # React contexts
│   │   └── AuthContext.tsx
│   ├── pages/             # Page components
│   │   ├── LoginPage.tsx
│   │   ├── DashboardPage.tsx
│   │   ├── DocumentsPage.tsx
│   │   ├── TemplatesPage.tsx
│   │   ├── APIKeysPage.tsx
│   │   ├── UsersPage.tsx
│   │   └── AuditLogsPage.tsx
│   ├── services/          # API services
│   │   └── api.ts
│   ├── App.tsx            # Root component with routing
│   ├── main.tsx           # Entry point
│   └── vite-env.d.ts      # Vite type definitions
├── index.html
├── vite.config.ts
├── tsconfig.json
└── package.json
```

## Features

### Authentication
- JWT-based authentication
- Protected routes based on user role
- Auto-redirect on session expiry

### Pages
1. **Dashboard** - Overview with stats and quick actions
2. **Documents** - Upload documents with drag-drop support
3. **Templates** - Manage extraction templates
4. **API Keys** - Create and manage API keys (Admin only)
5. **Users** - User management (Admin only)
6. **Audit Logs** - View system activity logs (Admin only)

### Role-Based Access
- **Admin** - Full access to all features
- **Operator** - Access to documents and templates
- **Reviewer** - Read-only access

## Default Credentials

See the login page for default credentials:
- **Admin**: admin@c-ocr.local / admin123
- **Operator**: operator@c-ocr.local / operator123

## API Integration

The frontend communicates with the backend API through the `apiService` class in `src/services/api.ts`.

All API calls include:
- Automatic JWT token injection
- 401 error handling (auto-logout)
- Proper error propagation

## Development Tips

1. **Hot Reload**: Vite provides instant hot module replacement (HMR)
2. **TypeScript**: Use strict mode for type safety
3. **Path Aliases**: Use `@/` prefix for absolute imports (e.g., `@/components/Layout`)
4. **Material-UI**: Follow MUI best practices for theming and styling

## Troubleshooting

### Dev server won't start
```bash
# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

### TypeScript errors
```bash
# Run type checking
npm run build
# or
npx tsc --noEmit
```

### API connection issues
- Ensure backend is running on port 8000
- Check CORS configuration in backend
- Verify network/firewall settings

## Production Deployment

1. Build the app:
   ```bash
   npm run build
   ```

2. The `dist/` folder contains the production-ready static files

3. Serve with any static file server:
   ```bash
   # Using serve
   npx serve -s dist -p 3000

   # Or nginx, Apache, etc.
   ```

4. Configure environment variables for production API URL

## License

Proprietary - C-OCR Platform
