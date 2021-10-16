import telebot as tb
import uuid
import os
import speech_recognition as sr
from telebot import types
from pydub import AudioSegment
import pyttsx3
import pprint

from config import *


bot = tb.TeleBot(TOKEN)
r = sr.Recognizer()                              # для обработки аудио
AudioSegment.converter = absolute_path_to_ffmpeg # необходимая строка, т.к. мы изменили путь к ffmpeg
speak_engine = pyttsx3.init("sapi5")             # для "генерации" аудио
voices = speak_engine.getProperty('voices')      # массив голосов. Необходимо при условии установленного RHVoice, увеличивающий количество допустимых голосов

# клавиатура для выбора голоса озвучивания
keyboard1 = types.InlineKeyboardMarkup()
for i in range(len(voices)): # используем цикл чтобы избежать ошибки индексации
    key_v = types.InlineKeyboardButton(text=i, callback_data=f'voice{i}')
    keyboard1.add(key_v)
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
keyboard3.add(key_a_to_t, key_t_to_a, key_music, key_talk)

recording = False

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

    global recording
    if recording:

        global speak_engine

        recording = False
        file_path = "record.wav"
        file_path1 = "record.ogg"
        # преобразуем message в речь и сохраняем
        print(message.text)
        speak_engine.save_to_file(message.text, "record.wav")
        speak_engine.runAndWait()
        speak_engine.stop()
        # отправляем результат
        result = open(file_path, 'rb')
        bot.send_audio(message.from_user.id, result)
        result.close()
        # os.remove(file_path)

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

    elif call.data.startswith('command'):

        if call.data == 'command1':
            bot.send_message(call.message.chat.id, "Просто отправь мне голосовое сообщение")

        elif call.data == 'command2':

            global keyboard1
            bot.send_message(call.message.chat.id, "Выбери голос для озвучивания:", reply_markup=keyboard1)

        elif call.data == 'command3':
            pass

        elif call.data == 'command4':
            bot.register_next_step_handler(call.message, get_text_message)

    elif call.data.startswith('voice'):
        # выбираем необходимый голос
        global speak_engine
        speak_engine.setProperty('voice', 'ru')
        speak_engine.setProperty('voice', voices[int(str(call.data)[5:])].id)
        speak_engine.setProperty('rate', 110)
        # ожидание сообщения от пользователя
        global recording
        recording = True
        bot.send_message(call.message.chat.id, "Отправь мне текст")


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