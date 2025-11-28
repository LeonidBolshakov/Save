def init_button_styles(self) -> None:
    """
    Настраивает внешний вид основных кнопок.
    """

    # Кнопка "Создать задачу" – основное действие (primary)
    base = """
        QPushButton {
            padding: 4px 10px;
        }
    """
    self.group_box_left.setStyleSheet(base)
    self.btn_create_task.setStyleSheet(
        """
        QPushButton {
            background-color: #e0f5ff;
            border: 1px solid #8ac9ff;
            border-radius: 4px;
        }
        QPushButton:disabled {
            background-color: #f3f3f3;
            border: 1px solid #d0d0d0;
            color: #808080;
        }
    """
    )

    # Кнопка "Отказаться от изменен."
    self.btn_reject_changes.setStyleSheet(
        """
        QPushButton {
            border: 1px solid #c0c0c0;
            border-radius: 4px;
        }
    """
    )

    self.btn_delete_task.setStyleSheet(
        """
        QPushButton {
            background: transparent;
            border: 1px solid #dddddd;
            border-radius: 4px;
            color: #666666;
        }
        QPushButton:hover {
            background: #f5f5f5;
            border-color: #cccccc;
            color: #444444;
        }
        QPushButton:pressed {
            background: #e8e8e8;
            border-color: #bbbbbb;
        }
        QPushButton:disabled {
            background: #f3f3f3;
            border: 1px solid #e0e0e0;
            color: #aaaaaa;
        }
    """
    )
