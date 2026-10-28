
# -*- coding: utf-8 -*-
"""Локальный ИИ-агент для MotoGymkhana Track Generator."""

import json
import urllib.request
import urllib.error
import socket

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL = "qwen2.5:1.5b"
TIMEOUT = 300


def ask_local_ai(cones):
    """Возвращает порядок прохождения индексов обычных конусов."""

    if not cones:
        raise RuntimeError("Нет конусов для планирования.")

    description = [
        {
            "id": i,
            "kind": cone.kind,
            "label": cone.label,
            "x": round(cone.x, 2),
            "y": round(cone.y, 2),
        }
        for i, cone in enumerate(cones)
    ]

    prompt = f"""
Ты планировщик последовательности элементов мотоджимханы.
Выбери порядок прохождения всех элементов, стараясь уменьшить
лишние перемещения между удалёнными конусами.

Верни только JSON формата:
{{"order": [0, 2, 1]}}

Правила:
- Используй каждый id ровно один раз.
- Не пропускай и не повторяй id.
- Не изменяй координаты.
- Верни только JSON без пояснений.

Элементы:
{json.dumps(description, ensure_ascii=False)}
"""

    payload = {
        "model": MODEL,
        "prompt": prompt,
        "format": "json",
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": max(100, len(cones) * 15),
            "num_ctx": 4096,
        },
    }

    request = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            raw = response.read().decode("utf-8")
        result = json.loads(raw)

    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Ollama вернула HTTP {exc.code}:\n{details}"
        ) from exc

    except (urllib.error.URLError, socket.timeout, TimeoutError) as exc:
        raise RuntimeError(
            "Не удалось получить ответ от Ollama.\n\n"
            "Проверь, что Ollama запущена и модель доступна.\n"
            f"Адрес: {OLLAMA_URL}\n"
            f"Подробности: {exc}"
        ) from exc

    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Ollama вернула некорректный JSON: {exc}"
        ) from exc

    try:
        answer = json.loads(result["response"])
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            "Не удалось прочитать ответ модели Ollama.\n"
            f"Ответ сервера: {result!r}"
        ) from exc

    order = answer.get("order")
    expected = set(range(len(cones)))

    if not isinstance(order, list):
        raise RuntimeError("ИИ не вернул список order.")

    if any(type(i) is not int for i in order):
        raise RuntimeError("ИИ вернул нецелые индексы конусов.")

    if len(order) != len(cones) or set(order) != expected:
        raise RuntimeError(
            "ИИ вернул неверный порядок конусов: "
            "есть пропуски, повторы или лишние индексы.\n"
            "Попробуй запустить генерацию ещё раз."
        )

    return order
