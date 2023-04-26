import re
import pymorphy2
import lyricsgenius
from collections import Counter
from datetime import datetime
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import telebot
import config
import matplotlib

matplotlib.use('agg')
bot = telebot.TeleBot(config.TELEGRAM_TOKEN)
timeString = datetime.now().strftime('%Y%m%d_%H%M%S')


# Приветственное
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message,
                 "Привет! Я бот, который создает облако слов для песен любимого исполнителя. "
                 "Чтобы начать, отправь мне имя исполнителя и желаемое количество песен в формате:"
                 " 'исполнитель:количество песен'.")


# Основной код (получение данных от пользователя, парсинг песен, очистка, создание изображения и отправка пользователю)
@bot.message_handler(func=lambda message: True)
def generate_wordcloud(message):
    # Ввод информации
    input_text = message.text.lower().split(':')
    if len(input_text) != 2 or '' in input_text:
        bot.reply_to(message,
                     "Некорректный формат ввода. "
                     "Пожалуйста, отправьте сообщение в формате: 'исполнитель:количество песен'.")
        return
    artist_CONSTANT, number_of_songs_str = input_text
    try:
        number_of_songs = int(number_of_songs_str)
    except ValueError:
        bot.reply_to(message, "Некорректный формат ввода количества песен.")
        return

    # Поиск артиста
    morph = pymorphy2.MorphAnalyzer()
    genius = lyricsgenius.Genius(config.GENIUS_TOKEN, timeout=20, sleep_time=0)
    #try:
    artist = genius.search_artist(artist_CONSTANT, include_features=False, max_songs=number_of_songs)
    # except lyricsgenius.exceptions.ArtistNotFoundException:  # обработать
    #     bot.reply_to(message,
    #                  "Исполнитель не найден. "
    #                  "Пожалуйста, проверьте правильность написания его имени и повторите попытку.")
    #     return
    # except Exception as e:
    #     print(f'An error occurred: {e}')

    bot.reply_to(message,
                 f"Произведен поиск и анализ {number_of_songs} песен  исполнителя "
                 f"'{' '.join(str(artist).split()[:-2])[:-1]}'")

    # Запись в файл

    with open(artist_CONSTANT + '-lyrics-' + '(' + str(number_of_songs) + ')-' + timeString + '.txt', 'w',
              encoding='utf-8') as f:
        for song in artist.songs:
            f.write(song.lyrics)
            f.write('\n')
        f.close()

    with open(artist_CONSTANT + '-lyrics-' + '(' + str(number_of_songs) + ')-' + timeString + '.txt', 'r',
              encoding='utf-8') as file:
        contents = file.read()

    if not contents:
        bot.reply_to(message, 'У этого исполнителя нет песен')
        return

    f = open(artist_CONSTANT + '-lyrics-' + '(' + str(number_of_songs) + ')-' + timeString + '.txt', 'r',
             encoding='utf-8')
    textLines = f.read().splitlines()

    uniqueLines = []

    for line in textLines:
        if 'Lyrics' not in line:
            uniqueLines.append(line)
            uniqueLines.append('\n')

    # Очистка

    text = ''.join(uniqueLines)
    text = text.replace('Embed', ' ').replace(' ', '\n').lower()
    text = text.replace('куплет', ' ').replace('припев', ' ').replace('аутро', ' ').replace('интро', ' ').replace(
        'бридж', ' ')
    text = re.findall('[А-Яа-яёЁ]+', text)

    normalizedWords = []
    for word in text:
        if len(word) > 2:
            p = morph.parse(word)[0]
            if 'NOUN' in str(p.tag):
                result = morph.parse(word)[0].normal_form
                normalizedWords.append(result)

    sortedWords = Counter(normalizedWords).most_common()

    with open(artist_CONSTANT + '-RESULT-' + '(' + str(number_of_songs) + ')-' + timeString + '.txt', 'w',
              encoding='utf-8') as f:
        for word in sortedWords:
            f.write(str(word).replace('(\'', '').replace('\', ', ' - ').replace(')', '').replace('деньга', 'деньги'))
            f.write('\n')

    # читаем файл с частотностью слов
    with open(artist_CONSTANT + '-RESULT-' + '(' + str(number_of_songs) + ')-' + timeString + '.txt', 'r',
              encoding='utf-8') as f:
        text = f.read()

    # создаем объект WordCloud с заданными параметрами
    wordcloud = WordCloud(width=800, height=800,
                          background_color='white',
                          min_font_size=10).generate(text)

    # отображаем облако слов на графике
    plt.figure(figsize=(8, 8), facecolor=None)
    plt.imshow(wordcloud)
    plt.axis("off")
    plt.tight_layout(pad=0)

    # сохраняем график в файл
    plt.savefig(artist_CONSTANT + '-RESULT-' + '(' + str(number_of_songs) + ')-' + timeString, dpi=300)

    photo = open(artist_CONSTANT + '-RESULT-' + '(' + str(number_of_songs) + ')-' + timeString + '.png', 'rb')

    # Отправляем фото пользователю
    bot.send_photo(message.chat.id, photo)
    photo.close()

    print("Готово!")


bot.infinity_polling()

# import nltk # библиотека для стоп слов
# nltk.download('stopwords')
# import nltk
# from nltk.corpus import stopwords
#
# stops = set(stopwords.words('russian'))
# print(stops)
