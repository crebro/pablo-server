from lib_nrf24 import NRF24
import RPi.GPIO as GPIO
import spidev
import time

GPIO.setmode(GPIO.BCM)

CEPIN = 0
CSNPIN = 5

radio = NRF24(GPIO, spidev.SpiDev())

pipes = [[0xE0, 0xE0, 0xF1, 0xF1, 0xE0], [0xF1, 0xF1, 0xF0, 0xF0, 0xE0]]
radio.begin(CEPIN, CSNPIN)

radio.setPayloadSize(32)

radio.setChannel(0x77)
radio.setDataRate(NRF24.BR_1MBPS)
radio.setPALevel(NRF24.PA_MIN)


radio.setAutoAck(False)
radio.enableDynamicPayloads()
radio.enableAckPayload()

radio.openWritingPipe(pipes[0])


message = "Hello, World!"
while len(message) < 32:
    message = message + " "


while True:
    start = time.Time()
    radio.write(message)
    print("Sent the message: {}".format(message))
