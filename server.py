import socket
import numpy as np
import mss
import cv2
import threading
import pyautogui
# import time

HOST = '0.0.0.0'  # IP address of the server
PORT = 8000         # Port to listen on


# pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0

# Create a TCP socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Bind the socket to the IP address and port
s.bind((HOST, PORT))

# mouse = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# mouse.bind((HOST ,PORT+1))
# mouse.listen(10)
# conn2, addr2 = mouse.accept()


# Listen for incoming connections
s.listen(10)

# Accept a client connection
conn, addr = s.accept()
print(f'Connected by {addr}')

# Create a monitor instance for screen recording


def send_screen(conn):

    with mss.mss() as monitor:

        while True:
            # Capture a screenshot of the entire screen
            screenshot = monitor.grab(monitor.monitors[1])

            # Convert the screenshot to a numpy array
            img = np.array(screenshot)

            # Convert the image to JPEG format for compression
            encoded, buffer = cv2.imencode('.jpg', img)

            # Send the size of the JPEG buffer to the client
            size = len(buffer)
            conn.sendall(size.to_bytes(4, byteorder='big'))

            # Send the JPEG buffer to the client
            conn.sendall(buffer)


def receive_mouse_input(conn):
    while True:
        # receive mouse input coordinates from client
        data = conn.recv(1024).decode()
        if not data:
            break
        print(data)
        data = data.split("|")
        data = data[1]
        try:
            x, y, z = data.split(':')
            x = float(x)
            y = float(y)
            z = int(z)
            if x > 0 and x < 1920:
                if y > 0 and y < 1080:
                    pass
                    print("moved to", x, y)
                    pyautogui.moveTo(round(x), round(y))
                    if (z == 0):
                        pyautogui.mouseUp(button="left")
                        # pyautogui.mouseUp(button="right")
                    elif (z == 1):
                        # print("click")
                        pyautogui.mouseDown(button="left")
                    elif (z == 2):
                        pyautogui.click(
                            button="right", clicks=1, interval=0.25)
        except:
            print("error in coordinates")


# function to handle client connections
def handle_client(conn, addr):
    print('Client connected from {}:{}'.format(addr[0], addr[1]))

    # create threads for sending screen and receiving mouse input
    send_screen_thread = threading.Thread(target=send_screen, args=(conn,))
    receive_mouse_input_thread = threading.Thread(
        target=receive_mouse_input, args=(conn,))

    # start threads
    send_screen_thread.start()
    receive_mouse_input_thread.start()

    # wait for threads to finish
    send_screen_thread.join()
    receive_mouse_input_thread.join()

    # close connection
    conn.close()
    print('Client disconnected from {}:{}'.format(addr[0], addr[1]))


client_thread = threading.Thread(target=handle_client, args=(conn, addr))
client_thread.start()
