# CV50 TOF 50M Driver -- Maintainer: Jiming Yang
# Dependencies: MentorPi_UART.py

import time
import MentorPi_UART as UART

# ===================== Protocol Constants (From Datasheet) =====================
CV50_FRAME_HEAD = 0xDF  # Frame header
CV50_DEV_ID     = 0x32  # Device ID
CV50_SYS_ID     = 0x00  # System ID
CV50_MSG_ID     = 0x40  # Message ID
CV50_PAYLOAD_LEN= 0x04  # Fixed payload length (4 bytes)
CV50_FRAME_LEN  = 11    # Total frame length (11 bytes)
CV50_DEV_NAME   = "CV50"# Logical device name in MentorPi_UART settings

# ===================== Initialization =====================
def CV50_Init() -> int:
    """
    Initialize CV50 via MentorPi_UART driver.
    (Ensure 'CV50' is configured in MentorPi_UART.serial_pingroups)
    ret: 0: success, 1: failure
    """
    return UART.UART_init(CV50_DEV_NAME)

# ===================== Helper: Read Single Byte =====================
def _read_byte(timeout_seconds: float = 0.1) -> int:
    """
    Private helper: Read 1 byte from UART buffer.
    ret: Byte value (0-255) or -1 on timeout/error
    """
    # We need to loop because UART_receive might return empty if buffer is empty
    start_time = time.time()
    while time.time() - start_time < timeout_seconds:
        data = UART.UART_receive(CV50_DEV_NAME, 1)
        if len(data) == 1:
            return data[0]
        time.sleep(0.001) # Avoid spamming CPU
    return -1

# ===================== Checksum Calculation =====================
def calc_checksum(frame_data: list) -> int:
    """
    Calculate checksum: Sum of first 10 bytes, keep lower 8 bits.
    """
    return sum(frame_data[:10]) & 0xFF

# ===================== Read One Complete Frame =====================
def CV50_Read_Frame(timeout: float = 0.2):
    """
    Read and validate one complete 11-byte data frame.
    Return: 11-byte frame list / None (timeout or invalid)
    """
    buf = []
    start_time = time.time()

    # 1. Find Frame Header (0xDF)
    while time.time() - start_time < timeout:
        byte = _read_byte()
        if byte == CV50_FRAME_HEAD:
            buf.append(byte)
            break

    if not buf:
        return None

    # 2. Read remaining 10 bytes
    while len(buf) < CV50_FRAME_LEN:
        if time.time() - start_time >= timeout:
            return None
        byte = _read_byte()
        if byte != -1:
            buf.append(byte)

    # 3. Validate fixed fields (Device ID, System ID, etc.)
    if (buf[1] != CV50_DEV_ID or 
        buf[2] != CV50_SYS_ID or 
        buf[3] != CV50_MSG_ID or 
        buf[5] != CV50_PAYLOAD_LEN):
        return None

    # 4. Validate Checksum
    if calc_checksum(buf) != buf[10]:
        return None

    return buf

# ===================== Parse Distance & Signal Strength =====================
def CV50_Get_Data():
    """
    Blocking read to get measurement data.
    Return:
        tuple (distance_mm, distance_m, signal_strength, seq)
        Returns (-1, -1, -1, -1) on error
    """
    frame = CV50_Read_Frame()
    if not frame:
        return -1, -1, -1, -1

    # Extract fields from buffer
    seq = frame[4]
    dist_low = frame[6]
    dist_high = frame[7]
    strength_low = frame[8]
    strength_high = frame[9]

    # Calculate values (Little Endian / Big Endian? Check datasheet if swapped)
    # Current logic: High << 8 | Low
    distance_mm = (dist_high << 8) | dist_low
    distance_m = distance_mm / 1000.0
    signal_strength = (strength_high << 8) | strength_low

    return distance_mm, distance_m, signal_strength, seq

# ===================== Main Loop Example =====================
if __name__ == "__main__":
    try:
        # 1. Initialize Driver
        if CV50_Init() != 0:
            print("[ERROR] CV50 Init Failed! Check wiring or permissions.")
            exit(1)
        
        print("[OK] CV50 Initialized")
        print("Start measurement (Ctrl+C to exit)\n")
        print("-" * 50)
        
        # 2. Main Loop
        while True:
            dist_mm, dist_m, strength, seq = CV50_Get_Data()
            
            if dist_mm >= 0:
                print(f"Seq: {seq:03d} | Dist: {dist_m:6.3f} m | Strength: {strength:5d}")
            else:
                # Uncomment below if you want to see errors, or keep silent for cleaner output
                # print("Lost frame...", end='\r') 
                pass
                
            # time.sleep(0.01) # Usually not needed, let CV50_Read_Frame handle timing

    except KeyboardInterrupt:
        print("\n\n[User Exit] Program stopped by Ctrl+C")
    finally:
        # 3. Cleanup
        UART.UART_close_all()
        print("[OK] UART ports closed")

# CV50 TOF 50M Driver -- Maintainer: Jiming Yang
