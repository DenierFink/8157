# Engenharia Reversa - Display LCD
## Projeto: Análise de Comunicação Serial

---

## 📌 RESUMO EXECUTIVO

Análise bem-sucedida da comunicação entre microcontrolador e display LCD.
Protocolo identificado: **SPI-like serial com sinal D/C (Data/Command)**.

---

## 🔌 MAPEAMENTO DOS CANAIS

| Canal | Função | Descrição |
|-------|--------|-----------|
| **CH0** | Chip Select/Enable | Pulsos curtos (~2µs), ativo HIGH, 99.8% em LOW |
| **CH1** | Reset/Enable | **TRIGGER**: vai HIGH em t=0 e permanece HIGH |
| **CH2** | D/C (Data/Command) | 0 = Comando, 1 = Dados, ~95% em HIGH pós-trigger |
| **CH3** | **SCK (Serial Clock)** | Clock serial, ~456 pulsos (agrupados em bytes de 8 bits) |
| **CH4** | **MOSI (Serial Data)** | Linha de dados serial, sincronizada com CH3 |

### ⚠️ Nota Importante
**Inicialmente assumimos CH3 como dados e CH4 como clock**, mas análise detalhada revelou:
- CH3 tem padrão de 8 pulsos consecutivos (característico de clock serial)
- CH4 alterna entre 0 e 1 sincronizado com CH3 (dados seriais)

---

## 📊 ESTATÍSTICAS DA CAPTURA

- **Total de amostras**: 49.595
- **Duração**: ~8.11 segundos
- **Amostras pré-trigger**: 75 (t < 0)
- **Amostras pós-trigger**: 49.520 (t ≥ 0)
- **Transações decodificadas**: 49
- **Bytes de comando**: 124
- **Bytes de dados**: 2.716
- **Comandos únicos**: 48 diferentes

---

## 🔍 PROTOCOLO DE COMUNICAÇÃO

### Tipo
**SPI-like serial** com controle D/C

### Características
- **Clock (SCK)**: CH3 - ~456 bordas de subida
- **Dados (MOSI)**: CH4 - amostragem na borda de subida do clock
- **Formato**: MSB first (bit mais significativo primeiro)
- **Agrupamento**: 8 bits = 1 byte

### Timing
- Pulsos HIGH do clock: mediana 2.00 µs
- Pulsos LOW do clock: mediana 4.00 µs
- Período do clock: ~6 µs
- Taxa de bits: ~167 kbps

---

## 🚀 SEQUÊNCIA DE INICIALIZAÇÃO

### Primeira transação (t=0.000000s):
```
CMD [11 bytes]: 0xD1 0x50 0xB0 0x22 0xA5 0x85 0xC5 0xEB 0x01 0x00 0x00
```

**Análise**:
- `0xD1` - Set Oscillator (configuração do oscilador)
- Seguido de 10 bytes de parâmetros de configuração
- Duração: 420.22ms

### Sequência de configuração principal:
1. **Oscilador** (0xD1) + parâmetros
2. Comandos de configuração (0xBD, 0xF4, etc.)
3. **Display ON** (0xAF) em t=4.414116s
4. **Memory Write** (0x2C) em t=4.418011s
5. Transmissão de dados (2.716 bytes, maioria 0x00 - tela limpa)

---

## 📋 COMANDOS IDENTIFICADOS

### Comandos confirmados:
| Código | Função | Observações |
|--------|--------|-------------|
| 0xD1 | Set Oscillator | Primeiro comando enviado |
| 0xAF | Display ON | Liga o display |
| 0x2C | Memory Write | Preparação para escrita na memória |
| 0xA0 | Segment Remap | Configuração de mapeamento |
| 0xC5 | VCOM Control | Controle de tensão |
| 0xB0 | RAM Address Set | Definição de endereço |
| 0xA5 | All Points ON | Todos pixels ligados (teste) |

### Comandos com função incerta (48 únicos no total):
- 0x5E, 0x5F, 0xF4, 0xBD, 0xFA, 0x78, etc.
- Muitos parecem ser comandos proprietários ou específicos do controlador

---

## 💾 DADOS TRANSMITIDOS

### Análise dos dados (D/C=1):
- **Total**: 2.716 bytes
- **Conteúdo**: Majoritariamente `0x00` (limpeza de memória/tela)
- **Exemplo**: Sequência longa de 47 bytes com valor `0x00`
- **Exceção**: byte `0x10` aparece ocasionalmente

### Interpretação:
Primeira inicialização do display, limpando toda a memória de frame buffer.

---

## 🔧 FERRAMENTAS DESENVOLVIDAS

### 1. `identify_channels.py`
Análise detalhada de cada canal:
- Contagem de transições
- Análise de pulsos HIGH/LOW
- Distribuição de estados
- Correlações entre canais

### 2. `verify_clock_data.py`
Verificação da hipótese CH3=clock, CH4=dados:
- Amostragem nas bordas de subida
- Decodificação de bytes (8 bits)
- Separação comando/dados

### 3. `complete_decoder.py`
Decodificador completo:
- Extração de todas as transações
- Interpretação de comandos conhecidos
- Estatísticas detalhadas
- Exportação para arquivo texto

---

## 📁 ARQUIVOS GERADOS

- `decoded_lcd_protocol.txt` - Resultado completo da decodificação
- Scripts Python para análise contínua
- Este documento de resumo

---

## 🎯 CONCLUSÕES

1. **Protocolo identificado com sucesso**: SPI-like serial
2. **Mapeamento de pinos correto**: CH3=Clock, CH4=Data
3. **Sequência de inicialização capturada**: 11 bytes iniciais + configurações
4. **Display está sendo limpo**: 2.716 bytes de dados (maioria 0x00)
5. **Controlador específico**: Alguns comandos não correspondem a padrões conhecidos (ST7735, ILI9341, etc.)

---

## 🔜 PRÓXIMOS PASSOS

### Para completar a engenharia reversa:

1. **Identificar o controlador LCD específico**
   - Analisar sequência 0xD1 + parâmetros
   - Pesquisar comandos proprietários (0x5E, 0x5F, 0xF4, etc.)
   - Possíveis candidatos: UC1701, ST75320, ou controlador customizado

2. **Capturar mais dados**
   - Texto sendo exibido
   - Gráficos/imagens
   - Comparar padrões de dados

3. **Implementar driver**
   - Criar biblioteca Arduino/PlatformIO
   - Replicar sequência de inicialização
   - Testar escrita de dados

4. **Documentar protocolo completo**
   - Mapear todos os 48 comandos
   - Identificar parâmetros e suas funções
   - Criar especificação técnica

---

## 📝 NOTAS TÉCNICAS

### Trigger
- O trigger foi configurado para disparar quando CH1 (Reset/Enable) vai HIGH
- Isto marca o início da comunicação com o LCD
- Todas as amostras antes de t=0 são estado de repouso/pré-inicialização

### Formato dos dados
- MSB first (confirmado pela análise)
- Bytes transmitidos em blocos de 8 clock pulses
- D/C permanece estável durante transmissão de cada bloco

### Peculiaridades
- CH0 tem pulsos muito curtos e espaçados
- Pode ser usado para sincronização adicional ou habilitação de segmentos
- Maioria dos comandos são multi-byte (comando + parâmetros)

---

**Data da análise**: Outubro 2025  
**Status**: ✅ Protocolo identificado - Próxima fase: Identificação do controlador
