from yandex_music import Client
from random import randint
import os

def download_random_track(mail, password, file_path):
    client = Client.from_credentials(mail, password)
    n = randint(0, len(YMClient.users_likes_tracks()))
    client.users_likes_tracks()[n].fetch_track().download(file_path)