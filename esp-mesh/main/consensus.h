#ifndef CONSENSUS_H_
#define CONSENSUS_H_

#include <stdint.h>
#include "esp_now.h"

// Select algorithm here
// Comment out to use naive version, #define to use the robust version
// #define ALGO_MODE_ROBUST

void consensus_init(float initial_value, float initial_weight, uint8_t num_nodes, uint8_t (*peer_macs)[6], int p_loss);
void consensus_tx_task(void *pvParameters);
void consensus_rx_callback(const esp_now_recv_info_t *esp_now_info, const uint8_t *data, int data_len);

#endif // CONSENSUS_H_
