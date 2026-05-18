#ifndef BC127_DMX_ENGINE_H
#define BC127_DMX_ENGINE_H

// =============================================================================
// dmx_engine.h — DMX universe management, blackout / restore
// =============================================================================

#include <Arduino.h>
#include <esp_dmx.h>
#include "config.h"

// ==== DMX Universe State ====================================================

static uint8_t  dmx_values[MDMX_PACKET_SIZE];   // intended channel values
static uint8_t  dmx_blank[MDMX_PACKET_SIZE];    // all-zero frame for blackout
static bool     dmx_blackout = false;           // blackout flag
static const dmx_port_t DMX_PORT = DMX_NUM_1;   // UART1

// ==== Init ==================================================================

inline void dmx_init() {
    memset(dmx_values, 0, MDMX_PACKET_SIZE);
    memset(dmx_blank,  0, MDMX_PACKET_SIZE);

    dmx_config_t config = DMX_CONFIG_DEFAULT;
    dmx_personality_t personalities[] = {};
    int personality_count = 0;
    dmx_driver_install(DMX_PORT, &config, personalities, personality_count);
    dmx_set_pin(DMX_PORT, DMX_TX_PIN, DMX_RX_PIN, DMX_EN_PIN);
}

// ==== Channel Access (1-based channel number, value 0–255) ==================

inline void dmx_set_channel(uint16_t channel, uint8_t value) {
    if (channel < 1 || channel > DMX_UNIVERSE_SIZE) return;
    dmx_values[channel] = value;
}

inline uint8_t dmx_get_channel(uint16_t channel) {
    if (channel < 1 || channel > DMX_UNIVERSE_SIZE) return 0;
    return dmx_values[channel];
}

// ==== Blackout / Restore ====================================================

inline void dmx_blackout_on() {
    dmx_blackout = true;
}

inline void dmx_blackout_off() {
    dmx_blackout = false;
}

inline bool dmx_is_blackout() {
    return dmx_blackout;
}

// ==== Transmit ==============================================================
// Call this periodically (e.g. every ~25 ms for 40 fps DMX refresh).
// Uses dmx_send_num (esp_dmx v4.1) which blocks until the driver is idle,
// then dmx_wait_sent to ensure the frame is fully on the wire before the
// buffer is touched again on the next iteration.

inline void dmx_transmit() {
    if (dmx_blackout) {
        dmx_write(DMX_PORT, dmx_blank, MDMX_PACKET_SIZE);
    } else {
        dmx_write(DMX_PORT, dmx_values, MDMX_PACKET_SIZE);
    }
    dmx_send_num(DMX_PORT, MDMX_PACKET_SIZE);
    dmx_wait_sent(DMX_PORT, pdMS_TO_TICKS(100));
}

#endif // BC127_DMX_ENGINE_H
