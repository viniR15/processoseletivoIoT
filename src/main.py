from machine import Pin, I2C
import utime

# ---------------------------------------------------------------------
# Parametros configuraveis
# ---------------------------------------------------------------------
LIMITE_TEMPO_X = 5000       # ms - tempo max. de porta aberta
LIMITE_VARIACAO_Y = 3.0     # C  - variacao termica tolerada

BUTTON_PIN = 4              # btn1 (ligado a 3V3, PULL_DOWN interno)
TELEMETRY_INTERVAL = 1000   # ms - periodo do log de telemetria

MPU6050_ADDR = 0x68
PWR_MGMT_1 = 0x6B
TEMP_OUT_H = 0x41

# ---------------------------------------------------------------------
# Driver minimo do MPU6050 (somente o necessario: acordar e ler temperatura)
# ---------------------------------------------------------------------
def mpu6050_init(i2c):
    try:
        i2c.writeto_mem(MPU6050_ADDR, PWR_MGMT_1, b"\x00")  # tira do sleep mode
    except OSError:
        print("Erro: MPU6050 nao encontrado!")


def mpu6050_read_temp(i2c):
    data = i2c.readfrom_mem(MPU6050_ADDR, TEMP_OUT_H, 2)
    raw = (data[0] << 8) | data[1]
    if raw & 0x8000:
        raw -= 0x10000
    return raw / 340.0 + 36.53


# ---------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------
button = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_DOWN)
i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=400000)
mpu6050_init(i2c)

door_was_open = False        # flag de borda (transicao fechado->aberto)
door_open_timestamp = 0      # marca de tempo do inicio da abertura
door_alarm_active = False

temp_referencia = 0.0
temp_referencia_set = False
thermal_alarm_active = False

last_telemetry = 0
prev_door_closed = True      # estado anterior da porta, p/ detectar transicao

# Mensagem obrigatoria de inicializacao
print("Sistema de Monitoramento Inicializado")


# ---------------------------------------------------------------------
# Telemetria (apenas visual, nao interfere na logica nem nos testes)
# ---------------------------------------------------------------------
def print_telemetry(current_temp, door_closed):
    linha = "[TELEMETRIA] Porta: " + ("FECHADA" if door_closed else "ABERTA")
    linha += " | Temp atual: {:.1f} C".format(current_temp)

    if temp_referencia_set:
        delta = current_temp - temp_referencia
        linha += " | Referencia: {:.1f} C | Delta: {:.1f} C".format(
            temp_referencia, delta
        )

    linha += " | Alarme Porta: " + ("SIM" if door_alarm_active else "nao")
    linha += " | Alarme Termico: " + ("SIM" if thermal_alarm_active else "nao")
    print(linha)


# ---------------------------------------------------------------------
# Loop principal (nao bloqueante)
# ---------------------------------------------------------------------
while True:
    # btn1: pressionado (1) = porta fechada | solto (0) = porta aberta
    door_closed = button.value() == 1

    current_temp = mpu6050_read_temp(i2c)
    now = utime.ticks_ms()

    # --- B) Logica de tempo de porta aberta -----------------------------
    if not door_closed:
        if not door_was_open:
            # Transicao fechado -> aberto: registra o carimbo de tempo
            door_was_open = True
            door_open_timestamp = now
        elif not door_alarm_active and utime.ticks_diff(now, door_open_timestamp) >= LIMITE_TEMPO_X:
            door_alarm_active = True
            print("ALERTA: Porta aberta por muito tempo!")
    else:
        door_was_open = False  # porta fechou: reseta a contagem de abertura

    # --- C) Logica de elevacao termica -----------------------------------
    if temp_referencia_set and not thermal_alarm_active:
        delta_t = current_temp - temp_referencia
        if abs(delta_t) >= LIMITE_VARIACAO_Y:
            thermal_alarm_active = True
            print("ALERTA: Degradacao termica detectada!")

    # Atualiza a temperatura de referencia somente quando o ambiente esta
    # estavel (porta fechada e nenhum alarme ativo)
    if door_closed and not door_alarm_active and not thermal_alarm_active:
        temp_referencia = current_temp
        temp_referencia_set = True

    # --- D) Normalizacao ---------------------------------------------------
    if door_alarm_active or thermal_alarm_active:
        temp_safe = True
        if temp_referencia_set:
            temp_safe = abs(current_temp - temp_referencia) < LIMITE_VARIACAO_Y

        if door_closed and temp_safe:
            door_alarm_active = False
            thermal_alarm_active = False
            temp_referencia = current_temp  # nova referencia estavel
            temp_referencia_set = True
            print("Status: Sistema Normalizado.")
        elif door_closed and not prev_door_closed and not temp_safe:
            # Porta acabou de fechar, mas o sistema segue em alerta porque a
            # condicao termica ainda nao voltou ao seguro (D exige AMBAS ao
            # mesmo tempo). Mensagem apenas informativa.
            print("[INFO] Porta fechada, mas alerta mantido: temperatura ainda fora do limite seguro.")

    prev_door_closed = door_closed

    # --- Telemetria para acompanhamento no Monitor Serial do Wokwi -------
    if utime.ticks_diff(now, last_telemetry) >= TELEMETRY_INTERVAL:
        last_telemetry = now
        print_telemetry(current_temp, door_closed)

    utime.sleep_ms(50)  # pequena pausa de amostragem, nao caracteriza bloqueio longo
