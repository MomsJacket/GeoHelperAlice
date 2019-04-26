from flask import Flask, request
import logging
import json
import requests
import math
import random

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)

"""
ID фотографий городов
"""
cities = {
    'москва': ['1540737/f076faa645822964a32a', '965417/7993a0c3795d3eeea03a', '213044/db87432185d35a7b2a91'],
    'санкт-петербург': ['213044/0ced5f317bc68a756e02', '1652229/bc0bd8fd8f0103f0d4c4', '1652229/f9f51efb7c3d7efa7429'],
    'челябинск': ['965417/b743dc4efe85d130e3a5', '1540737/ce46f3ac1e8abf9b6507', '965417/28854153e55e19f2dc4a'],
    'екатеринбург': ['1652229/2731e79080957ce6a59d', '1652229/1f9980c4b193bfaf98c0', '1030494/05b71e4263a56b38c44c'],
    'казань': ['1652229/4ff53b0908be48cf294c', '1540737/a0365c3208fe06337181', '965417/f54c1ea8e4ed0e35aa1d'],
    'новосибирск': ['1533899/872b38372d39f5f113d9', '1652229/078dc55dd47c588adbb6', '1540737/210e9262d8c18b9119b7']
}

sessionStorage = {}
api_key = "dda3ddba-c9ea-4ead-9010-f43fbc15c6e3"


@app.route('/post', methods=['POST'])
def main():
    logging.info('Request: %r', request.json)
    response = {
        'session': request.json['session'],
        'version': request.json['version'],
        'response': {
            'end_session': False
        }
    }
    handle_dialog(response, request.json)
    logging.info('Response: %r', response)
    return json.dumps(response)


