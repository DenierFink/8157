#pragma once
#include <Arduino.h>

// Keypad pin configuration (override in build or before including to change pins)
#ifndef KEYPAD_PIN_COMMON
#define KEYPAD_PIN_COMMON -1 // common wire: set to -1 when common is tied to board GND (not driven by software)
#endif
#ifndef KEYPAD_PIN_UP
#define KEYPAD_PIN_UP 4  // safe GPIO (avoid 26..32 which go to flash/PSRAM)
#endif
#ifndef KEYPAD_PIN_DOWN
#define KEYPAD_PIN_DOWN 5
#endif
#ifndef KEYPAD_PIN_LEFT
#define KEYPAD_PIN_LEFT 16
#endif
#ifndef KEYPAD_PIN_RIGHT
#define KEYPAD_PIN_RIGHT 17
#endif
#ifndef KEYPAD_PIN_OK
#define KEYPAD_PIN_OK 18
#endif

// Debounce settings (ms)
#ifndef KEYPAD_DEBOUNCE_MS
#define KEYPAD_DEBOUNCE_MS 30
#endif

typedef enum {
  KEY_NONE = 0,
  KEY_UP,
  KEY_DOWN,
  KEY_LEFT,
  KEY_RIGHT,
  KEY_OK
} Key;

// Initialize keypad hardware (call once in setup)
void keypadInit();

// Read raw key (no debounce)
Key readKeyRaw();

// Read debounced key (call frequently)
Key readKeyDebounced();
