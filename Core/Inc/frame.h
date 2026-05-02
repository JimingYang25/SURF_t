#ifndef __FRAME_H
#define __FRAME_H

#include "stm32f4xx_hal.h"
#include <stdint.h>
#include <string.h>

// ================= Protocol Constant Definitions =================
#define RRCLITE_HEADER_1        0xAA
#define RRCLITE_HEADER_2        0x55
#define RRCLITE_MAX_PAYLOAD_LEN 255
#define RRCLITE_RX_BUFFER_SIZE  512  // receive buffer size, should be large enough to hold multiple frames if needed

// Device ID definitions
typedef enum {
    DEV_ID_RCCLITE = 0x01,
    DEV_ID_OTHERS  = 0xFF
} RRCLite_DeviceID;

// Command ID definitions
typedef enum {
    CMD_ID_OTHERS = 0x00
} RRCLite_CommandID;

// Parsed frame structure
typedef struct {
    uint8_t dev_id;
    uint8_t cmd_id;
    uint8_t length;
    uint8_t payload[RRCLITE_MAX_PAYLOAD_LEN];
} RRCLite_Frame;

// ================= Driver Interface Functions =================

// Initialize UART (bind UART handle)
void RRCLite_Init(UART_HandleTypeDef *huart);

// Send a frame of data
HAL_StatusTypeDef RRCLite_SendFrame(uint8_t dev_id, uint8_t cmd_id, uint8_t *payload, uint8_t length);

// Receive and parse a frame of data (non-blocking, needs to be called periodically in the main loop or timer)
// Return value: 1 indicates a frame was successfully parsed, 0 indicates no complete frame or invalid data
uint8_t RRCLite_ReceiveFrame(RRCLite_Frame *frame);

#endif