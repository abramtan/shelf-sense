import os, sys

# otherwise there is ModuleNotFoundError: No module named 'schedule' when you run sudo python3 shelf-sense-bot.py
sys.path.append("/home/abc/.local/lib/python3.9/site-packages")

import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, BotCommand
from PIL import Image
import rgb_led
from camera import take_photo
from object_detection import identify_photo_objects
from dht_sensor import read_temp, read_humidity
import csv
import time, threading, schedule
from datetime import datetime

BOT_TOKEN= 'insert token here'

# notification period in seconds
temp_humidity_notif_freq = 1

# temp / humidity ranges
temp_high = 23
temp_low = 10
humidity_high = 40
humidity_low = 10

notif_sent = False
print(notif_sent)

# Items class and dictionary
class Items:
    def __init__(self, item_name=None, quantity=None, humidity=None, temperature=None):
        self.item_name = item_name
        self.quantity = quantity
        self.humidity = humidity
        self.temperature = temperature

items_dict = {} # format {box_number: Items(item_name, quantity, humidity, temperature)}

commands_dict = {  # command description used in the "help" command and for the menu button
    'start'                  : 'Get used to the bot',
    'help'                   : 'Gives you information about the available commands',
    'addbox'                 : 'Adds a box to your storage area',
    'additem'                : 'Adds an item to your storage area and connect it to a box you have added',
    'updatequantity'         : 'Update quantity of what is in the box',
    'removebox'              : 'Removes a box and its contents',
    'removeitem'             : 'Removes an item from your storage. The box remains.',
    'temp'                   : 'Get temperature',
    'humidity'               : 'Get the humidity',
    'lights_on'              : 'Turns the lights on',
    'lights_off'             : 'Turns the lights off',
    'summary'                : 'Get the summary of your storage area',
    'set_max_temp'           : 'Set the max valid temperature',
    'set_min_temp'           : 'Set the min valid temperature',
    'set_max_humidity'       : 'Set the max valid humidity',
    'set_min_humidity'       : 'Set the min valid humidity'
}

    # 'temp_humidity_notif_on' : 'Turn notifications on for when temperature and humidity exceed acceptable values',
    # 'temp_humidity_notif_off': 'Turn notifications off for when temperature and humidity exceed acceptable values'

# Define commands for menu button
commands = []
for key, value in commands_dict.items():
    commands.append(BotCommand(key, value))

bot = telebot.TeleBot(BOT_TOKEN)

# Defines suggested commands and commands in menu button
bot.set_my_commands(commands)

# get the box number
def get_box_number(input_list):
    # Create a set containing all numbers from 1 to the maximum number in the list
    all_numbers = set(range(1, 20))
    # Create a set from the input list
    input_set = set(input_list)
    # Find the missing numbers
    missing_numbers = list(all_numbers - input_set)
    return missing_numbers[0]

# Box not available error
def box_not_available(message, next_function=None):
    bot.send_message(message.chat.id, "Please choose a box from the boxes available")
    bot.register_next_step_handler(message, next_function)

# returns list of item_names
def get_item_names(items_dict):
    item_list = []
    for item in items_dict.values():
        if item.item_name != None:
            item_list.append(item.item_name)
    return item_list

