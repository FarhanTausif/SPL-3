# Frontend Phase 1 - Deployment Guide

## 🚀 Local Development

### Quick Start

```bash
# Clone/navigate to project
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev

# Open browser
# http://localhost:3000
```

### Environment Variables

Create `.env.local`:

```bash
# Backend API URL
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 🏗️ Production Build

### Build

```bash
npm run build
```

Output: `.next/` directory (optimized for production)

### Start Production Server

```bash
npm run start
```

Runs on default port 3000.

## 🐳 Docker Deployment

### Dockerfile

Create `frontend/Dockerfile`:

```dockerfile
FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy source code
COPY . .

# Build Next.js
RUN npm run build

# Expose port
EXPOSE 3000

# Start server
CMD ["npm", "start"]
```

### Build Docker Image

```bash
cd frontend
docker build -t dehalu-frontend:latest .
```

### Run Docker Container

```bash
docker run -p 3000:3000 \
  -e NEXT_PUBLIC_API_URL=http://backend:8000 \
  dehalu-frontend:latest
```

### Docker Compose

Create `docker-compose.yml` (root directory):

```yaml
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DEHALU_DATABASE_URL=postgresql+psycopg://user:pass@db:5432/dehalu
      - DEHALU_GEMINI_API_KEY=${GEMINI_API_KEY}
    depends_on:
      - db

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8000
    depends_on:
      - backend

  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=dehalu
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

Start with:

```bash
docker-compose up
```

## ☁️ Vercel Deployment

### Prerequisites

- GitHub account with repository
- Vercel account (sign up at https://vercel.com)

### 1. Push to GitHub

```bash
git add .
git commit -m "Frontend Phase 1 MVP ready for deployment"
git push origin main
```

### 2. Connect to Vercel

```bash
npm i -g vercel
cd frontend
vercel
```

### 3. Configure Environment

In Vercel Dashboard:

1. Go to Settings → Environment Variables
2. Add `NEXT_PUBLIC_API_URL`
3. Set value based on backend location:
   - Development: `http://localhost:8000`
   - Production: `https://api.example.com` (backend URL)

### 4. Deploy

```bash
vercel deploy --prod
```

Or trigger automatic deployment on GitHub push (recommended).

### Vercel Configuration

Create `vercel.json`:

```json
{
  "buildCommand": "npm run build",
  "devCommand": "npm run dev",
  "installCommand": "npm install",
  "framework": "nextjs"
}
```

## 🌍 AWS Deployment

### Option 1: AWS Amplify

```bash
npm install -g @aws-amplify/cli
amplify init
amplify add hosting
amplify publish
```

### Option 2: EC2 + nginx

```bash
# On EC2 instance
sudo apt update && sudo apt install nodejs npm nginx

# Clone repo
git clone <repo-url>
cd frontend

# Install and build
npm install
npm run build

# Configure nginx
sudo cat > /etc/nginx/sites-available/dehalu <<EOF
server {
    listen 80;
    server_name _;
    
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
    }
}
EOF

# Enable and start
sudo ln -s /etc/nginx/sites-available/dehalu /etc/nginx/sites-enabled/
sudo systemctl start nginx

# Start Next.js (use PM2 for production)
npm install -g pm2
pm2 start "npm start" --name dehalu-frontend
pm2 startup
```

## 🔒 SSL/HTTPS Setup

### Let's Encrypt (Free)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d example.com
```

### Nginx Configuration with SSL

```nginx
server {
    listen 443 ssl http2;
    server_name example.com;
    
    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;
    
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name example.com;
    return 301 https://$server_name$request_uri;
}
```

## 📊 Performance Optimization

### Next.js Optimization

Already included in Phase 1:

```typescript
// Automatic image optimization
// Code splitting per route
// CSS extraction
// Automatic minification
// Static generation where possible
```

### Additional Optimizations (Phase 2+)

```typescript
// Add Image optimization
import Image from 'next/image'

// Add dynamic imports
import dynamic from 'next/dynamic'
const HeavyComponent = dynamic(() => import('...'))

// Configure caching
// Cache-Control headers in next.config.js
```

## 🔍 Monitoring & Logging

### Vercel Analytics

Automatically included in Vercel deployment.

View at: https://vercel.com/dashboard

### Custom Logging

```typescript
// log/logger.ts
export const log = {
  error: (msg: string, err?: unknown) => console.error(`[ERROR] ${msg}`, err),
  warn: (msg: string) => console.warn(`[WARN] ${msg}`),
  info: (msg: string) => console.log(`[INFO] ${msg}`),
}
```

### Error Tracking (Optional)

```bash
npm install @sentry/nextjs
```

In `next.config.js`:

```javascript
import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.SENTRY_DSN,
  tracesSampleRate: 1,
});
```

## 🔄 CI/CD Pipeline

### GitHub Actions Workflow

Create `.github/workflows/frontend-deploy.yml`:

```yaml
name: Frontend Deploy

