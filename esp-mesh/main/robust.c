#include "consensus.h"
#include "esp_random.h"
#include "esp_mac.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include <stdint.h>
#include <string.h>

#ifdef ALGO_MODE_ROBUST

static const char *TAG = "robust";

// Data structure for message passing
typedef struct {
    float s_flow;
    float w_flow;
} payload_t;

// Tracking table for Flow-Updating
typedef struct {
    uint8_t mac[6];
    float S_s; // Cumulative sent value
    float S_w; // Cumulative sent weight
    float R_s; // Cumulative received value
    float R_w; // Cumulative received weight
} peer_state_t;

// Algorithm state variables
static float s_value;
static float s_weight;
static SemaphoreHandle_t algo_mutex;

static peer_state_t peer_tables[20]; // Safely sized array for up to 20 peers
static uint8_t num_peers;
static uint8_t my_mac[6];
static int packet_loss;

// Find a peer's index in the tracking table
static int get_peer_index(const uint8_t *mac) {
    for (int i = 0; i < num_peers; i++) {
        if (memcmp(peer_tables[i].mac, mac, 6) == 0) {
            return i;
        }
    }
    return -1; // Peer not found
}

// Init algorithm
void consensus_init(float initial_value, float initial_weight, uint8_t num_nodes, uint8_t (*peer_macs)[6], int p_loss) {
    s_value = initial_value;
    s_weight = initial_weight;
    num_peers = num_nodes;
    packet_loss = p_loss;
    
    esp_read_mac(my_mac, ESP_MAC_WIFI_STA);
    algo_mutex = xSemaphoreCreateMutex();

    // Initialize tracking tables for all peers to zero
    for (int i = 0; i < num_peers; i++) {
        memcpy(peer_tables[i].mac, peer_macs[i], 6);
        peer_tables[i].S_s = 0.0f;
        peer_tables[i].S_w = 0.0f;
        peer_tables[i].R_s = 0.0f;
        peer_tables[i].R_w = 0.0f;
    }
}

// Gossip Tx Task
void consensus_tx_task(void *pvParameters) {
    vTaskDelay(20000 / portTICK_PERIOD_MS); // initial 20s wait
    while(1) {
        // Choose a random node to send msg to
        uint32_t rnd_peer_idx = esp_random() % num_peers; 
        while (memcmp(my_mac, peer_tables[rnd_peer_idx].mac, 6) == 0) {
            rnd_peer_idx = esp_random() % num_peers;
        }

        payload_t tx_payload;

        if (xSemaphoreTake(algo_mutex, portMAX_DELAY)) {
            // Halve the internal state
            s_value /= 2.0f;
            s_weight /= 2.0f;
            // Add state to cumulative sent flow for this specific neighbor
            peer_tables[rnd_peer_idx].S_s += s_value;
            peer_tables[rnd_peer_idx].S_w += s_weight;
            // Add cumulative flow into the payload
            tx_payload.s_flow = peer_tables[rnd_peer_idx].S_s;
            tx_payload.w_flow = peer_tables[rnd_peer_idx].S_w;
            // Probabilistic packet loss
            if ((esp_random() % 100) >= packet_loss) {
                esp_err_t ret = esp_now_send(peer_tables[rnd_peer_idx].mac, (uint8_t *)&tx_payload, sizeof(payload_t));
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
        // Find transmitter
        int peer_idx = get_peer_index(esp_now_info->src_addr);
        if (peer_idx == -1) return; // Unknown sender, ignore
        if (xSemaphoreTake(algo_mutex, portMAX_DELAY)) {
            // Calculate the deltas (differences)
            float delta_s = received_data->s_flow - peer_tables[peer_idx].R_s;
            float delta_w = received_data->w_flow - peer_tables[peer_idx].R_w;
            // Add deltas to our local state
            s_value += delta_s;
            s_weight += delta_w;
            // Update the last known successfully received cumulative flow
            peer_tables[peer_idx].R_s = received_data->s_flow;
            peer_tables[peer_idx].R_w = received_data->w_flow;
            
            xSemaphoreGive(algo_mutex);
        }
    }
}

#endif
