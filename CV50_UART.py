# CV50 TOF 50M Driver -- Matiner:Jiming Yang
# Dependences：MentorPi_UART.py
import time
import MentorPi_UART as UART

# ===================== Protocol Constants =====================
CV50_FRAME_HEAD = 0xDF # frame head
CV50_DEV_ID     = 0x32 # device ID 
CV50_SYS_ID     = 0x00 # system ID
CV50_MSG_ID     = 0x40 # message ID 
CV50_PAYLOAD_LEN= 0x04 # fixed 4 data digits
CV50_FRAME_LEN  = 11   # fixed 11 digits
CV50_BAUD       = "HS" # high speed 115200

# Pin
TX_PIN = UART.TX_PIN["CV50_TX"]
RX_PIN = UART.RX_PIN["CV50_RX"]

# ===================== Initialization =====================
def CV50_Init():
    """Initialize UART for CV50, baud rate fixed at 115200"""
    UART.UART_Init(tx_pin=TX_PIN,rx_pin=RX_PIN)

# ===================== Checksum Calculation (per datasheet) =====================
def calc_checksum(frame_data):
    """Sum of first 10 bytes, keep lower 8 bits"""
    return sum(frame_data[:10]) & 0xFF

# ===================== Read One Complete Frame =====================
def CV50_Read_Frame(timeout=0.2):
    """
    Read and validate one data frame
    Return: 11-byte frame list / None (timeout or invalid)
    """
    buf = []
    start_time = time.time()

    # 1. Find frame header 0xDF
    while time.time() - start_time < timeout:
        try:
            byte = UART.uart_read_byte(RX_PIN, CV50_BAUD)
            if byte == CV50_FRAME_HEAD:
                buf.append(byte)
                break
        except:
            continue

    if not buf:
        return None

    # 2. Read remaining 10 bytes
    while len(buf) < CV50_FRAME_LEN:
        if time.time() - start_time >= timeout:
            return None
        try:
            byte = UART.uart_read_byte(RX_PIN, CV50_BAUD)
            buf.append(byte)
        except:
            return None

    # 3. Validate fixed fields
    if buf[1] != CV50_DEV_ID or buf[2] != CV50_SYS_ID or buf[3] != CV50_MSG_ID or buf[5] != CV50_PAYLOAD_LEN:
        return None

    # 4. Validate checksum
    if calc_checksum(buf) != buf[10]:
        return None

    return buf

# ===================== Parse Distance & Signal Strength =====================
def CV50_Get_Data():
    """
    Return:
    - distance_mm: distance in millimeters, -1 on error
    - distance_m: distance in meters
    - signal_strength: signal strength value
    - seq: packet sequence number
    """
    frame = CV50_Read_Frame()
    if not frame:
        return -1, -1, -1, -1

    # Parse fields
    seq = frame[4]
    dist_low = frame[6]
    dist_high = frame[7]
    strength_low = frame[8]
    strength_high = frame[9]

    # Calculate values
    distance_mm = (dist_high << 8) | dist_low
    distance_m = distance_mm / 1000.0
    signal_strength = (strength_high << 8) | strength_low

    return distance_mm, distance_m, signal_strength, seq

# ===================== Main Loop for Continuous Measurement =====================
if __name__ == "__main__":
    # Set GPIO pins (match your hardware wiring)
    UART.TX_PIN["CORVON_TOF_TX"] = 17
    UART.RX_PIN["CORVON_TOF_RX"] = 27

    try:
        CV50_Init()
        print("Start measurement (Ctrl+C to exit)\n")
        
        while True:
            dist_mm, dist_m, strength, seq = CV50_Get_Data()
            if dist_mm >= 0:
                print(f"Seq: {seq:03d} | Dist: {dist_m:5.2f} m | Strength: {strength:5d}")
            else:
                print("Waiting for valid data...")
            time.sleep(0.01)  # 100Hz update rate

    except KeyboardInterrupt:
        print("\nProgram exited")
    finally:
        import RPi.GPIO as GPIO
        GPIO.cleanup()