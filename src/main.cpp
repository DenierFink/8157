// Simple bit-banged LCD driver (SPI-like with D/C) for ESP32-S3
// Assumptions based on reverse engineering:
// - CS: active low
// - D/C: 0 = command, 1 = data
// - RST: active low
// - Data (MOSI) sampled on SCK rising edge, MSB first
// - Display uses 5x7 font, vertical columns per byte
//
// Display resolution: 132 columns × 48 rows (6 pages × 8 pixels)
// Visible area: columns 0-131, rows 0-47
//
// Features:
// - Framebuffer-based rendering (792 bytes RAM)
// - Graphics primitives: lines, rectangles, circles, filled shapes
// - Multiple fonts: 3x5 (compact), 5x7 (standard)
// - Bitmap support with PROGMEM
// - PWM backlight control (GPIO 15)
// - Public domain fonts included

#include <Arduino.h>
#include "font3x5.h"  // Compact 3x5 font for labels/small text
#include "font5x7.h"  // Standard 5x7 font (public domain)

// ======== Display resolution ========
#define LCD_WIDTH  132
#define LCD_HEIGHT 48
#define LCD_PAGES  6   // 48 rows / 8 pixels per page

// ======== Framebuffer ========
static uint8_t lcdBuffer[LCD_PAGES][LCD_WIDTH];

// ======== Pin configuration (change to match your wiring) ========
#ifndef LCD_PIN_CS
#define LCD_PIN_CS   10
#endif
#ifndef LCD_PIN_DC
#define LCD_PIN_DC   11
#endif
#ifndef LCD_PIN_RST
#define LCD_PIN_RST  12
#endif
#ifndef LCD_PIN_SCK
#define LCD_PIN_SCK  13
#endif
#ifndef LCD_PIN_MOSI
#define LCD_PIN_MOSI 14
#endif
#ifndef LCD_PIN_BACKLIGHT
#define LCD_PIN_BACKLIGHT 15  // PWM para controle de brilho
#endif


#include "keypad.h"

// PWM config para backlight
#define LCD_BACKLIGHT_CHANNEL 0
#define LCD_BACKLIGHT_FREQ    5000  // 5 kHz
#define LCD_BACKLIGHT_RESOLUTION 8  // 8 bits (0-255)

// Small delay to control bit-bang speed (microseconds)
static inline void tickDelay() {
  // ~1 MHz toggling if 0; increase if wiring/display needs slower clock
  // delayMicroseconds(1);
}

// ======== Low-level GPIO helpers ========
static inline void lcdCS(bool level)   { digitalWrite(LCD_PIN_CS,   level); }
static inline void lcdDC(bool level)   { digitalWrite(LCD_PIN_DC,   level); }
static inline void lcdRST(bool level)  { digitalWrite(LCD_PIN_RST,  level); }
static inline void lcdSCK(bool level)  { digitalWrite(LCD_PIN_SCK,  level); }
static inline void lcdMOSI(bool level) { digitalWrite(LCD_PIN_MOSI, level); }

// Write one byte MSB first on falling edge (clock idles HIGH)
static void lcdWriteByte(uint8_t b) {
  for (int i = 7; i >= 0; --i) {
    lcdSCK(LOW);   // clock goes low
    lcdMOSI((b >> i) & 0x01);
    tickDelay();
    lcdSCK(HIGH);  // clock returns high (data sampled on rising edge)
    tickDelay();
  }
  // Clock stays HIGH at idle
}

static void lcdWriteCommand(uint8_t cmd) {
  lcdCS(LOW);
  lcdDC(LOW);
  lcdWriteByte(cmd);
  lcdCS(HIGH);
}

static void lcdWriteData(uint8_t data) {
  lcdCS(LOW);
  lcdDC(HIGH);
  lcdWriteByte(data);
  lcdCS(HIGH);
}

static void lcdWriteDataBuffer(const uint8_t* buf, size_t len) {
  lcdCS(LOW);
  lcdDC(HIGH);
  for (size_t i = 0; i < len; ++i) {
    lcdWriteByte(buf[i]);
  }
  lcdCS(HIGH);
}

// Draw alternating vertical lines across the display (column stripes)
// Useful to count available visible columns. totalCols can be 128 or 132.
// (moved below once addressing helpers are declared)

// ======== Common page/column addressing (typical UC1701/ST7565 family) ========
// If your controller differs, adjust these.
static void lcdSetPage(uint8_t page) {            // page: 0..7
  lcdWriteCommand(0xB0 | (page & 0x0F));
}

static void lcdSetColumn(uint8_t col) {           // col: 0..127
  lcdWriteCommand(0x10 | ((col >> 4) & 0x0F));
  lcdWriteCommand(0x00 | (col & 0x0F));
}

// Draw alternating vertical lines across the display (column stripes)
// Useful to count available visible columns. totalCols can be 128 or 132.
static void lcdDrawInterleavedVerticalLines(uint8_t totalCols = LCD_WIDTH, bool evenOn = true) {
  for (uint8_t page = 0; page < LCD_PAGES; ++page) {
    lcdSetPage(page);
    lcdSetColumn(0);
    for (uint8_t col = 0; col < totalCols; ++col) {
      bool on = ((col & 1) == 0) == evenOn; // even columns ON when evenOn=true
      lcdWriteData(on ? 0xFF : 0x00);
    }
  }
}

// Font selector enum (needed for forward declarations)
enum FontSize {
  FONT_3X5 = 0,
  FONT_5X7 = 1
};

// Forward declarations
static void lcdDrawNumber(uint8_t page, uint8_t col, int num, FontSize font = FONT_5X7);
static void demoTextScrollBitmap();
static void demoGraphicsPrimitives();
static void demoFontSelfTest();
static void demoAllFeatures();
static void demoKeypadTest();
static void demoPinScanner();

// ======== Keypad API ========
// Declarations live in include/keypad.h, implementation in src/keypad.cpp

