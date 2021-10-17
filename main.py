import telebot as tb
import uuid
import os
import speech_recognition as sr
from telebot import types
from pydub import AudioSegment
import pprint
from random import randint
from comtypes.client import CreateObject

from search import search
from likes_playlist import download_random_track
from config import *


engine = CreateObject("SAPI.SpVoice")
bot = tb.TeleBot(TOKEN)
r = sr.Recognizer()                              # для обработки аудио
AudioSegment.converter = absolute_path_to_ffmpeg # необходимая строка, т.к. мы изменили путь к ffmpeg

# клавиатура выбора способа запроса музыки
keyboard1 = types.InlineKeyboardMarkup()
key_1 = types.InlineKeyboardButton(text='Авторизоваться и воспроизвести плейлист "Мне нравится"', callback_data='auth')
key_2 = types.InlineKeyboardButton(text='Поиск по названию', callback_data='search')
keyboard1.add(key_1)
keyboard1.add(key_2)
# клавиатура да/нет (по факту бесполезная, но добавленна чтоб не было навязчевого флуда)
keyboard2 = types.InlineKeyboardMarkup()
key_yes = types.InlineKeyboardButton(text='Да', callback_data='yes')
key_no  = types.InlineKeyboardButton(text='Нет', callback_data='no')
keyboard2.row(key_yes, key_no)
# клавиатура для выбора команды
keyboard3 = types.InlineKeyboardMarkup()
key_a_to_t = types.InlineKeyboardButton(text='Голосовое сообщение в виде текста', callback_data='command1')
key_t_to_a = types.InlineKeyboardButton(text='Озвучить текстовое сообщение', callback_data='command2')
key_music  = types.InlineKeyboardButton(text='Хочу послушать музыку', callback_data='command3')
key_talk   = types.InlineKeyboardButton(text='А давай-ка поговорим', callback_data='command4')
keyboard3.add(key_a_to_t)
keyboard3.add(key_t_to_a)
keyboard3.add(key_music)
keyboard3.add(key_talk)

recording   = False
searching   = False
authorising = False

def audio_to_text(filename):
    with sr.AudioFile(filename) as source:
        audio_text = r.listen(source)
        try:
            # здесь используется "онлайн" распознавание голоса
            # к тому же могут быть ошибки в распознавании при существовании созвучных слов или невнятном озвучивании
            # к примеру, "волос" и "голос" или "нету сил" и "не тусил"
            text = r.recognize_google(audio_text, language=language)
            print('Конвертация сообщения в текст ...')
            print(text)
            return text
        except: # К примеру, ошибка считывания файла (длина 0)
            print('Error')
            return "Упс, ошибочка... попробуй ещё раз..."

def text_to_wav(eingabe, ausgabe, text_aus_datei = True, geschwindigkeit = 2, Stimmenname = "Anna"):

    engine.rate = geschwindigkeit # von -10 bis 10

    for stimme in engine.GetVoices():
        print(stimme.GetDescription())
        if stimme.GetDescription().find(Stimmenname) >= 0:
            engine.Voice = stimme
            break
    else:
        print("Fehler Stimme nicht gefunden -> Standard wird benutzt")

    if text_aus_datei:
        datei = open(eingabe, 'r')
        text = datei.read()
        datei.close()
    else:
        text = eingabe

    stream = CreateObject("SAPI.SpFileStream")
    from comtypes.gen import SpeechLib

    stream.Open(ausgabe, SpeechLib.SSFMCreateForWrite)
    engine.AudioOutputStream = stream
    engine.speak(text)

    stream.Close()

