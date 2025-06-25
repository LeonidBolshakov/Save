import os
import sys
import platform
import subprocess
import urllib.request
import tempfile
import shutil
from pathlib import Path


class SevenZManager:
    def __init__(self):
        self.system = platform.system().lower()
        self.sevenzip_path = None

    def get_7z_path(self, auto_install=False):
        """Основной метод для получения пути к работоспособному 7z"""
        # 1. Использовать кэшированный путь, если он рабочий
        if self.sevenzip_path and self._check_working(self.sevenzip_path):
            return self.sevenzip_path

        # 2. Поиск в системе
        found_path = self._find_in_system()
        if found_path and self._check_working(found_path):
            self.sevenzip_path = found_path
            return found_path

        # 3. Автоматическая установка при разрешении
        if auto_install:
            installed_path = self._install_7z()
            if installed_path and self._check_working(installed_path):
                self.sevenzip_path = installed_path
                return installed_path

        # 4. Если ничего не найдено
        raise FileNotFoundError(
            "7-Zip не найден. Установите 7-Zip и добавьте в PATH в окружении системы или "
            "укажите путь через переменную SEVENZIP_PATH в окружении системы"
        )

    def _try_cached_path(self):
        """Проверить кэшированный путь (внутренний метод)"""
        return self.sevenzip_path and self._check_working(self.sevenzip_path)

    def _find_in_system(self):
        """Поиск 7z в системе"""
        # Проверить переменную окружения
        if path := os.environ.get("SEVENZIP_PATH"):
            if Path(path).exists() and self._check_working(path):
                return path

        # Проверить стандартные пути
        if path := self._check_common_paths():
            return path

        # Найти в системном PATH
        return self._find_in_path()

    def _check_common_paths(self) -> str | None:
        """Проверить стандартные пути установки"""
        common_paths = {
            "windows": [
                "C:\\Program Files\\7-Zip\\7z.exe",
                "C:\\Program Files (x86)\\7-Zip\\7z.exe",
            ],
            "linux": ["/usr/bin/7z", "/usr/local/bin/7z", "/snap/bin/7z"],
            "darwin": ["/usr/local/bin/7z", "/opt/homebrew/bin/7z"],
        }

        for path in common_paths.get(self.system, []):
            if Path(path).exists() and self._check_working(path):
                return path
        return None

    def _find_in_path(self):
        """Поиск 7z в системном PATH"""
        exe_names = ["7z", "7z.exe"] if self.system == "windows" else ["7z"]

        for dir_path in os.environ.get("PATH", "").split(os.pathsep):
            if not dir_path:
                continue

            for exe in exe_names:
                path = Path(dir_path) / exe
                if path.exists():
                    return str(path)
        return None

    @staticmethod
    def _check_working(path):
        """Проверить работоспособность 7z"""
        try:
            result = subprocess.run(
                [path, "--help"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=2,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.SubprocessError, OSError):
            return False

    def _install_7z(self):
        """Автоматическая установка 7-Zip (платформозависимая)"""
        print("⚙️ Установка 7-Zip...")

        if self.system == "windows":
            return self._install_windows()
        elif self.system == "linux":
            return self._install_linux()
        elif self.system == "darwin":
            return self._install_macos()
        else:
            print(
                f"❌ Автоматическая установка не поддерживается для {platform.system()}"
            )
            return None

    def _install_windows(self):
        """Установка 7-Zip на Windows"""
        try:
            # Попробовать через Chocolatey
            if shutil.which("choco"):
                print("  → Установка через Chocolatey...")
                subprocess.run(
                    ["choco", "install", "7zip", "-y", "--no-progress"],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return self._find_in_system()

            # Ручная установка
            print("  → Скачивание установщика...")
            url = "https://7-zip.org/a/7z2409-x64.exe"
            installer_path = Path(tempfile.gettempdir()) / "7z_installer.exe"

            with urllib.request.urlopen(url) as response, open(
                installer_path, "wb"
            ) as out_file:
                shutil.copyfileobj(response, out_file)

            # Путь по умолчанию
            default_path = Path("C:\\Program Files\\7-Zip")

            print("  → Запуск установщика...")
            subprocess.run(
                [str(installer_path), "/S", f"/D={default_path}"],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            # Проверить установку
            sevenzip_path = default_path / "7z.exe"
            if sevenzip_path.exists():
                self._add_to_path(str(default_path))
                return str(sevenzip_path)
            return None

        except Exception as e:
            print(f"❌ Ошибка установки: {e}")
            return None

    def _install_linux(self):
        """Установка 7-Zip на Linux"""
        try:
            print("  → Установка через системный менеджер пакетов...")

            if shutil.which("apt-get"):
                subprocess.run(["sudo", "apt-get", "update"], check=True)
                subprocess.run(
                    ["sudo", "apt-get", "install", "p7zip-full", "-y"], check=True
                )
            elif shutil.which("yum"):
                subprocess.run(["sudo", "yum", "install", "p7zip", "-y"], check=True)
            elif shutil.which("dnf"):
                subprocess.run(["sudo", "dnf", "install", "p7zip", "-y"], check=True)
            elif shutil.which("zypper"):
                subprocess.run(["sudo", "zypper", "install", "p7zip", "-y"], check=True)
            elif shutil.which("pacman"):
                subprocess.run(
                    ["sudo", "pacman", "-Sy", "p7zip", "--noconfirm"], check=True
                )
            else:
                print("❌ Не найден поддерживаемый пакетный менеджер")
                return None

            return self._find_in_system()
        except Exception as e:
            print(f"❌ Ошибка установки: {e}")
            return None

    def _install_macos(self):
        """Установка 7-Zip на macOS"""
        try:
            if shutil.which("brew"):
                print("  → Установка через Homebrew...")
                subprocess.run(["brew", "install", "p7zip"], check=True)
                return self._find_in_system()
            else:
                print("❌ Homebrew не установлен. Установите его командой:")
                print(
                    '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
                )
                return None
        except Exception as e:
            print(f"❌ Ошибка установки: {e}")
            return None

    @staticmethod
    def _add_to_path(path):
        """Добавить путь в системную переменную PATH"""
        if path not in os.environ["PATH"]:
            os.environ["PATH"] = f"{path}{os.pathsep}{os.environ['PATH']}"
            print(f"  → Добавлено в PATH: {path}")


# Пример использования
if __name__ == "__main__":
    print("🔍 Поиск 7-Zip...")
    manager = SevenZManager()

    try:
        # Пробуем найти существующую установку
        main_path = manager.get_7z_path()
        print(f"✅ Найден 7z: {main_path}")
    except FileNotFoundError:
        print("❌ 7-Zip не найден. Хотите установить автоматически? (y/n)")
        if input().lower() == "y":
            try:
                main_path = manager.get_7z_path(auto_install=True)
                print(f"🎉 7-Zip успешно установлен: {main_path}")

                # Проверка работоспособности
                print("🔧 Проверка работоспособности...")
                main_result = subprocess.run(
                    [main_path, "--help"], capture_output=True, text=True
                )
                if main_result.returncode == 0:
                    print("✅ 7z работает корректно!")
                else:
                    print(f"⚠️ Ошибка при запуске 7z: {main_result.stderr}")
            except Exception as main_e:
                print(f"❌ Критическая ошибка: {main_e}")
                sys.exit(1)
        else:
            print("ℹ️ Установите 7-Zip вручную: https://7-zip.org")
            sys.exit(1)

# # Создаем экземпляр менеджера
# manager = SevenZManager()
#
# try:
#     # Получаем путь к 7z (с возможностью автоматической установки)
#     sevenzip_path = manager.get_7z_path(auto_install=True)
#
#     # Создаем объект архивации
#     arch = Arch7zSpec(
#         arch_name="backup.exe",
#         list_file="files.txt",
#         sevenzip_path=sevenzip_path  # передаем полученный путь
#     )
#
#     # Выполняем архивацию
#     if arch.to_archive():
#         print("Архивация успешно завершена!")
#     else:
#         print("Ошибка при выполнении архивации")
#
# except FileNotFoundError as e:
#     print(f"Ошибка: {e}")
#     sys.exit(1)
# except Exception as e:
#     print(f"Неожиданная ошибка: {e}")
#     sys.exit(1)
