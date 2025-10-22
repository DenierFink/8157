# ESP32-S3 LCD Driver (132×48) - Projeto Completo

> Driver completo com framebuffer, múltiplas fontes, primitivas gráficas e controle PWM de backlight

## 🎯 Status do Projeto

**✅ DRIVER COMPLETO E FUNCIONAL!**

- ✅ Protocolo completamente implementado
- ✅ Framebuffer de 792 bytes funcionando
- ✅ Primitivas gráficas (linhas, círculos, triângulos, retângulos)
- ✅ Duas fontes (5×7 e 3×5) com 95 glifos ASCII cada
- ✅ Controle PWM de backlight (8 bits, 0-255)
- ✅ Suporte a bitmaps (PROGMEM)
- ✅ Demos incluídas e testadas

---

## 📋 Características

### Hardware
- **Display**: 132 colunas × 48 linhas (6 páginas × 8 pixels/página)
- **Controlador**: UC1701/ST7565-like (page-addressable)
- **Interface**: SPI bit-bang (SCK/MOSI/CS/D/C/RST)
- **Backlight**: PWM de 8 bits (GPIO 15, 5 kHz)
- **Plataforma**: ESP32-S3 (testado em 4D Systems GEN4-ESP32 S3 R8N16)

### Software
- ✅ **Framebuffer completo** (792 bytes RAM) - elimina artefatos visuais
- ✅ **Primitivas gráficas**: linhas, retângulos, círculos, triângulos (outline e filled)
- ✅ **Fontes múltiplas**: 
  - 5×7 pixels (fonte padrão, domínio público)
  - 3×5 pixels (compacta para labels)
- ✅ **95 glifos ASCII** (32..126) com fallback automático
- ✅ **Suporte a bitmaps** (PROGMEM) com qualquer tamanho
- ✅ **Controle PWM de backlight** (0-255)
- ✅ **Demos incluídas**: texto scrolling, animações, testes de fonte

---

## 🔌 Pinagem

| Função     | GPIO | Descrição                          |
|------------|------|------------------------------------|
| CS         | 10   | Chip Select (ativo LOW)            |
| D/C        | 11   | Data/Command (0=cmd, 1=data)       |
| RST        | 12   | Reset (ativo LOW)                  |
| SCK        | 13   | Clock (bit-bang, rising edge)      |
| MOSI       | 14   | Data out (MSB first)               |
| BACKLIGHT  | 15   | PWM backlight (HIGH=ON)            |

*Nota: pinos podem ser redefinidos em `src/main.cpp`*

---

## 🚀 Uso Rápido

### Inicialização
```cpp
lcdInit();           // Inicializa display
lcdBacklightOn();    // Liga backlight no máximo
lcdClearBuffer();    // Limpa framebuffer
lcdFlush();          // Envia buffer para LCD
```

### Desenho de Texto
```cpp
// Fonte 5×7 (padrão)
lcdDrawText(1, 10, "Hello World", FONT_5X7);

// Fonte 3×5 (compacta)
lcdDrawText(4, 5, "Compact text", FONT_3X5);

// Números
lcdDrawNumber(2, 50, 12345, FONT_5X7);
```

### Primitivas Gráficas
```cpp
// Linhas
lcdDrawLine(0, 0, 131, 47);
lcdDrawHLine(0, 131, 24);      // linha horizontal
lcdDrawVLine(66, 0, 47);       // linha vertical

// Retângulos
lcdDrawRect(10, 10, 50, 30);   // outline
lcdFillRect(70, 10, 50, 30);   // preenchido

// Círculos
lcdDrawCircle(66, 24, 20);

// Triângulos
lcdDrawTriangle(10, 10, 30, 10, 20, 30);
lcdFillTriangle(50, 10, 70, 10, 60, 30);

// Pixel individual
lcdSetPixel(66, 24, true);  // true=aceso, false=apagado
```

### Controle de Backlight
```cpp
lcdBacklightOn();         // Máximo (255)
lcdBacklightOff();        // Desligado (0)
lcdSetBacklight(128);     // Meio brilho (0-255)
```

### Bitmaps
```cpp
// Definir bitmap em PROGMEM (vertical, LSB=top)
static const uint8_t PROGMEM myBitmap[] = {
  0xFF, 0x81, 0xBD, 0xBD, 0x81, 0xFF  // 6×8 pixels
};

// Desenhar
lcdDrawBitmap(10, 20, myBitmap, 6, 8);
```

