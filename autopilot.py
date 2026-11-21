# autopilot.py — автопилот зонда «Гюйгенс» в KSP и запись телеметрии (kRPC)
# Перед запуском: KSP открыт, сервер kRPC запущен, зонд на орбите Tekto.
# Ступени: 1) основной купол, 2) разделитель под щитом, 3) стабилизирующий купол.
import csv
import json
import math
import time

import krpc

# ---------- Шаг 1. Подключение ----------
conn = krpc.connect(name="Huygens")
sc = conn.space_center
vessel = sc.active_vessel
body = vessel.orbit.body
print("Зонд:", vessel.name, "| планета:", body.name, "| парашютов:", len(vessel.parts.parachutes))

# ---------- Шаг 2. Параметры планеты ----------
heights = list(range(0, int(body.atmosphere_depth), 250))
planet = {
    "name": body.name,
    "gravitational_parameter": body.gravitational_parameter,
    "equatorial_radius": body.equatorial_radius,
    "atmosphere_profile": {
        "altitude_m": heights,
        "density_kg_m3": [body.density_at(h) for h in heights],
    },
}
with open("data/ksp_body.json", "w", encoding="utf-8") as f:
    json.dump(planet, f, ensure_ascii=False, indent=1)

# ---------- Шаг 3. Подготовка зонда ----------
for chute in vessel.parts.parachutes:
    chute.deploy_min_pressure = 0.0001
    chute.deploy_altitude = 100000
vessel.control.sas = True
vessel.control.sas_mode = sc.SASMode.retrograde

# ---------- Шаг 4. Потоки и файл ----------
flight = vessel.flight(body.reference_frame)
altitude = conn.add_stream(getattr, flight, "mean_altitude")
velocity = conn.add_stream(getattr, flight, "vertical_speed")
density = conn.add_stream(getattr, flight, "atmosphere_density")
q = conn.add_stream(getattr, flight, "dynamic_pressure")
drag = conn.add_stream(getattr, flight, "drag")
mass = conn.add_stream(getattr, vessel, "mass")
ut = conn.add_stream(getattr, sc, "ut")

file = open("data/ksp_telemetry.csv", "w", newline="", encoding="utf-8")
writer = csv.writer(file)
writer.writerow(["time", "altitude", "velocity", "atmosphere_density",
                 "dynamic_pressure", "drag", "mass", "phase", "chutes"])

# ---------- Шаги 5–7. Главный цикл ----------
phase = 0
t0 = ut()
next_t = 0.0
landed_at = 0.0
print("Жду входа в атмосферу...")

while True:
    t = ut() - t0
    if t < next_t:
        time.sleep(0.002)
        continue
    next_t = t + 0.1

    h = altitude()
    v = velocity()

    # события спуска (циклограмма «Гюйгенса»)
    if phase == 0 and h < 62700:
        vessel.control.sas = False
        vessel.control.activate_next_stage()
        print("Основной купол на", round(h), "м")
        phase = 1
    elif phase == 1 and h < 60800:
        vessel.control.activate_next_stage()
        print("Щит отстрелен на", round(h), "м")
        phase = 2
    elif phase == 2 and h < 49100:
        main = [c for c in vessel.parts.parachutes if c.deployed]
        vessel.control.activate_next_stage()
        for c in main:
            c.cut()
        print("Смена купола на", round(h), "м")
        phase = 3

    # посадка
    if phase < 4 and vessel.situation in (sc.VesselSituation.landed, sc.VesselSituation.splashed):
        print("Посадка, скорость", abs(round(v, 2)), "м/с")
        phase = 4
        landed_at = t
    if phase == 4 and t - landed_at > 2:
        break

    # запись строки (начинаем ниже верхней границы атмосферы)
    if h < body.atmosphere_depth:
        d = drag()
        chutes = "|".join(str(c.state).split(".")[-1] for c in vessel.parts.parachutes)
        writer.writerow([round(t, 2), h, v, density(), q(),
                         math.sqrt(d[0] ** 2 + d[1] ** 2 + d[2] ** 2), mass(), phase, chutes])

file.close()
print("Готово: data/ksp_telemetry.csv и data/ksp_body.json")
