#include "frame.h"

// Pointer to the internal serial port handle
static UART_HandleTypeDef *hrrclite_uart = NULL;

// Receive buffer and read/write indices (implementing circular/sliding window logic)
static uint8_t rx_buffer[RRCLITE_RX_BUFFER_SIZE];
static uint16_t rx_head = 0; // Data write position
static uint16_t rx_tail = 0; // Data parsing position

// ================= CRC-L8 checksum algorithm =================
// Corresponds to the following in Python: return sum(data) & 0xFF
static uint8_t CRC_L8(uint8_t *data, uint16_t len) {
    uint32_t sum = 0;
    for (uint16_t i = 0; i < len; i++) {
        sum += data[i];
    }
    return (uint8_t)(sum & 0xFF);
}

// ================= Driver interface implementation =================

// Initialize serial port and internal state
void RRCLite_Init(UART_HandleTypeDef *huart) {
    hrrclite_uart = huart;
    rx_head = 0;
    rx_tail = 0;
    // Enabling serial port idle interrupt or 
    //DMA reception yields better performance; 
    //basic non-blocking reception is used here.
    HAL_UART_Receive_IT(hrrclite_uart, &rx_buffer[rx_head], 1);
}

// Send a frame of data
HAL_StatusTypeDef RRCLite_SendFrame(uint8_t dev_id, uint8_t cmd_id, uint8_t *payload, uint8_t length) {
    if (hrrclite_uart == NULL || length > RRCLITE_MAX_PAYLOAD_LEN) {
        return HAL_ERROR;
    }

    uint8_t frame[6 + RRCLITE_MAX_PAYLOAD_LEN]; 
    uint16_t frame_len = 0;

  
    frame[frame_len++] = RRCLITE_HEADER_1;
    frame[frame_len++] = RRCLITE_HEADER_2;
    
    // Fill in the device ID, command ID and data length
    frame[frame_len++] = dev_id;
    frame[frame_len++] = cmd_id;
    frame[frame_len++] = length;

    // Fill in the data payload
    if (payload != NULL && length > 0) {
        memcpy(&frame[frame_len], payload, length);
        frame_len += length;
    }

    // Calculate and fill CRC (check range: from device ID to data end)
    uint8_t checksum = CRC_L8(&frame[2], frame_len - 2);
    frame[frame_len++] = checksum;

    // Send frame via serial port (blocking transmission, timeout set to 100ms)
    return HAL_UART_Transmit(hrrclite_uart, frame, frame_len, 100);
}

// Receive and parse a frame of data
uint8_t RRCLite_ReceiveFrame(RRCLite_Frame *frame) {
    if (hrrclite_uart == NULL || frame == NULL) return 0;

    // 1. Move UART received data to internal buffer (handling single-byte interrupt reception from HAL library)
    // Note: In actual projects, it's recommended to use DMA or idle interrupts for batch data reception; this is a simplified demonstration
    // Here we assume you call this function frequently in the main loop, or maintain rx_buffer in UART_RX_Callback
    
    // 2. Parse buffer data (imitating sliding window parsing in Python)
    while ((rx_head - rx_tail + RRCLITE_RX_BUFFER_SIZE) % RRCLITE_RX_BUFFER_SIZE >= 6) { // Buffer has at least 6 bytes (minimum frame length)
        
        // Find frame header 0xAA 0x55
        if (rx_buffer[rx_tail] != RRCLITE_HEADER_1) {
            rx_tail = (rx_tail + 1) % RRCLITE_RX_BUFFER_SIZE;
            continue;
        }
        if (rx_buffer[(rx_tail + 1) % RRCLITE_RX_BUFFER_SIZE] != RRCLITE_HEADER_2) {
            rx_tail = (rx_tail + 1) % RRCLITE_RX_BUFFER_SIZE;
            continue;
        }

        // Get data length and calculate full frame length
        uint8_t data_len = rx_buffer[(rx_tail + 4) % RRCLITE_RX_BUFFER_SIZE];
        uint16_t full_frame_len = 2 + 3 + data_len + 1; // Header(2) + Dev(1) + Cmd(1) + Len(1) + Data + CRC(1)

        // Check if the buffer has enough data for the full frame
        uint16_t available_len = (rx_head - rx_tail + RRCLITE_RX_BUFFER_SIZE) % RRCLITE_RX_BUFFER_SIZE;
        if (available_len < full_frame_len) {
            break; // Incomplete data received, exit and wait for the next reception.
        }

        // Extract checksum and calculate CRC
        uint8_t received_crc = rx_buffer[(rx_tail + full_frame_len - 1) % RRCLITE_RX_BUFFER_SIZE];
        
        // Prepare check data (starting from Dev_ID)
        uint8_t check_data[3 + RRCLITE_MAX_PAYLOAD_LEN];
        uint16_t check_idx = 0;
        for (uint16_t i = 2; i < full_frame_len - 1; i++) {
            check_data[check_idx++] = rx_buffer[(rx_tail + i) % RRCLITE_RX_BUFFER_SIZE];
        }

        uint8_t calculated_crc = CRC_L8(check_data, check_idx);

        if (calculated_crc == received_crc) {
        
            frame->dev_id = rx_buffer[(rx_tail + 2) % RRCLITE_RX_BUFFER_SIZE];
            frame->cmd_id = rx_buffer[(rx_tail + 3) % RRCLITE_RX_BUFFER_SIZE];
            frame->length = data_len;
            
            for (uint8_t i = 0; i < data_len; i++) {
                frame->payload[i] = rx_buffer[(rx_tail + 5 + i) % RRCLITE_RX_BUFFER_SIZE];
            }

            // Move the tail pointer to consume this frame of data.
            rx_tail = (rx_tail + full_frame_len) % RRCLITE_RX_BUFFER_SIZE;
            return 1; // Successfully parsed a frame
        } else {
            // CRC verification failed, discard the current frame header, continue searching for the next frame header
            rx_tail = (rx_tail + 1) % RRCLITE_RX_BUFFER_SIZE;
        }
    }
    return 0; 
}

// UART receive interrupt callback function (needs to be called in stm32f4xx_it.c or HAL library callback)
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart) {
    if (huart == hrrclite_uart) {
        // Receive complete, move the head pointer and continue receiving the next byte
        rx_head = (rx_head + 1) % RRCLITE_RX_BUFFER_SIZE;
        // Prevent buffer overflow from overwriting unprocessed data (simple handling: if caught up to tail, pause reception or report error)
        if (rx_head == rx_tail) {
           
        }
        HAL_UART_Receive_IT(hrrclite_uart, &rx_buffer[rx_head], 1);
    }
}