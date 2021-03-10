# -*- coding: utf-8 -*-

# В очередной спешке, проверив приложение с прогнозом погоды, вы выбежали
# навстречу ревью вашего кода, которое ожидало вас в офисе.
# И тут же день стал хуже - вместо обещанной облачности вас встретил ливень.

# Вы промокли, настроение было испорчено, и на ревью вы уже пришли не в духе.
# В итоге такого сокрушительного дня вы решили написать свою программу для прогноза погоды
# из источника, которому вы доверяете.

# Для этого вам нужно:

# Создать модуль-движок с классом WeatherMaker, необходимым для получения и формирования предсказаний.
# В нём должен быть метод, получающий прогноз с выбранного вами сайта (парсинг + re) за некоторый диапазон дат,
# а затем, получив данные, сформировать их в словарь {погода: Облачная, температура: 10, дата:datetime...}

# Добавить класс ImageMaker.
# Снабдить его методом рисования открытки
# (использовать OpenCV, в качестве заготовки брать /probe.jpg):
#   С текстом, состоящим из полученных данных (пригодится cv2.putText)
#   С изображением, соответствующим типу погоды
# (хранятся в /weather_img ,но можно нарисовать/добавить свои)
#   В качестве фона добавить градиент цвета, отражающего тип погоды
# Солнечно - от желтого к белому
# Дождь - от синего к белому
# Снег - от голубого к белому
# Облачно - от серого к белому

# Добавить класс DatabaseUpdater с методами:
#   Получающим данные из базы данных за указанный диапазон дат.
#   Сохраняющим прогнозы в базу данных (использовать peewee)

# Сделать программу с консольным интерфейсом, постаравшись все выполняемые действия вынести в отдельные функции.
# Среди действий, доступных пользователю, должны быть:
#   Добавление прогнозов за диапазон дат в базу данных
#   Получение прогнозов за диапазон дат из базы
#   Создание открыток из полученных прогнозов
#   Выведение полученных прогнозов на консоль
# При старте консольная утилита должна загружать прогнозы за прошедшую неделю.


import datetime
import os
import sys
import webbrowser
from settings import SECRET
from lxml import html
from requests import get
import cv2 as cv
import numpy as np
from re import findall
from os import path
from PIL import ImageDraw, ImageFont, Image
from peewee import SqliteDatabase, Model, ForeignKeyField, DateField, CharField, FloatField
from multiprocessing import Pool, cpu_count

DB = SqliteDatabase('weather.db')


def wait_key():
    print('Press any key to continue...')
    result = None

    if os.name != 'posix':
        import msvcrt
        result = msvcrt.getch()
    else:
        import termios
        fd = sys.stdin.fileno()

        oldterm = termios.tcgetattr(fd)
        newattr = termios.tcgetattr(fd)
        newattr[3] = newattr[3] & ~termios.ICANON & ~termios.ECHO
        termios.tcsetattr(fd, termios.TCSANOW, newattr)

        try:
            result = sys.stdin.read(1)
        except IOError:
            pass
        finally:
            termios.tcsetattr(fd, termios.TCSAFLUSH, oldterm)

    return result


class WeatherMaker:

    def __init__(self, url, days, city):
        self.city = city
        self.url = url
        self.days = days
        self.weather_data = []
        self.date_parameters = self.init_date()

    @staticmethod
    def init_date():
        current_date = datetime.datetime.now()
        current_year = current_date.year
        current_month = current_date.month
        return {
            'year': current_year,
            'month': current_month,
            'current_index': -1
        }

    def get_data(self):
        request_data = get(self.url)
        html_tree = html.document_fromstring(request_data.content)
        forecast_days_list = html_tree.xpath("//h3[@class='tab-day']/time/@datetime")
        forecast_days_list = forecast_days_list[:self.days]
        cloudiness = html_tree.xpath("//div[@class='tab-icon']/img/@title")
        temperature = html_tree.xpath("//div[@class='tab-temp']/span[1]/@data-value")
        temperature = [str(round(float(new_item))) for new_item in temperature]

        for index, forecast in enumerate(forecast_days_list):
            self.date_parameters['current_index'] = index
            self.weather_data.append({
                'city': self.city,
                'date': str(forecast),
                'cloudiness': str(cloudiness[index]).strip(),
                'temperature': int(temperature[index])
            })

    @staticmethod
    def get_past_week_weather():
        pass


