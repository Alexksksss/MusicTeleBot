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
import asyncio

matplotlib.use('agg')
bot = telebot.TeleBot(config.TELEGRAM_TOKEN)
timeString = datetime.now().strftime('%Y%m%d_%H%M%S')


def write_to_file(artist_name, number_of_songs, artist):
    with open(artist_name + '-lyrics-' + '(' + str(number_of_songs) + ')-' + timeString + '.txt', 'w',
              encoding='utf-8') as f:
        for song in artist.songs:
            f.write(song.lyrics)
            f.write('\n')
        f.close()

    with open(artist_name + '-lyrics-' + '(' + str(number_of_songs) + ')-' + timeString + '.txt', 'r',
              encoding='utf-8') as file:
        contents = file.read()
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


# Приветственное
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message,
                 f'Привет, {message.from_user.first_name}'
                 '! Я - бот, который создает облако слов для песен любимого исполнителя. '
                 'Чтобы начать, отправь мне имя исполнителя и желаемое количество песен в формате:'
                 ' \'исполнитель:количество песен\'.')


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
    genius = lyricsgenius.Genius(config.GENIUS_TOKEN, timeout=5, sleep_time=0)
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

    contents = write_to_file(artist_name, number_of_songs, artist)

    if not contents:
        bot.reply_to(message, 'У этого исполнителя нет песен')
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

    # создаем объект WordCloud с заданными параметрами
    pict = cloud(text)

    # сохраняем график в файл
    pict.savefig(artist_name + '-RESULT-' + '(' + str(number_of_songs) + ')-' + timeString, dpi=300)

    photo = open(artist_name + '-RESULT-' + '(' + str(number_of_songs) + ')-' + timeString + '.png', 'rb')

    # Отправляем фото пользователю
    bot.send_photo(message.chat.id, photo)
    photo.close()

    print("Готово!")


async def handle_messages(messages):
    for message in messages:
        await bot.process_message(message)


async def polling():
    while True:
        try:
            await bot.polling(none_stop=True)
        except Exception as e:
            print(f"Error occurred while polling: {e}")
            await asyncio.sleep(5)  # Wait for 5 seconds before retrying


if __name__ == '__main__':
    loop = asyncio.new_event_loop()  # Создает новый цикл событий asyncio и сохраняет его в переменную loop.
    # Цикл событий отвечает за выполнение асинхронных операций и обработку событий в асинхронном коде.
    asyncio.set_event_loop(loop)  # Устанавливает созданный цикл событий в качестве текущего цикла.
    # Это гарантирует, что все асинхронные операции будут выполняться в этом цикле.
    loop.create_task(polling())  # Создает задачу для выполнения функции polling().
    # Задача представляет собой асинхронную операцию, которая будет запущена и выполняться в цикле событий.
    loop.run_until_complete(handle_messages(bot.get_updates()))  # Запускает выполнение функции
    # handle_messages(bot.get_updates()) в цикле событий и блокирует основной поток выполнения до завершения функции.
    # Это позволяет обрабатывать входящие сообщения бота и выполнять другие асинхронные операции в течение работы бота.

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
# 3) Не нашелся такой исполнитель(Лобода)
# 4) Нет песен у этого исполнителя

#  добавить файлы. Человек пишет /start. Потом выбирает файл или артист. Если выбран артист - вызывается функция
