# Manual do Display e Keypad

## 1. Informações do Hardware

### Display LCD
*   **Resolução:** 132 x 48 pixels.
*   **Driver/Controlador:** Compatível com família ST7565 / UC1701.
*   **Interface:** Serial (SPI por software / "Bit-Bang").
*   **Tensão de operação:** 3.3V (Níveis lógicos do ESP32-S3).

### Keypad
*   **Tipo:** 5 botões (D-Pad + OK).
*   **Configuração:** Pull-up interno (Ativo em nível BAIXO / GND).

---

## 2. Mapeamento de Pinos (ESP32-S3)

### Display LCD (Interface SPI)
| Sinal | Pino ESP32 | Função | Notas |
| :--- | :--- | :--- | :--- |
| **CS** | **5** | Chip Select | Ativo em LOW. Seleciona o display no barramento. |
| **RST** | **4** | Reset | Ativo em LOW. Reinicia o controlador. |
| **DC** | **16** | Data/Command | LOW = Comando, HIGH = Dados. |
| **SCK** | **18** | Serial Clock | Clock da interface serial. |
| **MOSI** | **23** | Master Out | Dados enviados para o display. |
| **LED** | **15** | Backlight | Controle PWM de brilho (0-255). |

### Keypad (Botões)
*Atenção: Os pinos foram alterados para evitar conflito com a memória Octal PSRAM/Flash do ESP32-S3 (Pinos 33-37).*

| Botão | Pino ESP32 | Modo |
| :--- | :--- | :--- |
| **UP** | **10** | INPUT_PULLUP (Ativo LOW) |
| **DOWN** | **11** | INPUT_PULLUP (Ativo LOW) |
| **LEFT** | **12** | INPUT_PULLUP (Ativo LOW) |
| **RIGHT**| **13** | INPUT_PULLUP (Ativo LOW) |
| **OK** | **14** | INPUT_PULLUP (Ativo LOW) |

---

## 3. Controle via Software (Resumo)

### Arquitetura do Driver
O driver (`src/main.cpp`) utiliza um **Framebuffer** na RAM do ESP32. Nada é desenhado no display imediatamente; as funções gráficas desenham na memória e `lcdFlush()` envia os dados para a tela.

### Funções Principais
*   **Inicialização:** `lcdInit()` - Configura pinos e envia sequência de boot.
*   **Limpeza:** `lcdClearBuffer()` - Limpa a memória de vídeo.
*   **Atualização:** `lcdFlush()` - Copia o buffer para o hardware do LCD.
*   **Brilho:** `lcdSetBacklight(0-255)` - Ajusta o brilho do LED de fundo.

### Gráficos e Texto
*   `lcdDrawText(page, col, "Texto", FONT_5X7)` - Escreve texto.
*   `lcdSetPixel(x, y, on)` - Acende/apaga um pixel.
*   `lcdDrawLine(x0, y0, x1, y1)` - Desenha linha.
*   `lcdDrawRect(x, y, w, h)` - Desenha retângulo vazio.
*   `lcdFillRect(x, y, w, h)` - Desenha retângulo preenchido.
*   `lcdDrawCircle(x, y, r)` - Desenha círculo.

### Sequência de Inicialização (Bytes)
A sequência enviada ao ligar o display inclui:
1.  **Bias Ratio:** 1/9 (0xA2).
2.  **ADC Select:** Normal/Invertido horizontalmente (0xA0/0xA1).
3.  **Power Control:** Booster -> Regulator -> Follower (0x2C, 0x2E, 0x2F).
4.  **Display ON:** (0xAF).

---

## 4. Diagnóstico

Se o display não ligar:
1.  Verifique o **Backlight** (Pino 15 deve ter tensão/PWM).
2.  Verifique se **RST** (Pino 4) vai de LOW para HIGH na inicialização.
3.  Execute o `runPinPermutationTest()` (ativado no código atual na função `setup()`) para validar se a pinagem corresponde à PCB.
