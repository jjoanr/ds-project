idf_component_register(SRCS "esp-mesh.c" "naive.c" "robust.c"
                    PRIV_REQUIRES nvs_flash esp_event esp_netif esp_wifi
                    INCLUDE_DIRS ".")
