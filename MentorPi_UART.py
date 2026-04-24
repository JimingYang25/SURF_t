#Driver for UART -- Matiner:Jiming Yang

import RPi.GPIO as GPIO
import time

# ===================== Project UART Global Settings =====================
# Transit Pin
TX_PIN = {"CV50_TX": None}

# Receive Pin
RX_PIN = {"CV50_RX": None}

# Baud rate
BAUD_RATE = {"HS": 115200, "LS": 9600}
BIT_DELAY = {"HS": 1.0 / 115200, "LS": 1.0 / 9600}
SAMPLE_DELAY = {"HS": BIT_DELAY["HS"] / 2, "LS": BIT_DELAY["LS"] / 2}

# ===================== UART Initialization =====================
def UART_Init(tx_pin,rx_pin) -> None:
    """Init the GPIO part for UART"""
    GPIO.setmode(GPIO.BCM)
    # Initialize the send pin
    GPIO.setup(tx_pin, GPIO.OUT)
    GPIO.output(tx_pin, GPIO.HIGH)

    # Initialize the receive pin   
    GPIO.setup(rx_pin, GPIO.IN)

# ===================== UART sends one byte =====================
def uart_send_byte(send_pin, speed: str, byte):
    """
    UART timing transmission single-byte timing: 
    start bit → 8-bit data (LSB first) → 
    stop bit speed: "HS" or "LS"
    """
    delay = BIT_DELAY[speed]

    # 1. Starting position
    GPIO.output(send_pin, GPIO.LOW)
    time.sleep(delay)

    # 2. 8-bit data (low start)
    for i in range(8):
        bit = (byte >> i) & 0x01
        GPIO.output(send_pin, bit)
        time.sleep(delay)

    # 3. Stoping position
    GPIO.output(send_pin, GPIO.HIGH)
    time.sleep(delay)

# ===================== send string =====================
def uart_send_str(send_pin, speed: str, string):
    for char in string:
        uart_send_byte(send_pin, speed, ord(char))

# ===================== Receive One Bit =====================
def uart_read_byte(recv_pin, speed: str):
    delay = BIT_DELAY[speed]
    sample_delay = SAMPLE_DELAY[speed]

    # Waiting for starting position
    while GPIO.input(recv_pin) == GPIO.HIGH:
        pass

    time.sleep(sample_delay)

    byte = 0
    for i in range(8):
        time.sleep(delay)
        bit = GPIO.input(recv_pin)
        byte |= (bit << i)

    time.sleep(delay)
    return byte

# ===================== receive string =====================
def uart_read_str(recv_pin, speed: str, timeout=1.0):
    start_time = time.time()
    recv_str = ""
    while time.time() - start_time < timeout:
        try:
            char = uart_read_byte(recv_pin, speed)
            recv_str += chr(char)
            if char in (ord('\n'), ord('\r')):
                break
        except:
            pass
    return recv_str.strip()

#Driver for UART -- Matiner:Jiming Yang