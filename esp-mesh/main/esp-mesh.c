#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include "esp_err.h"
#include "esp_wifi_types.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"
#include "nvs.h"
#include "nvs_flash.h"
#include "esp_event.h"
#include "esp_netif.h"
#include "esp_wifi.h"
#include "esp_log.h"
#include "esp_system.h"
#include "esp_now.h"
#include "esp_sleep.h"
#include "esp_mac.h"
#include "esp_random.h"

#include "node_data.h"

SemaphoreHandle_t xMutex;

static const char *TAG = "main";

#define NUM_NODES 4
#define NODE_WEIGHT 1.0
#define MIN_VALUE 10.0 
#define MAX_VALUE 100.0
// Use integers, e.g. 10 % packet loss -> 10, not 0.10
#define PACKET_LOSS 50

/*
c8:f0:9e:2b:e1:50
54:43:b2:e6:50:40 **
3c:e9:0e:08:ec:80
c8:f0:9e:2c:10:70 **
*/

uint8_t nodes_mac[NUM_NODES][6] = {
    {0xc8, 0xf0, 0x9e, 0x2b, 0xe1, 0x50}, // Node 0
    {0x54, 0x43, 0xb2, 0xe6, 0x50, 0x40}, // Node 1
    {0x3c, 0xe9, 0x0e, 0x08, 0xec, 0x80}, // Node 2
    {0xc8, 0xf0, 0x9e, 0x2c, 0x10, 0x70}  // Node 3
};

uint8_t my_mac[6];

node_data_t node_data;

// ESP-NOW recieve callback
static void espnow_recv_cb(const esp_now_recv_info_t *recv_info, const uint8_t *data, int len) {
    node_data_t *received_data = (node_data_t *)data;
    if (xSemaphoreTake(xMutex, portMAX_DELAY)) {
        node_data.value += received_data->value;
        node_data.weight += received_data->weight;
        xSemaphoreGive(xMutex);
    }
}

// Initialize WiFi interface 
void wifi_init(void) {
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));
    ESP_ERROR_CHECK(esp_wifi_set_storage(WIFI_STORAGE_RAM));
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_start());
    ESP_ERROR_CHECK(esp_wifi_set_max_tx_power(8));
    ESP_ERROR_CHECK(esp_wifi_set_channel(8, WIFI_SECOND_CHAN_NONE)); // Use channel 8
}

// Initialize esp-now
void espnow_init(void) {
    // Initialize
    ESP_ERROR_CHECK(esp_now_init());
    // Add espnow recive callback
    ESP_ERROR_CHECK(esp_now_register_recv_cb(espnow_recv_cb));
    // Add the peers
    esp_now_peer_info_t peer = {
        .channel = 8,
        .ifidx = WIFI_IF_STA,
        .encrypt = false
    };
    for (int i = 0; i < NUM_NODES; i++) {
        // Only add peers that are not "you"
        if (memcmp(my_mac, nodes_mac[i], 6) != 0) {
            memcpy(peer.peer_addr, nodes_mac[i], 6);
            ESP_ERROR_CHECK(esp_now_add_peer(&peer));
            ESP_LOGI(TAG, "Added neighbor: " MACSTR, MAC2STR(nodes_mac[i]));
        }
    }
}

// Tx task
void pushSum_Tx_Task(void *pvParameters) {
    vTaskDelay(20000 / portTICK_PERIOD_MS); // initial 20s wait
    while(1) {
        // At each iteration, choose a random node to send msg to (gossip)
        uint32_t rnd_peer = esp_random() % NUM_NODES; // this results in a random integer between 0 and NUM_NODES-1
        while (memcmp(my_mac, nodes_mac[rnd_peer], 6) == 0) {
            rnd_peer = esp_random() % NUM_NODES;
        }
        if (xSemaphoreTake(xMutex, portMAX_DELAY)) {
            node_data.value /= 2.0;
            node_data.weight /= 2.0;
            // Probabilistic packet loss
            if ((esp_random() % 100) >= PACKET_LOSS) {
                esp_err_t ret = esp_now_send(nodes_mac[rnd_peer], (uint8_t *)&node_data, sizeof(node_data_t));
                if (ret != ESP_OK) {
                    ESP_LOGE(TAG, "ESP-NOW Send Failed");
                }
            } else {
                // ESP_LOGW(TAG, "Packet drop.");
            }
            xSemaphoreGive(xMutex);
        }
        // Log current ratio for the logger
        if (xSemaphoreTake(xMutex, portMAX_DELAY)) {
            float current_ratio = node_data.value / node_data.weight;
            ESP_LOGI(TAG, "STATUS MAC=" MACSTR " RATIO=%.5f VAL=%.5f W=%.5f", MAC2STR(my_mac), current_ratio, node_data.value, node_data.weight);
            xSemaphoreGive(xMutex);
        }
        // random delay between 800 ms and 1200 ms
        uint32_t rnd_delay = 800 + (esp_random() % 401);	
        vTaskDelay(rnd_delay / portTICK_PERIOD_MS);
    }
}

// Main
void app_main(void) {
    // Read MAC address
    esp_read_mac(my_mac, ESP_MAC_WIFI_STA);
    // semi-random wait timeout
    uint32_t boot_stagger = my_mac[5] * 30;
    vTaskDelay(boot_stagger / portTICK_PERIOD_MS);
    // NVS Init
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);
    // Turn on Wi-Fi
    wifi_init();

    xMutex = xSemaphoreCreateMutex();
    
    uint32_t int_min = (uint32_t)MIN_VALUE;
    uint32_t int_max = (uint32_t)MAX_VALUE;
    node_data.value = (float)(int_min + (esp_random() % (int_max - int_min + 1)));
    node_data.weight = NODE_WEIGHT; // initial weight of 1.0

    espnow_init();
    
    // Log initial state for the logger
    ESP_LOGI(TAG, "INIT_STATE MAC=" MACSTR " VAL=%.3f WEIGHT=%.3f", MAC2STR(my_mac), node_data.value, node_data.weight);
    
    // create Tx task
    xTaskCreate(pushSum_Tx_Task, "pushSum_Tx_Task", 8152, NULL, 5, NULL);
}