// ======== Framebuffer operations ========

// Set backlight brightness (0-255, invertido: 0=mais brilhante, 255=apagado)
static void lcdSetBacklight(uint8_t brightness) {
  // Lógica normal: 0 = desligado (LOW), 255 = brilho máximo (HIGH)
  ledcWrite(LCD_BACKLIGHT_CHANNEL, brightness);
}

// Turn backlight on/off
static void lcdBacklightOn() {
  lcdSetBacklight(255); // Máximo brilho
}

static void lcdBacklightOff() {
  lcdSetBacklight(0); // Apagado
}

// Clear framebuffer
static void lcdClearBuffer() {
  memset(lcdBuffer, 0x00, sizeof(lcdBuffer));
}

// Fill framebuffer with pattern
static void lcdFillBuffer(uint8_t pattern = 0xFF) {
  memset(lcdBuffer, pattern, sizeof(lcdBuffer));
}

// Flush framebuffer to LCD
static void lcdFlush() {
  for (uint8_t page = 0; page < LCD_PAGES; ++page) {
    lcdSetPage(page);
    lcdSetColumn(0);
    lcdWriteDataBuffer(lcdBuffer[page], LCD_WIDTH);
  }
}

// ======== Primitive graphics functions (framebuffer-based) ========

// Set a single pixel at (x, y) in framebuffer
static void lcdSetPixel(uint8_t x, uint8_t y, bool on = true) {
  if (x >= LCD_WIDTH || y >= LCD_HEIGHT) return;
  uint8_t page = y / 8;
  uint8_t bit = y % 8;
  
  if (on) {
    lcdBuffer[page][x] |= (1 << bit);
  } else {
    lcdBuffer[page][x] &= ~(1 << bit);
  }
}

// Get pixel state
static bool lcdGetPixel(uint8_t x, uint8_t y) {
  if (x >= LCD_WIDTH || y >= LCD_HEIGHT) return false;
  uint8_t page = y / 8;
  uint8_t bit = y % 8;
  return (lcdBuffer[page][x] & (1 << bit)) != 0;
}

// Draw a horizontal line
static void lcdDrawHLine(uint8_t x0, uint8_t x1, uint8_t y) {
  if (y >= LCD_HEIGHT) return;
  if (x0 > x1) { uint8_t tmp = x0; x0 = x1; x1 = tmp; }
  if (x0 >= LCD_WIDTH) return;
  if (x1 >= LCD_WIDTH) x1 = LCD_WIDTH - 1;
  
  for (uint8_t x = x0; x <= x1; ++x) {
    lcdSetPixel(x, y);
  }
}

// Draw a vertical line
static void lcdDrawVLine(uint8_t x, uint8_t y0, uint8_t y1) {
  if (x >= LCD_WIDTH) return;
  if (y0 > y1) { uint8_t tmp = y0; y0 = y1; y1 = tmp; }
  if (y0 >= LCD_HEIGHT) return;
  if (y1 >= LCD_HEIGHT) y1 = LCD_HEIGHT - 1;
  
  for (uint8_t y = y0; y <= y1; ++y) {
    lcdSetPixel(x, y);
  }
}

// Draw a line using Bresenham's algorithm
static void lcdDrawLine(int16_t x0, int16_t y0, int16_t x1, int16_t y1) {
  int16_t dx = abs(x1 - x0);
  int16_t dy = abs(y1 - y0);
  int16_t sx = x0 < x1 ? 1 : -1;
  int16_t sy = y0 < y1 ? 1 : -1;
  int16_t err = dx - dy;
  
  while (true) {
    if (x0 >= 0 && x0 < LCD_WIDTH && y0 >= 0 && y0 < LCD_HEIGHT) {
      lcdSetPixel(x0, y0);
    }
    
    if (x0 == x1 && y0 == y1) break;
    
    int16_t e2 = 2 * err;
    if (e2 > -dy) {
      err -= dy;
      x0 += sx;
    }
    if (e2 < dx) {
      err += dx;
      y0 += sy;
    }
  }
}

// Draw a rectangle outline
static void lcdDrawRect(uint8_t x, uint8_t y, uint8_t w, uint8_t h) {
  if (w == 0 || h == 0) return;
  lcdDrawHLine(x, x + w - 1, y);           // top
  lcdDrawHLine(x, x + w - 1, y + h - 1);   // bottom
  lcdDrawVLine(x, y, y + h - 1);           // left
  lcdDrawVLine(x + w - 1, y, y + h - 1);   // right
}

// Draw a filled rectangle
static void lcdFillRect(uint8_t x, uint8_t y, uint8_t w, uint8_t h) {
  if (x >= LCD_WIDTH || y >= LCD_HEIGHT) return;
  
  uint8_t x1 = (x + w > LCD_WIDTH) ? LCD_WIDTH - 1 : x + w - 1;
  uint8_t y1 = (y + h > LCD_HEIGHT) ? LCD_HEIGHT - 1 : y + h - 1;
  
  for (uint8_t cy = y; cy <= y1; ++cy) {
    for (uint8_t cx = x; cx <= x1; ++cx) {
      lcdSetPixel(cx, cy);
    }
  }
}

