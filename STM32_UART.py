# Driver for RCCLite — Maintainer: Jiming Yang
# Dependencies: MentorPi_UART.py

import struct
import time
import MentorPi_UART as UART

# ================= Protocol constances =================
# frame: Header(2bytes) + Device_ID(1byte) + Command_ID(1byte) + 
#        
#        data_length(1byte,max=255) + data + CRC(1byte)

HEADER = bytes([0xAA, 0x55])    # Framer header (fixed 2 bytes)
DEV_ID ={
         "RCCLite" : 0x01 ,
         "Others"  : None       #future add
         
         }               
CMD_ID ={
         "Others"  : None       #future add

        }

# ================= CRC function =================
def CRC_L8(data: bytes) -> int:
    """
    CRC-L8 Text:lower 8 digits
    of sum of former bytes
    """
    return sum(data) & 0xFF


def build_frame(dev_id: int, cmd_id: int, payload: bytes) -> bytes:
    """Build 1 frame"""
    
    length = len(payload)
    # text scope : from CMD_ID to data tail
    check_data = bytes([dev_id, cmd_id, length]) + payload
    checksum = CRC_L8(check_data)
    frame = HEADER + check_data + bytes([checksum])
    return frame


def parse_frame(frame: bytes) -> tuple[int, int, bytes] | None:
    """
    paraphrase a frame,return (dev_id, cmd_id, payload) or invalid frame(None) 
    Input should be a valid frame from other slave devices
    """
    if len(frame) < 6:
        return None
    if frame[0:2] != HEADER:
        return None
    check_data = frame[2:-1]
    if CRC_L8(check_data) != frame[-1]:
        return None
    dev_id = frame[2]
    cmd_id = frame[3]
    length = frame[4]
    payload = frame[5:5 + length]
    return dev_id, cmd_id, payload

#---------------------- RRCLite Correspond Class ------------------------

class RRCLite_Serial:
    __MAX_BUFFER = 4096
    def __init__(self,timeout=1.0):
        self.device_name = "RRCLite"
        self.buffer = bytearray()
        self.error_status=0
        self.timeout=timeout
        

    def error_handler_(self):
        """0 : success , others: error number """
        if self.error_status== 1:      # Open serial port error
            #self.get_logger().error("Open serial port error")
            pass
        elif self.error_status==2:     # Send frame error
            #self.get_logger().error("Send frame error")
            pass
        elif self.error_status==3:     # Close serial port error
            #self.get_logger().error("Close serial port error")
            pass

    def init_(self) -> int:
        """Open serial port. Return 0 or error 1."""
        ret = UART.UART_init(device_name=self.device_name,timeout=self.timeout)
        if ret != 0:
            self.error_status=1
            self.error_handler_()
            return 1
        UART.UART_flush(self.device_name)
        return 0

    # Pi Send a frame to RRCLite
    def send_frame_(self, frame: bytes) -> int:
        """ Send a pre-built frame via UART. Return 0:success or 1:error ."""
        ret = UART.UART_send(self.device_name, frame)
        if ret != 0:
            self.error_status=2
            self.error_handler_()
            return 1
        return 0

    def receive_frame_(self) -> tuple[int, int, bytes] | None:
        """
        Non-blocking receive. Returns (dev_id, cmd_id, payload) or None.
        Call this method periodically (e.g., in a ROS 2 timer callback).
        """
        raw = UART.UART_receive(self.device_name, num_bytes=256)
        if raw:
            self.buffer.extend(raw)
        
        # Handle buffer overload
        if len(self.buffer) > __MAX_BUFFER:
            self.buffer.clear()

        while len(self.buffer) >= 6:
            if self.buffer[0:2] != HEADER:
                del self.buffer[0]
                continue
            data_len = self.buffer[4]
            frame_len = 2 + 3 + data_len + 1
            if len(self.buffer) < frame_len:
                break
            candidate = self.buffer[:frame_len]
            check_data = candidate[2:-1]
            if CRC_L8(check_data) == candidate[-1]:
                dev_id = candidate[2]
                cmd_id = candidate[3]
                payload = candidate[5:5 + data_len]
                del self.buffer[:frame_len]
                return dev_id, cmd_id, payload
            else:
                del self.buffer[0]
        return None

    def deinit_(self) -> int :
       if UART.UART_deinit(device_name=self.device_name) :
           self.error_status=3
           self.error_handler_()
           return 1
       return 0

# Driver for RCCLite — Maintainer: Jiming Yang


