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

#include "consensus.h"

static const char *TAG = "main";

// Config parameters
#define NUM_NODES 8

#define NODE_WEIGHT 1.0
#define MIN_VALUE 10.0 
#define MAX_VALUE 100.0
// Define packet loss (in %)
// e.g. 10% packet loss -> PACKET_LOSS 10
#define PACKET_LOSS 50

/*
// 4-node mesh
c8:f0:9e:2b:e1:50
54:43:b2:e6:50:40 **
3c:e9:0e:08:ec:80
c8:f0:9e:2c:10:70 **

// 8-node mesh
34:86:5d:fd:3a:38
c8:f0:9e:a1:19:70
e0:e2:e6:ac:97:dc
a0:dd:6c:03:2f:88
*/

uint8_t nodes_mac[NUM_NODES][6] = {
    {0xc8, 0xf0, 0x9e, 0x2b, 0xe1, 0x50},  // Node 1
    {0x54, 0x43, 0xb2, 0xe6, 0x50, 0x40},  // Node 2
    {0x3c, 0xe9, 0x0e, 0x08, 0xec, 0x80},  // Node 3
    {0xc8, 0xf0, 0x9e, 0x2c, 0x10, 0x70},  // Node 4

    {0x34, 0x86, 0x5d, 0xfd, 0x3a, 0x38},  // Node 5
    {0xc8, 0xf0, 0x9e, 0xa1, 0x19, 0x70},  // Node 6
    {0xe0, 0xe2, 0xe6, 0xac, 0x97, 0xdc},  // Node 7
    {0xa0, 0xdd, 0x6c, 0x03, 0x2f, 0x88}   // Node 8
};

uint8_t my_mac[6];

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
    ESP_ERROR_CHECK(esp_now_register_recv_cb(consensus_rx_callback));
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

// Main
void app_main(void) {
    // NVS Init
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);
    // Turn on Wi-Fi
    wifi_init();
	
    uint32_t delay_ms = (esp_random() % 2000) + 5000;
    vTaskDelay(pdMS_TO_TICKS(delay_ms));
    
    esp_read_mac(my_mac, ESP_MAC_WIFI_STA);
    espnow_init();

    uint32_t int_min = (uint32_t)MIN_VALUE;
    uint32_t int_max = (uint32_t)MAX_VALUE;
    float initial_value = (float)(int_min + (esp_random() % (int_max - int_min + 1)));
    float initial_weight = NODE_WEIGHT; // initial weight of 1.0
    
    // Log initial state for the logger
    ESP_LOGI(TAG, "INIT_STATE MAC=" MACSTR " VAL=%.3f WEIGHT=%.3f", MAC2STR(my_mac), initial_value, initial_weight);

    // initialize the algorithm
    consensus_init(initial_value, initial_weight, NUM_NODES, nodes_mac, PACKET_LOSS);
    
    // create Tx task (defined either in naive.c or robust.c)
    xTaskCreate(consensus_tx_task, "consensus_tx_task", 8152, NULL, 5, NULL);
}
