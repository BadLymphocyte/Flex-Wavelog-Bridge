# Deploying Flex-Wavelog Bridge via Portainer Stacks

## Method 1: Using Portainer with Git Repository (Recommended)

### Step 1: Create a Git Repository
1. Create a new repository on GitHub/GitLab
2. Add these files to the repository:
   - `flex_radio_monitor.py`
   - `Dockerfile`
   - `docker-compose.yml`

### Step 2: Deploy in Portainer
1. Go to **Portainer** → **Stacks** → **Add stack**
2. Name: `flex-wavelog-bridge`
3. Build method: **Repository**
4. Repository URL: `https://github.com/yourusername/flex-wavelog-bridge`
5. Compose path: `docker-compose.yml`
6. Click **Deploy the stack**

### Step 3: Create Config File
After deployment, you need to create the config file manually:

```bash
# SSH into your Docker host
ssh user@your-docker-host

# Navigate to the stack's volume
cd /var/lib/docker/volumes/flex-wavelog-bridge_config/_data

# Create config.json
nano config.json
```

Paste this content:
```json
{
    "flex": {
        "ip": "192.168.25.179",
        "port": 4992
    },
    "wavelog": {
        "url": "http://wavelog:8086",
        "api_key": "YOUR_API_KEY_HERE",
        "radio_id": "1"
    }
}
```

Save and restart the stack in Portainer.

---

## Method 2: Custom Template (Easiest)

### Step 1: Create Custom Template in Portainer
1. Go to **Portainer** → **App Templates** → **Custom Templates**
2. Click **Add Custom Template**
3. Fill in the details:

**Title:** Flex Radio to Wavelog Bridge

**Description:** Bridges Flex Radio to Wavelog, pushing frequency and mode changes

**Platform:** Linux

**Type:** Stack (Compose)

**Template:**
```yaml
version: '3.8'

services:
  flex-wavelog-bridge:
    image: flex-wavelog-bridge:latest
    build:
      context: .
      dockerfile: Dockerfile
    container_name: flex-wavelog-bridge
    volumes:
      - config:/config
      - logs:/logs
    restart: unless-stopped
    environment:
      - CONFIG_FILE=/config/config.json
      - LOG_DIR=/logs
    networks:
      - nginx-proxy-manager-network

volumes:
  config:
  logs:

networks:
  nginx-proxy-manager-network:
    external: true
```

However, **this won't work** because Portainer can't build from inline Dockerfiles in templates.

---

## Method 3: Pre-built Image (Best for Portainer)

### Step 1: Build and Push to Docker Hub
On your local machine or Docker host:

```bash
# Build the image
docker build -t yourusername/flex-wavelog-bridge:latest .

# Login to Docker Hub
docker login

# Push to Docker Hub
docker push yourusername/flex-wavelog-bridge:latest
```

### Step 2: Modified Stack for Portainer

Use this stack definition in Portainer:

```yaml
version: '3.8'

services:
  flex-wavelog-bridge:
    image: yourusername/flex-wavelog-bridge:latest
    container_name: flex-wavelog-bridge
    volumes:
      - ./config:/config
      - ./logs:/logs
    restart: unless-stopped
    environment:
      - CONFIG_FILE=/config/config.json
      - LOG_DIR=/logs
    networks:
      - nginx-proxy-manager-network

networks:
  nginx-proxy-manager-network:
    external: true
```

### Step 3: Deploy in Portainer
1. Go to **Stacks** → **Add stack**
2. Name: `flex-wavelog-bridge`
3. Build method: **Web editor**
4. Paste the stack definition above
5. Click **Deploy the stack**

### Step 4: Add Config File
Create `config.json` in the mounted volume as shown in Method 1.

---

## Method 4: Direct Stack Deployment (Simplest)

### Step 1: Prepare Files on Docker Host
SSH into your Docker host and create the structure:

```bash
mkdir -p /opt/stacks/flex-wavelog-bridge/{config,logs}
cd /opt/stacks/flex-wavelog-bridge

# Create the Python script
nano flex_radio_monitor.py
# (paste the script content)

# Create Dockerfile
nano Dockerfile
# (paste Dockerfile content)

# Create config
nano config/config.json
# (paste your config)
```

### Step 2: Create Stack in Portainer
1. Go to **Portainer** → **Stacks** → **Add stack**
2. Name: `flex-wavelog-bridge`
3. Build method: **Web editor**
4. Paste this:

```yaml
version: '3.8'

services:
  flex-wavelog-bridge:
    build:
      context: /opt/stacks/flex-wavelog-bridge
      dockerfile: Dockerfile
    container_name: flex-wavelog-bridge
    volumes:
      - /opt/stacks/flex-wavelog-bridge/config:/config
      - /opt/stacks/flex-wavelog-bridge/logs:/logs
    restart: unless-stopped
    environment:
      - CONFIG_FILE=/config/config.json
      - LOG_DIR=/logs
    networks:
      - nginx-proxy-manager-network

networks:
  nginx-proxy-manager-network:
    external: true
```

5. Click **Deploy the stack**

---

## Recommended Approach for Portainer

I recommend **Method 4** (Direct Stack Deployment) because:
- ✓ Works entirely within Portainer
- ✓ No need for Docker Hub
- ✓ Easy to manage files
- ✓ Full control over configuration

## Managing the Stack in Portainer

### View Logs
1. Go to **Stacks** → `flex-wavelog-bridge`
2. Click on the container name
3. Click **Logs**

Or use the log file:
```bash
tail -f /opt/stacks/flex-wavelog-bridge/logs/flex_wavelog_bridge.log
```

### Update Configuration
1. SSH to Docker host
2. Edit `/opt/stacks/flex-wavelog-bridge/config/config.json`
3. In Portainer: **Stacks** → `flex-wavelog-bridge` → **Restart**

### Update Code
1. Edit the Python script on the Docker host
2. In Portainer: **Stacks** → `flex-wavelog-bridge` → **Stop**
3. Click **Editor** → **Update the stack** (triggers rebuild)

## Stack Environment Variables (Optional)

You can also expose config values as stack environment variables in Portainer:

```yaml
version: '3.8'

services:
  flex-wavelog-bridge:
    build:
      context: /opt/stacks/flex-wavelog-bridge
      dockerfile: Dockerfile
    container_name: flex-wavelog-bridge
    volumes:
      - /opt/stacks/flex-wavelog-bridge/config:/config
      - /opt/stacks/flex-wavelog-bridge/logs:/logs
    restart: unless-stopped
    environment:
      - CONFIG_FILE=/config/config.json
      - LOG_DIR=/logs
      - FLEX_IP=${FLEX_IP:-192.168.25.179}
      - WAVELOG_URL=${WAVELOG_URL:-http://wavelog:8086}
    networks:
      - nginx-proxy-manager-network

networks:
  nginx-proxy-manager-network:
    external: true
```

Then set values in Portainer's stack environment variables section.
