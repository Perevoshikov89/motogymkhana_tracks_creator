import urllib.request

url = "http://localhost:11434/api/tags"

try:
    with urllib.request.urlopen(url, timeout=5) as response:
        print(response.status)
        print(response.read().decode("utf-8"))
except Exception as exc:
    print(type(exc).__name__, str(exc))

input("Нажми Enter для выхода...")