// Draw a circle using midpoint algorithm
static void lcdDrawCircle(int16_t x0, int16_t y0, uint8_t r) {
  int16_t x = r;
  int16_t y = 0;
  int16_t err = 0;
  
  while (x >= y) {
    if (x0 + x >= 0 && x0 + x < LCD_WIDTH && y0 + y >= 0 && y0 + y < LCD_HEIGHT)
      lcdSetPixel(x0 + x, y0 + y);
    if (x0 + y >= 0 && x0 + y < LCD_WIDTH && y0 + x >= 0 && y0 + x < LCD_HEIGHT)
      lcdSetPixel(x0 + y, y0 + x);
    if (x0 - y >= 0 && x0 - y < LCD_WIDTH && y0 + x >= 0 && y0 + x < LCD_HEIGHT)
      lcdSetPixel(x0 - y, y0 + x);
    if (x0 - x >= 0 && x0 - x < LCD_WIDTH && y0 + y >= 0 && y0 + y < LCD_HEIGHT)
      lcdSetPixel(x0 - x, y0 + y);
    if (x0 - x >= 0 && x0 - x < LCD_WIDTH && y0 - y >= 0 && y0 - y < LCD_HEIGHT)
      lcdSetPixel(x0 - x, y0 - y);
    if (x0 - y >= 0 && x0 - y < LCD_WIDTH && y0 - x >= 0 && y0 - x < LCD_HEIGHT)
      lcdSetPixel(x0 - y, y0 - x);
    if (x0 + y >= 0 && x0 + y < LCD_WIDTH && y0 - x >= 0 && y0 - x < LCD_HEIGHT)
      lcdSetPixel(x0 + y, y0 - x);
    if (x0 + x >= 0 && x0 + x < LCD_WIDTH && y0 - y >= 0 && y0 - y < LCD_HEIGHT)
      lcdSetPixel(x0 + x, y0 - y);
    
    if (err <= 0) {
      y++;
      err += 2 * y + 1;
    }
    if (err > 0) {
      x--;
      err -= 2 * x + 1;
    }
  }
}

// Draw triangle (outline)
static void lcdDrawTriangle(int16_t x0, int16_t y0, int16_t x1, int16_t y1, int16_t x2, int16_t y2) {
  lcdDrawLine(x0, y0, x1, y1);
  lcdDrawLine(x1, y1, x2, y2);
  lcdDrawLine(x2, y2, x0, y0);
}

// Fill triangle (scan-line algorithm)
static void lcdFillTriangle(int16_t x0, int16_t y0, int16_t x1, int16_t y1, int16_t x2, int16_t y2) {
  // Sort vertices by y coordinate (y0 <= y1 <= y2)
  if (y0 > y1) { int16_t t; t=y0; y0=y1; y1=t; t=x0; x0=x1; x1=t; }
  if (y1 > y2) { int16_t t; t=y1; y1=y2; y2=t; t=x1; x1=x2; x2=t; }
  if (y0 > y1) { int16_t t; t=y0; y0=y1; y1=t; t=x0; x0=x1; x1=t; }
  
  if (y0 == y2) { // Degenerate case: all on same line
    int16_t a = x0, b = x0;
    if (x1 < a) a = x1; else if (x1 > b) b = x1;
    if (x2 < a) a = x2; else if (x2 > b) b = x2;
    lcdDrawHLine(a, b, y0);
    return;
  }
  
  int32_t dx01 = x1 - x0, dy01 = y1 - y0;
  int32_t dx02 = x2 - x0, dy02 = y2 - y0;
  int32_t dx12 = x2 - x1, dy12 = y2 - y1;
  int32_t sa = 0, sb = 0;
  
  int16_t last = (y1 == y2) ? y1 : y1 - 1;
  
  for (int16_t y = y0; y <= last; y++) {
    int16_t a = x0 + sa / dy02;
    int16_t b = x0 + sb / dy01;
    sa += dx02;
    sb += dx01;
    if (a > b) { int16_t t = a; a = b; b = t; }
    lcdDrawHLine(a, b, y);
  }
  
  sa = (int32_t)dx12 * (last - y0);
  sb = (int32_t)dx02 * (y1 - y0);
  for (int16_t y = last + 1; y <= y2; y++) {
    int16_t a = x1 + sa / dy12;
    int16_t b = x0 + sb / dy02;
    sa += dx12;
    sb += dx02;
    if (a > b) { int16_t t = a; a = b; b = t; }
    lcdDrawHLine(a, b, y);
  }
}

// Draw column ruler: small tick every 2 cols, bigger every 8 cols, labels every 16 cols.
// Marks visible window [0 .. visibleCols-1] with full-height borders.
static void lcdDrawColumnRuler(uint8_t totalCols = LCD_WIDTH, uint8_t visibleCols = LCD_WIDTH, uint8_t labelStep = 16) {
  // Clear all pages first
  for (uint8_t page = 0; page < LCD_PAGES; ++page) {
    lcdSetPage(page);
    lcdSetColumn(0);
    for (uint8_t i = 0; i < totalCols; ++i) lcdWriteData(0x00);
  }

  // Top ticks on page 0 only (height encoded in bits 0..4)
  lcdSetPage(0);
  lcdSetColumn(0);
  for (uint8_t col = 0; col < totalCols; ++col) {
    uint8_t v = 0x00;
    if ((col % 2) == 0) v = 0x03;     // small tick: 2px
    if ((col % 8) == 0) v = 0x0F;     // major tick: 4px
    if ((col % 16) == 0) v = 0x1F;    // bigger tick: 5px
    lcdWriteData(v);
  }

  // Labels every labelStep columns (on page 1)
  for (uint8_t col = 0; col < visibleCols; col += labelStep) {
    lcdDrawNumber(1, col, col);
  }

  // Draw full-height borders for visible area (col 0 and visibleCols-1)
  if (visibleCols > 0 && visibleCols <= totalCols) {
    uint8_t left = 0;
    uint8_t right = visibleCols - 1;
    for (uint8_t page = 0; page < LCD_PAGES; ++page) {
      lcdSetPage(page);
      lcdSetColumn(left);
      lcdWriteData(0xFF);
      lcdSetColumn(right);
      lcdWriteData(0xFF);
    }
  }
}

// ======== Font rendering functions ========

