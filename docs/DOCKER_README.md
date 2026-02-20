# AI Trading Bot - Docker/Podman Setup

## 🐳 Run Everything in Containers

Instead of running in background, you can now run the entire bot in a Docker/Podman container!

---

## 🚀 **Quick Start**

### Option 1: Simple Docker Run

```bash
# One command to run everything
./run-docker.sh
```

**What it does:**
- Builds Docker image
- Runs bot + dashboard
- Mounts logs/data volumes
- Exposes dashboard on port 8080

---

### Option 2: Docker Compose (Recommended)

```bash
# Run bot + database together
./run-compose.sh
```

**What it does:**
- Runs trading bot container
- Runs PostgreSQL container
- Networks them together
- Persistent database storage

---

## 📋 **Manual Commands**

### Build Image:

```bash
# Podman
podman build -f Dockerfile.prod -t ai-trading-bot:latest .

# Docker
docker build -f Dockerfile.prod -t ai-trading-bot:latest .
```

### Run Container:

```bash
# Podman
podman run -d \
    --name ai-trading-bot \
    -p 8080:8080 \
    -v $(pwd)/logs:/app/logs \
    -v $(pwd)/data:/app/data \
    -v $(pwd)/config:/app/config \
    --env-file .env \
    ai-trading-bot:latest

# Docker
docker run -d \
    --name ai-trading-bot \
    -p 8080:8080 \
    -v $(pwd)/logs:/app/logs \
    -v $(pwd)/data:/app/data \
    -v $(pwd)/config:/app/config \
    --env-file .env \
    ai-trading-bot:latest
```

### Docker Compose:

```bash
# Start
podman compose -f docker-compose.prod.yml up -d

# Stop
podman compose -f docker-compose.prod.yml down

# View logs
podman compose -f docker-compose.prod.yml logs -f
```

---

## 🔧 **Useful Commands**

```bash
# View running containers
podman ps

# View logs
podman logs -f ai-trading-bot

# Stop bot
podman stop ai-trading-bot

# Remove container
podman rm ai-trading-bot

# Rebuild image
podman build -f Dockerfile.prod -t ai-trading-bot:latest .

# Access container shell
podman exec -it ai-trading-bot /bin/bash
```

---

## 🌐 **Access Dashboard**

Once running:

**URL:** http://localhost:8080

Shows:
- Real-time profit
- Capital allocation
- Open positions
- Recent trades
- Win rate

---

## 📊 **Container Architecture**

```
┌─────────────────────────────────────┐
│  ai-trading-bot (Container)         │
│  ├─ Trading Bot (main.py)           │
│  └─ Web Dashboard (port 8080)       │
└─────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────┐
│  ai-trading-db (PostgreSQL)         │
│  └─ Persistent storage              │
└─────────────────────────────────────┘
```

---

## 💾 **Persistent Data**

Volumes mounted:
- `./logs` → `/app/logs` (Trading logs)
- `./data` → `/app/data` (Database files)
- `./config` → `/app/config` (Configuration)

Your data survives container restarts!

---

## ⚙️ **Environment Variables**

All from `.env` file:
- `ANTHROPIC_API_KEY` - AI API key
- `PRIMARY_API_KEY` - Binance API key
- `PRIMARY_API_SECRET` - Binance secret
- `PRIMARY_TESTNET` - true/false
- `DATABASE_URL` - Database connection
- etc.

---

## 🎯 **Advantages of Docker**

✅ **Isolation** - Clean environment, no conflicts  
✅ **Portability** - Run anywhere (Linux, Mac, Windows)  
✅ **Reproducibility** - Same environment everywhere  
✅ **Easy Deploy** - One command to start  
✅ **Auto-restart** - `--restart unless-stopped`  
✅ **Resource Control** - Limit CPU/memory if needed  

---

## 🐛 **Troubleshooting**

### Container won't start:

```bash
# Check logs
podman logs ai-trading-bot

# Remove and recreate
podman rm -f ai-trading-bot
./run-docker.sh
```

### Dashboard not accessible:

```bash
# Check if port 8080 is free
netstat -tlnp | grep 8080

# Check container is running
podman ps

# View dashboard logs
podman logs ai-trading-bot | grep "Dashboard"
```

### Database connection error:

```bash
# Restart database container
podman compose -f docker-compose.prod.yml restart postgres

# Check database is healthy
podman compose -f docker-compose.prod.yml ps
```

---

## 🚀 **Production Deployment**

For production (VPS/Cloud):

```bash
# 1. Copy files to server
scp -r ai-exp user@server:~/

# 2. SSH to server
ssh user@server

# 3. Run with compose
cd ai-exp
./run-compose.sh
```

Bot runs 24/7 with auto-restart!

---

## 📈 **Monitoring**

```bash
# Real-time logs
podman logs -f ai-trading-bot

# Resource usage
podman stats ai-trading-bot

# Dashboard
http://localhost:8080
```

---

**That's it! Run the bot in a container with one command!** 🎉
