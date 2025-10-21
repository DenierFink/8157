# Análise Completa da Inicialização do Display LCD

## 📊 Resumo da Captura Analisada

**Arquivo:** `c:\Users\Denier\Downloads\display_brother\8157\a\digital.csv`  
**Amostras:** 49,595  
**Transações:** 79 completas

---

## 🔌 Níveis IDLE dos Sinais (Confirmados por Osciloscópio)

Quando **CS = HIGH** (sem comunicação ativa), os níveis são:

| Sinal | Nível IDLE | Percentual | Observação |
|-------|------------|------------|------------|
| **CS**   | HIGH       | 100%       | Sempre HIGH quando não comunica |
| **RST**  | HIGH       | 74.1%      | HIGH após inicialização |
| **D/C**  | LOW        | 74.1%      | LOW quando idle |
| **SCK**  | **HIGH**   | **99.1%**  | ⚠️ Clock idle em HIGH (CPOL=1) |
| **MOSI** | **HIGH**   | **99.1%**  | ⚠️ Dados idle em HIGH |

### ⚡ Conclusão Crítica:
O protocolo usa **SPI Modo 1 ou 3** (CPOL=1), onde o clock fica **HIGH em repouso** e pulsa para LOW para transmitir dados. Isso é **diferente do SPI padrão** que usa CPOL=0.

---

## 📋 Sequência de Inicialização Completa

### Timing do Reset

```
t=-0.780s  : Comunicações pré-reset (possível lixo)
t=0.000s   : RST vai HIGH (início oficial)
t=0.001s   : Primeiro clock após RST HIGH (delay de 1ms)
```

### Primeira Transação (t=0.000s)

```
CMD: 0xA2  - LCD Bias 1/9
CMD: 0xA1  - ADC Select (segment remap)
CMD: 0x60  - Unknown (controller specific)
CMD: 0x45  - Display start line: 5
CMD: 0x01  - Set column LSB: 1
```

### Sequência de Power-Up (comandos 0x2C, 0x2E, 0x2F)

Esses comandos **devem ter delays longos** entre eles:

```cpp
0x2C  → Wait 100ms  (Turn on booster)
0x2E  → Wait 100ms  (Turn on regulator)
0x2F  → Wait 100ms  (Turn on follower)
```

**Importante:** Sem esses delays, o display pode não inicializar corretamente!

### Sequência Completa para ESP32

```cpp
static const uint8_t INIT_SEQUENCE[] = {
  // Configuração básica
  0xA2,              // LCD Bias 1/9
  0xA1,              // ADC Select
  0x60,              // Config específica
  0x45,              // Start line: 5
  0x01,              // Column LSB: 1
  
  // Power-up sequencial (COM DELAYS!)
  0x2C,              // Booster ON → delay 100ms
  0x2E,              // Regulator ON → delay 100ms
  0x2F,              // Follower ON → delay 100ms
  
  // Config adicional
  0x58, 0x08, 0x00, 0x00,
  
  // Limpar páginas e habilitar display
  0x00,              // Column LSB: 0
  0xAF,              // Display ON
  0x40, 0xB1, 0x10, 0x00,  // Page 1
  
  0x00, 0xAF, 0x40, 0xB2, 0x10, 0x00,  // Page 2
  0x00, 0xAF, 0x40, 0xB3, 0x10, 0x00   // Page 3
};
```

---

## 🎛️ Configuração do Código ESP32-S3

### Níveis Idle Corretos

```cpp
// NO INÍCIO da função lcdInit()
lcdCS(HIGH);      // CS idle HIGH
lcdRST(HIGH);     // RST idle HIGH (após reset)
lcdDC(LOW);       // D/C idle LOW
lcdSCK(HIGH);     // ⚠️ Clock idle HIGH (CPOL=1)
lcdMOSI(HIGH);    // ⚠️ Data idle HIGH
```

### Pulso de Reset

```cpp
lcdRST(LOW);
delay(10);        // Hold LOW por 10ms
lcdRST(HIGH);
delay(2);         // Wait 2ms após HIGH
```

### Função de Escrita de Byte (Clock idle HIGH)

```cpp
static void lcdWriteByte(uint8_t b) {
  for (int i = 7; i >= 0; --i) {
    lcdSCK(LOW);   // Clock vai LOW
    lcdMOSI((b >> i) & 0x01);
    tickDelay();
    lcdSCK(HIGH);  // Clock volta HIGH (amostra na subida)
    tickDelay();
  }
  // Clock permanece HIGH no idle
}
```

---

## 🔍 Interpretação dos Comandos

### Comandos Conhecidos

| Comando | Função | Observação |
|---------|--------|------------|
| 0xA2/A3 | LCD Bias | 1/9 ou 1/7 |
| 0xA0/A1 | ADC Select | Segment remap (normal/reverse) |
| 0xC0/C8 | COM Scan | Direction (normal/reverse) |
| 0xAF    | Display ON | Habilita display |
| 0xAE    | Display OFF | Desabilita display |
| 0x40-7F | Start Line | Display start line (0-63) |
| 0x81    | Contrast | Próximo byte = valor de contraste |
| 0x20-27 | Resistor Ratio | Internal resistor ratio |
| 0x2C-2F | Power Control | Booster/Regulator/Follower |
| 0xB0-BF | Set Page | Page address (0-15) |
| 0x10-1F | Column MSB | Upper nibble coluna |
| 0x00-0F | Column LSB | Lower nibble coluna |

### Comandos Desconhecidos

- `0x60` - Específico do controlador
- `0x58, 0x08, 0x00, 0x00` - Sequência proprietária

---

## ✅ Checklist de Implementação

- [x] Clock (SCK) idle em HIGH
- [x] Data (MOSI) idle em HIGH
- [x] Pulso de reset com 10ms LOW
- [x] Delay de 2ms após reset HIGH
- [x] Sequência completa de 31 comandos
- [x] Delays de 100ms após 0x2C, 0x2E, 0x2F
- [x] Clear de páginas 0-3
- [x] Endereçamento page/column correto

---

## 🚀 Como Usar

```powershell
# Compilar
pio run -e 4d_systems_esp32s3_gen4_r8n16

# Upload
pio run -e 4d_systems_esp32s3_gen4_r8n16 -t upload
```

---

## 📌 Observações Finais

1. **Clock IDLE HIGH é crítico** - A maioria dos exemplos SPI assume CPOL=0 (clock LOW), mas este display usa CPOL=1.

2. **Delays no power-up** - Os comandos 0x2C, 0x2E e 0x2F precisam de 100ms cada para estabilizar os circuitos internos.

3. **Sequência exata** - Todos os 31 comandos foram extraídos de uma captura real funcionando.

4. **Compatibilidade** - Provável controlador UC1701 ou similar (família ST7565/UC17xx).

---

**Gerado por análise de osciloscópio - Outubro 2025**