def handle_dialog(res, req):
    user_id = req['session']['user_id']
    if req['session']['new']:
        '''
        Приветствие 
        '''
        res['response']['text'] = random.choice(['Привет! Назови своё имя!',
                                                 'Здравствуйте, назовите своё имя.'])
        sessionStorage[user_id] = {
            'first_name': None,  # здесь будет храниться имя
            'started': False,  # здесь информация о том, что пользователь начал игру. По умолчанию False
            'stage': 'hello',  # здесь хранится информация о стадии диалога
            'city': None,
            'address': '',  # здесь хранится город пользователя
            'points': [],  # здесь хранятся места на карте
            'cords': []  # здесь хранятся координаты города и адреса
        }
        res['response']['buttons'] = [
            {
                'title': 'Помощь',
                'hide': False
            }
        ]
        return

    if sessionStorage[user_id]['stage'] == 'hello':
        '''
        Этап диалога, в котором пользователь говорил свое имя.
        Пока пользователь не введет корректное имя
        '''
        if 'помощь' != req['request']['nlu']['tokens'][0]:
            first_name = get_first_name(req)
            if first_name is None:
                res['response']['text'] = 'Не расслышала имя. Повтори, пожалуйста!'
            else:
                sessionStorage[user_id]['first_name'] = first_name
                res['response']['text'] = f'Приятно познакомиться, {first_name.title()}. Я Алиса,' \
                    f' могу помочь найти нужное тебе место! \n' \
                    f'Для начала напишите город, в котором сейчас находитесь.'
                res['response']['buttons'] = [
                    {
                        'title': 'Помощь',
                        'hide': False
                    }
                ]
                sessionStorage[user_id]['stage'] = 'asking city'
        else:
            res['response']['text'] = get_help(sessionStorage[user_id]['stage'])

    elif sessionStorage[user_id]['stage'] == 'asking city':
        '''
        Этап диалога, где Алиса узнает город пользователя. 
        Если у города предусмотрена фотография, формат ответа изменяется
        '''
        if 'помощь' == req['request']['nlu']['tokens'][0]:
            res['response']['text'] = get_help(sessionStorage[user_id]['stage'])
            res['response']['buttons'] = [
                {
                    'title': 'Москва',
                    'hide': True
                },
                {
                    'title': 'Санкт-Петербург',
                    'hide': True
                },
                {
                    'title': 'Екатеринбург',
                    'hide': True
                },
                {
                    'title': 'Челябинск',
                    'hide': True
                },
                {
                    'title': 'Казань',
                    'hide': True
                },
                {
                    'title': 'Новосибирск',
                    'hide': True
                }
            ]
        else:
            city = get_city(req)
            if city is None:
                res['response']['text'] = 'Не могу найти город с таким названием'
            else:
                if city.lower() == 'челябинск' or \
                        city.lower() == 'москва' or \
                        city.lower() == 'санкт-петербург' or \
                        city.lower() == 'казань' or \
                        city.lower() == 'екатеринбург' or \
                        city.lower() == 'новосибирск':
                    sessionStorage[user_id]['city'] = city
                    coords = get_cords(city)
                    coords = [float(i) for i in coords.split(',')]
                    sessionStorage[user_id]['cords'] = coords
                    res['response']['card'] = {}
                    res['response']['card']['type'] = 'BigImage'
                    res['response']['card']['title'] = f'{sessionStorage[user_id]["first_name"].title()},' \
                        f' чтобы найти ' \
                        f'нужное место напишите ключевое слово "Найди" \n Например: ' \
                        f'Найди аптеку. Больше команд в разделе "Помощь"'
                    res['response']['card']['image_id'] = cities[city][random.randint(0, 2)]
                    res['response']['text'] = 'Хорошо'
                    res['response']['buttons'] = [
                        {
                            'title': 'Помощь',
                            'hide': True
                        }
                    ]
                else:
                    sessionStorage[user_id]['city'] = city
                    coords = get_cords(city)
                    coords = [float(i) for i in coords.split(',')]
                    sessionStorage[user_id]['cords'] = coords
                    res['response'][
                        'text'] = f'Отлично, {sessionStorage[user_id]["first_name"].title()}.' \
                        f' Теперь ты можешь найти нужное тебе место! \n ' \
                        f'Поиск будет проводиться от центра города \n ' \
                        f'Если ты хочешь уточнить адрес то обратись в меню "Помощь" ниже'
                    res['response']['buttons'] = [
                        {
                            'title': 'Помощь',
                            'hide': False
                        }
                    ]
                sessionStorage[user_id]['stage'] = 'find place'
    elif sessionStorage[user_id]['stage'] == 'find place':
        '''
        Основной этап диалога. 
        Пользователь может найти место, поменять город и добавить адрес.
        Общение с алисой происходит путем написания ключевых слов
        '''
        if 'помощь' == req['request']['nlu']['tokens'][0]:
            res['response']['text'] = get_help(sessionStorage[user_id]['stage'])
        elif len(req['request']['nlu']['tokens']) >= 2 and 'добавь' == req['request']['nlu']['tokens'][0] and 'адрес' \
                == req['request']['nlu']['tokens'][1]:
            address = ' '.join(req['request']['nlu']['tokens'][2:])
            if address:
                geocoder_request = "http://geocode-maps.yandex.ru/1.x/?geocode={}" \
                                   "&format=json".format(sessionStorage[user_id]['city'] + ', ' + address)
                response = requests.get(geocoder_request)
                if response:
                    json_response = response.json()
                    toponym = json_response["response"]["GeoObjectCollection"]["featureMember"][0]["GeoObject"]
                    kind = toponym['metaDataProperty']['GeocoderMetaData']['kind']
                    coords = [float(i) for i in toponym["Point"]["pos"].split()]
                    if kind == 'house':
                        if sessionStorage[user_id]['address']:
                            sessionStorage[user_id]['address'] = address
                            sessionStorage[user_id]['cords'] = coords
                            res['response']['text'] = "Адрес успешно изменен"
                        else:
                            sessionStorage[user_id]['address'] = address
                            sessionStorage[user_id]['cords'] = coords
                            res['response']['text'] = "Адрес успешно добавлен"
                    else:
                        res['response']['text'] = random.choice(["Мне не удалось найти дом по этому адресу. "
                                                                 "\n Попробуйте еще раз.", "Дома по такому "
                                                                                           "адресу не существует.",
                                                                 "Я не смогла найти дом по данному адресу."])
            else:
                res['response']['text'] = "Вы не ввели адрес"
        elif 'найди' == req['request']['nlu']['tokens'][0]:
            '''
            При вводе ключевого слово найди Алиса выдает 5 самых ближайших к
            точке организации по запросу после ключевого слова
            '''
            if len(req['request']['nlu']['tokens']) > 1:
                sessionStorage[user_id]['points'] = []
                cords = get_cords(sessionStorage[user_id]['city'] + ', ' + sessionStorage[user_id]['address'])
                search = "https://search-maps.yandex.ru/v1/"
                search_params = {
                    "apikey": api_key,
                    "text": ' '.join(req['request']['nlu']['tokens'][1:]),
                    "lang": "ru_RU",
                    "type": "biz",
                    "ll": cords
                }
                response = requests.get(search, params=search_params)
                if not response:
                    res['response']['text'] = "Мне не удалось найти ни одной организации"
                else:
                    json_response = response.json()
                    organizations = get_best_five(json_response["features"], user_id)
                    count = 1
                    text = ''
                    points = []
                    for i in organizations:
                        address = i['properties']['CompanyMetaData']['address']
                        cords = i['geometry']['coordinates']
                        points.append(','.join([str(i) for i in cords]))
                        name = i['properties']['CompanyMetaData']['name']
                        text += str(count) + '. ' + 'Название: ' + name + '\n' + 'Адрес: ' + address + '\n'
                        count += 1
                        sessionStorage[user_id]['points'].append(i)
                    if text:
                        if len(text) > 1000:
                            text = text[:1000] + '...'
                        res['response']['text'] = text
                        res['response']['buttons'] = [
                            {
                                'title': 'Показать на карте',
                                'hide': True,
                                'url': get_url(points)
                            },
                            {
                                'title': 'Подробнее',
                                'hide': True
                            }
                        ]
                    else:
                        res['response']['text'] = "К сожалению я ничего не нашла"
            else:
                res['response']['text'] = "Вы не ввели название места"
        elif req["request"]["original_utterance"].lower() == 'показать на карте':
            '''
            Показывает на карте найденные места
            '''
            res['response']['text'] = "Надеюсь я помогла найти нужное вам место"
            res['response']['buttons'] = [
                {
                    'title': 'Подробнее',
                    'hide': True
                }
            ]
        elif req["request"]["original_utterance"].lower() == 'подробнее':
            '''
            Введя номер организации, выдается о ней подробная информация
            '''
            sessionStorage[user_id]['stage'] = 'info'
            count = len(sessionStorage[user_id]['points'])
            buttons = []
            for i in range(count):
                buttons.append({'title': str(i + 1), 'hide': True})
            buttons.append({'title': 'Назад', 'hide': True})
            res['response']['buttons'] = buttons
            res['response']['text'] = f'{sessionStorage[user_id]["first_name"].title()}, для получения ' \
                f'подробной информации об организации напишите ее номер из таблицы'
        elif req["request"]["original_utterance"].lower() == 'поменяй город':
            sessionStorage[user_id]['stage'] = 'asking city'
            res['response']['text'] = "Напиши название города"
            res['response']['buttons'] = [{'title': 'Помощь', 'hide': False}]
        else:
            res['response']['text'] = "Я вас не поняла. Можете пожалуйста повторить?"
            res['response']['buttons'] = [
                {
                    'title': 'Помощь',
                    'hide': False
                }
            ]

    elif sessionStorage[user_id]['stage'] == 'info':
        '''
        Этап диалога, который активируется при вводе "Подробнее" на этапе поиска
        Чтобы выйти из этого режима необходимо написать "Назад"
        '''
        if req["request"]["original_utterance"].lower() == 'назад':
            res['response']['text'] = "Вы вернулись к прежнему функционалу :D"
            res['response']['buttons'] = [{'title': 'Помощь', 'hide': False}]
            sessionStorage[user_id]['stage'] = 'find place'

        elif len(req['request']['nlu']['tokens']) > 1:
            res['response']['text'] = "Вы неправильно ввели номер"
            buttons = []
            count = len(sessionStorage[user_id]['points'])
            for i in range(count):
                buttons.append({'title': str(i + 1), 'hide': True})
            buttons.append({'title': 'Назад', 'hide': True})
            res['response']['buttons'] = buttons
        else:
            n = req["request"]["original_utterance"]
            if n.isdigit():
                if int(n) > len(sessionStorage[user_id]['points']) or int(n) < 1:
                    res['response']['text'] = "Вы неправильно ввели номер"
                    buttons = []
                    count = len(sessionStorage[user_id]['points'])
                    for i in range(count):
                        buttons.append({'title': str(i + 1), 'hide': True})
                    buttons.append({'title': 'Назад', 'hide': True})
                    res['response']['buttons'] = buttons
                else:
                    organization = sessionStorage[user_id]['points'][int(n) - 1]
                    try:
                        cords1 = organization['geometry']['coordinates']
                        cords2 = sessionStorage[user_id]['cords']
                        distance = get_distance(cords1, cords2)
                    except:
                        distance = 0.00
                    try:
                        telephones = [i['formatted'] for i in organization['properties']["CompanyMetaData"]["Phones"]]
                    except:
                        telephones = ['Отсутствует']
                    try:
                        hours = organization['properties']["CompanyMetaData"]["Hours"]['text']
                    except:
                        hours = "Неизвестны"
                    try:
                        site = organization['properties']['CompanyMetaData']['url']
                    except:
                        site = "Отсутствует"
                    buttons = []
                    count = len(sessionStorage[user_id]['points'])
                    for i in range(count):
                        buttons.append({'title': str(i + 1), 'hide': True})
                    buttons.append({'title': 'Назад', 'hide': True})
                    res['response']['buttons'] = buttons
                    res['response']['text'] = "Часы работы: " + hours + '\n' + "Телефон(ы): " + \
                                              ', '.join(telephones) + "\n" + "Сайт: " + site + \
                                              "\n" + "До организации: " + str('{:.2f}'.format(distance)) + "км."
            else:
                res['response']['text'] = "Вы неправильно ввели номер"
                buttons = []
                count = len(sessionStorage[user_id]['points'])
                for i in range(count):
                    buttons.append({'title': str(i + 1), 'hide': True})
                buttons.append({'title': 'Назад', 'hide': True})
                res['response']['buttons'] = buttons
    else:
        '''
        Если Алиса не нашла ни одной команды
        '''
        res['response']['text'] = "Можете повторить?"
        buttons = []
        count = len(sessionStorage[user_id]['points'])
        for i in range(count):
            buttons.append({'title': str(i + 1), 'hide': True})
        buttons.append({'title': 'Назад', 'hide': True})
        res['response']['buttons'] = buttons


