# -*- coding: utf-8 -*-

import telebot
from telebot import types
import random
import argparse
import subprocess
import sys
import os
import pyowm
from hashlib import md5
import duel

reload(sys)
sys.setdefaultencoding('utf8')

CONFIG_LIST = "key", "command_strings", "admins", "users", "main_group_id", "weather_api"
#Weather API
global owm
parser = argparse.ArgumentParser()
parser.add_argument("--key", help="AUTH Key do telegram bot")
parser.add_argument("-v", "--verbose", action="store_true", help="Mostra mais informação na tela")
parser.add_argument("-p", "--private_only", action="store_true", help="Considera apenas mensagens enviadas em conversa privada")

args = parser.parse_args()

def checksum(file):
    check = md5()
    check.update(open(file, 'rb').read())
    return check.hexdigest()

def print_verbose(string):
	if args.verbose:
		print string.encode("utf-8")
		
def obv(msg):
    if random.randint(1,4) == 1:
        msg += ', obviamente'
    return msg + '.'
	

configs = {}
if not os.path.isfile("config.ini"):
	print "Criando config.ini inicial"
	f = open("config_template.txt")
	template_data = f.read()
	f.close()
	
	f = open("config.ini", 'w')
	f.write(template_data)
	f.close()

f = open("config.ini")
for line in f.readlines():
	line = line.strip()
	if line and (not line.startswith('#')):
		config_key = line.split('=')[0]
		config_value = line.split('=')[1].split(',')
		configs[config_key] = config_value
		if '' in configs[config_key]:
			configs[config_key].remove('')
f.close()

for entry in CONFIG_LIST:
	if entry not in configs.keys():
		configs[entry] = ['']

print_verbose("Configs: %s" % (str(configs)))

if args.key:
	configs["key"] = [args.key]

if configs["key"] == ['']:
	print "AUTH key não encontrada, por favor insira no config.ini ou por via do comando --key"
	sys.exit(1)

if configs["weather_api"] != ['']:
	owm = pyowm.OWM(configs["weather_api"][0])

def get_weather(location):
	if not location or not owm:
		return
	observation = owm.weather_at_place(location)
	w = observation.get_weather()
	l = observation.get_location()

	loc = {'name' : l.get_name(), 'country' : l.get_country()}
	
	temp_c = w.get_temperature(unit='celsius')
	temp_f = w.get_temperature(unit='fahrenheit')
	temperatures = {'C' : temp_c['temp'], 'F' : temp_f['temp']}
	
	humidity = w.get_humidity()
	weather_status = w.get_detailed_status()
	
	msg = "Tempo em %s, %s:\n" % (loc['name'], loc['country'])
	msg += "%s C / %s F\n" % (temperatures['C'], temperatures['F'])
	msg += "Umidade: %s%%\n " % (humidity)
	msg += "Condicoes: %s" % (weather_status)
	
	return msg
	
	
bot = telebot.TeleBot(configs["key"][0])

updating = False #Flag pra quando for updatear
duel_atual = None
		
@bot.message_handler(content_types=['text'])
def handle_messages(message):
	global updating, duel_atual
	
	#Provavelmente redundante por causa do bot.stop_polling(), mas só pra ter certeza
	if updating:
		return 
	
	#Pra não ficar floodando o canal enquanto estivermos testando
	if (message.chat.type != "private") and args.private_only:
		return
		
	#Guarda o user numa lista pra ser usado no comando !user
	if message.from_user.username not in configs["users"] and not message.from_user.is_bot:
		configs["users"].append(message.from_user.username)
		
	nome_grupo = 'private'
	if message.chat.type != "private":
		nome_grupo = message.chat.title
	print ('%s(%s): %s' % (message.from_user.username, nome_grupo, message.text))
		

	print_verbose("%s: %s" % (message.from_user.username, message.text))
	command = None
	texto = message.text.strip()
	for string in configs["command_strings"]:
		if message.text.startswith(string):
			command = message.text[len(string):].split()[0]
			texto = ' '.join(message.text.split()[1:])
			break
			
	print_verbose("CMD: %s: %s\n" % (command, texto))
	
	admin_rights = message.from_user.username in configs["admins"]
	
	if command == "alt":
		if ':' not in texto:
			msg = texto.strip('?')
		else:
			msg = texto.split(':')[-1].strip().strip('?')
		alternativas = msg.split(' ou ')
		if len(alternativas) > 1:
			bot.send_message(message.chat.id, obv(random.choice(alternativas).capitalize()))
	
	if ('@' + bot.get_me().username) in texto or command == "bola":
		if ("update" in texto.split()) and admin_rights:
			bot.send_message(message.chat.id, "Fazendo update!")
			subprocess.call("git pull origin master", shell = True)
			updating = True
			bot.stop_polling()
		else:
			bot.send_message(message.chat.id, obv(random.choice(("Sim", "Não"))))
	
	if command == "user" and message.chat.type != "private" and configs["users"] != ['']:
		bot.send_message(message.chat.id, '@' + obv(random.choice(configs["users"])))
	
	if (command == "w" or command == "weather") and configs["weather_api"] != ['']:
		bot.send_message(message.chat.id, get_weather(texto))
	
	#Muito cuidado usando isso, pois praticamente tem acesso infinito
	if command == "eval" and admin_rights:
		try:
			output = "Output: " + str(eval(texto))
		except Exception as erro:
			output = "Erro: " + str(erro)
			
		bot.send_message(message.chat.id, output)		
		
	if command == "duel" or command == 'd':
		if duel_atual:
			if duel_atual.handle_message(message) == "ENDGAME":
				print 'endgame'
				duel_atual = None
		else:
			if texto:
				duel_atual = duel.Duelo(bot, message, texto)
			else:
				duel_atual = duel.Duelo(bot, message)

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
	global duel_atual
	application = call.data.split(':')[0]
	if application == "DUEL" and duel_atual:
		if duel_atual.handle_message(callback_answer = call) == "ENDGAME":
			duel_atual = None

bot.skip_pending = True
print_verbose("Iniciando: %s" % sys.argv)
#if (configs["main_group_id"][0] != ['']) and not args.private_only:
	#bot.send_message(int(configs["main_group_id"][0]), "%s online! MD5 atual: %s" % (bot.get_me().username, checksum(sys.argv[0])))
bot.polling()

if updating:
	print "Atualizando..."
	subprocess.Popen(["python"] + sys.argv)