---

## 📚 API Completa

### Controle de Display
| Função | Descrição |
|--------|-----------|
| `lcdInit()` | Inicializa display e framebuffer |
| `lcdClearBuffer()` | Limpa framebuffer (todos pixels apagados) |
| `lcdFillBuffer(pattern)` | Preenche framebuffer com padrão |
| `lcdFlush()` | Envia framebuffer para LCD |

### Backlight
| Função | Descrição |
|--------|-----------|
| `lcdBacklightOn()` | Liga backlight no máximo |
| `lcdBacklightOff()` | Desliga backlight |
| `lcdSetBacklight(brightness)` | Define brilho (0-255) |

### Gráficos
| Função | Descrição |
|--------|-----------|
| `lcdSetPixel(x, y, on)` | Define pixel individual |
| `lcdGetPixel(x, y)` | Lê estado de pixel |
| `lcdDrawLine(x0, y0, x1, y1)` | Linha (Bresenham) |
| `lcdDrawHLine(x0, x1, y)` | Linha horizontal |
| `lcdDrawVLine(x, y0, y1)` | Linha vertical |
| `lcdDrawRect(x, y, w, h)` | Retângulo (outline) |
| `lcdFillRect(x, y, w, h)` | Retângulo preenchido |
| `lcdDrawCircle(x, y, r)` | Círculo (midpoint) |
| `lcdDrawTriangle(x0,y0,x1,y1,x2,y2)` | Triângulo (outline) |
| `lcdFillTriangle(x0,y0,x1,y1,x2,y2)` | Triângulo preenchido |

### Texto
| Função | Descrição |
|--------|-----------|
| `lcdDrawChar(page, col, char, font)` | Desenha caractere |
| `lcdDrawText(page, col, text, font)` | Desenha string |
| `lcdDrawNumber(page, col, num, font)` | Desenha número |

**Fontes disponíveis**: `FONT_5X7` (padrão), `FONT_3X5` (compacta)

### Bitmaps
| Função | Descrição |
|--------|-----------|
| `lcdDrawBitmap(x, y, bitmap, w, h)` | Desenha bitmap (PROGMEM OK) |

---

## � Demos Incluídas

Descomente no `setup()` para ativar:

```cpp
demoFontSelfTest();       // Testa todas as fontes (A-Z, 0-9, símbolos)
demoGraphicsPrimitives(); // Linhas, círculos, retângulos
demoTextScrollBitmap();   // Texto scrolling + bitmaps animados
demoAllFeatures();        // Demo completa (fontes, shapes, animação, backlight)
```

---

## 📊 Uso de Memória

| Recurso | Tamanho | Observação |
|---------|---------|------------|
| Framebuffer | 792 bytes | RAM (6 páginas × 132 colunas) |
| Fonte 5×7 | ~475 bytes | Flash (95 glifos × 5 bytes) |
| Fonte 3×5 | ~285 bytes | Flash (95 glifos × 3 bytes) |
| **Total Flash** | ~249 KB | Firmware completo com demos |
| **Total RAM** | ~19 KB | 5.8% do ESP32-S3 |

---

## 🔧 Configuração Avançada

### Ajustar Velocidade do Clock
```cpp
static inline void tickDelay() {
  delayMicroseconds(1);  // Aumentar se necessário
}
```

### Redefinir Pinos
```cpp
#define LCD_PIN_CS    10
#define LCD_PIN_DC    11
#define LCD_PIN_RST   12
#define LCD_PIN_SCK   13
#define LCD_PIN_MOSI  14
#define LCD_PIN_BACKLIGHT 15
```

### Ajustar Frequência PWM do Backlight
```cpp
#define LCD_BACKLIGHT_FREQ 5000  // Hz
#define LCD_BACKLIGHT_RESOLUTION 8  // bits (0-255)
```

---

## 📁 Estrutura do Projeto

```
8157/
├── src/
│   └── main.cpp              # Driver completo
├── include/
│   ├── font5x7.h             # Fonte 5×7 (domínio público)
│   └── font3x5.h             # Fonte 3×5 (compacta)
├── analysis/                 # Scripts de engenharia reversa
│   ├── analyze_signals.py
│   └── ...
├── platformio.ini            # Configuração do projeto
└── README.md                 # Esta documentação
```

---

## 🛠️ Build e Upload

