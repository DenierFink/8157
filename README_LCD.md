# Driver LCD para ESP32-S3

Firmware para controlar o display LCD usando comunicação SPI bit-bang (software) baseado na engenharia reversa do protocolo original.

## � Especificações do Display

- **Resolução:** 132 × 48 pixels (confirmado por testes)
- **Páginas:** 6 páginas de 8 pixels de altura
- **Área visível:** Colunas 0-131, Linhas 0-47
- **Controlador:** Similar a UC1701/ST7565 (page-addressable)
- **Interface:** SPI-like, write-only

## �📌 Configuração de Pinos

Por padrão, o código usa os seguintes GPIOs do ESP32-S3:

| Sinal | GPIO | Função                          |
|-------|------|---------------------------------|
| CS    | 10   | Chip Select (ativo LOW)        |
| D/C   | 11   | Data/Command (0=cmd, 1=data)   |
| RST   | 12   | Reset (ativo LOW)              |
| SCK   | 13   | Serial Clock                    |
| MOSI  | 14   | Master Out Slave In (dados)    |

### ⚠️ Alterar Pinos

Para usar outros pinos, edite no topo de `src/main.cpp`:

```cpp
#define LCD_PIN_CS   10  // Seu pino CS
#define LCD_PIN_DC   11  // Seu pino D/C
#define LCD_PIN_RST  12  // Seu pino RST
#define LCD_PIN_SCK  13  // Seu pino SCK
#define LCD_PIN_MOSI 14  // Seu pino MOSI
```

**Pinos seguros no ESP32-S3:**
- ✅ GPIO 10-14 (escolhidos por padrão)
- ✅ GPIO 1, 2, 4-9, 15-18, 21, 33-38, 39-42, 47-48
- ⚠️ **EVITAR:** GPIO 0, 3, 19-20 (USB), 26-32 (Flash/PSRAM), 45-46 (straps)

## 🚀 Compilar e Upload

### 1. Compilar o firmware

```powershell
pio run -e 4d_systems_esp32s3_gen4_r8n16
```

### 2. Fazer upload para o ESP32-S3

Conecte o ESP32-S3 via USB e execute:

```powershell
pio run -e 4d_systems_esp32s3_gen4_r8n16 -t upload
```

### 3. Monitorar saída serial (opcional)

```powershell
pio device monitor -b 115200
```

## 🔧 Protocolo e Inicialização

### Sequência de Inicialização

O código usa a sequência extraída do microcontrolador que funciona:

```cpp
0xD1, 0x50, 0xB0, 0x2A, 0x58, 0x5C, 0x01
```

Essa é a sequência mínima e confirmada que inicializa o display corretamente.

### Timing

- **Clock:** ~1 MHz por padrão (pode ajustar com delays)
- **Polaridade:** Dados amostrados na borda de SUBIDA do SCK
- **Ordem:** MSB primeiro (bit 7 → bit 0)
- **CS:** Ativo LOW durante transmissão

### Comandos de Endereçamento

```cpp
lcdSetPage(0-5);        // Seleciona página (0-5 para 48 linhas)
lcdSetColumn(0-131);    // Seleciona coluna horizontal (0-131 para 132 colunas)
```

### Constantes Disponíveis

```cpp
LCD_WIDTH  = 132   // Largura total em pixels
LCD_HEIGHT = 48    // Altura total em pixels
LCD_PAGES  = 6     // Número de páginas (48 / 8)
```

## 📝 Fonte e Caracteres

O código inclui uma fonte 5x8 pixels com os seguintes caracteres:

- **Letras**: 'A', 'F'
- **Dígitos**: '0'-'9' (completo)
- **Símbolos**: '-', ':', ' ' (espaço)

Caracteres desconhecidos são renderizados como um box (▢).

### Adicionar Texto

```cpp
lcdDrawText(0, 0, "12:34");     // Página 0, coluna 0
lcdDrawNumber(1, 10, 2025);     // Desenha número na página 1, coluna 10
lcdDrawChar(2, 50, 'A');        // Caractere único
```

### Limites de Renderização

O código automaticamente limita a escrita à área visível (0-131 colunas, 0-5 páginas) para evitar overflow.

## 🐛 Troubleshooting

### Display não acende

1. **Verificar conexões físicas:**
   - Todos os pinos conectados corretamente?
   - Display alimentado com 3.3V?
   - GND comum entre ESP32 e display?

2. **Testar pulso de reset:**
   - RST deve ir LOW por 10ms, depois HIGH

3. **Ajustar velocidade do clock:**
   - No código, descomente `delayMicroseconds(1);` dentro de `tickDelay()`

### Display mostra pixels aleatórios

1. **Comandos de orientação:**
   - Adicione após a init: `lcdWriteCommand(0xA0);` ou `0xA1` (segment remap)
   - Adicione: `lcdWriteCommand(0xC0);` ou `0xC8` (COM scan direction)

2. **Limpar toda a RAM:**
   - Aumente o loop de limpeza para todas as páginas (0-7)

### Texto não aparece

1. **Verificar D/C:**
   - Comando: D/C = LOW
   - Dados: D/C = HIGH

2. **Confirmar endereçamento:**
   - `lcdSetPage()` antes de escrever
   - `lcdSetColumn()` define posição horizontal

## 📚 Referências

- **Análise do protocolo:** Ver arquivos em `analysis/`
- **Capturas originais:** `digital.csv`, `display1.csv`
- **Documentação detalhada:** `ANALISE_LCD.md`, `ANALISE_DISPLAY1.md`

## 🔮 Próximos Passos

- [ ] Adicionar fonte ASCII completa (32-127)
- [ ] Implementar scroll horizontal/vertical
- [ ] Ajustar contraste via comando 0x81
- [ ] Suporte a gráficos bitmap maiores
- [ ] Modo sleep/wake do display

---

**Criado por engenharia reversa - Outubro 2025**
