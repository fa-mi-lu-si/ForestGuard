# Conservation Area Intelligence Technology
# Monitoring Undisturbed Natural Areas
# Forest Advanced Monitoring Instrument

from machine import Pin, ADC, UART
from utime import sleep, time
from secrets import write_api_key, samy_phone_num, cait_phone_num

led = Pin("LED", Pin.OUT)

green_led = Pin("GP17", Pin.OUT)
orange_led = Pin("GP18", Pin.OUT)
blue_led = Pin("GP16", Pin.OUT)

sensor_button = Pin("GP0", Pin.IN)
buzzer = Pin("GP1", Pin.OUT)

pir = Pin("GP2", Pin.IN)
buzzer = Pin("GP19", Pin.OUT)
mq2 = ADC(26)

sim800l = UART(1, baudrate=9600, tx=Pin("GP4"), rx=Pin("GP5"))

last_sms_time = 0

human_present = False
last_motion_time = 0

mq2_R0 = 2.567148
mq2_voltage = 0
mq2_ppm = 0
last_gas_time = 0

smoke_present = False

V_IN = 5.0  # the voltage going into the mq2
COEF_A0 = 100.0
COEF_A1 = -1.513
CALIBRATION_CONSTANT = 5.0

calibration_seconds = 60
# calibration_seconds = 60 * 60 * 8


def convert_voltage(voltage):
    # ATD conversion
    return float(voltage) * (V_IN / 65535)


def read_rs(voltage):
    return (V_IN - voltage) / voltage


def read_ppm(Rs, R0):
    return COEF_A0 * (Rs / R0) ** COEF_A1


def calibrate_gas_sensor():

    # Rotating the knob clockwise increases sensitivity and counterclockwise decreases it.

    print("Calibrating sensor...")

    global mq2_R0
    mq2_Rs_sum = 0.0

    for i in range(1, calibration_seconds):
        mq2_voltage = mq2.read_u16()

        mq2_Rs_sum += read_rs(convert_voltage(mq2_voltage))

        print(f"i = {i}")
        print(f"MQ2 Voltage : {mq2_voltage}")
        print(f"Current R0 : {mq2_Rs_sum / i / CALIBRATION_CONSTANT}")

        sleep(1)

    mq2_R0 = mq2_Rs_sum / calibration_seconds / CALIBRATION_CONSTANT

    print("IT WORKED !!!!")
    print(f"Final R0 : {mq2_R0}")


def gas_measure():
    # sets the global mq2_ppm to the correct value
    global mq2_ppm
    global last_gas_time
    try:
        mq2_voltage = mq2.read_u16()
        mq2_ppm = read_ppm(read_rs(convert_voltage(mq2_voltage)), mq2_R0)
        last_gas_time = time()
    except:
        print("Failed to read gas sensor...")


def send_at_command(command, *, wait=3):
    sim800l.write(command + "\r\n")
    # sleep(2)  # Wait for response
    sleep(wait)  # Wait for response
    response = sim800l.read()  # Read the response
    if response:
        print(response.decode())
        return response.decode()
    else:
        print("No response from GSM")
        return None


def test_connection():
    response = send_at_command("AT")
    if response and ("OK" in response):
        print("module is properly connected.")
        send_at_command("AT+CMEE=2")  # Enable verbose errors
        return True
    else:
        print("module is not properly connected or not responding.")
        return False


def send_sms(number: str, text: str):
    send_at_command("AT+CMGF=1")
    send_at_command(f'AT+CMGS="{number}"')
    send_at_command(text + chr(26), wait=2)


def sms_to_thingspeak(field, value):
    global last_sms_time
    last_sms_time = time()
    print("sending to thingspeak")
    send_sms(
        samy_phone_num,
        f"https://api.thingspeak.com/update?api_key={write_api_key}&field{field}={value}",
    )


def receive_sms():
    send_at_command("AT+CMGF=1")

    sms_read = send_at_command('AT+CMGL="REC UNREAD"', wait=10)
    # sms_read = send_at_command('AT+CMGL="ALL"', wait=10)
    if not sms_read:
        return

    # fix this code to handle more than one sms being sent
    message_content = list(map(str.strip, sms_read.split("\n")))

    return message_content


def process_sms(sms_data: list[str]):

    messages = []
    for line_index in range(len(sms_data)):
        if "+CMGL:" in sms_data[line_index]:
            cmgl = sms_data[line_index].split(",")
            message_body = sms_data[line_index + 1]
            sender_number = cmgl[2].replace('"', "")
            messages.append((sender_number, message_body))
    return messages


def main():
    global last_gas_time
    global last_motion_time
    global last_sms_time
    global human_present
    global smoke_present

    last_gas_time = time()
    last_motion_time = time()
    last_sms_time = time()

    while True:
        # Check the gas levels every seven seconds
        if (time() - last_gas_time) > 7:
            print("measuring gas")
            gas_measure()
            if mq2_ppm > 200:
                if not smoke_present:
                    send_sms(cait_phone_num, "The smoke was detected")
                smoke_present = True
            else:
                smoke_present = False

        # Monitor for movement with the PIR
        if (time() - last_motion_time) > 30:
            human_present = False
            last_motion_time = time()

        human_present = human_present or (pir.value() == 1)

        if (time() - last_sms_time) > 30:
            led.value(1)
            print("sending to thingspeak")
            sms_to_thingspeak(1, mq2_ppm)
            print(mq2_ppm)

            sms_to_thingspeak(2, "1" if human_present else "0")

            sms_data = receive_sms()
            print(sms_data)
            if sms_data:
                sms_data = process_sms(sms_data)
                print(sms_data)
                for item in sms_data:

                    # Program the SMS commands
                    if "BUZZER" in item[1]:
                        buzzer.on()
                        sleep(10)
                        buzzer.off()

            led.value(0)

        orange_led.value(mq2_ppm > 200)
        green_led.value(pir.value())

        sleep(0.1)


main()
