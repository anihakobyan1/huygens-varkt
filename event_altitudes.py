# event_altitudes.py — на каких высотах Tekto раскрывать купола, чтобы было «как на Титане»
#
# Идея: Tekto ниже и меньше Титана, поэтому высоты Титана (159 / 152,5 / 111 км) повторить нельзя.
# Берём такие высоты Tekto, где плотность воздуха такая же, как на Титане в момент каждого события.
# Тогда сопротивление купола при той же скорости будет таким же.
import json
import os

import numpy as np

# ---------- Шаг 1. Плотность Титана (измерения зонда, прибор HASI) ----------
titan_h, titan_rho = [], []
with open("data/titan_density_profile.csv", encoding="utf-8") as f:
    for line in f:
        if line[0].isdigit():                 # пропускаем комментарии (#) и строку заголовков
            h, rho = line.split(",")
            titan_h.append(float(h))
            titan_rho.append(float(rho))
titan_h, titan_rho = np.array(titan_h), np.array(titan_rho)


def titan_density(h):
    # интерполируем логарифм плотности: между узлами плотность меняется по экспоненте
    return np.exp(np.interp(h, titan_h, np.log(titan_rho)))


# ---------- Шаг 2. Плотность Tekto ----------
if os.path.exists("data/ksp_body.json"):
    # лучший вариант: профиль, который автопилот сохранил прямо из игры
    with open("data/ksp_body.json", encoding="utf-8") as f:
        prof = json.load(f)["atmosphere_profile"]
    grid = np.array(prof["altitude_m"])
    rho_grid = np.array(prof["density_kg_m3"])
    source = "из игры (data/ksp_body.json)"
else:
    # пока игры нет: давление и температура из конфига мода (Tekto.cfg),
    # плотность по уравнению идеального газа  ρ = p·M / (R·T)
    p_h = np.array([0, 1000, 3000, 6000, 9000, 12000, 15000, 20000, 25000, 30000,
                    35000, 40000, 50000, 60000, 70000, 80000, 87500])
    p_kpa = np.array([124.62975, 111.096, 87.6643, 60.5584, 41.3176, 28.0070, 18.9613,
                      9.97089, 5.32110, 2.86917, 1.56612, 0.872768, 0.297566, 0.120956,
                      0.0570970, 0.0290375, 0.0181146])
    t_h = np.array([0, 26250, 45750, 67750, 95000])
    t_k = np.array([93.7, 69, 69, 87, 90])
    M, R = 0.0289644, 8.3144598                  # молярная масса воздуха в KSP, газовая постоянная

    grid = np.arange(0, 87500, 10.0)
    p = np.exp(np.interp(grid, p_h, np.log(p_kpa * 1000)))
    T = np.interp(grid, t_h, t_k)
    rho_grid = p * M / (R * T)
    source = "по конфигу мода (оценка)"

ok = rho_grid > 0
grid, rho_grid = grid[ok], rho_grid[ok]

# ---------- Шаг 3. Подбор высот ----------
# плотность падает с высотой, а np.interp нужен возрастающий аргумент — поэтому переворачиваем [::-1]
events = [("Основной купол", 159_000), ("Отстрел щита", 152_500), ("Стабилизирующий купол", 111_000)]
print("Плотность Tekto:", source)
for name, h_titan in events:
    rho = titan_density(h_titan)
    h_tekto = np.interp(np.log(rho), np.log(rho_grid[::-1]), grid[::-1])
    print(f"{name:22s} Титан {h_titan / 1000:6.1f} км   ρ = {rho:.5f} кг/м³   →   Tekto {h_tekto / 1000:5.1f} км")
