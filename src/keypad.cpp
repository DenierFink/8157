#include "keypad.h"

// Internal debounce state
static Key lastStableKey = KEY_NONE;
static unsigned long lastDebounceTime = 0;

void keypadInit() {
  // If the common line is defined (>=0), drive it LOW so pressed keys
  // connect the key input to LOW. If common is tied to GND on the board
  // define KEYPAD_PIN_COMMON as -1 in `include/keypad.h` and this will
  // be skipped.
#if KEYPAD_PIN_COMMON >= 0
  pinMode(KEYPAD_PIN_COMMON, OUTPUT);
  digitalWrite(KEYPAD_PIN_COMMON, LOW);
#endif
  pinMode(KEYPAD_PIN_UP, INPUT_PULLUP);
  pinMode(KEYPAD_PIN_DOWN, INPUT_PULLUP);
  pinMode(KEYPAD_PIN_LEFT, INPUT_PULLUP);
  pinMode(KEYPAD_PIN_RIGHT, INPUT_PULLUP);
  pinMode(KEYPAD_PIN_OK, INPUT_PULLUP);
}

Key readKeyRaw() {
  if (digitalRead(KEYPAD_PIN_UP) == LOW) return KEY_UP;
  if (digitalRead(KEYPAD_PIN_DOWN) == LOW) return KEY_DOWN;
  if (digitalRead(KEYPAD_PIN_LEFT) == LOW) return KEY_LEFT;
  if (digitalRead(KEYPAD_PIN_RIGHT) == LOW) return KEY_RIGHT;
  if (digitalRead(KEYPAD_PIN_OK) == LOW) return KEY_OK;
  return KEY_NONE;
}

Key readKeyDebounced() {
  Key k = readKeyRaw();
  unsigned long now = millis();
  if (k != lastStableKey) {
    if (now - lastDebounceTime >= KEYPAD_DEBOUNCE_MS) {
      lastDebounceTime = now;
      lastStableKey = k;
    }
  } else {
    lastDebounceTime = now;
  }
  return lastStableKey;
}
