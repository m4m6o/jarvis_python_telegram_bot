from yandex_music import Client


client = Client()

type_to_name = {
    'track': 'трек',
    'artist': 'исполнитель',
    'album': 'альбом',
    'playlist': 'плейлист',
}


def search(query):
    search_result = client.search(query)

    text = [f'Результаты по запросу "{query}":', '']

    best_result_text = ''
    if search_result.best:
        type_ = search_result.best.type
        best = search_result.best.result

        text.append(f'❗️Лучший результат: {type_to_name.get(type_)}')

        if type_ == 'track':
            artists = ''
            if best.artists:
                artists = ' - ' + ', '.join(artist.name for artist in best.artists)
            best_result_text = best.title + artists
        elif type_ == 'artist':
            best_result_text = best.name
        elif type_ == 'album':
            best_result_text = best.title
        elif type_ == 'playlist':
            best_result_text = best.title

        text.append(f'Содержимое лучшего результата: {best_result_text}\n')

    text.append('')
    return '\n'.join(text)


if __name__ == '__main__':
    while True:
        input_query = input('Введите поисковой запрос: ')
        print(search(input_query))