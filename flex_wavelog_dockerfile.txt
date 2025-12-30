FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install required Python packages
RUN pip install --no-cache-dir requests

# Copy the Python script
COPY flex_radio_monitor.py /app/

# Create config and logs directories
RUN mkdir -p /config /logs

# Set environment variables
ENV CONFIG_FILE=/config/config.json
ENV LOG_DIR=/logs

# Run the script
CMD ["python", "-u", "flex_radio_monitor.py"]
