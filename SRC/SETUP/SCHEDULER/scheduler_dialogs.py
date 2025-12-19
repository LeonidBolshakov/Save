from typing import Callable
from PyQt6.QtWidgets import QMessageBox


def confirm_delete_task(msg_parent: Callable[[], None]) -> bool:
    """
    Показывает диалог подтверждения удаления задачи.

    Returns:
        True, если пользователь подтвердил удаление, иначе False.
    """

    msg = QMessageBox(msg_parent())
    msg.setIcon(QMessageBox.Icon.Warning)
    msg.setWindowTitle("Подтверждение удаления")
    msg.setText("Удалить задачу?")
    msg.setInformativeText("После удаления задача будет безвозвратно удалена.")

    # Кнопки
    delete_btn = msg.addButton("Удалить", QMessageBox.ButtonRole.DestructiveRole)
    cancel_btn = msg.addButton("Отмена", QMessageBox.ButtonRole.RejectRole)

    # По умолчанию фокус — на Отмена
    msg.setDefaultButton(cancel_btn)

    msg.exec()

    return msg.clickedButton() is delete_btn


def error_message(text: str, informative_text: str) -> None:
    msg = QMessageBox(None)
    msg.setIcon(QMessageBox.Icon.Critical)
    msg.setWindowTitle("Ошибка")
    msg.setText(text)
    msg.setInformativeText(str(informative_text))
    msg.exec()
