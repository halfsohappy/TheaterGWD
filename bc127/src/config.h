#ifndef BC127_CONFIG_H
#define BC127_CONFIG_H

// =============================================================================
// config.h — Pin definitions and constants for M5Stack CoreS3 + DMX Base
// =============================================================================
//
// Pin mapping from the M5Stack DMX Base (M-BUS) for CoreS3:
//   https://docs.m5stack.com/en/base/DMX_Base
//
// =============================================================================

#include <Arduino.h>

// ==== DMX Base Pin Mapping (CoreS3 M-BUS) ===================================
// Pin map verified against M5Stack DMX Base schematic + CoreS3 M-BUS layout.
// The DMX Base wires TXD/RXD/DE to M-BUS positions that on CoreS3 route to:
#define DMX_TX_PIN   17   // UART TX → RS-485 DI  (CoreS3 GPIO17)
#define DMX_RX_PIN   18   // UART RX → RS-485 RO  (CoreS3 GPIO18)
#define DMX_EN_PIN   10   // RS-485 DE/RE          (CoreS3 GPIO10)

// ==== DMX Constants =========================================================
#define DMX_UNIVERSE_SIZE  512
#define DMX_PACKET_SIZE    513    // start code (0) + 512 channels

// ==== Display Constants =====================================================
#define DISPLAY_WIDTH   320
#define DISPLAY_HEIGHT  240

// ==== OSC Constants =========================================================
#define OSC_RECV_BUF  1024

// ==== OSC Log ===============================================================
#define OSC_LOG_LINES  14   // number of log lines displayed on screen

// ==== Colour Helpers ========================================================
inline uint8_t colour_r(uint32_t rgb) { return (rgb >> 16) & 0xFF; }
inline uint8_t colour_g(uint32_t rgb) { return (rgb >>  8) & 0xFF; }
inline uint8_t colour_b(uint32_t rgb) { return  rgb        & 0xFF; }

// Perceived brightness (fast integer approximation of luminance)
inline uint8_t colour_brightness(uint32_t rgb) {
    uint16_t r = colour_r(rgb);
    uint16_t g = colour_g(rgb);
    uint16_t b = colour_b(rgb);
    return (uint8_t)((r * 77 + g * 150 + b * 29) >> 8);
}

#endif // BC127_CONFIG_H
