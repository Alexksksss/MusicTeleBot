import re
from collections import Counter
from datetime import datetime
import pymorphy2
import lyricsgenius
import matplotlib
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import telebot
import config
import os

# import asyncio

matplotlib.use('agg')
bot = telebot.TeleBot(config.TELEGRAM_TOKEN)
timeString = datetime.now().strftime('%Y%m%d_%H%M%S')


def write_to_file(flag, artist_name=None, number_of_songs=None, artist=None, file_name=None):
    if flag == 'artist':
        with open(artist_name + '-lyrics-' + '(' + str(number_of_songs) + ')-' + timeString + '.txt', 'w',
                  encoding='utf-8') as f:
            for song in artist.songs:
                f.write(song.lyrics)
                f.write('\n')

        with open(artist_name + '-lyrics-' + '(' + str(number_of_songs) + ')-' + timeString + '.txt', 'r',
                  encoding='utf-8') as f:
            contents = f.read()

    elif flag == 'file':
        with open(file_name, 'r', encoding='utf-8') as f:
            contents = f.read()

    return contents


def cleansing(text_lines):
    unique_lines = []

    for line in text_lines:
        if 'Lyrics' not in line:
            unique_lines.append(line)
            unique_lines.append('\n')
    text = ''.join(unique_lines)
    text = text.replace('Embed', ' ').replace(' ', '\n').lower()
    text = text.replace('куплет', ' ').replace('припев', ' ').replace('аутро', ' ').replace('интро', ' ').replace(
        'бридж', ' ')
    text = re.findall('[А-Яа-яёЁ]+', text)
    return text


def normalizing(morph, text):
    normalized_words = []
    for word in text:
        if len(word) > 2:
            p = morph.parse(word)[0]
            if 'NOUN' in str(p.tag):
                result = morph.parse(word)[0].normal_form
                normalized_words.append(result)
    return normalized_words


def cloud(text):
    wordcloud = WordCloud(width=800, height=800,
                          background_color='white',
                          min_font_size=10).generate(text)

    # отображаем облако слов на графике
    plt.figure(figsize=(8, 8), facecolor=None)
    plt.imshow(wordcloud)
    plt.axis("off")
    plt.tight_layout(pad=0)
    return plt


def delete_file(file_name):
    if os.path.exists(file_name):
        os.remove(file_name)
        print(f"Файл {file_name} успешно удален.")
    else:
        print(f"Файл {file_name} не существует.")


# Приветственное
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message,
                 f'Привет, {message.from_user.first_name}!\n'
                 'Я - бот, который создает облако слов для песен любимого исполнителя с сайта genius.com '
                 'или из Вашего файла.\n'
                 'Чтобы я проанализировал песни исполнителя, введите /artist.\n'
                 'Чтобы я проанализировал ваш файл, введите /file')


@bot.message_handler(commands=['artist'])
def send_for_artist(message):
    bot.reply_to(message, 'Чтобы начать, отправь мне имя исполнителя и желаемое количество песен в формате:'
                          ' \'исполнитель:количество песен\'.')
    bot.message_handler(func=lambda message: True)


@bot.message_handler(commands=['file'])
def send_for_file(message):
    bot.reply_to(message, 'Чтобы начать, отправь мне файл в формате *.txt')
    bot.message_handler(content_types=['document'])


