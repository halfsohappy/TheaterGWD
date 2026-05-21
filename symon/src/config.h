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
// Press count cycles 1 → 2 → … → PRESS_MAX → 1 → …
#define PRESS_MAX     16
#define DEBOUNCE_MS   200

// ── WiFi ─────────────────────────────────────────────────────────────────────
#define WIFI_SSID        "your_ssid"
#define WIFI_PASSWORD    "your_password"
#define WIFI_TIMEOUT_MS  10000

// ── OSC target A — fixed message (same payload every press) ──────────────────
#define OSC_A_IP       "192.168.1.100"   // IP of target A
#define OSC_A_PORT     8000              // UDP port of target A
#define OSC_A_ADDRESS  "/symon/button"   // OSC address for target A
// Payload sent to A on every press (edit as needed):
#define OSC_A_PAYLOAD  1.0f

// ── OSC target B — counter message (payload = current count 1–16) ────────────
#define OSC_B_IP       "192.168.1.101"   // IP of target B
#define OSC_B_PORT     8000              // UDP port of target B
#define OSC_B_ADDRESS  "/symon/count"    // OSC address for target B

// ── OSC buffer ───────────────────────────────────────────────────────────────
#define OSC_BUF_SIZE  256

#endif // SYMON_CONFIG_H
