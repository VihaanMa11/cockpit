# Cockpit Hardware Wiring & Setup Guide

This guide details the complete wiring for the desk console setup:
- **Display**: 3.5" / 4.0" SPI TFT Screen (covers Physical Header Pins 1–26)
- **Controls**: 3 Momentary Push-Buttons (Screen Cycle, List Scroll, Select/Run)
- **Environment**: DHT22 Temperature & Humidity Sensor
- **Proximity / Auth**: RFID (RC522) Reader (or nRF module)

---

## 1. Push-Buttons (3 Total)

### Are Button Nodes Polarized?
**No.** Standard 2-pin momentary push buttons are simple mechanical switches. They have **no positive or negative polarity**; both pins/nodes are completely interchangeable.

### How to Connect Buttons Internally (Ground Daisy-Chain)
Instead of running 6 separate wires to the board, you only need **4 wires**:
1. Connect one terminal of **Button 1**, **Button 2**, and **Button 3** together using a single shared wire (**Daisy-Chained Ground**).
2. Connect that common ground wire to **Pin 34 (GND)** on the Raspberry Pi.
3. Connect the remaining individual terminal of each button to its assigned GPIO pin:

```
[Pin 34 GND] ───┬──────────────────┬──────────────────┐
                │                  │                  │
            [Button 1]         [Button 2]         [Button 3]
             (Screen)           (Scroll)           (Select)
                │                  │                  │
          [Pin 35 GPIO 19]   [Pin 38 GPIO 20]   [Pin 40 GPIO 21]
```

### Button Pin Assignment Table

| Button | Function | GPIO (BCM) | Pi Physical Pin | Other Leg Connection |
| :--- | :--- | :--- | :--- | :--- |
| **Button 1 (SCREEN)** | Cycles tabs: Home → Music → Agents → Tasks → Home (wrap) | **GPIO 19** | **Pin 35** | Daisy-chained to Pin 34 (GND) |
| **Button 2 (SCROLL)** | Scrolls list items: 1st → 2nd → ... → Last → 1st (wrap) | **GPIO 20** | **Pin 38** | Daisy-chained to Pin 34 (GND) |
| **Button 3 (SELECT)** | Agents: Run workflow / Tasks: Confirm done | **GPIO 21** | **Pin 40** | Daisy-chained to Pin 34 (GND) |

> **Resistors**: No external resistors needed. The software automatically enables the Pi's internal pull-up resistors (`pull_up=True`).

---

## 2. DHT22 Temperature & Humidity Sensor

The DHT22 has 4 pins (pins numbered 1 to 4 from left to right when facing the grid):
- Pin 1: VCC
- Pin 2: DATA
- Pin 3: NC (Not Connected / Ignore)
- Pin 4: GND

| DHT22 Pin | Connects To | Pi Physical Pin | Notes |
| :--- | :--- | :--- | :--- |
| **Pin 1 (VCC)** | **3.3V Power** | **Pin 1** or **Pin 17** | **Do NOT use 5V**; Pi GPIO pins are 3.3V only. |
| **Pin 2 (DATA)** | **GPIO 4** | **Pin 7** | Add a 4.7kΩ–10kΩ pull-up resistor to 3.3V (unless module has PCB). |
| **Pin 3 (NC)** | None | — | Leave disconnected. |
| **Pin 4 (GND)** | **Ground** | **Pin 9** (or any GND) | Ties sensor ground to Pi ground. |

---

## 3. RFID (RC522) Reader Wiring

If adding an **MFRC522 RFID reader** (or NRF sensor module) to the setup:
The RC522 communicates via SPI. Because the SPI TFT display already uses SPI0 (pins 19, 21, 23), the RC522 shares the SPI clock/data lines but uses a distinct Chip Select (**CE1 / GPIO 7**) or free GPIO pins.

| RC522 Pin | Connects To | Pi Physical Pin | Description |
| :--- | :--- | :--- | :--- |
| **VCC (3.3V)** | **3.3V Power** | **Pin 1** or **Pin 17** | **WARNING: 3.3V ONLY.** 5V will permanently damage the RC522. |
| **RST** | **GPIO 26** | **Pin 37** | Reset line (uses free pin outside TFT block). |
| **GND** | **Ground** | **Pin 30** or **Pin 39** | Common ground. |
| **IRQ** | Not Connected | — | Leave floating / unused. |
| **MISO** | **GPIO 9 (SPI0 MISO)** | **Pin 21** | Master In Slave Out (shared SPI line). |
| **MOSI** | **GPIO 10 (SPI0 MOSI)**| **Pin 19** | Master Out Slave In (shared SPI line). |
| **SCK** | **GPIO 11 (SPI0 SCLK)**| **Pin 23** | Serial Clock (shared SPI line). |
| **SDA / NSS** | **GPIO 7 (SPI0 CE1)** | **Pin 26** | Dedicated Chip Select for the RFID reader. |

*(Note: If using an **nRF24L01 / nRF52** 2.4GHz RF module instead of RFID, the pinout is identical: VCC=3.3V, GND=GND, CE=GPIO 26 (Pin 37), CSN=GPIO 7 (Pin 26), SCK=Pin 23, MOSI=Pin 19, MISO=Pin 21).*

---

## 4. Raspberry Pi 40-Pin Header Reference Map

```
                     3.3V PWR [ 1] [ 2] 5V PWR
                 (I2C1 SDA)   [ 3] [ 4] 5V PWR
                 (I2C1 SCL)   [ 5] [ 6] GND
              (DHT22) GPIO 4  [ 7] [ 8] GPIO 14 (UART TX)
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
