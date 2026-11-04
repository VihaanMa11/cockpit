# Cockpit Hardware Wiring & Setup Guide

This guide details the complete wiring for the desk console setup:
- **Display**: 3.5" / 4.0" SPI TFT Screen (covers Physical Header Pins 1–26)
- **Controls**: 3 Momentary Push-Buttons (Screen Cycle, List Scroll, Select/Run)
- **Environment**: 3-Pin DHT Sensor (`+`, `-`, `OUT`) — auto-detects DHT11 / DHT22
- **Proximity / Auth**: RFID (RC522) Reader (or nRF module)

---

## 1. 3-Pin DHT Sensor Wiring (Positive, Negative, Output)

Your 3-pin DHT sensor board has three terminals:
- `+` / `VCC` (Positive)
- `-` / `GND` (Negative)
- `OUT` / `S` / `DAT` (Signal / Output)

> **No External Resistor Needed**: 3-pin DHT breakout modules have the required 10kΩ pull-up resistor already soldered onto the PCB. You can connect it directly to the Pi.

| Sensor Pin / Marking | Connects To | Raspberry Pi Header Pin | Notes |
| :--- | :--- | :--- | :--- |
| **`+` (Positive)** | **3.3V Power** | **Physical Pin 1** or **Pin 17** | ⚠️ Connect to **3.3V**, never to 5V. |
| **`-` (Negative)** | **Ground (GND)** | **Physical Pin 9** (or any GND) | Connect to common ground. |
| **`OUT` (Output)** | **GPIO 4** | **Physical Pin 7** | Digital 1-wire signal. |

*The backend code is configured with `"type": "auto"`, meaning it automatically communicates with both blue 3-pin DHT11 and white 3-pin DHT22 sensors.*

---

## 2. Push-Buttons (3 Total)

### Are Button Nodes Polarized?
**No.** Push-buttons are passive mechanical switches without positive or negative polarity.

### How to Connect Buttons (Ground Daisy-Chain)
1. Join one leg of each button together into a single **shared Ground wire** tied to **Pin 34 (GND)**.
2. Run the second leg of each button directly to its assigned GPIO pin:

```
Pi Pin 34 (GND) ───┬──────────────────────┬──────────────────────┐
                   │                      │                      │
             [Button 1: SCREEN]     [Button 2: SCROLL]     [Button 3: SELECT]
                   │                      │                      │
             Pi Pin 35 (GPIO 19)    Pi Pin 38 (GPIO 20)    Pi Pin 40 (GPIO 21)
```

| Button | Function | GPIO (BCM) | Physical Pin | Other Leg Connection |
| :--- | :--- | :--- | :--- | :--- |
| **Button 1 (SCREEN)** | Cycles tabs: Home → Music → Agents → Tasks → Home | **GPIO 19** | **Pin 35** | Daisy-chained to Pin 34 (GND) |
| **Button 2 (SCROLL)** | Scrolls list items: 1st → 2nd → ... → Last → 1st (wrap) | **GPIO 20** | **Pin 38** | Daisy-chained to Pin 34 (GND) |
| **Button 3 (SELECT)** | Agents: Run workflow / Tasks: Confirm done | **GPIO 21** | **Pin 40** | Daisy-chained to Pin 34 (GND) |

*(Internal pull-ups are enabled in software — no external resistors needed).*

---

## 3. RFID (RC522) Reader Wiring

The RC522 communicates via SPI. Since the SPI TFT screen uses SPI0, the RC522 shares the SPI clock/data lines and uses a dedicated Chip Select (**CE1 / GPIO 7**) and free Reset pin (**GPIO 26 / Pin 37**):

| RC522 Pin | Description | Raspberry Pi Connection | Physical Pin | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **3.3V (VCC)** | Power | **3.3V** | **Pin 1** or **Pin 17** | ⚠️ **3.3V ONLY.** |
| **RST** | Reset | **GPIO 26** | **Pin 37** | Free pin outside TFT block. |
| **GND** | Ground | **GND** | **Pin 30** or **Pin 39** | Common ground. |
| **IRQ** | Interrupt | *Unused* | — | Leave disconnected. |
| **MISO** | Data In | **GPIO 9 (SPI0 MISO)** | **Pin 21** | Shared SPI bus line. |
| **MOSI** | Data Out | **GPIO 10 (SPI0 MOSI)**| **Pin 19** | Shared SPI bus line. |
| **SCK** | Clock | **GPIO 11 (SPI0 SCLK)**| **Pin 23** | Shared SPI bus line. |
| **SDA / NSS** | Chip Select | **GPIO 7 (SPI0 CE1)** | **Pin 26** | Dedicated CS line for RFID. |

*(If using an **nRF24L01 / nRF52** 2.4GHz RF transceiver module instead, it uses the identical SPI pinout: VCC=3.3V, GND=Pin 30/39, CE=Pin 37, CSN=Pin 26, SCK=Pin 23, MOSI=Pin 19, MISO=Pin 21).*

---

## 4. Raspberry Pi 40-Pin Header Reference Map

```
                     3.3V PWR [ 1] [ 2] 5V PWR
                 (I2C1 SDA)   [ 3] [ 4] 5V PWR
                 (I2C1 SCL)   [ 5] [ 6] GND
        (DHT OUT)     GPIO 4  [ 7] [ 8] GPIO 14 (UART TX)
                         GND  [ 9] [10] GPIO 15 (UART RX)
                     GPIO 17  [11] [12] GPIO 18 (PCM CLK)
                     GPIO 27  [13] [14] GND
                     GPIO 22  [15] [16] GPIO 23
                    3.3V PWR  [17] [18] GPIO 24
         (SPI0 MOSI) GPIO 10  [19] [20] GND
          (SPI0 MISO) GPIO 9  [21] [22] GPIO 25
          (SPI0 SCLK) GPIO 11 [23] [24] GPIO 8 (SPI0 CE0 - TFT CS)
                         GND  [25] [26] GPIO 7 (SPI0 CE1 - RFID CS)
      ═════════════════════════════════════════════════════════════
      ▲ PINS 1–26 OCCUPIED BY DIRECT-PLUG TFT HAT ▲
      ▼ PINS 27–40 FREE FOR PERIPHERALS & BUTTONS ▼
      ═════════════════════════════════════════════════════════════
                     GPIO 0   [27] [28] GPIO 1
                     GPIO 5   [29] [30] GND (RFID GND)
                     GPIO 6   [31] [32] GPIO 12
                     GPIO 13  [33] [34] GND (Buttons Common Rail)
    (SCREEN BTN)     GPIO 19  [35] [36] GPIO 16
        (RFID RST)   GPIO 26  [37] [38] GPIO 20 (SCROLL BTN)
                         GND  [39] [40] GPIO 21 (SELECT BTN)
```