# Append quantity and item to csv file
def append_csv(filename, list_of_terms):
    with open(filename, 'a+', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(list_of_terms)

# Get current date and time
def get_date_time():
    current_dateTime = datetime.now()
    current_dateTime_str = current_dateTime.strftime(f"%m/%d/%Y %H:%M:%S")
    return current_dateTime_str

@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = None
    user_name = None
    chat_user_list = []
    
    # get user_id and user_name to send messages without receiving messages from user
    chat_id = message.chat.id
    user_name = message.chat.username

    # store chat_id and user_name in csv
    with open('data/chats.csv', 'a+', newline='\n') as csvfile:
        writer = csv.writer(csvfile, delimiter=',')
        chat_user_list.append(chat_id)
        chat_user_list.append(user_name)
        writer.writerow(chat_user_list)

    # log temp and humidity every 1s
    schedule.every(1).seconds.do(temp_humidity_logging)

    # bot.reply_to(message, f'id: {chat_id}     username: {user_name}')
    bot.send_message(message.chat.id, "Howdy, how are you doing?")

# help page 
@bot.message_handler(commands=['help'])
def command_help(m):
    cid = m.chat.id
    help_text = "The following commands are available: \n"
    for key in commands_dict:  # generate help text out of the commands dictionary defined at the top
        help_text += "/" + key + ": "
        help_text += commands_dict[key] + "\n"
    bot.send_message(cid, help_text)  # send the generated help page

@bot.message_handler(commands=['add_box', 'addbox'])
def add_box(message):
    box_number = get_box_number(list(items_dict.keys())) # integer
    items_dict.update({box_number: Items()})
    print("1", items_dict)
    open(f'data/box_{box_number}.csv', 'a+', newline='')
    bot.send_message(message.chat.id, f"Box {box_number} added. You now have {len(items_dict)} box(es) in your storage. \nUse /additem to add an item to your box.")

@bot.message_handler(commands=['additem'])
def additem(message):
    if len(items_dict) == 0:
        bot.send_message(message.chat.id, "You have no boxes to store items in. Please use /addbox to add a box.")
    else:
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        for box in list(items_dict.keys()):
            markup.add(str(box))
        bot.send_message(message.chat.id, "Which box do you want to attach this item to?", reply_markup=markup)
        bot.register_next_step_handler(message, link_box)

def link_box(message):
    box_number = int(message.text)
    if box_number not in list(items_dict.keys()):
        box_not_available(message, link_box)
    else:
        bot.send_message(message.chat.id, "Box linked. Please wait while we determine what is in your container.", reply_markup=ReplyKeyboardRemove())
        photo_path, object_dict = identify_photo_objects()
        photo = Image.open(photo_path)
        detected_item_name = list(object_dict)[0]
        detected_quantity = list(object_dict.values())[0]
        bot.send_message(message.chat.id, f"We have detected {detected_quantity} {detected_item_name}")
        bot.send_photo(message.chat.id, photo)
        
        # detected_item_name = 'green'
        # detected_quantity = 8

        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        proceed_msg = f"Proceed with adding {detected_quantity} {detected_item_name} to the box."
        manual_entry_msg = f"Input the item and quantity myself"
        markup.add(proceed_msg)
        markup.add(manual_entry_msg)

        bot.send_message(message.chat.id, "Would you like to proceed with what we detected or input the item and quantity yourself?", reply_markup=markup)

        bot.register_next_step_handler(message, add_detected_item_list, box_number, detected_item_name, detected_quantity, proceed_msg, manual_entry_msg)

def add_detected_item_list(message, box_number, detected_item_name, detected_quantity, proceed_msg, manual_entry_msg):
    response = message.text
    if response == proceed_msg:
        item = Items(item_name=detected_item_name, quantity=detected_quantity)
        items_dict[box_number] = item
        append_csv(f"data/box_{box_number}.csv", [get_date_time(), detected_item_name, detected_quantity])
        print(f"type detected qty:{detected_quantity}")
        bot.send_message(message.chat.id, f" {detected_quantity} {detected_item_name} added to box {box_number}.", reply_markup=ReplyKeyboardRemove())
    
    elif response == manual_entry_msg:
        bot.send_message(message.chat.id, "Write what you want to add in the following format: quantity, item name \nFor example: 1, green onions", reply_markup=ReplyKeyboardRemove())
        bot.register_next_step_handler(message, add_custom_item, box_number)

def add_custom_item(message, box_number):
    response = message.text
    try: 
        quantity, item_name = response.split(",")
        quantity = int(quantity)
        item_name = item_name.strip()
        item = Items(item_name=item_name, quantity=quantity)
        items_dict[box_number] = item
        append_csv(f"data/box_{box_number}.csv", [get_date_time(), item_name, quantity])
        bot.send_message(message.chat.id, f"{item_name} added to box {box_number}. \nQuantity is {quantity}")
    except ValueError:
        bot.send_message(message.chat.id, "Please use the format: quantity, item name \nFor example: 1, green onions")
        bot.register_next_step_handler(message, add_custom_item, box_number)

@bot.message_handler(commands=['updatequantity'])
# Which box
def decide_box(message):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    print(list(items_dict.keys()))
    print("2", items_dict)
    for box in list(items_dict.keys()):
        markup.add(str(box))
    bot.send_message(message.chat.id, "Which box do you want to update?", reply_markup=markup)
    bot.register_next_step_handler(message, get_quantity)

def get_quantity(message):
    box_number = int(message.text)
    if box_number not in list(items_dict.keys()):
        box_not_available(message, get_quantity)
    else:
        item_in_box = items_dict[box_number].item_name
        item_quantity = items_dict[box_number].quantity
        bot.send_message(message.chat.id, f"You currently have {item_quantity} {item_in_box} in box {box_number}. Enter the updated quantity in your message.", reply_markup=ReplyKeyboardRemove())
        bot.register_next_step_handler(message, update_quantity, box_number, item_in_box)

def update_quantity(message, box_number, item_in_box):
    try:
        updated_quantity = int(message.text)
        append_csv(f"data/box_{box_number}.csv", [get_date_time(), item_in_box, updated_quantity])
        bot.send_message(message.chat.id, "Quantity updated!")
    except ValueError:
        bot.send_message(message.chat.id, "Please try again. Enter a positive integer value.")
        bot.register_next_step_handler(message, update_quantity)

@bot.message_handler(commands=['remove_item', 'removeitem'])
def remove_item(message):
    if len(items_dict) == 0:
        bot.send_message(message.chat.id, "You have no boxes in storage. Use /addbox to add a box to your storage area then add an item to the box.")
    
    elif get_item_names(items_dict) == 0:
        bot.send_message(message.chat.id, "You have no items in storage. Use /additem to add an item to a box in your storage area.")
        
    else:
        markup = ReplyKeyboardMarkup(resize_keyboard=True, input_field_placeholder="What do you want")
        for key in items_dict:
            item_name = items_dict[key].item_name
            if item_name != None:
                markup.add(f"{item_name}: in box {key}")
        bot.send_message(message.chat.id, "What item do you want to remove?", reply_markup=markup)
        bot.register_next_step_handler(message, remove_item_list)

def remove_item_list(message):
    try:
        item_to_remove = message.text.split(':')[0]
        print(item_to_remove)
        box_number = list(filter(lambda x: items_dict[x].item_name == item_to_remove, items_dict))[0]
        items_dict[box_number] = Items()
        print(items_dict)
        append_csv(f"data/box_{box_number}.csv", [get_date_time(), None, None])
        bot.send_message(message.chat.id, "Item removed", reply_markup=ReplyKeyboardRemove())
    except ValueError:
        bot.send_message(message.chat.id, "Item not in storage. Please choose another item")

@bot.message_handler(commands=['remove_box', 'removebox'])
def remove_box(message):
    if len(items_dict) == 0:
        bot.send_message(message.chat.id, "You have no boxes added. Use /addbox to add a box to your storage.")
    else:
        markup = ReplyKeyboardMarkup(resize_keyboard=True, input_field_placeholder="What do you want")
        print(f"keys of items_dict are {list(items_dict.keys())}")
        for box in list(items_dict.keys()):
            markup.add(f'{box}')
        bot.send_message(message.chat.id, "Which box do you want to remove?", reply_markup=markup)
        bot.register_next_step_handler(message, remove_box_list)

def remove_box_list(message):
    try:
        box_number = int(message.text)
        filename = f"data/box_{box_number}.csv"
        items_dict.pop(box_number)
        if os.path.exists(filename):
            os.remove(filename)
        bot.send_message(message.chat.id, "Box removed", reply_markup=ReplyKeyboardRemove())
    except ValueError:
        bot.send_message(message.chat.id, "No box available")

############################################ summmary ##################################################
@bot.message_handler(commands=['summary'])
def summary(message):
    print(items_dict)
    status_msg_list = []
    for box_number, item in items_dict.items():
        if item.item_name == None:
            status_msg = f"Box {box_number} is empty."
        else:
            status_msg = f" You have {item.quantity} {item.item_name} in box {box_number}. Temperature is {read_temp()}, humidity is {read_humidity()}."
        status_msg_list.append(status_msg)
    newline = '\n'
    if len(status_msg_list) != 0:
        bot.send_message(message.chat.id, f'{newline.join((f"{status_msg}" for status_msg in status_msg_list))}')
    else:
        bot.send_message(message.chat.id, f'Nothing to see here! Your storage area is empty. Start by using /addbox to add a box to your storage area.')

@bot.message_handler(commands=['lights_on'])
def lights_on(message):
    bot.reply_to(message, rgb_led.leds_on())

@bot.message_handler(commands=['lights_off'])
def lights_off(message):
    bot.reply_to(message, rgb_led.leds_off())

@bot.message_handler(commands=['temp'])
def get_temp(message):
    temp_text = f'The temperature is {read_temp()} celsius.'
    bot.send_message(message.chat.id, temp_text)
    return temp_text

@bot.message_handler(commands=['humidity'])
def get_humidity(message):
    humidity_text = f'The humidity is {read_humidity()}%.'
    bot.send_message(message.chat.id, humidity_text)
    return humidity_text

# temp / humidity logging and alerts
def temp_humidity_logging():
    temp_humidity_list = []
    temp = read_temp()
    humidity = read_humidity()

    # open and store in csv
    with open('data/temp_humidity.csv', 'a+', newline='\n') as csvfile:
        writer = csv.writer(csvfile, delimiter=',')
        temp_humidity_list.append(get_date_time())
        temp_humidity_list.append(temp)
        temp_humidity_list.append(humidity)
        writer.writerow(temp_humidity_list)

    # check for valid temp / humidity
    if (temp > temp_high or temp < temp_low or humidity > humidity_high or humidity < humidity_low):
        global notif_sent
        # if notif=false, send notif then set notif=true
        if notif_sent == False:
            # extract chat_ids / usernames from csv
            chat_ids = {}
            with open('data/chats.csv', 'r') as csvfile:
                csvreader = csv.reader(csvfile)
                for id, username in csvreader:
                    chat_ids.update({id: username})
            print(chat_ids)
            for id in list(chat_ids.keys()):
                bot.send_message(id, f'Temperature / humidity range exceeded! \nTemperature is {temp}C. \nHumidity is {humidity}%.')
            notif_sent = True
        print('exceeded')
    else:
        if notif_sent == True:
            # extract chat_ids / usernames from csv
            chat_ids = {}
            with open('data/chats.csv', 'r') as csvfile:
                csvreader = csv.reader(csvfile)
                for id, username in csvreader:
                    chat_ids.update({id: username})
            print(chat_ids)
            for id in list(chat_ids.keys()):
                bot.send_message(id, f'Temperature / humidity range is good! \nTemperature is {temp}C. \nHumidity is {humidity}%.')
            notif_sent = False
        print('all good')

def temp_humidity_summary(chat_id) -> None:
    temp = read_temp()
    humidity = read_humidity()

    chat_ids = {}
    with open('data/chats.csv', 'r') as csvfile:
        csvreader = csv.reader(csvfile)
        for id, username in csvreader:
            chat_ids.update({id: username})
    print(chat_ids)

    if notif_sent == False:
        for id in list(chat_ids.keys()):
            bot.send_message(id, f'Temperature / humidity range exceeded! \nTemperature is {temp}. \nHumidity is {humidity}.')
            print(f"notif_sent: {notif_sent}")
    # for past 1 hour: min, max, average
    # png graph
    # bot.send_message(chat_id, text=f't={temp}C \nh={humidity}%')

# @bot.message_handler(commands=['temp_humidity_notif_on'])
# def temp_humidity_notif_on(message):
#     # setup temp and humidity notifications
#     schedule.every(temp_humidity_notif_freq).seconds.do(temp_humidity_summary, message.chat.id).tag('temp_humidity_notif')
#     bot.send_message(message.chat.id, text='Temperature and humidity notifications are turned on.')

# @bot.message_handler(commands=['temp_humidity_notif_off'])
# def temp_humidity_notif_off(message):
#     schedule.clear('temp_humidity_notif')
#     bot.send_message(message.chat.id, text='Temperature and humidity notifications are turned off.')

# user-set ideal max temp
@bot.message_handler(commands=['set_max_temp'])
def set_max_temp(message):
    temp_text = f'Enter the maximum valid temperature in celsius:'
    bot.send_message(message.chat.id, temp_text, reply_markup=ReplyKeyboardRemove())
    bot.register_next_step_handler(message, set_max_temp_2)

def set_max_temp_2(message):
    global temp_high
    try:
        temp_high = int(message.text)
        bot.send_message(message.chat.id, f"Maximum temperature updated! It is currently set at {temp_high}C.")
    except ValueError:
        bot.send_message(message.chat.id, "Please try again. Enter an integer value.")
        bot.register_next_step_handler(message, set_max_temp)

# user-set ideal min temp
@bot.message_handler(commands=['set_min_temp'])
def set_min_temp(message):
    temp_text = f'Enter the minimum valid temperature in celsius:'
    bot.send_message(message.chat.id, temp_text, reply_markup=ReplyKeyboardRemove())
    bot.register_next_step_handler(message, set_min_temp_2)

def set_min_temp_2(message):
    global temp_low
    try:
        temp_low = int(message.text)
        bot.send_message(message.chat.id, f"Minimum temperature updated! It is currently set at {temp_low}C.")
    except ValueError:
        bot.send_message(message.chat.id, "Please try again. Enter an integer value.")
        bot.register_next_step_handler(message, set_min_temp)

# user-set ideal max humidity
@bot.message_handler(commands=['set_max_humidity'])
def set_max_humidity(message):
    humidity_text = f'Enter the maximum valid humidity in %:'
    bot.send_message(message.chat.id, humidity_text, reply_markup=ReplyKeyboardRemove())
    bot.register_next_step_handler(message, set_max_humidity_2)

def set_max_humidity_2(message):
    global humidity_high
    try:
        humidity_high = int(message.text)
        bot.send_message(message.chat.id, f"Maximum humidity updated! It is currently set at {humidity_high}%.")
    except ValueError:
        bot.send_message(message.chat.id, "Please try again. Enter an integer value.")
        bot.register_next_step_handler(message, set_max_humidity)

# user-set ideal min humidity
@bot.message_handler(commands=['set_min_humidity'])
def set_min_humidity(message):
    humidity_text = f'Enter the minimum valid humidity in %:'
    bot.send_message(message.chat.id, humidity_text, reply_markup=ReplyKeyboardRemove())
    bot.register_next_step_handler(message, set_min_humidity_2)

def set_min_humidity_2(message):
    global humidity_low
    try:
        humidity_low = int(message.text)
        bot.send_message(message.chat.id, f"Minimum humidity updated! It is currently set at {humidity_low}%.")
    except ValueError:
        bot.send_message(message.chat.id, "Please try again. Enter an integer value.")
        bot.register_next_step_handler(message, set_min_humidity)





# bot.infinity_polling()
if __name__ == '__main__':
    threading.Thread(target=bot.infinity_polling, name='bot_infinity_polling', daemon=True).start()
    while True:
        schedule.run_pending()
        time.sleep(1)
