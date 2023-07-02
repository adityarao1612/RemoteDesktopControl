import re
import os
from pynput.mouse import Listener, Button
import socket
import cv2
import numpy as np
import threading
import time
import pyautogui


import psutil
from scapy.all import ARP, Ether, srp
import time

# define the MAC address of the device you're looking for
target_mac = "00:00:00:00:00:00"
target_mac2 = "00:00:00:00:00:00"

HOST = 'localhost'

with os.popen('arp -a') as f:
    Arp_data = f.read()
Arp_table = []
for line in re.findall('([-.0-9]+)\s+([-0-9a-f]{17})', Arp_data):
    Arp_table.append(line)
    if (target_mac2 == line[1]):
        print("target's ip address found in ARP table")
        HOST = line[0]

if (HOST == 'localhost'):
    print("Could not find in ARP table")
    # get the IP address and netmask of the WiFi interface that's currently in use
    addrs = psutil.net_if_addrs()
    # print(addrs)
    interface = [i for i in addrs if i.startswith(
        'Wi-Fi')][0]  # assuming WiFi interface
    ip_address = addrs[interface][1].address
    netmask = addrs[interface][1].netmask

    # calculate the network address from the IP address and netmask
    ip_address_bytes = [int(x) for x in ip_address.split('.')]
    netmask_bytes = [int(x) for x in netmask.split('.')]
    network_address_bytes = [ip_address_bytes[i]
                             & netmask_bytes[i] for i in range(4)]
    network_address = '.'.join([str(x) for x in network_address_bytes])

    print("network=", network_address)

    # ans, unans = srp(Ether(dst="ff:ff:ff:ff:ff:ff") /
    #                  ARP(pdst="192.168.1.0/24"), timeout=2)

    # create an ARP request packet to send to the local network
    arp = ARP(op=1, pdst=f"{network_address}/24", hwdst="ff:ff:ff:ff:ff:ff")
    ether = Ether(dst="ff:ff:ff:ff:ff:ff")
    packet = ether/arp

    # send the packet and capture the response
    result = srp(packet, timeout=5, verbose=0)[0]

    # iterate over the responses and check if any of them match the target MAC address
    for sent, received in result:
        print(received.hwsrc, received.psrc)
        if received.hwsrc == target_mac:
            print("IP address of MAC address {} is {}".format(
                target_mac, received.psrc))
            HOST = str(received.psrc)


print("server IP=", HOST)

print("proceeding to connect to server")

# HOST = '192.168.106.46'

# HOST = 'localhost'  # IP address of the server
PORT = 8000         # Port to connect to

# Create a TCP socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Connect to the server
s.connect((HOST, PORT))
print('Connected to server')


STOP_BUTTON = 0
Button_state = 0  # 0-no click 1-left click 2-right click

mouse_refresh_time = 0.075

# Function to send mouse coordinates to the server

win_x = 0
win_y = 0
win_width = 1920
win_height = 1080


def send_mouse_coords(conn):

    global STOP_BUTTON
    global Button_state
    global win_x
    global win_y
    global win_width
    global win_height

    global mouse_refresh_time
    while True:
        # Get the current mouse position
        if STOP_BUTTON:
            break

        x, y = pyautogui.position()

        try:
            msg = "|"+str((x-win_x)/(win_width/1920))+":" + \
                str((y-win_y)/(win_height/1080))+":"+str(Button_state)+"|"
            # print(msg)
        except:
            pass
        # print(msg.encode())
        s.sendall(msg.encode())
        # Wait for some time before sending the next mouse coordinates
        time.sleep(mouse_refresh_time)

# Function to receive video data from the server


def clicking(conn):
    global STOP_BUTTON
    global Button_state

    if STOP_BUTTON:
        return

    def on_click(x, y, button, pressed):
        global STOP_BUTTON
        global Button_state

        if STOP_BUTTON:
            return
        global win_x
        global win_y
        global win_width
        global win_height

        global mouse_refresh_time

        if pressed:
            # print(button == Button.left)
            print(button)
            if (button == Button.left):
                Button_state = 1
            elif (button == Button.right):
                Button_state = 2
            else:
                Button_state = 0

            try:
                msg = "|"+str((x-win_x)/(win_width/1920))+":" + \
                    str((y-win_y)/(win_height/1080))+":"+str(Button_state)+"|"
                print(msg)
            except:
                pass
            # print(msg.encode())
            s.sendall(msg.encode())
            # Wait for some time before sending the next mouse coordinates
            time.sleep(mouse_refresh_time)
        else:
            Button_state = 0
    with Listener(on_click=on_click) as listener:
        listener.join()


def receive_video_data(conn):
    # Create a buffer to hold the received video data
    global STOP_BUTTON

    global win_x
    global win_y
    global win_width
    global win_height
    cv2.namedWindow('Screen', cv2.WINDOW_NORMAL)

    win_x = cv2.getWindowImageRect("Screen")[0]
    win_y = cv2.getWindowImageRect("Screen")[1]
    win_width = cv2.getWindowImageRect("Screen")[2]
    win_height = cv2.getWindowImageRect("Screen")[3]

    buffer = b''

    while True:

        win_x = cv2.getWindowImageRect("Screen")[0]
        win_y = cv2.getWindowImageRect("Screen")[1]
        win_width = cv2.getWindowImageRect("Screen")[2]
        win_height = cv2.getWindowImageRect("Screen")[3]

        # Receive the size of the JPEG buffer from the server
        size_bytes = conn.recv(4)
        if not size_bytes:
            break
        size = int.from_bytes(size_bytes, byteorder='big')
        print(size)
        # Receive the JPEG buffer from the server
        while len(buffer) < size:
            data = conn.recv(min(1024, size - len(buffer)))
            if not data:
                break
            buffer += data

        # Convert the JPEG buffer to a numpy array
        img = cv2.imdecode(np.frombuffer(
            buffer, dtype=np.uint8), cv2.IMREAD_COLOR)

        # Display the image
        cv2.imshow('Screen', img)
        # cv2.waitKey(1)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            STOP_BUTTON = 1
            break

        # Reset the buffer for the next image
        buffer = b''


# Create threads for sending mouse coordinates and receiving video data
send_mouse_coords_thread = threading.Thread(
    target=send_mouse_coords, args=(s,))
receive_video_data_thread = threading.Thread(
    target=receive_video_data, args=(s,))
detect_mouse_click_thread = threading.Thread(
    target=clicking, args=(s,))

# Start threads
send_mouse_coords_thread.start()
receive_video_data_thread.start()
detect_mouse_click_thread.start()

# Wait for threads to finish
send_mouse_coords_thread.join()
receive_video_data_thread.join()
detect_mouse_click_thread.join()
# Close the socket


s.close()