```bash
# Compilar
pio run -e 4d_systems_esp32s3_gen4_r8n16

# Compilar e fazer upload
pio run -e 4d_systems_esp32s3_gen4_r8n16 -t upload

# Monitor serial
pio device monitor
```

---

## 📖 Protocolo do Display

### Comandos Principais
| Comando | Descrição |
|---------|-----------|
| `0xA2` | LCD Bias 1/9 |
| `0xA1` | ADC Select (segment remap) |
| `0xC0` | Common output mode normal |
| `0x2C/2E/2F` | Power control (staged) |
| `0xB0-B5` | Set page (0-5) |
| `0x10+MSB, 0x00+LSB` | Set column (0-131) |

### Formato de Dados
- **Page-addressable**: 6 páginas × 8 pixels/página
- **Byte vertical**: LSB = topo, MSB = fundo
- **MSB first**: bit 7 transmitido primeiro

---

## ⚠️ Notas Importantes

1. **Sempre usar framebuffer**: escrever diretamente no LCD causa artefatos visuais
2. **Chamar `lcdFlush()`**: após desenhar no framebuffer para atualizar display
3. **Backlight invertido**: alguns displays usam LOW=ON (ajustar se necessário)
4. **Bounds checking**: primitivas gráficas fazem clipping automático

---

## 🐛 Troubleshooting

| Problema | Solução |
|----------|---------|
| Display em branco | Verificar init sequence, adicionar delays |
| Artefatos visuais | Usar framebuffer (`lcdClearBuffer()` + `lcdFlush()`) |
| Backlight não acende | Inverter lógica em `lcdSetBacklight()` |
| Texto cortado | Verificar bounds (col + largura < 132) |
| Clock muito rápido | Adicionar delay em `tickDelay()` |

---

## 📝 Licença

- **Driver**: Criado para este projeto (uso livre)
- **Fonte 5×7**: Domínio público (Adafruit GFX)
- **Fonte 3×5**: Domínio público

---

## 🙏 Créditos

- Reverse engineering do protocolo via analisador lógico Saleae
- Fonte 5×7 baseada em Adafruit GFX Library (domínio público)
- Algoritmos gráficos: Bresenham (linhas), Midpoint (círculos), Scan-line (triângulos)

---

## 📞 Informações

**Projeto**: ESP32-S3 LCD Driver  
**Versão**: 1.0  
**Data**: Outubro 2025  
**Plataforma**: PlatformIO + Arduino Framework  
**Testado**: ESP32-S3 (4D Systems GEN4-ESP32 S3 R8N16)

---

## 🎯 Resultados

```
✅ Display: 132×48 pixels funcionando perfeitamente
✅ Framebuffer: Renderização sem artefatos
✅ Gráficos: Todas primitivas testadas
✅ Fontes: 2 tamanhos completos (ASCII 32-126)
✅ Backlight: Controle PWM 8-bit funcionando
✅ Demos: 4 demos completas incluídas
✅ Memória: Flash 3.8%, RAM 5.8%
```

**Driver completo e pronto para uso! 🎉**

---

## 📁 Estrutura do Projeto

```
8157/
├── digital.csv              # Captura Saleae (49.595 amostras)
├── platformio.ini           # Configuração PlatformIO
├── Session 1.sal            # Arquivo de sessão Saleae
│
├── analysis/                # 🔬 Scripts de análise
│   ├── identify_channels.py      # Identifica função de cada canal
│   ├── verify_clock_data.py      # Verifica clock vs data
│   ├── complete_decoder.py       # Decoder completo
│   ├── visualize_timeline.py     # Timeline visual
│   └── visualize_characters.py   # Visualiza bitmaps de caracteres
│
├── src/
│   └── main.cpp             # Código do microcontrolador
│
├── ANALISE_LCD.md           # 📊 Documentação técnica completa
├── RESUMO_FINAL.md          # 🎯 Resumo executivo
└── decoded_lcd_protocol.txt # 📝 Todas transações decodificadas
```

---

## 🔌 Mapeamento dos Canais (CORRETO)

| Canal | Sinal | Função | Características |
|-------|-------|--------|-----------------|
| CH0 | CS/EN | Chip Select/Enable | Pulsos curtos (~2µs), 99.8% LOW |
| CH1 | RST | Reset/Enable | **TRIGGER** - vai HIGH e permanece |
| CH2 | D/C | Data/Command | 0=Comando, 1=Dados (95% HIGH) |
| CH3 | **SCK** | **Serial Clock** | ~456 pulsos, período 6µs |
| CH4 | **MOSI** | **Serial Data** | Sincronizado com CH3 |

