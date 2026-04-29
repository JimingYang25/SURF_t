# Driver for MentorPi_UART -- Maintainer Jiming Yang

import serial
import time

#-------------------- Global setting --------------------------

# Dictionary mapping device names to their serial port paths
serial_pingroups = {'RRCLite': '/dev/ttyAMA0', 'Others_...': None}

# Dictionary mapping device names to their baud rates
serial_baud_rates = {'RRCLite': 115200, 'Others...': None}

# Dictionary to store active serial connections
serial_connections = {}

#--------------------- Init Device -----------------------------

def UART_init(device_name: str,timeout = 1.0) -> int:
    """
    Initialize UART serial port by device name.
    para: device_name: The device name string. set timeout to 0 in ros2 time_callback
    ret: 0: success, 1: failure
    """
    global serial_connections
    
    # Check if device is already initialized
    if device_name in serial_connections:
        # If port is already open, return success
        if serial_connections[device_name].is_open:
            return 0
        # If port exists but is closed, remove it from connections
        del serial_connections[device_name]

    # Get port path and baud rate from configuration dictionaries
    port_path = serial_pingroups.get(device_name)
    baud_rate = serial_baud_rates.get(device_name)

    # Return failure if device is not configured
    if port_path is None or baud_rate is None:
        return 1

    try:
        # Initialize serial port with explicit parameters for reliability
        ser = serial.Serial(
            port=port_path,
            baudrate=baud_rate,
            bytesize=serial.EIGHTBITS,      # 8 data bits (most common configuration)
            parity=serial.PARITY_NONE,       # No parity bit
            stopbits=serial.STOPBITS_ONE,    # 1 stop bit
            timeout=timeout,                      # Read timeout in seconds 
            write_timeout=1.0                 # Write timeout in seconds
        )
        
        # Small delay to ensure port stabilization after opening
        time.sleep(0.05)
        
        # Verify port is actually open
        if not ser.is_open:
            return 1
        
        # Store the connection in our dictionary
        serial_connections[device_name] = ser
    except serial.SerialException as e:
        # Capture common serial port errors:
        # - Insufficient permissions (not in dialout group)
        # - Port already occupied by another process
        # - Device path does not exist
        return 1
    else:
        return 0

#-------------------- Data Transmission -----------------------------

def UART_send(device_name: str, data: bytes) -> int:
    """
    Send bytes data to a specific device.
    para: device_name: The device name string.
          data: Bytes to send (e.g., b'hello').
    ret: 0: success, 1: failure
    """
    global serial_connections
    
    # Check if device exists and is open
    if device_name not in serial_connections:
        return 1
    if not serial_connections[device_name].is_open:
        return 1
        
    try:
        # Write data to serial port
        serial_connections[device_name].write(data)
    except:
        # Catch any write errors (timeout, disconnect, etc.)
        return 1
        
    return 0


def UART_receive(device_name: str, num_bytes: int = 128) -> bytes:
    """
    Receive bytes data from a specific device (non-blocking read).
    May return fewer bytes than requested if timeout occurs.
    para: device_name: The device name string.
          num_bytes: Maximum number of bytes to read.
    ret: Received bytes (returns empty bytes b"" on failure or timeout).
    """
    global serial_connections
    
    # Check if device exists and is open
    if device_name not in serial_connections:
        return b""
    if not serial_connections[device_name].is_open:
        return b""
        
    try:
        # Read up to 'num_bytes' from serial port
        # Returns immediately if timeout is reached
        return serial_connections[device_name].read(num_bytes)
    except:
        # Catch any read errors
        return b""


def UART_read_exact(device_name: str, num_bytes: int) -> bytes:
    """
    Read EXACTLY 'num_bytes' from the device (blocking read).
    Will block indefinitely or until timeout if insufficient data is available.
    para: device_name: The device name string.
          num_bytes: Exact number of bytes to read.
    ret: Received bytes (returns empty bytes b"" on failure or timeout).
    """
    global serial_connections
    
    # Check if device exists and is open
    if device_name not in serial_connections:
        return b""
    if not serial_connections[device_name].is_open:
        return b""
        
    try:
        # Read exactly 'num_bytes' - will wait until all data arrives
        return serial_connections[device_name].readexactly(num_bytes)
    except:
        # Catch any read errors or timeout exceptions
        return b""


def UART_flush(device_name: str) -> int:
    """
    Flush (clear) both input and output serial buffers.
    Use this before sending new commands to avoid reading stale data.
    para: device_name: The device name string.
    ret: 0: success, 1: failure
    """
    global serial_connections
    
    # Check if device exists and is open
    if device_name not in serial_connections:
        return 1
    if not serial_connections[device_name].is_open:
        return 1
        
    try:
        # Clear input buffer (discard all received but unread data)
        serial_connections[device_name].reset_input_buffer()
        # Clear output buffer (discard all written but not transmitted data)
        serial_connections[device_name].reset_output_buffer()
        return 0
    except:
        # Catch any flush errors
        return 1

#-------------------- Resource Management -----------------------------

def UART_deinit(device_name: str) -> int:
    """
    Close a specific UART device and remove it from connections.
    para: device_name: The device name string.
    ret: 0: success, 1: failure
    """
    global serial_connections
    
    # Check if device exists in our connections
    if device_name not in serial_connections:
        return 1
        
    try:
        # Close the port if it's open
        if serial_connections[device_name].is_open:
            serial_connections[device_name].close()
        # Remove the device from our connections dictionary
        del serial_connections[device_name]
    except:
        # Catch any close errors
        return 1
        
    return 0


def UART_deinit_all() -> None:
    """
    Close all opened UART devices and clear the connections dict.
    Usually called in the 'finally' block of the main program to ensure
    proper cleanup even if an exception occurs.
    """
    global serial_connections
    # Iterate over a copy of the dictionary items to avoid modification during iteration
    for name, ser in list(serial_connections.items()):
        try:
            # Close the port if it's open
            if ser.is_open:
                ser.close()
        except:
            # Ignore any errors during cleanup - we're shutting down anyway
            pass
    # Clear the entire connections dictionary
    serial_connections.clear()

#------------------------- Addition for ROS2 -----------------------------------

    

# Driver for MentorPi_UART -- Maintainer Jiming Yang