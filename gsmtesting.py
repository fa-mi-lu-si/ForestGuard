from machine import Pin, ADC, UART
from time import sleep
from random import randint
from secrets import write_api_key, samy_phone_num, cait_phone_num

sim800l = UART(1, baudrate=9600, tx=Pin("GP4"), rx=Pin("GP5"))


def send_at_command(command, *, wait=1):
    sim800l.write(command + "\r\n")
    sleep(wait)  # Wait for response
    response = sim800l.read()  # Read the response
    if response:
        print(response.decode())
        return response.decode()
    else:
        print("No response from GSM")
        return None


def at(command):
    send_at_command(command)


def test_connection():
    response = send_at_command("AT")
    send_at_command("AT+CMEE=2")  # Enable verbose errors
    if response and ("OK" in response):
        print("module is properly connected.")
        return True
    else:
        print("module is not properly connected or not responding.")
        return False


def data_to_thingspeak():
    # send an http request like
    send_at_command("AT+HTTPINIT")
    send_at_command('AT+HTTPPARA="CID",1')
    send_at_command(
        # change the field and value
        f'AT+HTTPPARA="URL","https://api.thingspeak.com/update?api_key={write_api_key}&field1=0"'
    )
    send_at_command("AT+HTTPACTION=0")


def configure_apn():
    # hope this works, it kept giving us a private IP
    send_at_command('AT+SAPBR=3,1,"CONTYPE","GPRS"')
    send_at_command('AT+SAPBR=3,1,"APN","econet.net"')
    send_at_command("AT+SAPBR=1,1")
    send_at_command("AT+SAPBR=2,1")


def send_sms(number: str, text: str):
    send_at_command("AT+CMGF=1")
    send_at_command(f'AT+CMGS="{number}"')
    send_at_command(text + chr(26), wait=2)


def receive_sms():
    send_at_command("AT+CMGF=1")

    # sms_read = send_at_command('AT+CMGL="REC UNREAD"')
    sms_read = send_at_command('AT+CMGL="ALL"')
    if not sms_read:
        return None

    # fix this code to handle more than one sms being sent
    sms_read_list = list(map(str.strip, sms_read.split("\n")))
    message_content = sms_read_list[2]

    return message_content


def delete_sms():
    response = send_at_command('AT+CMGDA="DEL ALL"')
    print(response)


def sms_to_thingspeak(field, value):
    send_sms(
        samy_phone_num,
        f"https://api.thingspeak.com/update?api_key={write_api_key}&field{field}={value}",
    )


test_connection()
