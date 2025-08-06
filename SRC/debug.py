from abc import ABC


class BaseArchiving(ABC):
    @staticmethod
    def start() -> int:
        print("Приступили к архивированию")


class BaseBackupManager(ABC):
    def __init__(self, _archiver: BaseArchiving):
        self.archiver = _archiver

    def start(self) -> None:
        print(f"Приступили к управлению сохранения данных. Архиватор {archiver}")
        self.archiver.start()


class BackupManager7z(BaseBackupManager):
    def __init__(self, _archiver: BaseArchiving):
        super().__init__(_archiver)

    def backup(self) -> None:  # Реализуем абстрактный метод
        pass


class CreateArch7zSpec(BaseArchiving):
    def create_archive(self) -> int:
        pass


# Создаём экземпляр архиватора
archiver = CreateArch7zSpec()
print(f"{archiver=}")

# Создаём менеджер для 7z
manager_7z = BackupManager7z(archiver)

# Вызываем backup
manager_7z.start()  # Выведет: "Creating 7z archive"
