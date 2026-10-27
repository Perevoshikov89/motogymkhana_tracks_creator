# -*- coding: utf-8 -*-
"""MotoGymkhana Track Generator. Python 3.10+, standard library only."""
from __future__ import annotations

import math
import random
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from dataclasses import dataclass


# ============================================================
# МОДЕЛИ
# ============================================================

@dataclass
class Cone:
    x: float
    y: float
    kind: str
    label: str = ""


@dataclass
class Track:
    width: float
    height: float
    cones: list[Cone]
    route: list[tuple[float, float]]
    seed: int
    start_gate: tuple[tuple[float, float], tuple[float, float]]
    finish_gate: tuple[tuple[float, float], tuple[float, float]]


# ============================================================
# ГЕНЕРАТОР ТРАССЫ
# ============================================================

class TrackGenerator:
    MIN_SPACING = 4.0
    MIRROR_SPACING = 3.5
    MARGIN = 2.0

    def __init__(self, w, h, count, difficulty, seed=None):
        self.w = w
        self.h = h
        self.count = count
        self.difficulty = difficulty
        self.seed = seed if seed is not None else random.randrange(1, 10**9)
        self.rng = random.Random(self.seed)

    def generate(self):
        if self.w < 12 or self.h < 16:
            raise ValueError("Минимальный размер площадки — 12 × 16 м.")

        if self.count < 8 or self.count > 200:
            raise ValueError(
                "Количество конусов: от 8 до 200. "
                "В количество входят стойки стартовых и финишных ворот."
            )

        # Ворота расположены по центру коротких сторон площадки.
        # Старт и финиш — одни и те же ворота
        gate_half_width = 1.5
        start_y = 3.0
        finish_y = start_y
        center_x = self.w / 2

        start_gate = (
            (center_x - gate_half_width, start_y),
            (center_x + gate_half_width, start_y),
        )

        # Финиш использует тот же створ, что и старт
        finish_gate = start_gate

        gate_cones = [
            Cone(*start_gate[0], "gate_start", "Старт / финиш"),
            Cone(*start_gate[1], "gate_start", "Старт / финиш"),
        ]

        regular_count = self.count - len(gate_cones)
        cones = []
        mirror_pairs = []

        spin_probability = {
            "Начальный": 0.08,
            "Средний": 0.18,
            "Продвинутый": 0.28,
        }.get(self.difficulty, 0.18)

        def inside(x, y):
            return (
                self.MARGIN <= x <= self.w - self.MARGIN
                and self.MARGIN <= y <= self.h - self.MARGIN
            )

        def away_from_gates(x, y):
            # Не размещаем элементы рядом с воротами и линиями старта/финиша.
            if abs(y - start_y) < 2.0 or abs(y - finish_y) < 2.0:
                return False

            for gate_cone in gate_cones:
                if math.dist((x, y), (gate_cone.x, gate_cone.y)) < 4.0:
                    return False

            return True

        def away_from_existing(x, y, min_distance=4.0):
            return all(
                math.dist((x, y), (cone.x, cone.y)) >= min_distance
                for cone in cones
            )

        # Сначала случайно размещаем обычные элементы и зеркальные пары.
        attempts = 0
        max_attempts = 100000

        while len(cones) < regular_count and attempts < max_attempts:
            attempts += 1
            remaining = regular_count - len(cones)

            # Зеркало состоит строго из двух жёлтых конусов.
            if remaining >= 2 and self.rng.random() < 0.12:
                angle = self.rng.uniform(0, math.tau)
                dx = (self.MIRROR_SPACING / 2) * math.cos(angle)
                dy = (self.MIRROR_SPACING / 2) * math.sin(angle)

                cx = self.rng.uniform(
                    self.MARGIN + abs(dx),
                    self.w - self.MARGIN - abs(dx),
                )
                cy = self.rng.uniform(
                    self.MARGIN + abs(dy),
                    self.h - self.MARGIN - abs(dy),
                )

                p1 = (cx - dx, cy - dy)
                p2 = (cx + dx, cy + dy)

                valid = True
                for x, y in (p1, p2):
                    if not inside(x, y) or not away_from_gates(x, y):
                        valid = False
                        break

                    if not away_from_existing(x, y, self.MIN_SPACING):
                        valid = False
                        break

                if not valid:
                    continue

                pair_id = len(mirror_pairs) + 1
                first = Cone(*p1, "yellow", f"Зеркало {pair_id}")
                second = Cone(*p2, "yellow", f"Зеркало {pair_id}")

                cones.extend([first, second])
                mirror_pairs.append((first, second))
                continue

            x = self.rng.uniform(self.MARGIN, self.w - self.MARGIN)
            y = self.rng.uniform(self.MARGIN, self.h - self.MARGIN)

            if not away_from_gates(x, y):
                continue

            if not away_from_existing(x, y, self.MIN_SPACING):
                continue

            roll = self.rng.random()

            if roll < spin_probability:
                kind = "red_yellow"
                label = "Вращение 360° вправо"
            elif roll < spin_probability * 2:
                kind = "blue_yellow"
                label = "Вращение 360° влево"
            elif self.rng.random() < 0.5:
                kind = "red"
                label = "Правый поворот"
            else:
                kind = "blue"
                label = "Левый поворот"

            cones.append(Cone(x, y, kind, label))

        if len(cones) < regular_count:
            raise ValueError(
                "Не удалось разместить конусы с заданными расстояниями.\n"
                "Попробуйте увеличить площадку или уменьшить количество конусов."
            )

        # Строим случайную последовательность прохождения.
        route = self._build_route(cones, start_y, finish_y, center_x)

        return Track(
            self.w,
            self.h,
            gate_cones + cones,
            route,
            self.seed,
            start_gate,
            finish_gate,
        )

    def _build_route(self, cones, start_y, finish_y, center_x):
        """
        Траектория строится через случайную последовательность элементов.
        Красный — обход с правой стороны направления движения.
        Синий — обход с левой стороны направления движения.
        Красно-жёлтый и сине-жёлтый — круг на 360 градусов.
        """
        route = [(center_x, start_y + 1.0)]
        remaining = cones[:]
        current = route[-1]

        while remaining:
            # Выбираем случайный элемент из ближайших, чтобы маршрут
            # не превращался ни в строгую змейку, ни в хаотичную кашу.
            ordered = sorted(
                remaining,
                key=lambda c: math.dist(current, (c.x, c.y)),
            )

            pool = ordered[:min(4, len(ordered))]
            cone = self.rng.choice(pool)
            remaining.remove(cone)

            if cone.kind == "yellow":
                # Обрабатываем вторую стойку зеркала сразу после первой.
                mate = next(
                    (
                        other for other in remaining
                        if other.kind == "yellow"
                        and other.label == cone.label
                    ),
                    None,
                )

                if mate is not None:
                    remaining.remove(mate)
                    route.extend(
                        self._mirror_waypoints(cone, mate, current)
                    )
                    current = (
                        (cone.x + mate.x) / 2,
                        (cone.y + mate.y) / 2,
                    )
                else:
                    route.append((cone.x, cone.y))
                    current = (cone.x, cone.y)

            elif cone.kind == "red_yellow":
                route.extend(
                    self._spin_waypoints(
                        cone.x, cone.y, clockwise=True
                    )
                )
                current = (cone.x, cone.y)

            elif cone.kind == "blue_yellow":
                route.extend(
                    self._spin_waypoints(
                        cone.x, cone.y, clockwise=False
                    )
                )
                current = (cone.x, cone.y)

            else:
                side = 1 if cone.kind == "red" else -1
                points = self._turn_waypoints(
                    cone.x, cone.y, current, side
                )
                route.extend(points)
                current = (cone.x, cone.y)

        # Маршрут возвращается к тем же воротам, откуда начался
        route.append((center_x, start_y + 1.0))

        return self._smooth_route(route, samples=5)

    def _turn_waypoints(self, x, y, previous, side):
        """Три точки дуги обхода конуса с заданной стороны."""
        dx = x - previous[0]
        dy = y - previous[1]
        length = max(0.001, math.hypot(dx, dy))

        # Правая нормаль к направлению движения в координатах Canvas.
        right_x = -dy / length
        right_y = dx / length

        offset = 1.8 * side
        lead = 2.0

        return [
            (
                x - dx / length * lead + right_x * offset,
                y - dy / length * lead + right_y * offset,
            ),
            (
                x + right_x * offset,
                y + right_y * offset,
            ),
            (
                x + dx / length * lead + right_x * offset,
                y + dy / length * lead + right_y * offset,
            ),
        ]

    def _spin_waypoints(self, x, y, clockwise=True):
        """Петля вокруг центра элемента 360°."""
        radius = max(1.3, min(2.0, min(self.w, self.h) / 18.0))
        sign = 1 if clockwise else -1
        start_angle = -math.pi / 2

        return [
            (
                x + radius * math.cos(
                    start_angle + sign * i * math.tau / 32
                ),
                y + radius * math.sin(
                    start_angle + sign * i * math.tau / 32
                ),
            )
            for i in range(33)
        ]

    def _mirror_waypoints(self, first, second, previous):
        """Подход к зеркалу, проход между конусами и выход."""
        cx = (first.x + second.x) / 2
        cy = (first.y + second.y) / 2

        dx = second.x - first.x
        dy = second.y - first.y
        length = max(0.001, math.hypot(dx, dy))

        # Направление прохода между стойками зеркала.
        nx = -dy / length
        ny = dx / length

        approach_x = cx - nx * 2.0
        approach_y = cy - ny * 2.0
        exit_x = cx + nx * 2.0
        exit_y = cy + ny * 2.0

        return [
            (approach_x, approach_y),
            (cx, cy),
            (exit_x, exit_y),
        ]

    @staticmethod
    def _smooth_route(points, samples=5):
        """Сглаживание траектории Catmull–Rom."""
        if len(points) < 3:
            return points

        padded = [points[0]] + points + [points[-1]]
        result = []

        for i in range(1, len(padded) - 2):
            p0, p1, p2, p3 = padded[i - 1:i + 3]

            for j in range(samples):
                t = j / samples
                t2 = t * t
                t3 = t2 * t

                x = 0.5 * (
                    2 * p1[0]
                    + (-p0[0] + p2[0]) * t
                    + (2*p0[0] - 5*p1[0] + 4*p2[0] - p3[0]) * t2
                    + (-p0[0] + 3*p1[0] - 3*p2[0] + p3[0]) * t3
                )

                y = 0.5 * (
                    2 * p1[1]
                    + (-p0[1] + p2[1]) * t
                    + (2*p0[1] - 5*p1[1] + 4*p2[1] - p3[1]) * t2
                    + (-p0[1] + 3*p1[1] - 3*p2[1] + p3[1]) * t3
                )

                result.append((x, y))

        result.append(points[-1])
        return result


