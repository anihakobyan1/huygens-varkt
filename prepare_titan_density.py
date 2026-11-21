# prepare_titan_density.py — готовит таблицу плотности Титана из измерений зонда (прибор HASI)
#
# Вход:  data/HASI_L4_ATMO_PROFILE_DESCEN.TAB  (архив NASA PDS)
#        5 столбцов через «;»: время (мс), высота (м), давление (Па), температура (К), плотность (кг/м³)
# Выход: data/titan_density_profile.csv — высота и плотность, по одной строке на каждый километр
import numpy as np

data = np.loadtxt("data/HASI_L4_ATMO_PROFILE_DESCEN.TAB", delimiter=";")
height = data[:, 1]        # столбец 1 — высота, м
density = data[:, 4]       # столбец 4 — плотность, кг/м³
print("Измерений в файле:", len(height))

# ---------- Шаг 2. Слои по 1 км и медиана в каждом ----------
layer = np.floor(height / 1000)            # номер слоя: 146 797 м -> слой 146
rows = []
for n in np.unique(layer):                 # перебираем все слои по порядку
    in_layer = layer == n                  # какие измерения попали в этот слой
    rows.append((np.median(height[in_layer]), np.median(density[in_layer])))

# ---------- Шаг 3. Продолжаем вверх до 160 км ----------
# выше 120 км плотность падает по экспоненте: ln(ρ) = c + k·h — это прямая,
# проводим её через точки методом наименьших квадратов
top = height > 120_000
k, c = np.polyfit(height[top], np.log(density[top]), 1)
rows.append((160_000, np.exp(c + k * 160_000)))
print(f"Шкала высот над 120 км: H = {-1 / k / 1000:.1f} км")

# ---------- Шаг 4. Сохраняем ----------
with open("data/titan_density_profile.csv", "w", encoding="utf-8") as f:
    f.write("altitude_m,density_kg_m3\n")
    for h, rho in rows:
        f.write(f"{h:.0f},{rho:.6g}\n")
print("Сохранено строк:", len(rows), "-> data/titan_density_profile.csv")
