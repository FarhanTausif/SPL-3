# DeHalu Frontend - Phase 1 MVP

Real-time hallucination detection and mitigation visualization for AI-generated code.

## 🚀 Features

### ✅ Phase 1 MVP Implementation

- **Input Wizard** - User-friendly form to submit code generation prompts
- **Real-time Polling** - 2-second poll intervals for live status updates
- **Live Monitoring** - Visual display of verification pipeline progress
- **Results Display** - Code verdicts with confidence scores and evidence
- **Responsive Design** - Works on mobile, tablet, and desktop
- **Error Handling** - Comprehensive error messages and recovery

### Architecture

```
Input Prompt
  ↓
[Verification Form] → Submit to Backend
  ↓
[Live Monitor] ← Real-time polling every 2s
  ↓
[Results Display] ← Show verdict & evidence
```

## 📦 Tech Stack

- **Framework**: Next.js 14+ (App Router)
- **Language**: TypeScript (strict)
- **Styling**: Tailwind CSS
- **State**: Zustand (local) + TanStack Query (server)
- **UI**: Lucide icons
- **HTTP**: Axios

## 🏗️ Project Structure

```
frontend/
├── app/                          # Next.js App Router pages
│   ├── page.tsx                 # Home/Dashboard
│   ├── monitor/[id]/page.tsx    # Live monitoring page
│   ├── layout.tsx               # Root layout with providers
│   └── globals.css              # Global styles
├── components/                   # React components
│   ├── VerificationForm.tsx     # Input wizard form
│   ├── LiveMonitor.tsx          # Status display during verification
│   └── ResultsDisplay.tsx       # Results after completion
├── hooks/                        # Custom React hooks
│   └── useRunStatus.ts          # Polling and data fetching hooks
├── lib/                          # Utilities and helpers
│   └── api.ts                   # Backend API client
├── stores/                       # State management
│   └── runStore.ts              # Zustand run state store
├── package.json                 # Dependencies
├── tsconfig.json               # TypeScript config
├── tailwind.config.ts          # Tailwind configuration
├── .env.local                  # Environment variables
└── README.md                   # This file
```

## 🔧 Setup & Development

### Prerequisites

- Node.js 18+
- npm or yarn

### Installation

```bash
cd frontend
npm install
```

### Configuration

Create `.env.local`:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Development Server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Build for Production

```bash
npm run build
npm run start
```

## 🔌 API Integration

### Endpoints Used

The frontend communicates with the backend via 5 REST endpoints:

1. **POST /v1/runs** - Create new verification run
   ```typescript
   {
     prompt: string
     language: string
     risk_level?: 'low' | 'medium' | 'high'
     max_retries?: number
   }
   ```

2. **GET /v1/runs/{run_id}** - Poll run status (every 2 seconds)
   ```typescript
   {
     run_id: string
     status: 'queued' | 'started' | 'completed' | 'failed'
     created_at: string
     updated_at: string
     hallucination_detected?: boolean
     confidence?: number
     generated_code?: string
   }
   ```

3. **GET /v1/runs/{run_id}/evidence** - Get verification evidence
   ```typescript
   [
     {
       id: string
       evidence_kind: 'claims' | 'static' | 'sandbox' | 'judge' | 'cove' | 'policy'
       finding: string
       severity?: string
       timestamp: string
     }
   ]
   ```

4. **GET /v1/runs/{run_id}/events** - Get audit trail

5. **GET /health** - Check backend health

### Backend Requirements

- Backend must be running on `localhost:8000`
- Ensure all 5 API endpoints are implemented
- Database persistence working
- CORS enabled for `localhost:3000`

## 🎨 UI Components

### VerificationForm

Input wizard for users to submit code generation requests.

**Props**: None (uses Zustand store)

**Features**:
- Prompt textarea with character counter
- Language selector (Python, JS, TS, Java, C++, C#, Go, Rust)
- Risk level selection (Low/Medium/High)
- Form validation
- Loading state during submission

### LiveMonitor

Real-time status display during verification.

**Props**:
- `runId: string` - The verification run ID

**Features**:
- Polling hook (2-second intervals)
- Progress visualization of pipeline stages
- Animated loading indicators
- Error messages
- Timestamps

### ResultsDisplay

Shows verification results after completion.

**Props**: None (uses Zustand store)

**Features**:
- Hallucination verdict with icon
- Confidence score and progress bar
- Generated code display with copy button
- Evidence summary
- Timestamps

## 🔄 Data Flow

1. **User submits form** → `VerificationForm.handleSubmit()`
2. **API call** → `runApi.createRun()` → Backend POST /v1/runs
3. **Run ID received** → Store in Zustand + Navigate to /monitor/{id}
4. **Start polling** → `useRunStatus()` hook polls every 2s
5. **Status updates** → Update Zustand store + Re-render
6. **Run complete** → Stop polling + Show `ResultsDisplay`
7. **Fetch evidence** → `useRunEvidence()` hook fetches details
8. **Display results** → Show verdict + code + evidence

## 🎯 Polling Strategy

- **Interval**: 2 seconds (configurable in `useRunStatus`)
- **Retry**: 3 attempts on failure
- **Backoff**: Exponential backoff up to 30 seconds
- **Stale Time**: 1 second
- **Stop Condition**: When `status === 'completed'` or `'failed'`

## 🧪 Testing (Phase 2+)

Tests will be added in Phase 2:

```bash
npm run test           # Unit tests (Vitest)
npm run test:e2e       # E2E tests (Cypress)
```

## 🚢 Deployment

### Docker

```bash
docker build -t dehalu-frontend .
docker run -p 3000:3000 -e NEXT_PUBLIC_API_URL=http://backend:8000 dehalu-frontend
```

### Vercel

```bash
npm i -g vercel
vercel
```

Set environment variable `NEXT_PUBLIC_API_URL` in Vercel dashboard.

## 🐛 Troubleshooting

### "Cannot connect to backend"

- Ensure backend is running on `localhost:8000`
- Check `NEXT_PUBLIC_API_URL` in `.env.local`
- Verify CORS is enabled in backend

### "Run ID not found"

- Check backend database
- Verify run was created successfully
- Check browser console for errors

### Polling not updating

- Check network tab in DevTools
- Verify 2s interval polling requests
- Check backend responses

## 📚 Phase Roadmap

### ✅ Phase 1: MVP (Current)
- Input wizard
- Polling infrastructure
- Basic monitoring
- Results display
- Responsive design (basic)

### 🚀 Phase 2: Premium Visualization
- React Flow DAG visualization
- Animated agent state transitions
- Hallucination risk gauge
- Evidence panel with expansion
- Glassmorphism design enhancements

### 🎯 Phase 3: Polish & Testing
- Mobile optimization
- Accessibility (WCAG 2.1 AA)
- Component Storybook
- Unit tests
- E2E tests
- Performance optimization

### 🌟 Phase 4-5: Future Enhancements
- WebSocket real-time updates
- Agent details modals
- History & favorites
- Dark mode
- Advanced analytics
- Export reports

## 📝 Contributing

When adding features:

1. Create components in `components/`
2. Create hooks in `hooks/`
3. Follow TypeScript strict mode
4. Use Zustand for state
5. Use TanStack Query for server state
6. Add Tailwind classes for styling

## 📄 License

MIT

## 🎉 Status

**MVP Phase 1**: ✅ Complete and ready for backend integration

**Next Steps**:
1. Ensure backend is running
2. Test API endpoints
3. Run `npm run dev`
4. Open http://localhost:3000
5. Test end-to-end workflow