def get_city(req):
    """
    Функция для определение, является ли
    введеный текст названием города
    :param req: ответ пользователя
    :return: город или нет
    """
    for entity in req['request']['nlu']['entities']:
        if entity['type'] == 'YANDEX.GEO':
            # возвращаем None, если не нашли сущности с типом YANDEX.GEO
            return entity['value'].get('city', None)


def get_first_name(req):
    # перебираем сущности
    for entity in req['request']['nlu']['entities']:
        # находим сущность с типом 'YANDEX.FIO'
        if entity['type'] == 'YANDEX.FIO':
            # Если есть сущность с ключом 'first_name', то возвращаем её значение.
            # Во всех остальных случаях возвращаем None.
            return entity['value'].get('first_name', None)


def get_help(stage):
    """
    Функция необходима для написания пользователю
    подсказок, необходимых на некотором этапе диалога
    :param stage: этап диалога
    :return: текстовый ответ с необходимой инфой
    """
    if stage == 'hello':
        return "Напишите свое имя в тексте сообщения \n Если я не могу найти так и не могу " \
               "найти твое имя, то приношу извинения, я исправлюсь в следующий раз! \n" \
               " Также можешь придумать себе любое имя :)"
    elif stage == 'asking city':
        return "Напиши город, в котором сейчас находишся. \n " \
               "Город должен быть в России, иначе ничего не получится \n" \
               " Я предложила тебе несколько вариантов популярных городов!"
    elif stage == 'find place':
        return "Для поиска необходимо сказать мне ключевое слово: Найди (место) \n " \
               " Например: Найди аптеку, Найди Пятерочку \n " \
               "Для поиска организаций рядом с твоим домом напиши свой адрес Алисе в" \
               " таком формате: Добавь адрес (адрес) \n" \
               "Например: Добавь адрес Ленина, 64 \n " \
               "В адресе должен быть обязательно указан дом \n" \
               "Для смены города напишите: Поменяй город"


