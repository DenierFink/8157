# 🔬 Projeto: Engenharia Reversa - Display LCD

> Análise completa da comunicação serial entre microcontrolador e display LCD usando captura Saleae Logic Analyzer

## 🎯 Status do Projeto

**✅ PROTOCOLO COMPLETAMENTE DECODIFICADO!**

- ✅ Canais identificados
- ✅ Protocolo SPI-like confirmado
- ✅ Sequência de inicialização capturada
- ✅ Caracteres decodificados (letra "A" confirmada)
- ✅ Comandos documentados

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