class ImageMaker:

    def __init__(self, weather_data):
        self.weather = weather_data
        self.weather_img = ''

    def put_text(self, img):
        font_path = './fonts/Inter-Light.ttf'
        font = ImageFont.truetype(font_path, 24, encoding='unic')
        pil_img = Image.fromarray(img)
        draw_text = ImageDraw.Draw(pil_img)
        text = f'{self.weather["date"]}'
        text += '\n' + self.weather['cloudiness'] + "\nTemperature: " + str(self.weather['temperature']) + u'\u2103'
        draw_text.text((30, 100), text=text, font=font, fill=(0, 0, 0, 0))

        img = np.array(pil_img)

        return img

    @staticmethod
    def fill_gradient(img, gradient_color='cloud'):

        def change_color(color_number, increment):
            if color_number >= 255:
                return 255
            else:
                return color_number + increment

        img_width = img.shape[1]
        color = {
            'cloud': [183, 183, 183, 0],
            'sun': [255, 255, 150, 0],
            'rain': [200, 200, 255, 0],
            'snow': [150, 255, 255, 0]
        }
        for x in range(img_width):

            local_color = [
                change_color(color[gradient_color][0], int((255 - color[gradient_color][0]) / img_width * x)),
                change_color(color[gradient_color][1], int((255 - color[gradient_color][1]) / img_width * x)),
                change_color(color[gradient_color][2], int((255 - color[gradient_color][2]) / img_width * x))
            ]
            cv.line(
                img,
                (x, 0),
                (x, img.shape[0]),
                local_color,
                1)

    def get_weather_gradient(self):
        cloudiness = self.weather['cloudiness'].lower()
        gradient = ''
        if findall(r'snow', cloudiness):
            gradient = 'snow'
        elif findall(r'cloudy', cloudiness) or findall(r'overcast', cloudiness):
            gradient = 'cloud'
        elif findall(r'sunny', cloudiness):
            gradient = 'sun'
        elif findall(r'rain', cloudiness):
            gradient = 'rain'
        self.weather_img = './weather_img/' + '_'.join(cloudiness.split(' ')) + '.png'
        return gradient

    def create_picture(self):
        bgr_card = cv.imread('./probe.jpg')
        weather_gradient = self.get_weather_gradient()
        bgr_card = cv.cvtColor(bgr_card, cv.COLOR_BGR2RGBA)

        self.fill_gradient(bgr_card, weather_gradient)

        if path.isfile(self.weather_img):
            card_img = cv.imread(self.weather_img, cv.IMREAD_UNCHANGED)
        else:
            card_img = np.zeros((96, 96, 4), dtype='uint8')

        card_img_height, card_img_width = card_img.shape[:2]
        bgr_card_height, bgr_card_width = bgr_card.shape[:2]

        for x, row in enumerate(card_img):
            for y, column in enumerate(row):
                if column[3] > 0:
                    bgr_card[x, bgr_card_width - card_img_width + y] = column

        bgr_card = cv.cvtColor(bgr_card, cv.COLOR_RGBA2BGRA)

        date = datetime.datetime.strptime(self.weather['date'], '%d %B %Y').strftime('%Y_%m_%d')
        cv.imwrite(f'./weather/{date}.jpg', bgr_card)
        bgr_card = cv.imread(f'./weather/{date}.jpg')

        bgr_card = self.put_text(bgr_card)
        cv.imwrite(f'./weather/{date}.jpg', bgr_card)


class BaseTable(Model):

    class Meta:
        database = DB


