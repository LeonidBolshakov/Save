# import requests
# from datetime import datetime
# from progress.bar import Bar
# from pathlib import Path
#
URL = "https://cloud-api.yandex.net/v1/disk/resources"
TOKEN = "y0__xDg3sbNAxiz5Tcg0vrAlBOf5-cqbTAUIjRi3wmHbtaD2tk1KA"
headers = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Authorization": f"OAuth {TOKEN}",
}

#
# def err(rc: int):
#     print(f"Ошибка создания директории на Yandex. Диск - {rc}")
#
#
# def create_folder(path: str) -> int:
#     """
#     Создание папки на Yandex Диске
#     :param path: (str). Путь к создаваемой папке
#     :return: int. Код статуса ответа на запрос о создании директории
#     """
#     response = requests.put(f"{URL}?path={path}", headers=headers)
#     print(response.status_code)
#     return response.status_code
#
#
# def upload_file(loadfile, savefile, replace=False):
#     """Загрузка файла
#     savefile: Путь к файлу на Диске
#     loadfile: Путь к загружаемому файлу
#     replace: true or false Замена файла на Диске"""
#     res = requests.get(
#         f"{URL}/upload?path={savefile}&overwrite={replace}", headers=headers
#     ).json()
#     with open(loadfile, "rb") as f:
#         try:
#             requests.put(res["href"], files={"file": f})
#         except KeyError:
#             print(res)
#
#
# def backup(save_path: str, load_path: str) -> None:
#     """
#     Загрузка папки на Yandex. Диск
#     :param save_path: (str). Путь к папке на Диске для сохранения
#     :param load_path: (str). Путь к загружаемой папке
#     :return:
#     """
#     folder_date = (
#         f'{load_path.split("\\")[-1]}_{datetime.now().strftime("%Y.%m.%d-%H.%M.%S")}'
#     )
#     rc = create_folder(save_path)
#     if rc != 201:
#         print(f"{rc=}")
#         err(rc)
#     for item in Path(load_path).rglob("*"):
#         if item.is_dir():
#             print(item.name)
#             create_folder(
#                 "{0}/{1}/{2}".format(
#                     save_path,
#                     folder_date,
#                     item.name.replace(load_path, "").replace("\\", "/"),
#                 )
#             )
#         # bar = Bar("Loading", fill="X", max=len(files))
#         # for file in files:
#         #     bar.next()
#         #     upload_file(
#         #         "{0}/{1}".format(address, file),
#         #         "{0}/{1}{2}/{3}".format(
#         #             save_path,
#         #             folder_date,
#         #             address.replace(load_path, "").replace("\\", "/"),
#         #             file,
#         #         ),
#         #     )
#         # bar.finish()
#
#
# if __name__ == "__main__":
#     # backup('Backup', r'C:\Files\backup')
#     backup("Backup", str(Path.cwd()))
#
# import requests
#
# TOKEN = "y0__xDg3sbNAxiz5Tcg0vrAlBOf5-cqbTAUIjRi3wmHbtaD2tk1KA"
# headers = {"Authorization": f"OAuth {TOKEN}"}
#
#
# # Проверка токена
# def check_token():
#     url = "https://cloud-api.yandex.net/v1/disk"
#     response = requests.get(url, headers=headers)
#     print("Статус проверки токена:", response.status_code)
#     return response.json() if response.status_code == 200 else None
#
#
# check_token()
import requests


def debug_folder_creation():
    url = "https://cloud-api.yandex.net/v1/disk/resources"
    params = {"path": "app:/debug_folder"}

    response = requests.put(url, headers=headers, params=params)

    print(f"Status: {response.status_code}")
    print("Response:", response.json())  # Здесь будет конкретная ошибка от API

    if response.status_code == 403:
        print("\nВозможные причины:")
        print("- Токен не имеет прав на запись")
        print("- Попытка создать папку в системной директории")
        print("- Ограничения родительской папки")


debug_folder_creation()
