import keyring
import os

# Импортируем fallback backend
try:
    from keyrings.alt.file import PlaintextKeyring
except ImportError:
    raise ImportError("Установите fallback backend: pip install keyrings.alt")

# 1. Устанавливаем file-based keyring
kr = PlaintextKeyring()
kr.file_path = os.path.expanduser("~/.bol_save_keyring.cfg")
keyring.set_keyring(kr)

# 2. Логируем активный backend
backend = keyring.get_keyring()
print(f"📦 Активный backend: {backend}")
if isinstance(backend, PlaintextKeyring):
    print(f"📄 Keyring файл: {backend.file_path}")

# 3. Тестовые данные
SERVICE = "BOL_SAVE"
KEY = "ACCESS_TOKEN"
VALUE = "test-token-123"

# 4. Запись
keyring.set_password(SERVICE, KEY, VALUE)
print(f"✅ Значение записано: {VALUE}")

# 5. Чтение
retrieved = keyring.get_password(SERVICE, KEY)
print(f"📥 Получено из keyring: {retrieved!r}")

# 6. Проверка
if retrieved == VALUE:
    print("✅ Всё работает!")
else:
    print("❌ Ошибка: данные не сохранены корректно")
