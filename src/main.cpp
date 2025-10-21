// Simple bit-banged LCD driver (SPI-like with D/C) for ESP32-S3
// Assumptions based on reverse engineering:
// - CS: active low
// - D/C: 0 = command, 1 = data
// - RST: active low
// - Data (MOSI) sampled on SCK rising edge, MSB first
// - Display uses 5x8 font, vertical columns per byte
//
// Display resolution: 132 columns × 48 rows (6 pages × 8 pixels)
// Visible area: columns 0-131, rows 0-47

#include <Arduino.h>

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

// Forward declarations
static void lcdDrawNumber(uint8_t page, uint8_t col, int num);

// ======== Framebuffer operations ========

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

// Draw a column ruler: small tick every 2 cols, bigger every 8 cols, labels every 16 cols.
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

// ======== Minimal 5x8 font subset (vertical columns, LSB at top) ========
// Known glyphs from captures: 'A', 'F', '-', ':' and space
// Added: digits 0-9
static bool glyph5x8(char c, uint8_t out[5]) {
  switch (c) {
    case 'A': { uint8_t g[5] = {0xF8, 0x24, 0x22, 0x24, 0xF8}; memcpy(out, g, 5); return true; }
    case 'F': { uint8_t g[5] = {0xFE, 0x12, 0x12, 0x12, 0x02}; memcpy(out, g, 5); return true; }
    case '-': { uint8_t g[5] = {0x80, 0x80, 0x80, 0x80, 0x80}; memcpy(out, g, 5); return true; }
    case ':': { uint8_t g[5] = {0x08, 0x08, 0x08, 0x08, 0x08}; memcpy(out, g, 5); return true; }
    case ' ': { uint8_t g[5] = {0x00, 0x00, 0x00, 0x00, 0x00}; memcpy(out, g, 5); return true; }
    
    // Digits 0-9 (5x8 bitmap, vertical columns)
    case '0': { uint8_t g[5] = {0x7C, 0x82, 0x82, 0x82, 0x7C}; memcpy(out, g, 5); return true; }
    case '1': { uint8_t g[5] = {0x00, 0x84, 0xFE, 0x80, 0x00}; memcpy(out, g, 5); return true; }
    case '2': { uint8_t g[5] = {0x84, 0xC2, 0xA2, 0x92, 0x8C}; memcpy(out, g, 5); return true; }
    case '3': { uint8_t g[5] = {0x42, 0x82, 0x92, 0x92, 0x6C}; memcpy(out, g, 5); return true; }
    case '4': { uint8_t g[5] = {0x30, 0x28, 0x24, 0xFE, 0x20}; memcpy(out, g, 5); return true; }
    case '5': { uint8_t g[5] = {0x4E, 0x8A, 0x8A, 0x8A, 0x72}; memcpy(out, g, 5); return true; }
    case '6': { uint8_t g[5] = {0x7C, 0x92, 0x92, 0x92, 0x60}; memcpy(out, g, 5); return true; }
    case '7': { uint8_t g[5] = {0x02, 0xE2, 0x12, 0x0A, 0x06}; memcpy(out, g, 5); return true; }
    case '8': { uint8_t g[5] = {0x6C, 0x92, 0x92, 0x92, 0x6C}; memcpy(out, g, 5); return true; }
    case '9': { uint8_t g[5] = {0x0C, 0x92, 0x92, 0x92, 0x7C}; memcpy(out, g, 5); return true; }
    
    default: {
      // Placeholder: open box
      uint8_t g[5] = {0x7E, 0x42, 0x5A, 0x42, 0x7E};
      memcpy(out, g, 5);
      return true;
    }
  }
}

static void lcdDrawChar(uint8_t page, uint8_t col, char c, uint8_t spacing = 1) {
  uint8_t g[5];
  glyph5x8(c, g);
  if (col + 5 > LCD_WIDTH) return; // Evitar overflow
  
  // Desenhar no framebuffer
  for (uint8_t i = 0; i < 5; ++i) {
    if (col + i < LCD_WIDTH) {
      lcdBuffer[page][col + i] = g[i];
    }
  }
  
  // Espaçamento (colunas em branco)
  for (uint8_t i = 0; i < spacing && (col + 5 + i) < LCD_WIDTH; ++i) {
    lcdBuffer[page][col + 5 + i] = 0x00;
  }
}

static void lcdDrawText(uint8_t page, uint8_t col, const char* text) {
  uint8_t x = col;
  for (const char* p = text; *p && x < LCD_WIDTH; ++p) {
    lcdDrawChar(page, x, *p);
    x += 6; // 5 columns + 1 spacing
  }
}

static void lcdDrawNumber(uint8_t page, uint8_t col, int num) {
  char buf[12];
  snprintf(buf, sizeof(buf), "%d", num);
  lcdDrawText(page, col, buf);
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
  // Optional: slow down if needed
  // setCpuFrequencyMhz(80);
  lcdInit();

  // Limpar framebuffer
  lcdClearBuffer();
  
  // Teste de gráficos: demonstração de primitivas usando framebuffer
  
  // 1. Retângulo externo (borda do display)
  lcdDrawRect(0, 0, LCD_WIDTH, LCD_HEIGHT);
  
  // 2. Linhas diagonais nos cantos
  lcdDrawLine(0, 0, 20, 10);      // Superior esquerdo
  lcdDrawLine(LCD_WIDTH-1, 0, LCD_WIDTH-21, 10);  // Superior direito
  lcdDrawLine(0, LCD_HEIGHT-1, 20, LCD_HEIGHT-11);  // Inferior esquerdo
  lcdDrawLine(LCD_WIDTH-1, LCD_HEIGHT-1, LCD_WIDTH-21, LCD_HEIGHT-11);  // Inferior direito
  
  // 3. Círculos
  lcdDrawCircle(66, 24, 20);      // Círculo central grande
  lcdDrawCircle(30, 15, 10);      // Círculo pequeno esquerda
  lcdDrawCircle(102, 15, 10);     // Círculo pequeno direita
  
  // 4. Retângulos internos
  lcdDrawRect(10, 10, 30, 15);    // Retângulo pequeno esquerdo
  lcdFillRect(92, 30, 30, 10);    // Retângulo preenchido direito
  
  // 5. Linhas horizontais e verticais
  lcdDrawHLine(5, LCD_WIDTH-6, LCD_HEIGHT/2);  // Linha horizontal central
  lcdDrawVLine(LCD_WIDTH/2, 5, LCD_HEIGHT-6);  // Linha vertical central
  
  // 6. Padrão de linhas
  for (uint8_t i = 0; i < 5; ++i) {
    lcdDrawLine(50 + i*3, 35, 70 + i*3, 45);
  }
  
  // 7. Texto
  lcdDrawText(0, 40, "LCD");
  lcdDrawNumber(5, 100, 132);
  
  // Flush: transferir framebuffer para LCD
  lcdFlush();
  
  delay(100); // Tempo para estabilizar
}

void loop() {
  // Nothing here for now
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
    lcdDrawNumber(page, 8, page * 8);
  }
}