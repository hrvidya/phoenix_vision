import socket
import struct
import time

# Set the IP and port where FlightGear is listening
FG_IP = "127.0.0.1"  # Localhost
FG_PORT = 5501       # This must match the input port in your FlightGear command

# Create the socket to send data
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
def send_controls(aileron, elevator, rudder, throttle):
    # Pack four float values to send as bytes
    data = struct.pack('ffff', aileron, elevator, rudder, throttle)
    sock.sendto(data, (FG_IP, FG_PORT))
# Loop to fly straight for a few seconds
for _ in range(500):
    send_controls(0.0, 0.0, 0.0, 0.6)  # Fly straight with 60% throttle
    time.sleep(0.05)  # 50 milliseconds pause (20 times per second)
# Create a socket to receive data from FG
recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
recv_sock.bind(("127.0.0.1", 5502))  # Output port set in FG command

# Receive and print flight data
while True:
    data, _ = recv_sock.recvfrom(1024)  # read UDP message
    altitude, airspeed, pitch, roll = struct.unpack('ffff', data[:16])
    print(f"Altitude: {altitude:.1f} ft | Speed: {airspeed:.1f} kt | Pitch: {pitch:.1f}° | Roll: {roll:.1f}°")
altitude, airspeed, pitch, roll = receive_data()

if altitude < 1000:
    throttle = 1.0  # full power
else:
    throttle = 0.5  # cruise

send_controls(0.0, 0.0, 0.0, throttle)
