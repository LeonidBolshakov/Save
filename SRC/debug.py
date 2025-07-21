from SRC.GENERAL.environment_variables import EnvironmentVariables
from SRC.GENERAL.constant import Constant as C
from pprint import pprint

variables = EnvironmentVariables()

ACCESS_TOKEN_IN_TOKEN = "access_token"
REFRESH_TOKEN_IN_TOKEN = "refresh_token"
EXPIRES_IN_IN_TOKEN = "expires_in"

token_data = {
    "grant_type": "refresh_token",
    "refresh_token": variables.get_var(C.REFRESH_TOKEN),
    "client_id": variables.get_var(C.ENV_YANDEX_CLIENT_ID),
    "client_secret": variables.get_var(C.ENV_CLIENT_SECRET),
}
pprint(token_data)