def get_cords(place):
    """
    Функция для определение координат по адресу или названию
    :param place: название места для поискового запроса
    :return: координаты этого места
    """
    geocoder_request = "http://geocode-maps.yandex.ru/1.x/?geocode={}&format=json".format(place)
    try:
        response = requests.get(geocoder_request)
        if response:
            json_response = response.json()
            toponym = json_response["response"]["GeoObjectCollection"]["featureMember"][0]["GeoObject"]
            toponym_coodrinates = toponym["Point"]["pos"]
            cords = ','.join(toponym_coodrinates.split())
        else:
            return None
    except:
        return None
    return cords


def get_url(points):
    """
    :param points: координаты точке на карте
    :return: запрос, ответом которого является изобрадение карты
    с введеными точками
    """
    url = 'https://static-maps.yandex.ru/1.x/?l=map&pt='
    count = 1
    for i in points:
        url += i + ',pm2lbl' + str(count) + '~'
        count += 1
    url = url.rstrip('~')
    # Если точка одна, то увеличивает зону показа
    if len(points) == 1:
        url += "&spn=0.013,0.013"
    return url


def get_distance(p1, p2):
    """
    Функция для определения расстояния между точками
    :param p1: Координаты певрого места
    :param p2: Координаты второго места
    :return: Расстояние в километрах
    """
    radius = 6373.0

    lon1 = math.radians(p1[0])
    lat1 = math.radians(p1[1])
    lon2 = math.radians(p2[0])
    lat2 = math.radians(p2[1])

    d_lon = lon2 - lon1
    d_lat = lat2 - lat1

    a = math.sin(d_lat / 2) ** 2 + math.cos(lat1) * \
        math.cos(lat2) * math.sin(d_lon / 2) ** 2
    c = 2 * math.atan2(a ** 0.5, (1 - a) ** 0.5)

    distance = radius * c
    return distance


def get_best_five(organizations, user_id):
    """
    :param organizations: список организаций
    :param user_id: id пользователя
    :return: 5 ближайших организаций
    """
    check = []
    orgs = []
    for i in range(len(organizations)):
        distance = get_distance(sessionStorage[user_id]['cords'],
                                [float(i) for i in organizations[i]['geometry']['coordinates']])
        check.append([i, distance])
    check = sorted(check, key=lambda x: x[1])
    for i in check:
        orgs.append(organizations[i[0]])
    return orgs[:5]


if __name__ == '__main__':
    app.run()
