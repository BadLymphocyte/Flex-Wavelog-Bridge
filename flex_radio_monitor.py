#!/usr/bin/env python3
"""
Flex Radio Slice A Monitor with Wavelog Integration
Connects to a Flex radio and pushes frequency/mode to Wavelog
"""

import socket
import time
import re
import requests
import json
import sys
import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime

CONFIG_FILE = os.getenv('CONFIG_FILE', '/config/config.json')
LOG_DIR = os.getenv('LOG_DIR', '/logs')
LOG_FILE = os.path.join(LOG_DIR, 'flex_wavelog_bridge.log')

class FlexRadioMonitor:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.flex_ip = config['flex']['ip']
        self.flex_port = config['flex']['port']
        self.flex_slice = config['flex'].get('slice', 'A').upper()  # Default to 'A'
        self.wavelog_url = config['wavelog']['url']
        self.wavelog_api_key = config['wavelog']['api_key']
        self.wavelog_radio_id = config['wavelog']['radio_id']
        
        # Validate slice letter
        if self.flex_slice not in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']:
            self.logger.error(f"Invalid slice '{self.flex_slice}'. Must be A-H. Defaulting to A.")
            self.flex_slice = 'A'
        
        # Map slice letters to numeric IDs (Flex uses 0-7)
        self.slice_letter_to_id = {
            'A': '0', 'B': '1', 'C': '2', 'D': '3',
            'E': '4', 'F': '5', 'G': '6', 'H': '7'
        }
        self.target_slice_id = self.slice_letter_to_id[self.flex_slice]
        
        self.sock = None
        self.handle = None
        self.slice_info = {"frequency": "Unknown", "mode": "Unknown"}
        self.slice_id = None
        
    def connect(self):
        """Connect to the Flex radio"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(5)
            self.sock.connect((self.flex_ip, self.flex_port))
            msg = f"Connected to Flex radio at {self.flex_ip}:{self.flex_port}"
            print(msg)
            self.logger.info(msg)
            self.logger.info(f"Monitoring Slice {self.flex_slice} (ID: {self.target_slice_id})")
            
            # Receive initial connection message
            response = self.receive_response()
            
            # Extract handle from response (format: "H<handle>")
            handle_match = re.search(r'H([0-9A-F]+)', response)
            if handle_match:
                self.handle = handle_match.group(1)
                msg = f"Connection handle: {self.handle}"
                print(msg)
                self.logger.info(msg)
            
            return True
        except Exception as e:
            msg = f"Connection failed: {e}"
            print(msg)
            self.logger.error(msg)
            return False
    
    def receive_response(self, timeout=1):
        """Receive response from radio"""
        self.sock.settimeout(timeout)
        try:
            data = self.sock.recv(8192).decode('utf-8')
            return data
        except socket.timeout:
            return ""
        except Exception as e:
            self.logger.error(f"Receive error: {e}")
            return ""
    
    def send_command(self, command):
        """Send command to radio"""
        try:
            cmd = f"C{self.handle}|{command}\n"
            self.sock.sendall(cmd.encode('utf-8'))
        except Exception as e:
            self.logger.error(f"Send error: {e}")
    
    def parse_response(self, response):
        """Parse all status messages in response"""
        for line in response.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            # Status messages start with S followed by handle
            if line.startswith('S'):
                # Extract the message content after the handle
                parts = line.split('|', 1)
                if len(parts) == 2:
                    message = parts[1]
                    
                    # Check if it's a slice status message
                    if message.startswith('slice '):
                        self.parse_slice_status(message)
    
    def parse_slice_status(self, message):
        """Parse slice status message"""
        # Format: slice <id> <key>=<value> <key>=<value> ...
        parts = message.split(' ', 2)
        if len(parts) >= 2:
            slice_id = parts[1]
            
            # Only monitor the configured slice
            if slice_id == self.target_slice_id:
                if self.slice_id is None:
                    self.slice_id = slice_id
                    self.logger.info(f"Locked onto Slice {self.flex_slice} (ID: {slice_id})")
                
                changed = False
                
                # Parse key=value pairs
                if len(parts) >= 3:
                    params = parts[2]
                    
                    # Extract frequency
                    freq_match = re.search(r'RF_frequency=([\d.]+)', params)
                    if freq_match:
                        freq_mhz = float(freq_match.group(1))
                        new_freq = f"{freq_mhz:.6f} MHz"
                        if new_freq != self.slice_info["frequency"]:
                            self.slice_info["frequency"] = new_freq
                            changed = True
                    
                    # Extract mode - ignore OFF state
                    mode_match = re.search(r'mode=(\w+)', params)
                    if mode_match:
                        mode = mode_match.group(1)
                        # Only update mode if it's not OFF (keeps last valid mode)
                        if mode != "OFF" and mode != self.slice_info["mode"]:
                            self.slice_info["mode"] = mode
                            changed = True
                
                # Push to Wavelog if something changed
                if changed:
                    self.push_to_wavelog()
    
    def convert_mode_for_wavelog(self, mode):
        """Convert Flex mode names to Wavelog-compatible format"""
        mode_map = {
            'USB': 'SSB',
            'LSB': 'SSB',
            'CW': 'CW',
            'CWL': 'CW',
            'AM': 'AM',
            'SAM': 'AM',
            'FM': 'FM',
            'NFM': 'FM',
            'DFM': 'FM',
            'DIGU': 'DIGI',
            'DIGL': 'DIGI',
            'RTTY': 'RTTY',
        }
        return mode_map.get(mode.upper(), mode)
    
    def push_to_wavelog(self):
        """Push current frequency and mode to Wavelog"""
        # Extract numeric frequency value
        freq_str = self.slice_info["frequency"]
        mode_str = self.slice_info["mode"]
        
        if freq_str == "Unknown" or mode_str == "Unknown":
            return False
        
        try:
            # Extract frequency in MHz
            freq_match = re.search(r'([\d.]+)', freq_str)
            if not freq_match:
                return False
            
            freq_mhz = float(freq_match.group(1))
            # Convert MHz to Hz for Wavelog (Wavelog expects frequency in Hz)
            # 14.250 MHz = 14,250,000 Hz
            freq_hz = int(freq_mhz * 1000000)
            
            # Convert mode
            wavelog_mode = self.convert_mode_for_wavelog(mode_str)
            
            # Wavelog API endpoint for radio update
            url = f"{self.wavelog_url}/index.php/api/radio"
            
            headers = {
                'Content-Type': 'application/json',
            }
            
            data = {
                'key': self.wavelog_api_key,
                'radio': self.wavelog_radio_id,
                'frequency': freq_hz,
                'mode': wavelog_mode
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=2)
            
            if response.status_code == 200:
                msg = f"✓ Pushed to Wavelog - Slice {self.flex_slice}: Frequency: {freq_str} ({freq_hz} Hz), Mode: {mode_str} ({wavelog_mode})"
                print(msg)
                self.logger.info(f"Pushed to Wavelog - Slice {self.flex_slice}: Frequency: {freq_str} ({freq_hz} Hz), Mode: {mode_str} ({wavelog_mode})")
                return True
            else:
                msg = f"✗ Wavelog API error: {response.status_code} - {response.text}"
                print(msg)
                self.logger.error(f"Wavelog API error: {response.status_code} - {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            msg = f"✗ Failed to connect to Wavelog: {e}"
            print(msg)
            self.logger.error(f"Failed to connect to Wavelog: {e}")
            return False
        except Exception as e:
            msg = f"✗ Error pushing to Wavelog: {e}"
            print(msg)
            self.logger.error(f"Error pushing to Wavelog: {e}")
            return False
    
    def monitor_loop(self):
        """Main monitoring loop"""
        msg = f"\nMonitoring Slice {self.flex_slice} and pushing to Wavelog on changes (Press Ctrl+C to stop)...\n"
        print(msg)
        self.logger.info(f"Monitoring Slice {self.flex_slice} started")
        
        # Initial subscription
        self.send_command("sub slice all")
        time.sleep(0.2)
        initial_response = self.receive_response(timeout=1)
        self.parse_response(initial_response)
        
        try:
            while True:
                # Listen for updates from the radio
                response = self.receive_response(timeout=0.5)
                if response:
                    self.parse_response(response)
                
                # Small sleep to prevent busy loop
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            msg = "\n\nMonitoring stopped by user"
            print(msg)
            self.logger.info("Monitoring stopped by user")
        except Exception as e:
            msg = f"\nError in monitoring loop: {e}"
            print(msg)
            self.logger.error(f"Error in monitoring loop: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
        finally:
            self.disconnect()
    
    def disconnect(self):
        """Close connection to radio"""
        if self.sock:
            try:
                self.sock.close()
                msg = "Disconnected from radio"
                print(msg)
                self.logger.info(msg)
            except:
                pass

def setup_logging(log_level='INFO'):
    """Setup logging to file and console"""
    # Create logs directory if it doesn't exist
    os.makedirs(LOG_DIR, exist_ok=True)
    
    # Convert string log level to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Create logger
    logger = logging.getLogger('FlexWavelogBridge')
    logger.setLevel(numeric_level)
    
    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_formatter = logging.Formatter('%(message)s')
    
    # File handler with rotation (10MB per file, keep 5 files)
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(file_formatter)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(console_formatter)
    
    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def load_config():
    """Load configuration from JSON file"""
    if not os.path.exists(CONFIG_FILE):
        print(f"Configuration file '{CONFIG_FILE}' not found!")
        print("\nCreating example configuration file...")
        
        example_config = {
            "flex": {
                "ip": "192.168.25.179",
                "port": 4992,
                "slice": "A"
            },
            "wavelog": {
                "url": "http://wavelog:8086",
                "api_key": "YOUR_API_KEY_HERE",
                "radio_id": "1"
            },
            "logging": {
                "level": "INFO"
            }
        }
        
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(example_config, f, indent=4)
            print(f"✓ Created '{CONFIG_FILE}'")
            print(f"\nPlease edit '{CONFIG_FILE}' with your settings and run the script again.")
            print("\nTo get your Wavelog API key:")
            print("  1. Log into Wavelog")
            print("  2. Go to Options → API")
            print("  3. Copy your API key")
            sys.exit(0)
        except Exception as e:
            print(f"✗ Failed to create config file: {e}")
            sys.exit(1)
    
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        
        # Validate required fields
        required_fields = {
            'flex': ['ip', 'port'],
            'wavelog': ['url', 'api_key', 'radio_id']
        }
        
        for section, fields in required_fields.items():
            if section not in config:
                print(f"✗ Missing '{section}' section in config file")
                sys.exit(1)
            for field in fields:
                if field not in config[section]:
                    print(f"✗ Missing '{field}' in '{section}' section")
                    sys.exit(1)
        
        # Validate slice if provided
        if 'slice' in config['flex']:
            slice_letter = config['flex']['slice'].upper()
            if slice_letter not in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']:
                print(f"✗ Invalid slice '{slice_letter}'. Must be A-H.")
                sys.exit(1)
        
        # Validate log level if provided
        if 'logging' in config and 'level' in config['logging']:
            log_level = config['logging']['level'].upper()
            valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
            if log_level not in valid_levels:
                print(f"✗ Invalid log level '{log_level}'. Must be one of: {', '.join(valid_levels)}")
                sys.exit(1)
        
        # Check if API key needs to be configured
        if config['wavelog']['api_key'] == "YOUR_API_KEY_HERE":
            print("⚠️  WARNING: Wavelog API key not configured!")
            print(f"   Please edit '{CONFIG_FILE}' and set your API key")
            print("\nTo get your Wavelog API key:")
            print("  1. Log into Wavelog")
            print("  2. Go to Options → API")
            print("  3. Copy your API key")
            sys.exit(1)
        
        return config
        
    except json.JSONDecodeError as e:
        print(f"✗ Invalid JSON in config file: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Error loading config: {e}")
        sys.exit(1)

def main():
    print("=" * 60)
    print("Flex Radio to Wavelog Bridge")
    print("=" * 60)
    
    # Load configuration first
    config = load_config()
    
    # Get log level from config, default to INFO
    log_level = config.get('logging', {}).get('level', 'INFO')
    
    # Setup logging with configured level
    logger = setup_logging(log_level)
    logger.info("=" * 60)
    logger.info("Flex Radio to Wavelog Bridge - Starting")
    logger.info("=" * 60)
    
    print(f"\nConfiguration:")
    print(f"  Flex Radio: {config['flex']['ip']}:{config['flex']['port']}")
    print(f"  Flex Slice: {config['flex'].get('slice', 'A')}")
    print(f"  Wavelog:    {config['wavelog']['url']}")
    print(f"  Radio ID:   {config['wavelog']['radio_id']}")
    print(f"  Log Level:  {log_level}")
    print(f"  Log file:   {LOG_FILE}")
    
    logger.info(f"Configuration loaded - Flex: {config['flex']['ip']}:{config['flex']['port']}, Slice: {config['flex'].get('slice', 'A')}, Wavelog: {config['wavelog']['url']}, Log Level: {log_level}")
    
    monitor = FlexRadioMonitor(config, logger)
    
    if monitor.connect():
        monitor.monitor_loop()
    else:
        print("\nFailed to connect to radio. Please check:")
        print(f"  - Radio is powered on and accessible at {config['flex']['ip']}")
        print(f"  - Network connectivity is working")
        print(f"  - API port {config['flex']['port']} is not blocked")
        logger.error(f"Failed to connect to Flex radio at {config['flex']['ip']}:{config['flex']['port']}")

if __name__ == "__main__":
    main()
