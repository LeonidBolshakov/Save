import pytest
from unittest.mock import patch
import logging
import sys
from SRC.backupmanager import BackupManager
from SRC.constant import Constant as C

# Настройка логгера для тестов
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


@pytest.fixture
def backup_manager():
    """Фикстура для создания экземпляра BackupManager."""
    return BackupManager()


@pytest.fixture
def mock_file7zarchiving():
    """Фикстура для мокирования Archiver7z."""
    with patch("backupmanager.Archiver7z") as mock:
        instance = mock.return_value
        instance.make_local_archive.return_value = "/tmp/test_archive.exe"
        yield mock


@pytest.fixture
def mock_yandex_disk():
    """Фикстура для мокирования YandexDisk."""
    with patch("backupmanager.YandexDisk") as mock:
        instance = mock.return_value
        instance.write_file_fast.return_value = "/remote/test_archive.exe"
        yield mock


@pytest.fixture
def mock_message_mail():
    """Фикстура для мокирования MessageMail."""
    with patch("backupmanager.MessageMail") as mock:
        yield mock


def test_main_success(
    backup_manager, mock_file7zarchiving, mock_yandex_disk, mock_message_mail
):
    """Тест успешного выполнения основного процесса."""
    with patch("backupmanager.TemporaryDirectory") as mock_temp_dir:
        mock_temp_dir.return_value.__enter__.return_value = "/tmp"

        # Заменяем sys.exit для проверки кода выхода
        with patch.object(sys, "exit") as mock_exit:
            backup_manager.main()

            # Проверяем вызовы
            mock_file7zarchiving.return_value.make_local_archive.assert_called_once_with(
                "/tmp"
            )
            mock_yandex_disk.return_value.write_file_fast.assert_called_once_with(
                "/tmp/test_archive.exe"
            )
            mock_exit.assert_called_once_with(0)


def test_main_failure(backup_manager, mock_file7zarchiving, mock_yandex_disk):
    """Тест обработки ошибки в основном процессе."""
    with patch("backupmanager.TemporaryDirectory") as mock_temp_dir:
        mock_temp_dir.return_value.__enter__.return_value = "/tmp"
        mock_file7zarchiving.return_value.make_local_archive.side_effect = Exception(
            "Test error"
        )

        with patch.object(sys, "exit") as mock_exit:
            backup_manager.main()
            mock_exit.assert_called_once_with(1)


def test_write_file_success(backup_manager, mock_yandex_disk):
    """Тест успешной загрузки файла на Яндекс.Диск."""
    remote_path = backup_manager.write_file("/local/test.exe")
    assert remote_path == "/remote/test_archive.exe"
    mock_yandex_disk.return_value.write_file_fast.assert_called_once_with(
        "/local/test.exe"
    )


def test_write_file_failure(backup_manager, mock_yandex_disk):
    """Тест ошибки при загрузке файла на Яндекс.Диск."""
    mock_yandex_disk.return_value.write_file_fast.return_value = None

    with pytest.raises(OSError):
        backup_manager.write_file("/local/test.exe")


def test_write_file_exception(backup_manager, mock_yandex_disk):
    """Тест исключения при загрузке файла на Яндекс.Диск."""
    mock_yandex_disk.return_value.write_file_fast.side_effect = Exception("API error")

    with pytest.raises(RuntimeError):
        backup_manager.write_file("/local/test.exe")


def test_completion_success(backup_manager, mock_message_mail):
    """Тест успешного завершения."""
    with patch("backupmanager.MaxLevelHandler") as mock_handler:
        mock_instance = mock_handler.return_value
        mock_instance.get_highest_level.return_value = logging.INFO

        with patch.object(sys, "exit") as mock_exit:
            backup_manager._completion(failure=False, remote_path="/remote/test.exe")

            # Проверяем вызовы
            mock_message_mail.return_value.compose_and_send_email.assert_called_once()
            mock_exit.assert_called_once_with(0)

            # Проверяем, что критическое сообщение содержит путь
            assert any(
                C.STOP_SERVICE_MESSAGE in record.message
                for record in logger.handlers[0].records
                if record.levelno == logging.CRITICAL
            )


def test_completion_failure(backup_manager, mock_message_mail):
    """Тест завершения с ошибкой."""
    with patch("backupmanager.MaxLevelHandler") as mock_handler:
        mock_instance = mock_handler.return_value
        mock_instance.get_highest_level.return_value = logging.ERROR

        with patch.object(sys, "exit") as mock_exit:
            backup_manager._completion(failure=True)

            mock_message_mail.return_value.compose_and_send_email.assert_called_once()
            mock_exit.assert_called_once_with(1)


def test_completion_log_info(backup_manager):
    """Тест логирования успешного завершения."""
    with patch.object(logger, "info") as mock_info:
        BackupManager._log_end_messages(logging.INFO, "INFO")
        mock_info.assert_called_with("Задание успешно завершено!")


def test_completion_log_warning(backup_manager):
    """Тест логирования завершения с предупреждениями."""
    with patch.object(logger, "warning") as mock_warning:
        BackupManager._log_end_messages(logging.WARNING, "WARNING")
        mock_warning.assert_called_with(
            "WARNING --> Задание завершено с предупреждениями"
        )


def test_completion_log_error(backup_manager):
    """Тест логирования завершения с ошибками."""
    with patch.object(logger, "error") as mock_error:
        BackupManager._log_end_messages(logging.ERROR, "ERROR")
        mock_error.assert_called_with("Задание завершено с ошибками уровня ERROR")