// Get glyph data for selected font
static bool getGlyph(char c, uint8_t* out, FontSize font, uint8_t* width) {
  if (font == FONT_3X5) {
    *width = 3;
    if (c >= 32 && c <= 126) {
      uint16_t idx = (uint16_t)(c - 32) * 3;
      for (uint8_t i = 0; i < 3; ++i) {
        #if defined(ARDUINO_ARCH_AVR)
        out[i] = pgm_read_byte(&font3x5[idx + i]);
        #else
        out[i] = font3x5[idx + i];
        #endif
      }
      return true;
    }
    // Fallback box for 3x5
    out[0] = 0x1F; out[1] = 0x11; out[2] = 0x1F;
    return true;
  }
  else { // FONT_5X7
    *width = 5;
    // Font5x7 has ALL 256 characters (0-255), so use ASCII value directly
    uint16_t idx = (uint16_t)((uint8_t)c) * 5;
    for (uint8_t i = 0; i < 5; ++i) {
      #if defined(ARDUINO_ARCH_AVR)
      out[i] = pgm_read_byte(&font5x7[idx + i]);
      #else
      out[i] = font5x7[idx + i];
      #endif
    }
    return true;
  }
}

// Draw single character with specified font
static void lcdDrawChar(uint8_t page, uint8_t col, char c, FontSize font = FONT_5X7, uint8_t spacing = 1) {
  uint8_t g[5];
  uint8_t w;
  getGlyph(c, g, font, &w);
  if (col + w > LCD_WIDTH) return;
  
  for (uint8_t i = 0; i < w; ++i) {
    if (col + i < LCD_WIDTH) {
      lcdBuffer[page][col + i] = g[i];
    }
  }
  
  // Spacing (blank columns)
  for (uint8_t i = 0; i < spacing && (col + w + i) < LCD_WIDTH; ++i) {
    lcdBuffer[page][col + w + i] = 0x00;
  }
}

// Draw text string with specified font
static void lcdDrawText(uint8_t page, uint8_t col, const char* text, FontSize font = FONT_5X7) {
  uint8_t x = col;
  uint8_t charWidth = (font == FONT_3X5) ? 4 : 6; // width + 1 spacing
  for (const char* p = text; *p && x < LCD_WIDTH; ++p) {
    lcdDrawChar(page, x, *p, font);
    x += charWidth;
  }
}

static void lcdDrawNumber(uint8_t page, uint8_t col, int num, FontSize font) {
  char buf[12];
  snprintf(buf, sizeof(buf), "%d", num);
  lcdDrawText(page, col, buf, font);
}

// ======== Font self-test demo ========
static void demoFontSelfTest() {
  lcdClearBuffer();
  lcdDrawRect(0, 0, LCD_WIDTH, LCD_HEIGHT);

  // Linha 1: Dígitos
  lcdDrawText(1, 2, "0123456789");

  // Linha 2: Maiúsculas
  lcdDrawText(2, 2, "ABCDEFGHIJKLMNOPQRSTUVWXYZ");

  // Linha 3: Minúsculas
  lcdDrawText(3, 2, "abcdefghijklmnopqrstuvwxyz");

  // Linha 4: Pontuacao e símbolos comuns
  lcdDrawText(4, 2, " !\"#$%&'()*+,-./:;<=>?@[\\]^_{|}~");

  lcdFlush();
}

// ======== Initialization sequence ========
// Extracted from scope capture after RST goes HIGH
// Complete sequence that successfully initializes the display
static const uint8_t INIT_SEQUENCE[] = {
  // Basic config
  0xA2,              // LCD Bias 1/9
  0xA1,              // ADC Select (segment remap)
  0x60,              // Unknown (controller specific)
  0x45,              // Display start line: 5
  0x01,              // Set column LSB: 1
  
  // Power control sequence (gradual power-up)
  0x2C,              // Power control: booster ON
  // Delay needed here (see lcdInit)
  0x2E,              // Power control: regulator ON
  // Delay needed here
  0x2F,              // Power control: follower ON
  // Delay needed here
  
  // Additional config
  0x58, 0x08, 0x00, 0x00,  // Unknown sequence
  
  // Clear and enable display (page addressing)
  0x00,              // Set column LSB: 0
  0xAF,              // Display ON
  0x40,              // Display start line: 0
  0xB1,              // Set page: 1
  0x10, 0x00,        // Set column address
  
  0x00,              // Set column LSB: 0  
  0xAF,              // Display ON
  0x40,              // Display start line: 0
  0xB2,              // Set page: 2
  0x10, 0x00,        // Set column address
  
  0x00,              // Set column LSB: 0
  0xAF,              // Display ON  
  0x40,              // Display start line: 0
  0xB3,              // Set page: 3
  0x10, 0x00         // Set column address
};

static void lcdReset() {
  lcdRST(LOW);
  delay(10);
  lcdRST(HIGH);
  delay(10);
}