# ============================================================
# ГРАФИЧЕСКИЙ ИНТЕРФЕЙС
# ============================================================

class App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Генератор трасс. powered by Motogymkhana Glazov")
        self.geometry("1180x780")
        self.minsize(900, 620)

        self.track = None
        self.configure(bg="#f1f3f5")

        self.build()
        self.generate()

    def build(self):
        top = ttk.Frame(self, padding=12)
        top.pack(fill=tk.X)

        ttk.Label(
            top,
            text="Генератор трасс для мотоджимханы",
            font=("Segoe UI", 17, "bold"),
        ).pack(anchor="w")

        ttk.Label(
            top,
            text="Схема сверху • размеры в метрах • случайная расстановка",
        ).pack(anchor="w", pady=(2, 8))

        box = ttk.LabelFrame(top, text="Параметры", padding=8)
        box.pack(fill=tk.X)

        self.w = tk.StringVar(value="30")
        self.h = tk.StringVar(value="50")
        self.n = tk.StringVar(value="20")
        self.diff = tk.StringVar(value="Средний")
        self.seed = tk.StringVar()

        for label, var, width in [
            ("Ширина, м", self.w, 7),
            ("Длина, м", self.h, 7),
            ("Всего конусов", self.n, 8),
        ]:
            ttk.Label(box, text=label).pack(
                side=tk.LEFT, padx=(0, 4)
            )
            ttk.Entry(box, textvariable=var, width=width).pack(
                side=tk.LEFT, padx=(0, 12)
            )

        ttk.Label(box, text="Сложность").pack(
            side=tk.LEFT, padx=(0, 4)
        )

        ttk.Combobox(
            box,
            textvariable=self.diff,
            values=["Начальный", "Средний", "Продвинутый"],
            state="readonly",
            width=13,
        ).pack(side=tk.LEFT, padx=(0, 12))

        ttk.Label(box, text="Seed").pack(
            side=tk.LEFT, padx=(0, 4)
        )

        ttk.Entry(box, textvariable=self.seed, width=10).pack(
            side=tk.LEFT, padx=(0, 12)
        )

        ttk.Button(
            box,
            text="Сгенерировать трассу",
            command=self.generate,
        ).pack(side=tk.LEFT, padx=4)

        ttk.Button(
            box,
            text="Сохранить схему",
            command=self.save,
        ).pack(side=tk.LEFT, padx=4)

        body = ttk.Frame(self, padding=(12, 0, 12, 12))
        body.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(
            body,
            bg="white",
            highlightthickness=1,
            highlightbackground="#cbd2d9",
        )
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.canvas.bind("<Configure>", lambda event: self.draw())

        side = ttk.Frame(body, width=275)
        side.pack(side=tk.RIGHT, fill=tk.Y, padx=(12, 0))
        side.pack_propagate(False)

        ttk.Label(
            side, text="Легенда",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w", pady=(4, 8))

        legend = [
            ("#d62728", "Красный — правый поворот", False),
            ("#1769d2", "Синий — левый поворот", False),
            ("#d62728", "Красный + жёлтая полоса — 360° вправо", True),
            ("#1769d2", "Синий + жёлтая полоса — 360° влево", True),
            ("#f2c500", "Два жёлтых — зеркало (3–4 м)", False),
            ("#2e8b57", "Стартовые ворота", False),
            ("#222222", "Финишные ворота", False),
        ]

        for color, text, stripe in legend:
            row = ttk.Frame(side)
            row.pack(fill=tk.X, pady=3)

            swatch = tk.Canvas(
                row, width=26, height=24,
                bg="#f1f3f5", highlightthickness=0,
            )
            swatch.pack(side=tk.LEFT, padx=(0, 6))
            swatch.create_oval(
                4, 4, 22, 22,
                fill=color, outline="#222",
            )

            if stripe:
                swatch.create_line(
                    5, 13, 21, 13,
                    fill="#ffe64a", width=4,
                )

            ttk.Label(
                row, text=text, wraplength=220,
            ).pack(side=tk.LEFT, fill=tk.X)

        ttk.Separator(side).pack(fill=tk.X, pady=10)

        ttk.Label(
            side, text="Сводка",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w")

        self.info = tk.Text(
            side,
            height=16,
            wrap=tk.WORD,
            font=("Segoe UI", 9),
            relief=tk.FLAT,
            bg="#f1f3f5",
        )
        self.info.pack(fill=tk.BOTH, expand=True, pady=6)
        self.info.configure(state=tk.DISABLED)

        ttk.Label(
            side,
            text=(
                "Схема предварительная. Перед заездом проверьте "
                "проходимость, радиусы поворотов и безопасность площадки."
            ),
            wraplength=255,
            foreground="#8b3a00",
        ).pack(anchor="w")

        self.status = tk.StringVar(value="Готов к генерации")

        ttk.Label(
            self,
            textvariable=self.status,
            relief=tk.SUNKEN,
            anchor="w",
            padding=5,
        ).pack(side=tk.BOTTOM, fill=tk.X)

    def generate(self):
        try:
            width = float(self.w.get().replace(",", "."))
            height = float(self.h.get().replace(",", "."))
            count = int(self.n.get())

            seed = (
                int(self.seed.get())
                if self.seed.get().strip()
                else None
            )

            self.track = TrackGenerator(
                width, height, count, self.diff.get(), seed
            ).generate()

            self.draw()
            self.summary()

            self.status.set(
                f"Готово: {width:g} × {height:g} м • "
                f"{count} конусов • seed {self.track.seed}"
            )

        except Exception as error:
            messagebox.showerror(
                "Не удалось сгенерировать трассу",
                str(error),
            )

    def coords(self):
        if not self.track:
            return None

        canvas_width = max(100, self.canvas.winfo_width())
        canvas_height = max(100, self.canvas.winfo_height())
        padding = 42

        scale = min(
            (canvas_width - 2 * padding) / self.track.width,
            (canvas_height - 2 * padding) / self.track.height,
        )

        origin_x = (canvas_width - self.track.width * scale) / 2
        origin_y = (canvas_height - self.track.height * scale) / 2

        return scale, origin_x, origin_y

    def draw(self):
        self.canvas.delete("all")

        if not self.track:
            return

        values = self.coords()
        if not values:
            return

        scale, ox, oy = values

        x2 = ox + self.track.width * scale
        y2 = oy + self.track.height * scale

        self.canvas.create_rectangle(
            ox, oy, x2, y2,
            outline="#252a30",
            width=2,
            fill="#fbfcfd",
        )

        # Сетка площадки с шагом 1 метр.
        for meter in range(1, int(self.track.width)):
            self.canvas.create_line(
                ox + meter * scale, oy,
                ox + meter * scale, y2,
                fill="#edf0f2",
            )

        for meter in range(1, int(self.track.height)):
            self.canvas.create_line(
                ox, oy + meter * scale,
                x2, oy + meter * scale,
                fill="#edf0f2",
            )

        self.canvas.create_text(
            (ox + x2) / 2,
            max(12, oy - 17),
            text=f"{self.track.width:g} м",
            font=("Segoe UI", 10, "bold"),
        )

        self.canvas.create_text(
            max(12, ox - 22),
            (oy + y2) / 2,
            text=f"{self.track.height:g} м",
            angle=90,
            font=("Segoe UI", 10, "bold"),
        )

        # Пунктирная сглаженная траектория без нумерации конусов.
        route_points = []

        for x, y in self.track.route:
            route_points.extend([
                ox + x * scale,
                oy + y * scale,
            ])

        if len(route_points) >= 4:
            self.canvas.create_line(
                *route_points,
                fill="#707982",
                width=2,
                dash=(6, 4),
                arrow=tk.LAST,
            )

        # Единый створ старта и финиша
        (ax, ay), (bx, by) = self.track.start_gate

        self.canvas.create_line(
            ox + ax * scale,
            oy + ay * scale,
            ox + bx * scale,
            oy + by * scale,
            fill="#2e8b57",
            width=4,
        )

        self.canvas.create_text(
            ox + (ax + bx) * scale / 2,
            oy + ay * scale - 12,
            text="СТАРТ / ФИНИШ",
            fill="#2e8b57",
            font=("Segoe UI", 8, "bold"),
        )

        radius = max(5, min(10, scale * 0.38))

        colors = {
            "red": "#d62728",
            "blue": "#1769d2",
            "red_yellow": "#d62728",
            "blue_yellow": "#1769d2",
            "yellow": "#f2c500",
            "gate_start": "#2e8b57",
            "gate_finish": "#222222",
        }

        for cone in self.track.cones:
            x = ox + cone.x * scale
            y = oy + cone.y * scale
            color = colors[cone.kind]

            self.canvas.create_oval(
                x - radius, y - radius,
                x + radius, y + radius,
                fill=color,
                outline="#171717",
                width=1.4,
            )

            # Жёлтая полоса на конусах вращения.
            if cone.kind in ("red_yellow", "blue_yellow"):
                self.canvas.create_line(
                    x - radius * 0.72, y,
                    x + radius * 0.72, y,
                    fill="#ffe64a",
                    width=max(2, radius * 0.55),
                )

            # Белая метка на стойках ворот.
            elif cone.kind in ("gate_start", "gate_finish"):
                self.canvas.create_line(
                    x - radius * 0.55, y - radius * 0.55,
                    x + radius * 0.55, y + radius * 0.55,
                    fill="white",
                    width=2,
                )

        self.canvas.create_text(
            ox + 5,
            y2 + 14,
            text="Пунктир — рекомендуемая траектория движения",
            anchor="w",
            fill="#666",
            font=("Segoe UI", 8),
        )

    def summary(self):
        counts = {}

        for cone in self.track.cones:
            counts[cone.kind] = counts.get(cone.kind, 0) + 1

        lines = [
            f"Площадка: {self.track.width:g} × {self.track.height:g} м",
            f"Всего конусов: {len(self.track.cones)}",
            f"Seed: {self.track.seed}",
            "",
            f"Правые повороты: {counts.get('red', 0)}",
            f"Левые повороты: {counts.get('blue', 0)}",
            f"Вращения вправо: {counts.get('red_yellow', 0)}",
            f"Вращения влево: {counts.get('blue_yellow', 0)}",
            f"Жёлтые конусы зеркала: {counts.get('yellow', 0)}",
            "",
            "Ворота:",
            "• старт - финиш — 4 стойки",
            "",

            "Важно: траектория схематическая. Проверьте её на площадке.",
        ]

        self.info.configure(state=tk.NORMAL)
        self.info.delete("1.0", tk.END)
        self.info.insert("1.0", "\n".join(lines))
        self.info.configure(state=tk.DISABLED)

    def save(self):
        if not self.track:
            return

        path = filedialog.asksaveasfilename(
            title="Сохранить схему",
            defaultextension=".ps",
            filetypes=[("PostScript (*.ps)", "*.ps")],
        )

        if path:
            try:
                self.canvas.postscript(file=path, colormode="color")
                self.status.set(
                    "Сохранено: " + path
                    + " (PS; можно конвертировать в PNG/PDF)"
                )
            except Exception as error:
                messagebox.showerror("Ошибка сохранения", str(error))


if __name__ == "__main__":
    App().mainloop()