on:
  push:
    branches: [main]
    paths:
      - 'frontend/**'
      - '.github/workflows/frontend-deploy.yml'

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
          cache: 'npm'
          cache-dependency-path: 'frontend/package-lock.json'
      
      - run: cd frontend && npm ci
      
      - run: cd frontend && npm run lint
      
      - run: cd frontend && npm run build
      
      - name: Deploy to Vercel
        env:
          VERCEL_TOKEN: ${{ secrets.VERCEL_TOKEN }}
          VERCEL_PROJECT_ID: ${{ secrets.VERCEL_PROJECT_ID }}
          VERCEL_ORG_ID: ${{ secrets.VERCEL_ORG_ID }}
        run: |
          cd frontend
          npx vercel deploy --prod --token=$VERCEL_TOKEN
```

## 📈 Scaling Considerations

### For Phase 2-3:

- Add caching layers
- Implement service worker for offline
- Use CDN for static assets
- Database connection pooling (backend)
- Load balancing for backend

### Recommended Architecture:

```
User → CDN (CloudFlare) → Load Balancer (AWS/GCP)
  ├─ Frontend (Vercel/Docker) ×N
  └─ Backend (FastAPI) ×N → Database (PostgreSQL)
```

## 🚀 Health Check

After deployment, verify:

```bash
# Frontend loads
curl http://localhost:3000

# API connectivity
curl http://localhost:3000/api/health (if implemented)

# Backend communication
curl $NEXT_PUBLIC_API_URL/health
```

## 🎯 Deployment Checklist

- [ ] `.env.local` configured
- [ ] `npm run build` succeeds
- [ ] No console errors
- [ ] API endpoints verified
- [ ] CORS configured in backend
- [ ] SSL/HTTPS working (production)
- [ ] Environment variables set
- [ ] Database connected
- [ ] Monitoring configured
- [ ] Backups enabled
- [ ] DNS configured (if custom domain)

## 📞 Troubleshooting

### "Build fails with TypeScript errors"
```bash
npm run lint
# Fix errors before build
```

### "API returns 404"
```bash
# Verify NEXT_PUBLIC_API_URL
# Check backend is running
# Test with curl
curl $NEXT_PUBLIC_API_URL/health
```

### "High latency on API calls"
```
1. Check network throttling
2. Enable compression in nginx
3. Add caching headers
4. Consider edge locations
```

### "Out of memory during build"
```bash
# Increase Node memory
NODE_OPTIONS=--max-old-space-size=4096 npm run build
```

## 📚 Resources

- [Next.js Deployment](https://nextjs.org/docs/deployment/static-exports)
- [Vercel Documentation](https://vercel.com/docs)
- [AWS Amplify](https://docs.amplify.aws)
- [Docker Documentation](https://docs.docker.com)
- [nginx Documentation](https://nginx.org/en/docs)

## ✅ Next Steps

After Phase 1 deployment:

1. **Monitor** - Set up error tracking and analytics
2. **Test** - Run end-to-end tests with real traffic
3. **Optimize** - Profile and optimize performance
4. **Scale** - Add caching and CDN if needed
5. **Phase 2** - Add React Flow visualization

---

**Status**: Phase 1 Deployment Guide Ready ✅
