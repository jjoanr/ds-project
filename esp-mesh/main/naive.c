#include "consensus.h"
#include "esp_random.h"
#include "esp_mac.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include <stdint.h>
#include <string.h>
#include "esp_now.h"

#ifndef ALGO_MODE_ROBUST // if algorithm mode is not robust

static const char *TAG = "naive";

// Data structure for message passing
typedef struct {
    float value;
    float weight;
} payload_t;

// Algorithm state variables
static float s_value;
static float s_weight;
static SemaphoreHandle_t algo_mutex;

static uint8_t (*peers)[6];
static uint8_t num_peers;
static uint8_t my_mac[6];
static int packet_loss;

// Init algorithm
void consensus_init(float initial_value, float initial_weight, uint8_t num_nodes, uint8_t (*peer_macs)[6], int p_loss) {
    s_value = initial_value;
    s_weight = initial_weight;
    num_peers = num_nodes;
    peers = peer_macs;
    packet_loss = p_loss;
    esp_read_mac(my_mac, ESP_MAC_WIFI_STA);
    algo_mutex = xSemaphoreCreateMutex();
}

// Gossip Tx Task
void consensus_tx_task(void *pvParameters) {
    vTaskDelay(20000 / portTICK_PERIOD_MS); // initial 20s wait
    while(1) {
        // Choose a random node to send msg to
        uint32_t rnd_peer = esp_random() % num_peers; 
        while (memcmp(my_mac, peers[rnd_peer], 6) == 0) {
            rnd_peer = esp_random() % num_peers;
        }
        
	payload_t tx_payload; // Create a struct to send
        
	if (xSemaphoreTake(algo_mutex, portMAX_DELAY)) {
            // Halve the internal state
            s_value /= 2.0f;
            s_weight /= 2.0f;
            // Pack the halved state into the payload
            tx_payload.value = s_value;
            tx_payload.weight = s_weight;
            // Probabilistic packet loss
            if ((esp_random() % 100) >= packet_loss) {
                esp_err_t ret = esp_now_send(peers[rnd_peer], (uint8_t *)&tx_payload, sizeof(payload_t));
                if (ret != ESP_OK) {
                    ESP_LOGE(TAG, "ESP-NOW Send Failed");
                }
            }
            xSemaphoreGive(algo_mutex);
        }
        // Log current ratio for the logger
        if (xSemaphoreTake(algo_mutex, portMAX_DELAY)) {
            float current_ratio = s_value / s_weight;
            ESP_LOGI(TAG, "STATUS MAC=" MACSTR " RATIO=%.5f VAL=%.5f W=%.5f", 
                     MAC2STR(my_mac), current_ratio, s_value, s_weight);
            xSemaphoreGive(algo_mutex);
        }
	
        // random delay between 800 ms and 1200 ms
        uint32_t rnd_delay = 800 + (esp_random() % 401);	
        vTaskDelay(rnd_delay / portTICK_PERIOD_MS);
    }
}

// RX Callback
void consensus_rx_callback(const esp_now_recv_info_t *esp_now_info, const uint8_t *data, int data_len) {
    if (data_len == sizeof(payload_t)) {
        payload_t *received_data = (payload_t *)data;
        if (xSemaphoreTake(algo_mutex, portMAX_DELAY)) {
            s_value += received_data->value;
            s_weight += received_data->weight;

            xSemaphoreGive(algo_mutex);
        }
    }
}

#endif
