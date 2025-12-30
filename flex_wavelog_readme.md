# Flex Radio to Wavelog Bridge (Docker)

This Docker container bridges your Flex radio to Wavelog, automatically pushing frequency and mode changes.

## Quick Start

### 1. Create Project Directory

```bash
mkdir flex-wavelog-bridge
cd flex-wavelog-bridge
```

### 2. Create Files

Save these three files in the directory:
- `flex_radio_monitor.py` - The Python script
- `Dockerfile` - Docker build instructions
- `docker-compose.yml` - Docker Compose configuration

### 3. Create Config Directory

```bash
mkdir config
mkdir logs
```

### 4. Create Configuration File

Create `config/config.json`:

```json
{
    "flex": {
        "ip": "YOUR_FLEX_RADIO_IP",
        "port": 4992
    },
    "wavelog": {
        "url": "http://YOUR_WAVELOG_URL",
        "api_key": "YOUR_WAVELOG_API_KEY",
        "radio_id": "1"
    }
}
```

**Important:** Update the values:
- `flex.ip` - Your Flex radio IP address (must be accessible from Docker host)
- `wavelog.url` - Your Wavelog container name (e.g., `http://wavelog` or `http://wavelog-container-name`) since they're on the same Docker network
- `wavelog.api_key` - Get from Wavelog: Options → API
- `wavelog.radio_id` - Usually "1" for the first radio

**Note:** Since Wavelog is on the same `nginx-proxy-manager-network`, you can use the Wavelog container name directly (e.g., `http://wavelog` or `http://wavelog:80`). Check your Wavelog container name with `docker ps`.

### 5. Build and Run

```bash
# Build the container
docker-compose build

# Start the container
docker-compose up -d

# View logs
docker-compose logs -f
```

## Directory Structure

```
flex-wavelog-bridge/
├── config/
│   └── config.json          # Your configuration (persisted)
├── logs/
│   └── flex_wavelog_bridge.log  # Application logs (persisted)
├── docker-compose.yml       # Docker Compose file
├── Dockerfile               # Docker build file
└── flex_radio_monitor.py    # Python script
```

## Docker Commands

```bash
# Start the container
docker-compose up -d

# Stop the container
docker-compose down

# View logs (console output)
docker-compose logs -f

# View application log file
tail -f logs/flex_wavelog_bridge.log

# Restart the container
docker-compose restart

# Rebuild after changes
docker-compose up -d --build
```

## Log Files

Logs are written to two places:

1. **Console output** (Docker logs): `docker-compose logs -f`
2. **Log file**: `./logs/flex_wavelog_bridge.log`

The log file includes:
- Connection events
- Frequency and mode changes pushed to Wavelog
- Errors and warnings
- Automatic rotation (10MB per file, keeps 5 backup files)

**View log file:**
```bash
# View live logs
tail -f logs/flex_wavelog_bridge.log

# View last 100 lines
tail -n 100 logs/flex_wavelog_bridge.log

# Search logs for errors
grep ERROR logs/flex_wavelog_bridge.log
```

## Manual Docker Run (without docker-compose)

```bash
# Build the image
docker build -t flex-wavelog-bridge .

# Run the container
docker run -d \
  --name flex-wavelog-bridge \
  --network host \
  -v $(pwd)/config:/config \
  --restart unless-stopped \
  flex-wavelog-bridge
```

## Troubleshooting

### Container won't start
```bash
# Check logs
docker-compose logs

# Common issues:
# - Config file not found: Make sure config/config.json exists
# - Invalid JSON: Validate your config.json syntax
# - Missing API key: Set your Wavelog API key in config.json
```

### Can't connect to Flex radio
```bash
# Verify Flex radio IP
ping 192.168.25.179

# Check if port 4992 is accessible
telnet 192.168.25.179 4992
```

### Can't connect to Wavelog
```bash
# Find your Wavelog container name
docker ps | grep wavelog

# Test connection from the bridge container
docker exec flex-wavelog-bridge ping wavelog

# Test Wavelog API from container
docker exec flex-wavelog-bridge curl http://wavelog/index.php/api/radio

# Common issues:
# - Wrong container name: Use the exact name from 'docker ps'
# - Wrong port: Check if Wavelog needs a port (e.g., :80 or :8080)
# - Network issue: Verify both containers are on nginx-proxy-manager-network
```

### Verify Network Configuration
```bash
# Check which network the containers are on
docker inspect flex-wavelog-bridge | grep NetworkMode
docker inspect wavelog | grep NetworkMode

# List containers on the network
docker network inspect nginx-proxy-manager-network
```

### View real-time logs
```bash
docker-compose logs -f
```

## Network Configuration

This container connects to the `nginx-proxy-manager-network` Docker network, which allows it to communicate with Wavelog and other services on the same network.

**Key Points:**
- The container is on the same network as Wavelog, so you can use Wavelog's container name in the URL
- The Flex radio IP must be accessible from the Docker host (it's on your physical network)
- Find your Wavelog container name: `docker ps | grep wavelog`

**Example Wavelog URLs:**
- If Wavelog container is named `wavelog`: `http://wavelog`
- If Wavelog container is named `wavelog-app`: `http://wavelog-app`
- With port: `http://wavelog:80` or `http://wavelog:8080`

## Updating Configuration

1. Edit `config/config.json`
2. Restart the container: `docker-compose restart`

The config directory is mounted as a volume, so changes persist across container restarts.

## Getting Wavelog API Key

1. Log into your Wavelog instance
2. Navigate to **Options → API**
3. Copy your API key
4. Paste it into `config/config.json` under `wavelog.api_key`

## Features

- ✓ Automatic reconnection on failure
- ✓ Real-time frequency and mode updates
- ✓ Minimal resource usage
- ✓ Persistent configuration
- ✓ Persistent logging with automatic rotation
- ✓ Easy updates via config file
- ✓ Automatic restart with `unless-stopped`
- ✓ Detailed logging to file and console