class Location(BaseTable):

    city_name = CharField()
    city_code = CharField()
    city_lat = CharField()
    city_lon = CharField()

    class Meta:
        table_name = 'Location'


class Forecast(BaseTable):

    city = ForeignKeyField(Location)
    date = DateField()
    cloudiness = CharField()
    temperature = FloatField()

    class Meta:
        table_name = 'Forecast'


class DatabaseUpdater:
    DB.create_tables([Location, Forecast])

    def __init__(self):
        self.database = DB

    def update_db(self, data):
        self.check_for_existing_fields(data)
        with self.database.atomic():
            Forecast.insert_many(data).execute()

    def check_for_existing_fields(self, data):
        city = data[0]['city']
        date_interval = [forecast_date['date'] for forecast_date in data]
        with self.database.atomic():
            existing_records = Forecast.delete().where(
                (Forecast.city_id == (Location.select(Location.city_name).where(Location.city_name == city))) &
                (Forecast.date.in_(date_interval))
            )
            existing_records.execute()


class Interface:

    def __init__(self):
        self.possible_actions = {
            'Add forecast on selected interval': self.add_forecast,
            'Give forecast on selected interval': self.get_forecast,
            'Make weather forecast cards': self.make_cards,
            'Print out forecast data': self.print_out,
            'Exit': False
        }
        self.CITIES = Location.select()
        self.forecast_from_db = {}

    @staticmethod
    def add_location_data():
        DatabaseUpdater()
        city_name = input('Enter city name: ')
        city_code = input('Enter city code: ')
        city_lat = input('Enter city latitude: ')
        city_lon = input('Enter city longitude: ')
        Location.get_or_create(
            city_name=city_name,
            city_code=city_code,
            city_lat=city_lat,
            city_lon=city_lon
        )

    def choose_city(self, header=''):

        os.system('cls||clear')

        if header:
            print(header)
        print('Pick up city from list below:')
        for index, location in enumerate(self.CITIES):
            print(f'{index + 1}) {location.city_name}')

        chosen_city = input()

        if chosen_city.isalpha() or 1 > int(chosen_city) or int(chosen_city) > len(self.CITIES):
            return self.CITIES[0]
        else:
            return self.CITIES[int(chosen_city) - 1]

    @staticmethod
    def no_forecast_data_err():
        print('\n\u001b[96mThere is no forecast data. You should retrieved it before [2]\u001b[0m')
        wait_key()

    def add_forecast(self):

        chosen_city = self.choose_city('You choice is add forecast to database')

        os.system('cls||clear')
        print('Now you should select days forecast from 1 to 6 (optional, 6 days by default)')
        days_interval = input('Enter days quantity: ')
        if days_interval == '' or days_interval.isalpha():
            days_interval = 6
        else:
            days_interval = int(days_interval)
        weather = WeatherMaker(f'https://www.metoffice.gov.uk/weather/forecast/{chosen_city.city_code}', days_interval, chosen_city.city_name)
        weather.get_data()
        db = DatabaseUpdater()
        db.update_db(weather.weather_data)

        print('\nForecast added to data base\n')
        wait_key()

    def get_forecast(self):

        self.forecast_from_db = {'city_name': '', 'days': []}  # initialize data template
        chosen_city = self.choose_city('You choice is retrieve data from database')
        date_interval = Forecast.select(Forecast.date).distinct().where(Forecast.city_id == chosen_city.city_name)
        begin_interval = datetime.datetime.strftime(date_interval[0].date, '%d %B %Y')
        end_interval = datetime.datetime.strftime(date_interval[-1].date, '%d %B %Y')
        print(f'Select date between \u001b[3m\u001b[1m{begin_interval}\u001b[0m and \u001b[3m\u001b[1m{end_interval}\u001b[0m')

        begin_date = input('Begin date (dd/mm/yyyy): ')
        end_date = input('End date (dd/mm/yyyy):')

        begin_date = datetime.datetime.strptime(begin_date, '%d/%m/%Y').strftime('%Y-%m-%d')
        end_date = datetime.datetime.strptime(end_date, '%d/%m/%Y').strftime('%Y-%m-%d')
        request_forecast = Forecast.select().where(
            (Forecast.date.between(begin_date, end_date)) &
            (Forecast.city_id == chosen_city.city_name))
        self.forecast_from_db['city_name'] = chosen_city.city_name
        for day in request_forecast:
            self.forecast_from_db['days'].append({
                'date': datetime.datetime.strftime(day.date, '%d %B %Y'),
                'cloudiness': day.cloudiness,
                'temperature': day.temperature
            })
        print("\nCompleted\n")
        wait_key()

    def make_cards(self):

        if not self.forecast_from_db:
            self.no_forecast_data_err()
            return None
        for day in self.forecast_from_db['days']:
            day_pic = ImageMaker(day)
            day_pic.create_picture()
        print('\nCards created\n')
        answer = input('Would you like to open containing folder (y/n)?')
        if answer.lower() == 'y':
            dir_path = os.path.abspath('./weather/')
            webbrowser.open('file:///' + dir_path)
        wait_key()

    def print_out(self):

        if not self.forecast_from_db:
            self.no_forecast_data_err()
            return None
        os.system('cls||clear')
        print(f'Forecast for {self.forecast_from_db["city_name"]}')
        print('-' * 60)
        print(f'{"Date":^20}|{"Cloudiness":^25} | {"Temperature":^}')
        print('-' * 60)
        for day in self.forecast_from_db['days']:
            print(f'{day["date"]:20}| {day["cloudiness"]:25}| {day["temperature"]}')
        print('=' * 60)

        wait_key()

    @staticmethod
    def day_response(day_url):
        response = get(day_url).json()
        forecast_data = response['forecast']['forecastday'][0]
        return forecast_data

    def show_weather_before(self):

        chosen_city = self.choose_city()
        url = "http://api.weatherapi.com/v1/history.json?key=%key%&q=%lat%,%lon%&dt=%date%"
        url = url.replace('%lat%', chosen_city.city_lat).replace('%lon%', chosen_city.city_lon).replace('%key%', SECRET)

        os.system('cls||clear')
        print(f'Weather on previous week in {chosen_city.city_name.upper()}')
        day_count = 7
        url_list = []
        while day_count > 0:
            previous_day = datetime.datetime.now() - datetime.timedelta(day_count)
            day_count -= 1
            url_list.append(url.replace('%date%', previous_day.strftime('%Y-%m-%d')))
        with Pool(processes=cpu_count()) as pool:
            results = pool.map(self.day_response, url_list)

        results.sort(key=lambda val: val['date'])
        print('-' * 60)
        print(f'{"Date":^20}|{"Cloudiness":^25} | {"Temperature":^}')
        print('-' * 60)
        for day in results:
            formatted_date = datetime.datetime.strptime(day["date"], '%Y-%m-%d').strftime("%d %B %Y")
            print(f'{formatted_date:20}| {day["hour"][12]["condition"]["text"]:25}| {day["hour"][12]["temp_c"]}')
        print('=' * 60)
        print()
        wait_key()

    def run(self):

        # load past 7 days weather data
        self.show_weather_before()

        WeatherMaker.get_past_week_weather()

        err_msg = '\u001b[91;2mWrong input. You should enter the number between 1-5\u001b[0m'

        while True:
            os.system('cls||clear')
            for index, name in enumerate(self.possible_actions, 1):
                print(f'{index} - {name}')

            user_choice = input('Enter your choice: ')

            if user_choice.isdigit():
                user_choice = int(user_choice) - 1
                if 0 <= user_choice < len(self.possible_actions):
                    keys_list = tuple(self.possible_actions.keys())
                    function = self.possible_actions[keys_list[user_choice]]
                    if function:
                        function()
                    else:
                        break
                else:
                    print(err_msg)
            else:
                print(err_msg)


if __name__ == '__main__':
    starter = Interface()
    starter.run()