static void lcdInit() {
  // Configure pins
  pinMode(LCD_PIN_CS, OUTPUT);
  pinMode(LCD_PIN_DC, OUTPUT);
  pinMode(LCD_PIN_RST, OUTPUT);
  pinMode(LCD_PIN_SCK, OUTPUT);
  pinMode(LCD_PIN_MOSI, OUTPUT);
  pinMode(LCD_PIN_BACKLIGHT, OUTPUT);

  // Configure PWM for backlight
  ledcSetup(LCD_BACKLIGHT_CHANNEL, LCD_BACKLIGHT_FREQ, LCD_BACKLIGHT_RESOLUTION);
  ledcAttachPin(LCD_PIN_BACKLIGHT, LCD_BACKLIGHT_CHANNEL);
  lcdSetBacklight(255); // Ligar backlight no máximo

  // Idle levels - confirmed from scope capture
  // CS HIGH, RST HIGH, D/C LOW, SCK HIGH, MOSI HIGH
  lcdCS(HIGH);
  lcdDC(LOW);
  lcdRST(HIGH);
  lcdSCK(HIGH);   // Clock idles HIGH
  lcdMOSI(HIGH);  // Data idles HIGH

  // Reset pulse (active LOW)
  lcdRST(LOW);
  delay(10);      // Hold reset for 10ms
  lcdRST(HIGH);
  delay(2);       // Wait 2ms after reset

  // Send init sequence with delays for power-up
  // Commands 0-4: Basic config
  for (size_t i = 0; i <= 4; ++i) {
    lcdWriteCommand(INIT_SEQUENCE[i]);
    delay(1);
  }
  
  // Command 5 (0x2C): Turn on booster
  lcdWriteCommand(INIT_SEQUENCE[5]);
  delay(100);  // Wait 100ms for booster to stabilize
  
  // Command 6 (0x2E): Turn on regulator
  lcdWriteCommand(INIT_SEQUENCE[6]);
  delay(100);  // Wait 100ms for regulator
  
  // Command 7 (0x2F): Turn on follower
  lcdWriteCommand(INIT_SEQUENCE[7]);
  delay(100);  // Wait 100ms for follower
  
  // Remaining commands
  for (size_t i = 8; i < sizeof(INIT_SEQUENCE); ++i) {
    lcdWriteCommand(INIT_SEQUENCE[i]);
    delay(1);
  }

  // Clear first 4 pages (all 132 columns to ensure no garbage)
  for (uint8_t page = 0; page < 4; ++page) {
    lcdSetPage(page);
    lcdSetColumn(0);
    for (uint8_t i = 0; i < LCD_WIDTH; ++i) lcdWriteData(0x00);
  }
  
  // Extra: clear pages 4-7 as well (total 8 pages)
  for (uint8_t page = 4; page < 8; ++page) {
    lcdSetPage(page);
    lcdSetColumn(0);
    for (uint8_t i = 0; i < LCD_WIDTH; ++i) lcdWriteData(0x00);
  }
}

void setup() {
  Serial.begin(115200);
  Serial.println("\nESP32-S3 LCD 132x48 Driver");
  Serial.println("Modo: Jogo da Cobrinha");
  
  lcdInit();
  lcdBacklightOn();
  keypadInit();
  
  // Tela inicial será desenhada pelo jogo
}

// ======== Demo functions ========

// Demo 1: Primitivas gráficas (salvo para referência)
static void demoGraphicsPrimitives() {
  lcdClearBuffer();
  
  // Retângulo externo
  lcdDrawRect(0, 0, LCD_WIDTH, LCD_HEIGHT);
  
  // Linhas diagonais nos cantos
  lcdDrawLine(0, 0, 20, 10);
  lcdDrawLine(LCD_WIDTH-1, 0, LCD_WIDTH-21, 10);
  lcdDrawLine(0, LCD_HEIGHT-1, 20, LCD_HEIGHT-11);
  lcdDrawLine(LCD_WIDTH-1, LCD_HEIGHT-1, LCD_WIDTH-21, LCD_HEIGHT-11);
  
  // Círculos
  lcdDrawCircle(66, 24, 20);
  lcdDrawCircle(30, 15, 10);
  lcdDrawCircle(102, 15, 10);
  
  // Retângulos
  lcdDrawRect(10, 10, 30, 15);
  lcdFillRect(92, 30, 30, 10);
  
  // Linhas cruzadas
  lcdDrawHLine(5, LCD_WIDTH-6, LCD_HEIGHT/2);
  lcdDrawVLine(LCD_WIDTH/2, 5, LCD_HEIGHT-6);
  
  // Padrão
  for (uint8_t i = 0; i < 5; ++i) {
    lcdDrawLine(50 + i*3, 35, 70 + i*3, 45);
  }
  
  lcdDrawText(0, 40, "LCD");
  lcdDrawNumber(5, 100, 132, FONT_5X7);
  
  lcdFlush();
}

// Bitmap de exemplo: smiley 16x16
static const uint8_t PROGMEM smiley16x16[] = {
  0x00, 0xE0, 0x18, 0x04, 0xC2, 0x22, 0x11, 0x11,
  0x11, 0x11, 0x22, 0xC2, 0x04, 0x18, 0xE0, 0x00,
  0x00, 0x07, 0x18, 0x20, 0x43, 0x44, 0x88, 0x88,
  0x88, 0x88, 0x44, 0x43, 0x20, 0x18, 0x07, 0x00,
};

// Desenha bitmap (largura múltiplo de 8)
static void lcdDrawBitmap(uint8_t x, uint8_t y, const uint8_t* bitmap, uint8_t w, uint8_t h) {
  uint8_t pages = (h + 7) / 8;
  for (uint8_t py = 0; py < pages; ++py) {
    for (uint8_t px = 0; px < w; ++px) {
      uint8_t col = pgm_read_byte(&bitmap[py * w + px]);
      uint8_t destPage = (y / 8) + py;
      uint8_t destX = x + px;
      
      if (destPage < LCD_PAGES && destX < LCD_WIDTH) {
        uint8_t shift = y % 8;
        if (shift == 0) {
          lcdBuffer[destPage][destX] |= col;
        } else {
          lcdBuffer[destPage][destX] |= (col << shift);
          if (destPage + 1 < LCD_PAGES) {
            lcdBuffer[destPage + 1][destX] |= (col >> (8 - shift));
          }
        }
      }
    }
  }
}

