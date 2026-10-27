# -*- coding: utf-8 -*-
"""MotoGymkhana Track Generator. Python 3.10+, standard library only."""
from __future__ import annotations

import math
import random
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from dataclasses import dataclass
from pathlib import Path
from PIL import Image


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
        start_y = self.h - 3.0
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
        
        # Максимальное количество элементов «зеркало».
        # 8–25 конусов — 1 пара, 26–49 — 2 пары и далее.
        if self.count <= 25:
            max_mirrors = 1
        else:
            max_mirrors = self.count // 25 + 1

        # Лимит вращений отдельно для каждого направления.
        # 8–24 конуса — по 1, 25–49 — по 2,
        # 50–74 — по 3, 75–99 — по 4 и далее.
        max_spins_per_direction = max(1, self.count // 25 + 1)

        spins_right = 0
        spins_left = 0

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
            # Оставляем свободную зону вокруг общего створа.
            if abs(y - start_y) < 2.0:
                return False

            for gate_cone in gate_cones:
                if math.dist(
                    (x, y),
                    (gate_cone.x, gate_cone.y)
                ) < 4.0:
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
            if (
                remaining >= 2
                and len(mirror_pairs) < max_mirrors
                and self.rng.random() < 0.12
            ):
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

            can_spin_right = spins_right < max_spins_per_direction
            can_spin_left = spins_left < max_spins_per_direction

            red_count = sum(
                1 for c in cones if c.kind in ("red", "red_yellow")
            )
            blue_count = sum(
                1 for c in cones if c.kind in ("blue", "blue_yellow")
            )

            # Вращения вправо и влево — с учётом лимитов и баланса.
            if (
                roll < spin_probability
                and can_spin_right
                and red_count - blue_count < 3
            ):
                kind = "red_yellow"
                label = "Вращение 360° вправо"
                spins_right += 1

            elif (
                roll < spin_probability * 2
                and can_spin_left
                and blue_count - red_count < 3
            ):
                kind = "blue_yellow"
                label = "Вращение 360° влево"
                spins_left += 1

            # Если вращение не выбрано, балансируем обычные повороты.
            elif red_count - blue_count < 0:
                kind = "red"
                label = "Правый поворот"

            elif blue_count - red_count < 0:
                kind = "blue"
                label = "Левый поворот"

            elif red_count - blue_count < 3 and (
                blue_count - red_count >= 3
                or self.rng.random() < 0.5
            ):
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
        """Строит маршрут с обходом конусов и общим створом старта/финиша."""
        start = (center_x, start_y - 1.0)
        route = [start]
        remaining = cones[:]
        current = start

        while remaining:
            ordered = sorted(
                remaining,
                key=lambda c: math.dist(current, (c.x, c.y))
            )
            pool = ordered[:min(4, len(ordered))]
            cone = self.rng.choice(pool)
            remaining.remove(cone)

            if cone.kind == "yellow":
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
                    points = self._mirror_waypoints(cone, mate, current)
                    route.extend(points)
                    current = points[-1]
                else:
                    points = self._turn_waypoints(
                        cone.x, cone.y, current, 1
                    )
                    route.extend(points)
                    current = points[-1]

            elif cone.kind == "red_yellow":
                points = self._spin_waypoints(
                    cone.x, cone.y, current, clockwise=True
                )
                route.extend(points)
                current = points[-1]

            elif cone.kind == "blue_yellow":
                points = self._spin_waypoints(
                    cone.x, cone.y, current, clockwise=False
                )
                route.extend(points)
                current = points[-1]

            else:
                side = 1 if cone.kind == "red" else -1
                points = self._turn_waypoints(
                    cone.x, cone.y, current, side
                )
                route.extend(points)
                current = points[-1]

        # Возвращение в тот же створ.
        route.append(start)

        # Не применять Catmull–Rom: он может срезать дуги
        # и провести линию через конусы.
        return self._smooth_route(route, samples=5)

    def _turn_waypoints(self, x, y, previous, side):
        """Дуга обхода конуса с безопасным радиусом."""

        radius = 1.7

        dx = previous[0] - x
        dy = previous[1] - y
        distance = math.hypot(dx, dy)

        if distance < 0.001:
            start_angle = -math.pi / 2
        else:
            start_angle = math.atan2(dy, dx)

        # Полукруг начинается со стороны подхода к конусу.
        # Направление обхода зависит от типа конуса.
        direction = 1 if side >= 0 else -1
        points = []

        for i in range(25):
            angle = start_angle + direction * math.pi * i / 24
            points.append((
                x + radius * math.cos(angle),
                y + radius * math.sin(angle),
            ))

        return points
    def _spin_waypoints(self, x, y, previous, clockwise=True):
        """Полный круг вокруг конуса с безопасным радиусом."""

        radius = 1.7

        dx = previous[0] - x
        dy = previous[1] - y

        if math.hypot(dx, dy) < 0.001:
            start_angle = -math.pi / 2
        else:
            start_angle = math.atan2(dy, dx)

        direction = 1 if clockwise else -1
        points = []

        # Полный круг с плотными точками, без прямых срезов.
        for i in range(49):
            angle = start_angle + direction * math.tau * i / 48
            points.append((
                x + radius * math.cos(angle),
                y + radius * math.sin(angle),
            ))

        return points
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
        """Плотная линейная интерполяция построенной траектории."""
        if len(points) < 2:
            return points[:]

        result = []

        for i in range(len(points) - 1):
            x1, y1 = points[i]
            x2, y2 = points[i + 1]

            for j in range(samples):
                t = j / samples
                result.append((
                    x1 + (x2 - x1) * t,
                    y1 + (y2 - y1) * t,
                ))

        result.append(points[-1])
        return result


# ============================================================
# ГРАФИЧЕСКИЙ ИНТЕРФЕЙС
# ============================================================

class App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Генератор трасс для мотоджимханы.")
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
            text="Генератор трасс для мотоджимханы. powered by Motogymkhana Glazov",
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
            text="Сохранить как",
            command=self.save_as,
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
            ("#2e8b57", "Ворота старт/финиш", False),
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
            oy + ay * scale - -12,
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
            f"Жёлтые конусы (зеркало): {counts.get('yellow', 0)}",
            "",
            "Ворота:",
            "• старт / финиш — 2 стойки, общий створ",
            "",

            "Важно: траектория схематическая. Проверьте её на площадке.",
        ]

        self.info.configure(state=tk.NORMAL)
        self.info.delete("1.0", tk.END)
        self.info.insert("1.0", "\n".join(lines))
        self.info.configure(state=tk.DISABLED)

    def save_as(self):
        if not self.track:
            return

        path = filedialog.asksaveasfilename(
            title="Сохранить схему",
            defaultextension=".png",
            filetypes=[
                ("PNG — изображение", "*.png"),
                ("JPG — изображение", "*.jpg"),
                ("JPEG — изображение", "*.jpeg"),
            ],
        )

        if not path:
            return

        try:
            import os
            from PIL import Image, ImageDraw, ImageFont

            track = self.track

            # Масштаб экспорта: 40 пикселей на метр.
            scale = 40
            padding = 100
            label_space = 55

            width = int(track.width * scale + 2 * padding)
            height = int(
                track.height * scale + 2 * padding + label_space
            )

            # Белый фон подходит и для PNG, и для JPG.
            img = Image.new("RGB", (width, height), "white")
            draw = ImageDraw.Draw(img)

            def get_font(size, bold=False):
                candidates = (
                    ["segoeuib.ttf", "arialbd.ttf"]
                    if bold
                    else ["segoeui.ttf", "arial.ttf"]
                )

                for name in candidates:
                    try:
                        return ImageFont.truetype(name, size)
                    except OSError:
                        pass

                return ImageFont.load_default()

            font = get_font(24)
            small_font = get_font(18)
            bold_font = get_font(22, bold=True)

            ox = padding
            oy = padding
            s = scale

            x2 = ox + track.width * s
            y2 = oy + track.height * s

            # Площадка.
            draw.rectangle(
                (ox, oy, x2, y2),
                fill="#fbfcfd",
                outline="#252a30",
                width=4,
            )

            # Метровая сетка.
            for meter in range(1, int(track.width)):
                x = ox + meter * s
                draw.line(
                    (x, oy, x, y2),
                    fill="#edf0f2",
                    width=1,
                )

            for meter in range(1, int(track.height)):
                y = oy + meter * s
                draw.line(
                    (ox, y, x2, y),
                    fill="#edf0f2",
                    width=1,
                )

            # Размеры площадки.
            draw.text(
                ((ox + x2) / 2, oy - 42),
                f"{track.width:g} м",
                fill="#171717",
                font=bold_font,
                anchor="mm",
            )

            draw.text(
                (ox - 48, (oy + y2) / 2),
                f"{track.height:g} м",
                fill="#171717",
                font=bold_font,
                anchor="mm",
            )

            # Общие ворота старта и финиша.
            (ax, ay), (bx, by) = track.start_gate

            draw.line(
                (
                    ox + ax * s,
                    oy + ay * s,
                    ox + bx * s,
                    oy + by * s,
                ),
                fill="#2e8b57",
                width=8,
            )

            gate_label = "СТАРТ / ФИНИШ"
            draw.text(
                (
                    ox + (ax + bx) * s / 2,
                    oy + ay * s - 24,
                ),
                gate_label,
                fill="#2e8b57",
                font=small_font,
                anchor="mm",
            )

            colors = {
                "red": "#d62728",
                "blue": "#1769d2",
                "red_yellow": "#d62728",
                "blue_yellow": "#1769d2",
                "yellow": "#f2c500",
                "gate_start": "#2e8b57",
                "gate_finish": "#222222",
            }

            # Конусы.
            radius = max(10, int(s * 0.38))

            for cone in track.cones:
                x = ox + cone.x * s
                y = oy + cone.y * s
                r = radius
                color = colors.get(cone.kind, "#888888")

                draw.ellipse(
                    (x - r, y - r, x + r, y + r),
                    fill=color,
                    outline="#171717",
                    width=3,
                )

                # Жёлтая полоса на конусах вращения.
                if cone.kind in ("red_yellow", "blue_yellow"):
                    draw.line(
                        (x - int(r * 0.72), y,
                         x + int(r * 0.72), y),
                        fill="#ffe64a",
                        width=max(4, int(r * 0.55)),
                    )

                # Белая метка на стойках ворот.
                elif cone.kind in ("gate_start", "gate_finish"):
                    draw.line(
                        (x - r // 2, y - r // 2,
                         x + r // 2, y + r // 2),
                        fill="white",
                        width=4,
                    )

            # Подпись внизу схемы.
            draw.text(
                (ox, y2 + 22),
                "Схема площадки для мотоджимханы",
                fill="#666666",
                font=small_font,
            )

            # Выбираем формат по расширению файла.
            extension = os.path.splitext(path)[1].lower()

            if extension in (".jpg", ".jpeg"):
                img.save(path, format="JPEG", quality=95)
            else:
                if extension != ".png":
                    path += ".png"
                img.save(path, format="PNG")

            self.status.set("Схема сохранена: " + path)

            messagebox.showinfo(
                "Готово",
                f"Изображение сохранено:\n{path}",
            )

        except Exception as error:
            messagebox.showerror(
                "Ошибка сохранения",
                f"Не удалось сохранить изображение:\n{error}",
            )






if __name__ == "__main__":
    App().mainloop()