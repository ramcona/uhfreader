# config.py

# Flask Configuration
FLASK_HOST = '0.0.0.0'  # Host for Flask app
FLASK_PORT = 5000        # Port for Flask app
FLASK_DEBUG = True       # Debug mode for Flask

# Serial Port Configuration
DEFAULT_SERIAL_PORT = '/dev/tty.usbmodemXXXX'  # Default serial port for macOS
DEFAULT_BAUD_RATE = 57600                     # Default baud rate
SERIAL_TIMEOUT = 1                            # Serial connection timeout

# CSV Configuration
DEFAULT_CSV_FILE = 'rfid_data.csv'            # Default CSV file for storing RFID data

# RFID Reader Configuration
INVENTORY_COMMANDS = [
    bytearray([0xBB, 0x00, 0x22, 0x00, 0x00, 0x22, 0x7E]),  # Standard inventory command
    bytearray([0xA0, 0x04, 0x01, 0xDB, 0x4B]),              # Alternative command
]

# Logging Configuration
LOG_FILE = 'rfid_reader.log'                  # Log file for debugging
LOG_LEVEL = 'DEBUG'                           # Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)