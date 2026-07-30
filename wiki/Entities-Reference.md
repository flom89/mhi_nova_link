# Entities Reference

Entity availability depends on what the gateway reports for each zone/indoor unit.

## Climate

Per zone:

- **Climate**
  - HVAC modes: Off, Cool, Heat, Auto, Dry, Fan
  - Fan modes: Auto, Low, Medium, High, Power
  - Swing mode support based on gateway patch options

## Select

Per zone:

- **Air guide louver** (`select`)
- **Swing louver** (`select`)

## Switch

Per zone:

- **3D Auto** (`switch`)

## Binary sensors

Per zone:

- Running
- Available
- 3D Auto
- Temperature range
- Critical error
- Maintenance required
- TS_Compressor active
- TS_Defrosting
- Active notifications

Per indoor unit (when available):

- Indoor unit
- Indoor unit filter reminder

Gateway level:

- Free cooling request
- Free cooling active
- System stop
- System fault
- Gateway update available

## Sensors

Per zone:

- Temperature
- Setpoint
- Cooling temperature minimum / maximum
- Heating temperature minimum / maximum
- Mode
- Fan

Indoor unit / time-series related (when available):

- Indoor unit temperature
- Indoor unit setpoint
- Indoor unit mode
- Indoor unit fan
- TS_Outdoor air temperature
- TS_Compressor frequency
- TS_Compressor current
- TS_Compressor power
- TS_Protection state
- TS_Indoor unit capacity
- TS_Indoor unit discharge temperature
- TS_Outdoor heat exchanger bottom temperature
- TS_Outdoor heat exchanger top temperature

Gateway info:

- Gateway software version
