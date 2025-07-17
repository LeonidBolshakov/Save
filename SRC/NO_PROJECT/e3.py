import webbrowser
import yadisk

CLIENT_ID = "86d21a515c3344e4bbe2641b5d41a6df"
REDIRECT_URI = "urn:ietf:wg:oauth:2.0:oob"  # Укажите это в настройках OAuth!

# Открываем браузер для авторизации
auth_url = f"https://oauth.yandex.ru/authorize?response_type=code&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}"
webbrowser.open(auth_url)

# Пользователь вводит код вручную
code = input("Введите код из браузера: ")

# Получаем токен
y = yadisk.YaDisk(client_id=CLIENT_ID, client_secret="ваш_client_secret")
y.get_token(code)
print("Токен:", y.token)
