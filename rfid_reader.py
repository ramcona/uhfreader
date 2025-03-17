import serial
import csv
import time
import glob
from datetime import datetime
import threading
import serial.tools.list_ports
from threading import Thread
from queue import Queue

class RFIDReader:
    def __init__(self):
        self.serial_conn = None
        self.current_data = []
        self.raw_packets = []
        self.settings = {
            'serial_port': None,
            'baud_rate': 57600,
            'csv_file': 'rfid_data.csv'
        }
        self.lock = threading.Lock()
        self.running = False
        self.thread = None
        self.process_thread = None
        self.data_queue = Queue()  # Thread-safe queue for incoming data
        self.last_inventory_time = 0

    def list_serial_ports(self):
        """List all available serial ports and their connection status."""
        ports = []
        for port in serial.tools.list_ports.comports():
            try:
                # Try to open the port to check if it's connected
                ser = serial.Serial(port.device)
                ser.close()
                status = "Connected"
            except (OSError, serial.SerialException):
                status = "Disconnected"
            ports.append({
                'device': port.device,
                'description': port.description,
                'status': status
            })
        return ports

    def setup_connection(self, port, baud_rate=57600):
        """Establish a serial connection with the UHF reader."""
        try:
            self.serial_conn = serial.Serial(
                port=port,
                baudrate=baud_rate,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
                timeout=2,  # Increase timeout to 2 seconds
                write_timeout=2,  # Set write timeout
                rtscts=True,  # Enable hardware flow control (if supported)
                dsrdtr=True  # Enable hardware flow control (if supported)
            )
            self.settings['serial_port'] = port
            self.settings['baud_rate'] = baud_rate
            return True, f"Successfully connected to {port}"
        except serial.SerialException as e:
            return False, f"Error connecting to {port}: {e}"
    
    def stop(self):
        """Stop the RFID reader and processing threads."""
        self.running = False
        
        # Stop inventory if active for Chaofan reader
        if self.serial_conn and self.serial_conn.is_open:
            try:
                # Using the Chaofan command to stop inventory
                stop_cmd = bytearray([0xA0, 0x03, 0x00, 0xA3])
                self.serial_conn.write(stop_cmd)
                time.sleep(0.1)
            except Exception as e:
                print(f"Error sending stop command: {e}")
        
        if self.thread:
            self.thread.join(timeout=2)  # Wait for the read_loop thread to finish with timeout
        if self.process_thread:
            self.process_thread.join(timeout=2)  # Wait for the process_queue thread to finish with timeout
        if self.serial_conn:
            self.serial_conn.close()  # Close the serial connection
        return True, "Reader stopped"

    def clear_data(self):
        """Clear current data and reset CSV."""
        with self.lock:
            self.current_data = []  # Clear in-memory data
            self.raw_packets = []  # Clear raw packets
            
            # Reset the CSV file
            try:
                with open(self.settings['csv_file'], 'w', newline='') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=['timestamp', 'epc', 'rssi', 'antenna', 'detected_as'])
                    writer.writeheader()  # Write header only
                print("Data cleared and CSV reset.")
            except Exception as e:
                print(f"Error clearing CSV file: {e}")

    def read_loop(self):
        """Main reading loop with improved buffer handling for Chaofan reader."""
        buffer = bytearray()
        while self.running:
            try:
                if self.serial_conn and self.serial_conn.in_waiting:
                    # Read all available data
                    new_data = self.serial_conn.read(self.serial_conn.in_waiting)
                    if new_data:
                        # For debugging
                        # print(f"Received data: {' '.join([f'{b:02X}' for b in new_data])}")
                        self.data_queue.put(new_data)
                
                # Periodically restart inventory to improve tag detection
                current_time = time.time()
                if current_time - self.last_inventory_time > 3:  # Every 3 seconds
                    self.start_fast_inventory()
                    self.last_inventory_time = current_time
                
                time.sleep(0.01)  # Small delay to prevent CPU hogging
            except Exception as e:
                print(f"Error in read loop: {e}")
                time.sleep(0.1)  # Longer delay after error

    def process_queue(self):
        """Process data from the queue."""
        buffer = bytearray()  # Buffer to accumulate data across queue entries
        
        while self.running:
            try:
                if not self.data_queue.empty():
                    data = self.data_queue.get()
                    
                    # Add to our accumulating buffer
                    buffer.extend(data)
                    
                    # Process complete packets from the buffer
                    i = 0
                    while i < len(buffer):
                        # Check for Chaofan packet structure
                        if len(buffer) - i >= 21:
                            # For debugging
                            # print(f"Processing potential packet: {' '.join([f'{b:02X}' for b in buffer[i:i+21]])}")
                            # Process the packet and check if it was valid
                            if self.process_data(buffer[i:i+21]):
                                i += 21  # Move past this packet
                            else:
                                i += 1   # Not a valid packet, move one byte
                        else:
                            # Not enough data for a complete packet
                            break
                    
                    # Keep only unprocessed data in the buffer
                    if i > 0:
                        buffer = buffer[i:]
                
                else:
                    time.sleep(0.01)  # Small delay when queue is empty
            except Exception as e:
                print(f"Error processing data from queue: {e}")
                time.sleep(0.1)  # Longer delay after error

    def start(self):
        """Start the RFID reader and processing threads."""
        if not self.serial_conn or not self.serial_conn.is_open:
            return False, "Serial connection not established"
        
        self.running = True
        
        # Start the reading thread
        self.thread = threading.Thread(target=self.read_loop, daemon=True)
        self.thread.start()

        # Start a separate thread for processing data
        self.process_thread = threading.Thread(target=self.process_queue, daemon=True)
        self.process_thread.start()
        
        # Start initial inventory
        self.start_fast_inventory()
        self.last_inventory_time = time.time()
        
        return True, "Reader started"
    
    def process_data(self, data):
        """Process Chaofan UHF reader data packet and extract EPC."""
        # Check if this looks like a valid Chaofan packet
        if len(data) == 21:  # Expected length for Chaofan tag data
            try:
                # Chaofan packet format check (this may need adjustment based on your specific reader)
                epc = data[6:18]  # Extract EPC (12 bytes)
                epc_hex = ''.join([f"{b:02X}" for b in epc])  # Convert to hex string

                rssi = data[18]  # Extract RSSI
                antenna = data[19]  # Extract antenna number

                tag_data = {
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'),
                    'epc': epc_hex,
                    'rssi': rssi,
                    'antenna': antenna,
                    'detected_as': 'chaofan_custom'
                }

                with self.lock:
                    # Check if this is a new tag
                    if not any(tag['epc'] == epc_hex for tag in self.current_data):
                        self.current_data.append(tag_data)
                        self.write_to_csv(tag_data)
                        print(f"Tag found: {epc_hex}, RSSI: {rssi}, Antenna: {antenna}")
                        print(f"Total tags processed: {len(self.current_data)}")
                return True  # Valid packet processed
            except Exception as e:
                print(f"Error parsing tag data: {e}")
                return False  # Error processing packet
        return False  # Not a valid packet
    
    def debug_print_bytes(self, data):
        """Print byte data in a readable format."""
        hex_str = ' '.join([f"{b:02X}" for b in data])
        return hex_str
    
    def write_to_csv(self, tag_data):
        """Write tag data to CSV."""
        try:
            with open(self.settings['csv_file'], 'a', newline='') as csvfile:
                fieldnames = ['timestamp', 'epc', 'rssi', 'antenna', 'detected_as']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                if csvfile.tell() == 0:
                    writer.writeheader()
                writer.writerow(tag_data)
        except Exception as e:
            print(f"Error saving to CSV: {e}")

    def get_data(self):
        """Get current tag data."""
        with self.lock:
            return self.current_data.copy()

    def get_stats(self):
        """Get statistics about the current session."""
        with self.lock:
            return {
                'total_reads': len(self.current_data),
                'last_read': self.current_data[0]['timestamp'] if self.current_data else 'Never'
            }
        
    def start_fast_inventory(self):
        """Send command to start fast inventory mode for Chaofan reader."""
        if self.serial_conn and self.serial_conn.is_open:
            try:
                # First stop any ongoing inventory
                stop_cmd = bytearray([0xA0, 0x03, 0x00, 0xA3])
                self.serial_conn.write(stop_cmd)
                time.sleep(0.1)
                
                # Chaofan fast inventory command with optimized parameters for multiple tags
                # This may need adjustment based on your specific model
                fast_inventory_cmd = bytearray([0xA0, 0x06, 0x01, 0xFF, 0x10, 0x20, 0xD6])
                self.serial_conn.write(fast_inventory_cmd)
                
                # Debug message
                print("Fast inventory started with optimized settings")
                return True
            except Exception as e:
                print(f"Error starting fast inventory: {e}")
                return False
        return False

    def retry_missed_tags(self):
        """Attempt to detect any potentially missed tags by restarting inventory with different parameters."""
        if not self.serial_conn or not self.serial_conn.is_open:
            return False
            
        try:
            # Stop current inventory
            stop_cmd = bytearray([0xA0, 0x03, 0x00, 0xA3])
            self.serial_conn.write(stop_cmd)
            time.sleep(0.2)
            
            # Clear input buffer
            self.serial_conn.reset_input_buffer()
            
            # Set higher power (if supported by your reader)
            power_cmd = bytearray([0xA0, 0x07, 0x3B, 0x30, 0x00, 0x00, 0x12])
            self.serial_conn.write(power_cmd)
            time.sleep(0.2)
            
            # Start inventory with different parameters to catch missed tags
            # Using alternative antenna settings and sensitivity
            alt_inventory_cmd = bytearray([0xA0, 0x06, 0x01, 0xF0, 0x10, 0x10, 0xC7])
            self.serial_conn.write(alt_inventory_cmd)
            
            print("Retrying with alternate settings to detect missed tags")
            return True
        except Exception as e:
            print(f"Error in retry operation: {e}")
            return False