@bot.message_handler(content_types=['document'])
def generate_wordcloud_file(message):
    file_name = message.document.file_name

    if not file_name.lower().endswith('.txt'):
        bot.reply_to(message, "Пожалуйста, отправьте файл в формате .txt")
        return

    file_info = bot.get_file(message.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    with open(file_name, 'wb') as f:
        f.write(downloaded_file)
    bot.reply_to(message, "Скачиваю файл... Ожидайте")
    contents = write_to_file(flag='file', file_name=file_name)

    if not contents:
        bot.reply_to(message, 'Файл - пустой')
        return

    f = open(file_name, 'r', encoding='utf-8')
    text_lines = f.read().splitlines()
    f.close()

    text = cleansing(text_lines)
    morph = pymorphy2.MorphAnalyzer()
    normalized_words = normalizing(morph, text)
    sorted_words = Counter(normalized_words).most_common()

    file_name = file_name[:-4]

    with open(file_name + '-RESULT' + '.txt', 'w', encoding='utf-8') as f:
        for word in sorted_words:
            f.write(str(word).replace('(\'', '').replace('\', ', ' - ').replace(')', ''))
            f.write('\n')

    with open(file_name + '-RESULT' + '.txt', 'r', encoding='utf-8') as f:
        text = f.read()

    if not text:
        bot.reply_to(message, 'Вы отправили файл, не содержащий слов на русском. '
                              'Данный бот умеет работать только со словами, написанными на русском языке. '
                              'Повторите попытку')
        delete_file(file_name + '.txt')
        delete_file(file_name + '-RESULT' + '.txt')

        return

    # создаем объект WordCloud с заданными параметрами
    pict = cloud(text)

    # сохраняем график в файл
    pict.savefig(file_name + '-RESULT', dpi=300)

    photo = open(file_name + '-RESULT' + '.png', 'rb')

    # Отправляем фото пользователю
    bot.send_photo(message.chat.id, photo)
    photo.close()

    # Пример вызова функции для удаления файла 'example.txt'
    delete_file(file_name + '-RESULT' + '.png')
    delete_file(file_name + '.txt')
    delete_file(file_name + '-RESULT' + '.txt')

    print("Готово!")


# Основной код (получение данных от пользователя, парсинг песен, очистка, создание изображения и отправка пользователю)
@bot.message_handler(func=lambda message: True)
def generate_wordcloud_artist(message):
    # Ввод информации
    input_text = message.text.lower().split(':')
    if len(input_text) != 2 or '' in input_text:  # проверка на неправильный ввод
        bot.reply_to(message,
                     "Некорректный формат ввода. "
                     "Пожалуйста, отправьте сообщение в формате: 'исполнитель:количество песен'.")
        return
    artist_name, number_of_songs_str = input_text

    try:
        number_of_songs = int(number_of_songs_str)
    except ValueError:
        bot.reply_to(message, "Некорректный формат ввода количества песен.")
        return
    bot.reply_to(message, "Принято в работу! Ожидайте.")

    # Поиск артиста
    morph = pymorphy2.MorphAnalyzer()
    genius = lyricsgenius.Genius(config.GENIUS_TOKEN, timeout=10, sleep_time=0)
    artist = genius.search_artist(artist_name, include_features=False, max_songs=number_of_songs)

    if ' '.join(str(artist).split()[:-2])[:-1] == '':
        bot.reply_to(message,
                     "Исполнитель не найден. "
                     "Пожалуйста, проверьте правильность написания его имени и повторите попытку.")
        return

    bot.reply_to(message,
                 f"Произведен поиск и анализ {number_of_songs} песен  исполнителя "
                 f"'{' '.join(str(artist).split()[:-2])[:-1]}'")

    # Запись в файл

    contents = write_to_file(flag='artist', artist_name=artist_name, number_of_songs=number_of_songs, artist=artist)

    if not contents:
        bot.reply_to(message, 'У этого исполнителя нет песен')
        delete_file(artist_name + '-lyrics-' + '(' + str(number_of_songs) + ')-' + timeString + '.txt')
        return

    f = open(artist_name + '-lyrics-' + '(' + str(number_of_songs) + ')-' + timeString + '.txt', 'r',
             encoding='utf-8')
    text_lines = f.read().splitlines()
    f.close()

    text = cleansing(text_lines)

    normalized_words = normalizing(morph, text)

    sorted_words = Counter(normalized_words).most_common()

    with open(artist_name + '-RESULT-' + '(' + str(number_of_songs) + ')-' + timeString + '.txt', 'w',
              encoding='utf-8') as f:
        for word in sorted_words:
            f.write(str(word).replace('(\'', '').replace('\', ', ' - ').replace(')', '').replace('деньга', 'деньги'))
            f.write('\n')

    # читаем файл с частотностью слов
    with open(artist_name + '-RESULT-' + '(' + str(number_of_songs) + ')-' + timeString + '.txt', 'r',
              encoding='utf-8') as f:
        text = f.read()

    if not text:
        bot.reply_to(message, 'У этого исполнителя нет на русском')
        delete_file(artist_name + '-lyrics-' + '(' + str(number_of_songs) + ')-' + timeString + '.txt')
        delete_file(artist_name + '-RESULT-' + '(' + str(number_of_songs) + ')-' + timeString + '.txt')
        return

    # создаем объект WordCloud с заданными параметрами
    pict = cloud(text)

    # сохраняем график в файл
    pict.savefig(artist_name + '-RESULT-' + '(' + str(number_of_songs) + ')-' + timeString, dpi=300)

    photo = open(artist_name + '-RESULT-' + '(' + str(number_of_songs) + ')-' + timeString + '.png', 'rb')

    # Отправляем фото пользователю
    bot.send_photo(message.chat.id, photo)
    photo.close()

    print("Готово!")

    delete_file(artist_name + '-RESULT-' + '(' + str(number_of_songs) + ')-' + timeString + '.png')
    delete_file(artist_name + '-RESULT-' + '(' + str(number_of_songs) + ')-' + timeString + '.txt')
    delete_file(artist_name + '-lyrics-' + '(' + str(number_of_songs) + ')-' + timeString + '.txt')


if __name__ == '__main__':
    bot.infinity_polling()

# import nltk # библиотека для стоп слов
# nltk.download('stopwords')
# import nltk
# from nltk.corpus import stopwords
#
# stops = set(stopwords.words('russian'))
# print(stops)


# Варианты ошибок:
# 1) Неправильный ввод по шаблону исполнитель:количество песен
# 2) Ввод количества песен не числовым значением
# 3) Не нашелся такой исполнитель
# 4) Нет песен у этого исполнителя
