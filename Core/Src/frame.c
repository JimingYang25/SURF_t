#include "frame.h"

// 内部使用的串口句柄指针
static UART_HandleTypeDef *hrrclite_uart = NULL;

// 接收缓冲区及读写索引（实现环形/滑动窗口逻辑）
static uint8_t rx_buffer[RRCLITE_RX_BUFFER_SIZE];
static uint16_t rx_head = 0; // 数据写入位置
static uint16_t rx_tail = 0; // 数据解析位置

// ================= CRC-L8 校验算法 =================
// 对应Python中的: return sum(data) & 0xFF
static uint8_t CRC_L8(uint8_t *data, uint16_t len) {
    uint32_t sum = 0;
    for (uint16_t i = 0; i < len; i++) {
        sum += data[i];
    }
    return (uint8_t)(sum & 0xFF);
}

// ================= 驱动接口实现 =================

// 初始化串口
void RRCLite_Init(UART_HandleTypeDef *huart) {
    hrrclite_uart = huart;
    rx_head = 0;
    rx_tail = 0;
    // 开启串口空闲中断或DMA接收效果更佳，这里采用基础的非阻塞接收
    HAL_UART_Receive_IT(hrrclite_uart, &rx_buffer[rx_head], 1);
}

// 发送一帧数据
HAL_StatusTypeDef RRCLite_SendFrame(uint8_t dev_id, uint8_t cmd_id, uint8_t *payload, uint8_t length) {
    if (hrrclite_uart == NULL || length > RRCLITE_MAX_PAYLOAD_LEN) {
        return HAL_ERROR;
    }

    uint8_t frame[6 + RRCLITE_MAX_PAYLOAD_LEN]; // 最大帧长：2(头)+1(设备)+1(命令)+1(长度)+255(数据)+1(CRC)
    uint16_t frame_len = 0;

    // 填充帧头
    frame[frame_len++] = RRCLITE_HEADER_1;
    frame[frame_len++] = RRCLITE_HEADER_2;
    
    // 填充设备ID、命令ID、数据长度
    frame[frame_len++] = dev_id;
    frame[frame_len++] = cmd_id;
    frame[frame_len++] = length;

    // 填充数据载荷
    if (payload != NULL && length > 0) {
        memcpy(&frame[frame_len], payload, length);
        frame_len += length;
    }

    // 计算并填充CRC（校验范围：从设备ID到数据末尾）
    uint8_t checksum = CRC_L8(&frame[2], frame_len - 2);
    frame[frame_len++] = checksum;

    // 通过串口发送（阻塞式发送，超时时间设为100ms）
    return HAL_UART_Transmit(hrrclite_uart, frame, frame_len, 100);
}

// 接收并解析一帧数据
uint8_t RRCLite_ReceiveFrame(RRCLite_Frame *frame) {
    if (hrrclite_uart == NULL || frame == NULL) return 0;

    // 1. 将UART接收到的数据搬运到内部缓冲区（处理HAL库的单字节中断接收）
    // 注意：在实际工程中，建议配合DMA或空闲中断来批量接收数据，此处为简化演示逻辑
    // 这里假设你在主循环中频繁调用此函数，或者在UART_RX_Callback中维护rx_buffer
    
    // 2. 解析缓冲区数据（模仿Python中的滑动窗口解析）
    while ((rx_head - rx_tail + RRCLITE_RX_BUFFER_SIZE) % RRCLITE_RX_BUFFER_SIZE >= 6) { // 缓冲区至少有6字节（最小帧长）
        
        // 寻找帧头 0xAA 0x55
        if (rx_buffer[rx_tail] != RRCLITE_HEADER_1) {
            rx_tail = (rx_tail + 1) % RRCLITE_RX_BUFFER_SIZE;
            continue;
        }
        if (rx_buffer[(rx_tail + 1) % RRCLITE_RX_BUFFER_SIZE] != RRCLITE_HEADER_2) {
            rx_tail = (rx_tail + 1) % RRCLITE_RX_BUFFER_SIZE;
            continue;
        }

        // 获取数据长度，并计算完整帧长度
        uint8_t data_len = rx_buffer[(rx_tail + 4) % RRCLITE_RX_BUFFER_SIZE];
        uint16_t full_frame_len = 2 + 3 + data_len + 1; // Header(2) + Dev(1) + Cmd(1) + Len(1) + Data + CRC(1)

        // 检查缓冲区是否有足够的数据
        uint16_t available_len = (rx_head - rx_tail + RRCLITE_RX_BUFFER_SIZE) % RRCLITE_RX_BUFFER_SIZE;
        if (available_len < full_frame_len) {
            break; // 数据未收全，跳出等待下次接收
        }

        // 提取校验和并计算CRC
        uint8_t received_crc = rx_buffer[(rx_tail + full_frame_len - 1) % RRCLITE_RX_BUFFER_SIZE];
        
        // 准备校验数据（从 Dev_ID 开始）
        uint8_t check_data[3 + RRCLITE_MAX_PAYLOAD_LEN];
        uint16_t check_idx = 0;
        for (uint16_t i = 2; i < full_frame_len - 1; i++) {
            check_data[check_idx++] = rx_buffer[(rx_tail + i) % RRCLITE_RX_BUFFER_SIZE];
        }

        uint8_t calculated_crc = CRC_L8(check_data, check_idx);

        if (calculated_crc == received_crc) {
            // CRC校验通过，提取数据
            frame->dev_id = rx_buffer[(rx_tail + 2) % RRCLITE_RX_BUFFER_SIZE];
            frame->cmd_id = rx_buffer[(rx_tail + 3) % RRCLITE_RX_BUFFER_SIZE];
            frame->length = data_len;
            
            for (uint8_t i = 0; i < data_len; i++) {
                frame->payload[i] = rx_buffer[(rx_tail + 5 + i) % RRCLITE_RX_BUFFER_SIZE];
            }

            // 移动尾部指针，消耗掉这帧数据
            rx_tail = (rx_tail + full_frame_len) % RRCLITE_RX_BUFFER_SIZE;
            return 1; // 成功解析一帧
        } else {
            // CRC校验失败，丢弃当前帧头，继续寻找下一个帧头
            rx_tail = (rx_tail + 1) % RRCLITE_RX_BUFFER_SIZE;
        }
    }
    return 0; // 未解析到有效帧
}

// UART接收中断回调函数（需要在 stm32f4xx_it.c 或 hal 库回调中调用）
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart) {
    if (huart == hrrclite_uart) {
        // 接收完一个字节，移动头部指针并继续接收下一个字节
        rx_head = (rx_head + 1) % RRCLITE_RX_BUFFER_SIZE;
        // 防止缓冲区溢出覆盖未解析的数据（简单处理：如果追上尾部则暂停接收或报错）
        if (rx_head == rx_tail) {
            // 缓冲区满，这里可以做错误处理，比如清空缓冲区或丢弃旧数据
        }
        HAL_UART_Receive_IT(hrrclite_uart, &rx_buffer[rx_head], 1);
    }
}