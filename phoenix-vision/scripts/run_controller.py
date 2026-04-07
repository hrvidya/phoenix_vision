import telnetlib, time

HOST, PORT = "localhost", 5400
tn = telnetlib.Telnet(HOST, PORT)

def send(cmd):
    tn.write(f"{cmd}\n".encode())

# Engage autopilot for demo
send("set /autopilot/heading-bug/bug-deg 180")
send("set /autopilot/heading-hold 1")
send("set /autopilot/altitude/altitude-ft 3000")
send("set /autopilot/altitude-hold 1")
print("✅ Autopilot engaged to heading 180, altitude 3000ft")
