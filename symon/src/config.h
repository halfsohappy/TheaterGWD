#ifndef SYMON_CONFIG_H
#define SYMON_CONFIG_H

// ============================================================================
//  symon — Configuration
// ============================================================================

// ── I2C pins (Olimex ESP32-C3-DevKit-Lipo) ──────────────────────────────────
#define PIN_SDA  8
#define PIN_SCL  9

// ── SSD1306 128×64 OLED Display ─────────────────────────────────────────────
#define SCREEN_WIDTH   128
#define SCREEN_HEIGHT  64
#define OLED_ADDR      0x3C
#define OLED_RESET     -1       // share reset with MCU (no dedicated pin)

// ── Adafruit Seesaw ANO Rotary Navigation Encoder ───────────────────────────
#define SEESAW_ADDR    0x49
#define SS_BTN_SELECT  1        // centre button seesaw GPIO pin
#define SS_NEOPIX_PIN  18       // NeoPixel ring data pin on seesaw
#define SS_NEOPIX_NUM  8        // 8-pixel ring

// ── Button counter ───────────────────────────────────────────────────────────
// Press count cycles 0 → 1 → 2 → … → PRESS_MAX → 0 → …
#define PRESS_MAX     14
#define DEBOUNCE_MS   200

// ── WiFi ─────────────────────────────────────────────────────────────────────
#define WIFI_SSID        "your_ssid"
#define WIFI_PASSWORD    "your_password"
#define WIFI_TIMEOUT_MS  10000

// ── OSC target ───────────────────────────────────────────────────────────────
#define OSC_TARGET_IP    "192.168.1.100"  // IP of the receiving host
#define OSC_TARGET_PORT  8000             // UDP port of the receiving host
#define OSC_ADDRESS      "/symon/button"  // OSC address to send

// ── OSC count option ─────────────────────────────────────────────────────────
// Set to 1 to include the current press count as a float argument in each
// OSC message.  Set to 0 to send the address with no argument (bare trigger).
//
// You can also embed the count in the address itself by building a dynamic
// address string in send_osc() in main.cpp, e.g.:
//   snprintf(addr, sizeof(addr), "/symon/button/%d", count);
#define OSC_INCLUDE_COUNT  1

// ── OSC buffer ───────────────────────────────────────────────────────────────
#define OSC_BUF_SIZE  256

#endif // SYMON_CONFIG_H
