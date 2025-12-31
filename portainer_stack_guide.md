# Deploying Flex-Wavelog Bridge via Portainer Stacks

## Method 1: Using Portainer with Git Repository (Recommended)

### (SKIP IF REPO ALREADY EXISTS) Step 1: Create a Git Repository
1. Create a new repository on GitHub/GitLab
2. Add these files to the repository:
   - `flex_radio_monitor.py`
   - `Dockerfile`
   - `docker-compose.yml`

### Step 2: Deploy in Portainer
1. Go to **Portainer** → **Stacks** → **Add stack**
2. Name: `flex-wavelog-bridge`
3. Build method: **Repository**
4. Repository URL: `REPO_URL_HERE`
5. Compose path: `docker-compose.yml`
6. Click **Deploy the stack**

### Step 3: Create Config File
After deployment, you need to create the config file manually:

```bash
# SSH into your Docker host
ssh user@your-docker-host

# Navigate to the stack's volume - THIS MIGHT BE WRONG. CHECK CONTAINER SETTINGS TO SEE CORRECT PATH TO VOLUME.
cd /var/lib/docker/volumes/flex-wavelog-bridge_config/_data

# Create config.json
nano config.json
```

Paste this content:
```json
{
    "flex": {
        "ip": "192.168.2.9",
        "port": 4992,
        "slice": "A"
    },
    "wavelog": {
        "url": "http://wavelog-main:8086",
        "api_key": "WAVELOG_API_KEY",
        "radio_id": "1"
    },
    "logging": {
        "level": "INFO"
    }
}
```

Save and restart the stack in Portainer.

---

