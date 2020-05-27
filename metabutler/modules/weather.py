import requests
from telegram import ParseMode
from telegram.ext import run_async
from metabutler import dispatcher, LOGGER
from metabutler.modules.disable import DisableAbleCommandHandler

@run_async
def weather(update, context):
	chat_id = update.effective_chat.id
	msg_id = update.effective_message.message_id
	args = update.message.text.split()
	if len(args) < 2:
		context.bot.sendMessage(chat_id, text = "You need to give me a city to get weather of", reply_to_message_id = msg_id)
	else:
		city = args[1]
		url = "https://api.openweathermap.org/data/2.5/weather?q=" + city + "&appid=2f370427a4e24ed13e0fe6cabbefe5f3&units=metric"
		response = requests.get(url).json()
		if response['cod'] == '404':
			context.bot.sendMessage(chat_id, text = "That city does not exist", reply_to_message_id = msg_id)
			return
		else:
			description = response['weather'][0]['description'].capitalize()
			temp = response['main']['temp']
			feels_like = response['main']['feels_like']
			temp_min = response['main']['temp_min']
			temp_max = response['main']['temp_max']
			try:
				pressure = response['main']['pressure']
			except Exception:
				pressure = None
			try:
				sea_level = response['main']['sea_level']
			except Exception:
				sea_level = None
			try:
				humidity = response['main']['humidity']
			except Exception:
				humidity = None
			try:
				grnd_level = response['main']['grnd_level']
			except Exception:
				grnd_level = None
			try:
				wind_speed = response['wind']['speed']
			except Exception:
				None
			try:
				wind_deg = response['wind']['deg']
			except Exception:
				wind_deg = None
			msg = "<b>Weather - </b> {0}\n".format(description)
			msg += "<b>Temperature - </b> {0}°C actually, but feels like {1}°C\n".format(temp, feels_like)
			msg += "<b>Minimum Temperature - </b> {0}°C\n".format(temp_min)
			msg += "<b>Maximum Temperature - </b> {0}°C\n".format(temp_max)
			if pressure is not None:
				msg += "<b>Pressure - </b> {0} hPa\n".format(pressure)
			if humidity is not None:
				msg += "<b>Humidity - </b> {0} %%\n".format(humidity)
			if wind_speed is not None:
				msg += "<b>Wind Speed - </b> {0} m/s\n".format(wind_speed)
			if wind_deg is not None:
				msg += "<b>Wind Direction - </b> {0}°".format(wind_deg)
			context.bot.sendMessage(chat_id, msg, parse_mode='HTML', reply_to_message_id=msg_id)
			
WEATHER_HANDLER = DisableAbleCommandHandler("weather", weather)
dispatcher.add_handler(WEATHER_HANDLER)
