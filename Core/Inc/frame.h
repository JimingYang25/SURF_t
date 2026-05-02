#ifndef __FRAME_H
#define __FRAME_H

#include "stm32f4xx_hal.h"
#include <stdint.h>
#include <string.h>

// ================= 协议常量定义 =================
#define RRCLITE_HEADER_1        0xAA
#define RRCLITE_HEADER_2        0x55
#define RRCLITE_MAX_PAYLOAD_LEN 255
#define RRCLITE_RX_BUFFER_SIZE  512  // 接收缓冲区大小，可根据实际需求调整

// 设备ID定义
typedef enum {
    DEV_ID_RCCLITE = 0x01,
    DEV_ID_OTHERS  = 0xFF
} RRCLite_DeviceID;

// 命令ID定义（根据你的Python代码，目前Others为None，这里预留）
typedef enum {
    CMD_ID_OTHERS = 0x00
} RRCLite_CommandID;

// 解析后的帧结构体
typedef struct {
    uint8_t dev_id;
    uint8_t cmd_id;
    uint8_t length;
    uint8_t payload[RRCLITE_MAX_PAYLOAD_LEN];
} RRCLite_Frame;

// ================= 驱动接口函数 =================

// 初始化串口（绑定UART句柄）
void RRCLite_Init(UART_HandleTypeDef *huart);

// 发送一帧数据
HAL_StatusTypeDef RRCLite_SendFrame(uint8_t dev_id, uint8_t cmd_id, uint8_t *payload, uint8_t length);

// 接收并解析一帧数据（非阻塞，需在主循环或定时器中周期性调用）
// 返回值: 1 表示成功解析到一帧，0 表示暂无完整帧或数据无效
uint8_t RRCLite_ReceiveFrame(RRCLite_Frame *frame);

#endif