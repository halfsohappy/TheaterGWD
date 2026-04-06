// symon — centre-button OSC sender
//
// Hardware:
//   - Olimex ESP32-C3-DevKit-Lipo (or compatible ESP32-C3 board)
//   - SSD1306 128×64 OLED display (I2C, 0x3C)
//   - Adafruit Seesaw ANO Rotary Navigation Encoder (I2C, 0x49)
//
// Each press of the ANO centre button:
//   1. Increments a counter that cycles 0 → 1 → … → 14 → 0
//   2. Updates the OLED display with the current count
//   3. Sends an OSC message over WiFi (see config.h for address and options)

#include <Arduino.h>
#include <Wire.h>
#include <WiFi.h>
#include <WiFiUdp.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <Adafruit_seesaw.h>
#include <MicroOsc.h>
#include <MicroOscUdp.h>
#include "config.h"

// ── Globals ──────────────────────────────────────────────────────────────────

static Adafruit_SSD1306         display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);
static Adafruit_seesaw          seesaw;
static WiFiUDP                  udp;
static MicroOscUdp<OSC_BUF_SIZE> osc(&udp);

static int           press_count = 0;
static bool          btn_last    = true;    // true = released (pull-up, active-low)
static unsigned long btn_time    = 0;

// ── Display ──────────────────────────────────────────────────────────────────

static void display_count(int count) {
    display.clearDisplay();
    display.setTextColor(SSD1306_WHITE);

    // Small header row
    display.setTextSize(1);
    display.setCursor(0, 0);
    display.print("symon   ");
    display.print(count);
    display.print(" / ");
    display.print(PRESS_MAX);

    // Large count centred on screen
    display.setTextSize(4);
    String num = String(count);
    int16_t  x1, y1;
    uint16_t w, h;
    display.getTextBounds(num, 0, 0, &x1, &y1, &w, &h);
    display.setCursor((SCREEN_WIDTH - (int16_t)w) / 2,
                      (SCREEN_HEIGHT - (int16_t)h) / 2 + 4);
    display.print(num);

    display.display();
}

static void display_status(const char* line1, const char* line2 = nullptr) {
    display.clearDisplay();
    display.setTextSize(1);
    display.setTextColor(SSD1306_WHITE);
    display.setCursor(0, 0);
    display.println(line1);
    if (line2) display.println(line2);
    display.display();
}

// ── WiFi ─────────────────────────────────────────────────────────────────────

static void wifi_connect() {
    display_status("Connecting WiFi...", WIFI_SSID);
    Serial.printf("[WiFi] Connecting to %s\n", WIFI_SSID);

    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    unsigned long t0 = millis();
    while (WiFi.status() != WL_CONNECTED) {
        if (millis() - t0 > WIFI_TIMEOUT_MS) {
            Serial.println("[WiFi] Timeout — running offline");
            display_status("WiFi timeout", "Running offline");
            delay(1500);
            return;
        }
        delay(200);
    }

    Serial.printf("[WiFi] Connected: %s\n", WiFi.localIP().toString().c_str());
    udp.begin(9000);
    osc.setDestination(OSC_TARGET_IP, OSC_TARGET_PORT);
}

// ── OSC ──────────────────────────────────────────────────────────────────────

static void send_osc(int count) {
    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("[OSC] Offline — skipping send");
        return;
    }

#if OSC_INCLUDE_COUNT
    osc.sendFloat(OSC_ADDRESS, (float)count);
    Serial.printf("[OSC] %s %.0f\n", OSC_ADDRESS, (float)count);
#else
    osc.sendFloat(OSC_ADDRESS, 1.0f);
    Serial.printf("[OSC] %s\n", OSC_ADDRESS);
#endif
}

// ── Setup ────────────────────────────────────────────────────────────────────

void setup() {
    Serial.begin(115200);
    delay(200);

    Wire.begin(PIN_SDA, PIN_SCL);

    // OLED
    if (!display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR)) {
        Serial.println("[OLED] Init failed — halting");
        while (true) delay(500);
    }
    display.clearDisplay();
    display.display();

    // Seesaw ANO
    if (!seesaw.begin(SEESAW_ADDR)) {
        Serial.println("[Seesaw] Init failed — halting");
        display_status("Seesaw fail", "check wiring");
        while (true) delay(500);
    }
    seesaw.pinMode(SS_BTN_SELECT, INPUT_PULLUP);
    btn_last = seesaw.digitalRead(SS_BTN_SELECT);
    Serial.println("[Seesaw] OK");

    // WiFi + OSC
    wifi_connect();

    // Show initial count
    display_count(press_count);
    Serial.println("[symon] Ready");
}

// ── Loop ─────────────────────────────────────────────────────────────────────

void loop() {
    bool btn_now = seesaw.digitalRead(SS_BTN_SELECT);

    // Falling edge = button just pressed (active-low with internal pull-up)
    if (!btn_now && btn_last && (millis() - btn_time > DEBOUNCE_MS)) {
        btn_time    = millis();
        press_count = (press_count + 1) % (PRESS_MAX + 1);

        Serial.printf("[button] count = %d\n", press_count);
        display_count(press_count);
        send_osc(press_count);
    }

    btn_last = btn_now;
    delay(10);
}