// Demo 2: Texto, scroll e bitmap
static void demoTextScrollBitmap() {
  // Fade in do backlight
  for (uint8_t b = 0; b <= 255; b += 5) {
    lcdSetBacklight(b);
    delay(10);
  }
  
  // Moldura inicial
  lcdClearBuffer();
  lcdDrawRect(0, 0, LCD_WIDTH, LCD_HEIGHT);
  lcdFlush();
  delay(500);
  
  // Texto centralizado
  lcdClearBuffer();
  lcdDrawRect(0, 0, LCD_WIDTH, LCD_HEIGHT);
  lcdDrawText(1, 30, "ESP32-S3");
  lcdDrawText(3, 35, "132x48");
  lcdFlush();
  delay(1500);
  
  // Scroll texto da direita para esquerda
  const char* scrollText = "  Framebuffer Graphics Demo  ";
  for (int16_t scroll = LCD_WIDTH; scroll > -150; scroll -= 2) {
    lcdClearBuffer();
    lcdDrawRect(0, 0, LCD_WIDTH, LCD_HEIGHT);
    
    int16_t textX = scroll;
    for (const char* p = scrollText; *p; ++p) {
      if (textX >= -6 && textX < LCD_WIDTH) {
        lcdDrawChar(2, textX, *p, FONT_5X7, 1);
      }
      textX += 6;
    }
    
    lcdFlush();
    delay(30);
  }
  
  delay(500);
  
  // Bitmaps piscando
  for (uint8_t i = 0; i < 3; ++i) {
    lcdClearBuffer();
    lcdDrawRect(0, 0, LCD_WIDTH, LCD_HEIGHT);
    
    lcdDrawBitmap(10, 16, smiley16x16, 16, 16);
    lcdDrawBitmap(58, 8, smiley16x16, 16, 16);
    lcdDrawBitmap(106, 16, smiley16x16, 16, 16);
    
    lcdFlush();
    delay(300);
    
    lcdClearBuffer();
    lcdDrawRect(0, 0, LCD_WIDTH, LCD_HEIGHT);
    lcdFlush();
    delay(300);
  }
  
  delay(500);
  
  // Padrão animado
  for (int8_t frame = 0; frame < 20; ++frame) {
    lcdClearBuffer();
    
    for (uint8_t y = 0; y < LCD_HEIGHT; y += 4) {
      uint8_t lineY = (y + frame) % LCD_HEIGHT;
      lcdDrawHLine(0, LCD_WIDTH-1, lineY);
    }
    
    lcdDrawText(2, 20, "GRAPHICS");
    lcdDrawNumber(3, 45, frame, FONT_5X7);
    
    lcdFlush();
    delay(50);
  }
  
  delay(500);
  
  // Tela final invertida
  lcdClearBuffer();
  lcdDrawRect(0, 0, LCD_WIDTH, LCD_HEIGHT);
  lcdFillRect(10, 10, LCD_WIDTH-20, LCD_HEIGHT-20);
  
  for (uint8_t page = 1; page < 5; ++page) {
    for (uint8_t x = 20; x < LCD_WIDTH-20; ++x) {
      lcdBuffer[page][x] ^= 0xFF;
    }
  }
  
  lcdDrawText(2, 40, "READY");
  lcdFlush();
  
  // Efeito de pulsação do backlight
  for (uint8_t i = 0; i < 3; ++i) {
    for (uint8_t b = 255; b > 100; b -= 5) {
      lcdSetBacklight(b);
      delay(10);
    }
    for (uint8_t b = 100; b <= 255; b += 5) {
      lcdSetBacklight(b);
      delay(10);
    }
  }
}

// ===================== Jogo da Cobrinha =====================

struct Point { uint8_t x; uint8_t y; };

// Grid do jogo: reservar 1 página (8 px) no topo para HUD (texto)
static const uint8_t HUD_HEIGHT = 8;          // 1 página de fonte 5x7
static const uint8_t CELL = 4;                // tamanho do tile em pixels (reduzido para aproveitar mais)
static const uint8_t GRID_OFFSET_Y = HUD_HEIGHT;          // início da área jogável
static const uint8_t GRID_ROWS = (LCD_HEIGHT - HUD_HEIGHT) / CELL; // 40/4=10 linhas
static const uint8_t GRID_COLS = LCD_WIDTH / CELL;        // 132/4=33 colunas

static const uint16_t SNAKE_MAX = GRID_COLS * GRID_ROWS;

// Estado do jogo
static Point snake[SNAKE_MAX];
static uint16_t snakeLen = 0;
static int8_t dirX = 1, dirY = 0;   // direção atual
static int8_t nextDirX = 1, nextDirY = 0; // direção desejada pelas teclas
static Point food = {0,0};
static bool gameOver = false;
static bool paused = false;
static bool okHeld = false;
static uint16_t score = 0;
static unsigned long lastTick = 0;
static uint16_t tickMs = 180; // velocidade base (ms por passo)

static bool snakeOccupies(uint8_t x, uint8_t y) {
  for (uint16_t i = 0; i < snakeLen; ++i) {
    if (snake[i].x == x && snake[i].y == y) return true;
  }
  return false;
}

static void placeFood() {
  for (int attempts = 0; attempts < 100; ++attempts) {
    uint8_t fx = random(0, GRID_COLS);
    uint8_t fy = random(0, GRID_ROWS);
    if (!snakeOccupies(fx, fy)) { food = {fx, fy}; return; }
  }
  for (uint8_t y = 0; y < GRID_ROWS; ++y) {
    for (uint8_t x = 0; x < GRID_COLS; ++x) {
      if (!snakeOccupies(x, y)) { food = {x, y}; return; }
    }
  }
}

static void snakeReset() {
  randomSeed((uint32_t)micros());
  snakeLen = 3;
  uint8_t cx = GRID_COLS / 2;
  uint8_t cy = GRID_ROWS / 2;
  snake[0] = { (uint8_t)(cx+1), cy }; // cabeça
  snake[1] = { cx, cy };
  snake[2] = { (uint8_t)(cx-1), cy };
  dirX = 1; dirY = 0;
  nextDirX = 1; nextDirY = 0;
  score = 0;
  gameOver = false;
  paused = false;
  okHeld = false;
  tickMs = 180;
  placeFood();

  // Desenhar HUD inicial
  lcdClearBuffer();
  lcdDrawRect(0, 0, LCD_WIDTH, LCD_HEIGHT);
  lcdDrawText(0, 2, "SNAKE  Pts:", FONT_5X7);
  lcdDrawNumber(0, 70, score, FONT_5X7);
  lcdFlush();
}