### ⚠️ Observação Importante
Inicialmente assumimos CH3=dados e CH4=clock, mas análise revelou:
- **CH3 tem padrão de 8 pulsos** (clock de bytes)
- **CH4 alterna sincronizado** (linha de dados)

---

## 📊 Estatísticas da Captura

- **Duração total**: 8.11 segundos
- **Amostras**: 49.595
- **Bytes decodificados**: 2.840
- **Comandos**: 124 bytes (48 únicos)
- **Dados**: 2.716 bytes
- **Transações**: 49

---

## 🚀 Quick Start - Análise

### 1. Identificar canais
```bash
python analysis/identify_channels.py
```
Mostra transições, pulsos e comportamento de cada canal.

### 2. Verificar clock e dados
```bash
python analysis/verify_clock_data.py
```
Confirma CH3=clock, CH4=dados e decodifica primeiros bytes.

### 3. Decodificar tudo
```bash
python analysis/complete_decoder.py
```
Decodifica todas transações e exporta para `decoded_lcd_protocol.txt`.

### 4. Visualizar timeline
```bash
python analysis/visualize_timeline.py
```
Mostra timeline visual com comandos e dados.

### 5. Ver caracteres
```bash
python analysis/visualize_characters.py
```
Visualiza bitmaps de caracteres encontrados.

---

## 🎨 Descobertas Principais

### 1. Protocolo
**SPI-like serial** com sinal D/C (Data/Command)
- MSB first
- Amostragem na borda de subida do clock
- ~167 kbps

### 2. Sequência de Inicialização
```
0xD1 0x50 0xB0 0x22 0xA5 0x85 0xC5 0xEB 0x01 0x00 0x00
```
Primeiro comando enviado após reset.

### 3. Display ON
```
0xAF 0x40 0x80 0x00  @ t=4.414s
```

### 4. Escrita de Dados
```
0x2C 0xC4 0x00 0x00  @ t=4.418s  (Memory Write)
```
Seguido de bitmaps de caracteres.

### 5. Caractere Identificado
**Letra "A"** encontrada nos dados:
```
0xF8 0x24 0x22 0x24 0xF8
```
Formato: bytes verticais (coluna de pixels)

---

## 🔍 Controlador LCD Candidato

Baseado nos comandos:
- **UC1701** (provável)
- **ST75320**
- **SSD1306-like**

Evidências:
- `0xAF` = Display ON (padrão)
- `0xA0` = Segment Remap
- `0xD1` = Oscillator config
- Organização em colunas verticais

---

## 📝 Próximos Passos

### Para completar:
1. ✅ Identificar canais → **FEITO**
2. ✅ Decodificar protocolo → **FEITO**
3. ✅ Encontrar dados → **FEITO** (letra "A")
4. ⏳ Identificar controlador exato
5. ⏳ Implementar driver Arduino
6. ⏳ Testar comunicação bidirecional

### Capturar mais dados:
- Diferentes caracteres/textos
- Números
- Gráficos
- Animações

---

## 🛠️ Tecnologias Utilizadas

- **Saleae Logic Analyzer** - Captura de sinais
- **Python 3** - Scripts de análise
- **PlatformIO** - Desenvolvimento embedded
- **VS Code** - IDE

---

## 📚 Documentação

| Arquivo | Descrição |
|---------|-----------|
| [ANALISE_LCD.md](ANALISE_LCD.md) | Documentação técnica completa |
| [RESUMO_FINAL.md](RESUMO_FINAL.md) | Resumo executivo das descobertas |
| `decoded_lcd_protocol.txt` | Todas as transações decodificadas |

---

## 📞 Informações

**Projeto**: Engenharia Reversa LCD  
**Data**: Outubro 2025  
**Status**: ✅ Protocolo identificado com sucesso  
**Próxima fase**: Identificação do controlador e implementação de driver

---

## 🎯 Resultados

```
✅ Protocolo: SPI-like serial identificado
✅ Canais: CH3=Clock, CH4=Data (corrigido)
✅ Taxa: ~167 kbps
✅ Formato: MSB first, bytes verticais
✅ Dados: Letra "A" decodificada
✅ Comandos: 48 únicos documentados
✅ Sequência init: Capturada
```

**Engenharia reversa bem-sucedida! 🎉**