@bot.message_handler(content_types=['voice'])
def audio_to_text_processing(message):

    # создание папок для "сырых" и сконвертированных айдио
    filename = str(uuid.uuid4())
    file_name           = "voice/"+filename+".ogg"
    file_name_converted = "ready/"+filename+".wav"
    # считывание и сохрание в пути file_name
    downloaded_file = bot.download_file(bot.get_file(message.voice.file_id).file_path)
    with open(file_name, 'wb') as new_file:
        new_file.write(downloaded_file)
    # конвертируем аудио файл из формата .ogg в формат .wav
    given_audio = AudioSegment.from_file(file_name, format="ogg")
    given_audio.export(file_name_converted, format="wav")
    # распознавание и ответ пользователю
    text = audio_to_text(file_name_converted)
    bot.reply_to(message, text)

    os.remove(file_name)
    os.remove(file_name_converted)


@bot.message_handler(content_types=['text'])
def get_text_message(message):

    global recording, searching, authorising
    if recording:

        recording = False
        # преобразуем message в речь и сохраняем
        print(message.text)
        file_path = str(uuid.uuid4()) + ".wav"
        text_to_wav(message.text, file_path, False)
        # отправляем результат
        result = open(file_path, 'rb')
        bot.send_audio(message.from_user.id, result)
        result.close()
        os.remove(file_path)

    elif searching:

        # поиск результата
        searching = False
        bot.send_message(message.from_user.id, search(message.text))

    elif authorising:

        authorising = False
        # авторизация и возвращение случайного трека из "мне нравится"
        mail, password = message.text.split()
        file_path = "music/" + str(uuid.uuid4()) + ".wav"
        download_random_track(mail, password, file_path)
        bot.send_audio(message.from_user.id, file_path)


    elif 'привет' in message.text.lower(): # предполагается второй и последующие вызовы get_info

        global keyboard2
        bot.send_message(message.from_user.id, "Привет!")
        bot.send_message(message.from_user.id, text="Нужна помощь?", reply_markup=keyboard2)

    else:
        bot.register_next_step_handler(message, talk)


@bot.callback_query_handler(func = lambda call: True)
def callback_worker(call):
    if call.data == 'yes':

        bot.send_message(call.message.chat.id, "Круто!")
        global info_text
        bot.send_message(call.message.chat.id, info_text)
        bot.send_message(call.message.chat.id, text="Выбери одну из функций:", reply_markup=keyboard3)

    elif call.data == 'no':

        bot.send_message(call.message.chat.id, "Жаль")
        bot.send_sticker(call.message.chat.id, open('static/sad_sti.webp', 'rb'))

    elif call.data == 'auth':

        recording, searching, authorising = False, False, True
        bot.send_message(call.message.chat.id, "Введи свой логин и пароль (Пример: example@yandex.com password)")

    elif call.data == 'search':

        recording, searching, authorising = False, True, False
        bot.send_message(call.message.chat.id, "Введи название трека/исполнителя/альбома/плейлиста")

    elif call.data.startswith('command'):

        if call.data == 'command1':
            bot.send_message(call.message.chat.id, "Просто отправь мне голосовое сообщение")

        elif call.data == 'command2':

            # ожидание сообщения от пользователя
            recording, searching, authorising = True, False, False
            bot.send_message(call.message.chat.id, "Отправь мне текст. Работает только с инглиш лангуаге")

        elif call.data == 'command3':

            # выбор между поиском и "мне нравится"
            global keyboard1
            bot.send_message(call.message.chat.id, "Выбери один из способов воспроизведения музыки", reply_markup=keyboard1)

        elif call.data == 'command4':
            bot.register_next_step_handler(call.message, get_text_message)


@bot.message_handler(commands=['start'])
def send_welcome(message):

    global keyboard2
    bot.send_message(message.from_user.id, 'Привет! Я Jarvis! Хочешь узнать что я могу?', reply_markup=keyboard2)


@bot.message_handler(commands=['help'])
def send_info(msg):

    global info_text, keyboard3
    bot.send_message(msg.from_user.id, info_text)
    bot.send_message(msg.from_user.id, text="Выбери одну из функций:", reply_markup=keyboard3)


@bot.message_handler(commands=['talk'])
def talk(message):
    pass


bot.polling()