static void drawCell(uint8_t gx, uint8_t gy) {
  uint8_t x = gx * CELL;
  uint8_t y = GRID_OFFSET_Y + gy * CELL;
  // bloco com margem interna de 1 px
  uint8_t w = (CELL >= 2) ? CELL - 2 : CELL;
  uint8_t h = (CELL >= 2) ? CELL - 2 : CELL;
  lcdFillRect(x + 1, y + 1, w, h);
}

static void renderGame() {
  lcdClearBuffer();
  // moldura da área jogável
  lcdDrawRect(0, GRID_OFFSET_Y, LCD_WIDTH, LCD_HEIGHT - GRID_OFFSET_Y);

  // HUD
  lcdDrawText(0, 2, "SNAKE  Pts:", FONT_5X7);
  lcdDrawNumber(0, 70, score, FONT_5X7);

  // comida
  drawCell(food.x, food.y);

  // cobra
  for (uint16_t i = 0; i < snakeLen; ++i) {
    drawCell(snake[i].x, snake[i].y);
  }

  if (gameOver) {
    lcdDrawText(2, 30, "GAME OVER", FONT_5X7);
    lcdDrawText(4, 10, "OK = Reiniciar", FONT_3X5);
  } else if (paused) {
    lcdDrawText(2, 40, "PAUSE", FONT_5X7);
  }

  lcdFlush();
}

static void handleInput() {
  Key k = readKeyDebounced();

  if (gameOver) {
    if (k == KEY_OK && !okHeld) { snakeReset(); renderGame(); }
    okHeld = (k == KEY_OK);
    return;
  }

  // Pause com OK
  if (k == KEY_OK && !okHeld) { paused = !paused; }
  okHeld = (k == KEY_OK);

  if (paused) return;

  // mudar direção (impedir inversão imediata)
  if (k == KEY_UP && dirY != 1) { nextDirX = 0; nextDirY = -1; }
  if (k == KEY_DOWN && dirY != -1) { nextDirX = 0; nextDirY = 1; }
  if (k == KEY_LEFT && dirX != 1) { nextDirX = -1; nextDirY = 0; }
  if (k == KEY_RIGHT && dirX != -1) { nextDirX = 1; nextDirY = 0; }
}

static void stepGame() {
  if (gameOver || paused) return;

  // aplicar direção desejada
  dirX = nextDirX; dirY = nextDirY;

  // nova cabeça
  int16_t nx = (int16_t)snake[0].x + dirX;
  int16_t ny = (int16_t)snake[0].y + dirY;

  // warp nas bordas (atravessa para o lado oposto)
  if (nx < 0) nx = GRID_COLS - 1;
  if (nx >= GRID_COLS) nx = 0;
  if (ny < 0) ny = GRID_ROWS - 1;
  if (ny >= GRID_ROWS) ny = 0;

  // colisão com o próprio corpo
  for (uint16_t i = 0; i < snakeLen; ++i) {
    if (snake[i].x == nx && snake[i].y == ny) { gameOver = true; renderGame(); return; }
  }

  // deslocar corpo
  for (int i = (int)snakeLen - 1; i > 0; --i) snake[i] = snake[i - 1];
  snake[0].x = (uint8_t)nx; snake[0].y = (uint8_t)ny;

  // comer comida
  if (snake[0].x == food.x && snake[0].y == food.y) {
    if (snakeLen < SNAKE_MAX) { snake[snakeLen] = snake[snakeLen - 1]; snakeLen++; }
    score += 1;
    if (tickMs > 80) tickMs -= 5; // acelera
    placeFood();
  }

  renderGame();
}

void loop() {
  static bool started = false;
  if (!started) { snakeReset(); renderGame(); started = true; lastTick = millis(); }

  handleInput();

  unsigned long now = millis();
  if (now - lastTick >= tickMs) { lastTick = now; stepGame(); }

  delay(10);
}

// Desenha uma régua horizontal de linhas (para contar a altura visível)
// visibleRows: número de linhas a marcar (ex.: 48)
// Marcas: a cada 2 linhas (curta), a cada 8 linhas (média), a cada 16 linhas (maior)
static void lcdDrawRowRuler(uint8_t totalCols = LCD_WIDTH, uint8_t visibleRows = LCD_HEIGHT, uint8_t labelStep = 16) {
  // Limpa tudo
  for (uint8_t page = 0; page < LCD_PAGES; ++page) {
    lcdSetPage(page);
    lcdSetColumn(0);
    for (uint8_t i = 0; i < totalCols; ++i) lcdWriteData(0x00);
  }

  // Construir marcas por página nos primeiros 5-6 pixels de coluna
  uint8_t lastPage = (visibleRows + 7) / 8; // páginas realmente visíveis
  for (uint8_t page = 0; page < lastPage && page < LCD_PAGES; ++page) {
    uint8_t c0 = 0, c1 = 0, c2 = 0, c3 = 0, c4 = 0; // 5 colunas de ticks
    for (uint8_t bit = 0; bit < 8; ++bit) {
      uint8_t y = page * 8 + bit;
      if (y >= visibleRows) break;
      bool small = (y % 2) == 0;
      bool major = (y % 8) == 0;
      bool big   = (y % 16) == 0;

      uint8_t m = (1u << bit);
      if (small) c0 |= m;          // marca curta (1 coluna)
      if (major) { c1 |= m; c2 |= m; }     // marca média (+2 colunas)
      if (big)   { c3 |= m; c4 |= m; }     // marca grande (+2 colunas)
    }

    lcdSetPage(page);
    lcdSetColumn(0);
    lcdWriteData(c0);
    lcdWriteData(c1);
    lcdWriteData(c2);
    lcdWriteData(c3);
    lcdWriteData(c4);

    // Rótulo por página (valor aproximado da primeira linha desta página)
    lcdDrawNumber(page, 8, page * 8, FONT_5X7);
  }
}

