#Driver for UART -- Matiner:Jiming Yang

import RPi.GPIO as GPIO
import time

# ===================== Project UART Global Settings =====================
TX_PIN = {"CV50_TX": None}
RX_PIN = {"CV50_RX": None}

BAUD_RATE = {"HS": 115200, "LS": 9600}
BIT_DELAY = {"HS": 1.0 / 115200, "LS": 1.0 / 9600}
SAMPLE_DELAY = {"HS": BIT_DELAY["HS"] / 2, "LS": BIT_DELAY["LS"] / 2}

def uart_delay(duration):
    """
    This function enclosed for accurate delay
    duration: unit : S
    """
    
    end = time.perf_counter() + duration
    while time.perf_counter() < end:
        pass

# ===================== UART Initialization =====================
def UART_Init(tx_pin, rx_pin) -> None:
    """
    Initialize UART GPIO pins
    Set TX as output with HIGH idle state, RX as input
    """
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(tx_pin, GPIO.OUT)
    GPIO.output(tx_pin, GPIO.HIGH)
    GPIO.setup(rx_pin, GPIO.IN)

# ===================== UART sends one byte =====================
def uart_send_byte(send_pin, speed: str, byte) -> int:
    """
    Transmit one byte via UART
    Format: start bit(1) + 8 data bits(LSB first) → stop bit(1)
    Return: 0 = success, 1 = failure
    """
    try:
        if speed not in ["HS","LS"]:
            return 1
        if not isinstance(byte,int) or byte < 0 or byte > 255:
            return 1
        
        delay = BIT_DELAY[speed]

        GPIO.output(send_pin, GPIO.LOW)
        uart_delay(delay)

        for i in range(8):
            bit = (byte >> i) & 0x01
            GPIO.output(send_pin, bit)
            uart_delay(delay)

        GPIO.output(send_pin, GPIO.HIGH)
        uart_delay(delay)
        return 0
    except:
        return 1
    
# ===================== send string =====================
def uart_send_str(send_pin, speed: str, string):
    """
    Transmit a string via UART byte by byte
    Convert each character to ASCII code and send
    """
    for char in string:
        uart_send_byte(send_pin, speed, ord(char))

# ===================== Receive One Bit =====================
def uart_read_byte(recv_pin, speed: str):
    """
    Receive one byte via UART
    Sample data at middle of each bit
    Return: received byte value
    """
    delay = BIT_DELAY[speed]
    sample_delay = SAMPLE_DELAY[speed]

    timeout = time.time() + 0.1
    while GPIO.input(recv_pin) == GPIO.HIGH:
        if time.time() > timeout:
            return 0
        pass

    uart_delay(sample_delay)

    byte = 0
    for i in range(8):
        uart_delay(delay)
        bit = GPIO.input(recv_pin)
        byte |= (bit << i)

    uart_delay(delay)
    return byte

# ===================== receive string =====================
def uart_read_str(recv_pin, speed: str, timeout=1.0):
    """
    Receive string via UART with timeout
    Stop when receiving \n or \r
    Return: received string without blank characters
    """
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