// ======== Demo: All Features ========
static void demoAllFeatures() {
  // Test 1: Multiple fonts
  lcdClearBuffer();
  lcdDrawRect(0, 0, LCD_WIDTH, LCD_HEIGHT);
  lcdDrawText(0, 2, "Font 5x7:", FONT_5X7);
  lcdDrawText(1, 2, "ABCDEFG 0123", FONT_5X7);
  lcdDrawText(3, 2, "Font 3x5:", FONT_3X5);
  lcdDrawText(4, 2, "ABCDEFGHIJKLM 012345", FONT_3X5);
  lcdFlush();
  delay(3000);
  
  // Test 2: Shapes
  lcdClearBuffer();
  lcdDrawRect(0, 0, LCD_WIDTH, LCD_HEIGHT);
  lcdDrawText(0, 35, "SHAPES", FONT_5X7);
  
  // Triangles
  lcdDrawTriangle(10, 35, 25, 15, 40, 35);
  lcdFillTriangle(50, 35, 65, 15, 80, 35);
  
  // Circles
  lcdDrawCircle(100, 25, 15);
  lcdFillRect(95, 20, 10, 10);
  
  lcdFlush();
  delay(3000);
  
  // Test 3: Animation - bouncing ball
  for (int frame = 0; frame < 50; frame++) {
    lcdClearBuffer();
    lcdDrawRect(0, 0, LCD_WIDTH, LCD_HEIGHT);
    
    // Calculate ball position (simple sine wave)
    int x = 20 + frame * 2;
    int y = 24 + (int)(12.0 * sin(frame * 0.3));
    
    if (x < LCD_WIDTH - 20) {
      lcdDrawCircle(x, y, 8);
      lcdFillRect(x-2, y-2, 4, 4);
    }
    
    lcdDrawText(5, 2, "Bouncing!", FONT_3X5);
    lcdFlush();
    delay(50);
  }
  
  delay(1000);
  
  // Test 4: Backlight fade
  lcdClearBuffer();
  lcdDrawRect(0, 0, LCD_WIDTH, LCD_HEIGHT);
  lcdDrawText(2, 10, "BACKLIGHT", FONT_5X7);
  lcdDrawText(3, 20, "Fading", FONT_5X7);
  lcdFlush();
  
  // Fade out
  for (int b = 255; b >= 0; b -= 5) {
    lcdSetBacklight(b);
    delay(20);
  }
  delay(500);
  
  // Fade in
  for (int b = 0; b <= 255; b += 5) {
    lcdSetBacklight(b);
    delay(20);
  }
  
  delay(1000);
}

// Demo: Keypad test (shows current pressed key)
static void demoKeypadTest() {
  keypadInit();
  lcdClearBuffer();
  lcdDrawRect(0, 0, LCD_WIDTH, LCD_HEIGHT);
  lcdDrawText(0, 4, "Keypad Test", FONT_5X7);
  lcdDrawText(5, 2, "Press UP/DOWN/", FONT_3X5);
  lcdDrawText(6-1, 2, "LEFT/RIGHT/OK", FONT_3X5); // using page 5 (last row)
  lcdFlush();

  while (true) {
    Key k = readKeyDebounced();
    lcdClearBuffer();
    lcdDrawRect(0, 0, LCD_WIDTH, LCD_HEIGHT);
    lcdDrawText(0, 4, "Keypad Test", FONT_5X7);
    const char* name = "NONE";
    switch (k) {
      case KEY_UP: name = "UP"; break;
      case KEY_DOWN: name = "DOWN"; break;
      case KEY_LEFT: name = "LEFT"; break;
      case KEY_RIGHT: name = "RIGHT"; break;
      case KEY_OK: name = "OK"; break;
      default: name = "NONE"; break;
    }
    lcdDrawText(2, 10, "Pressed:", FONT_5X7);
    lcdDrawText(3, 10, name, FONT_5X7);
    lcdFlush();
    delay(50);
  }
}

// Demo: Pin scanner - probes candidate GPIOs using INPUT_PULLUP and reports via Serial + LCD
static void demoPinScanner() {
  const int pins[] = {0, 2, 4, 5, 12, 13, 14, 15, 16, 17, 18, 19, 21, 22, 23, 25, 26, 27, 32, 33, 34, 35, 36, 37, 38, 39};
  const int count = sizeof(pins)/sizeof(pins[0]);
  Serial.println("Starting pin scanner (INPUT_PULLUP probe)...");
  lcdClearBuffer();
  lcdDrawRect(0,0,LCD_WIDTH,LCD_HEIGHT);
  lcdDrawText(0,4,"Pin Scanner", FONT_5X7);
  lcdFlush();

  for (int i=0;i<count;i++) {
    int p = pins[i];
    // skip pins that are known unsafe (flash pins 6-11)
    if (p >= 6 && p <= 11) {
      Serial.printf("GPIO %d: skipped (flash)", p);
      Serial.println();
      continue;
    }
    // Try INPUT_PULLUP probe (non-destructive)
    pinMode(p, INPUT_PULLUP);
    delay(5);
    int v = digitalRead(p);
    Serial.printf("GPIO %2d -> %d\n", p, v);

    // Show a rolling status on the LCD (two columns per pin)
    char buf[20];
    snprintf(buf, sizeof(buf), "GPIO%2d: %d", p, v);
    uint8_t page = 1 + (i / 3); // a few pins per page
    uint8_t col = 2 + (i % 3) * 40;
    if (page >= LCD_PAGES) page = LCD_PAGES-1;
    lcdDrawText(page, col, buf, FONT_3X5);
    lcdFlush();
    delay(100);
  }

  Serial.println("Pin scan complete.");
  lcdDrawText(LCD_PAGES-1, 2, "Scan complete", FONT_3X5);
  lcdFlush();
}