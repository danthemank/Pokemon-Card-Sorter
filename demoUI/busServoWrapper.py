import os

if False:
    if os.name == 'nt':
        import msvcrt
        def getch():
            return msvcrt.getch().decode()
            
    else:
        import sys, tty, termios
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        def getch():
            try:
                tty.setraw(sys.stdin.fileno())
                ch = sys.stdin.read(1)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            return ch

from scservosdk import *                    # Uses SCServo SDK library

# Control table address
ADDR_SCS_TORQUE_ENABLE     = 40
ADDR_SCS_GOAL_ACC          = 41
ADDR_SCS_GOAL_POSITION     = 42
ADDR_SCS_GOAL_SPEED        = 46
ADDR_SCS_PRESENT_POSITION  = 56

# Default setting
SCS_ID                      = 1                 # SCServo ID : 1
BAUDRATE                    = 115200            # Driver board default baudrate : 115200
DEVICENAME                  = '/dev/ttyUSB0'    # Check which port is being used on your controller
                                                # ex) Windows: "COM1"   Linux: "/dev/ttyUSB0" Mac: "/dev/tty.usbserial-*"

SCS_MOVING_STATUS_THRESHOLD = 20          # SCServo moving status threshold
SCS_MOVING_SPEED            = 3096           # SCServo moving speed
SCS_MOVING_ACC              = 0           # SCServo moving acc
protocol_end                = 0           # SCServo bit end(STS/SMS=0, SCS=1)

index = 0

class busServoWrapper():
    def __init__(self):
        pass

    def __del__(self):
        pass

    def __enter__(self):
        # Initialize any resources here

        self.initialize()

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # Clean up resources here
        self.close()

    def initialize(self):
        # Initialize PortHandler instance
        # Set the port path
        # Get methods and members of PortHandlerLinux or PortHandlerWindows
        self.portHandler = PortHandler(DEVICENAME)

        # Initialize PacketHandler instance
        # Get methods and members of Protocol
        self.packetHandler = PacketHandler(protocol_end)

        # Open port
        if self.portHandler.openPort():
            print("Succeeded to open the port")
        else:
            raise Exception("Failed to open the serial port for the bus serial servo")
        
        # Set port baudrate
        if self.portHandler.setBaudRate(BAUDRATE):
            print("Succeeded to change the baudrate")
        else:
            raise Exception("Failed to change the baudrate")


        print('testing servo motor driver')
        self.read_state(print_state=True)

        self.set_acceleration(SCS_MOVING_ACC)

        self.set_speed(SCS_MOVING_SPEED)

    def soft_exit(self):
        # Close port
        self.portHandler.closePort()

    def writeTxRx(self, byte_length, address, value, servo_id=SCS_ID):
        value_int=int(value)
        if byte_length == 1:
            scs_comm_result, scs_error = self.packetHandler.write1ByteTxRx(self.portHandler, servo_id, address, value_int)
        elif byte_length == 2:
            scs_comm_result, scs_error = self.packetHandler.write2ByteTxRx(self.portHandler, servo_id, address, value_int)
        else:
            raise Exception("Invalid byte length")

        if scs_comm_result != COMM_SUCCESS:
            message = self.packetHandler.getTxRxResult(scs_comm_result)
            print("%s" % message)
            if 'There is no status packet' in message:
                print('restarting serial mode')

        elif scs_error != 0:
            print("%s" % self.packethandler.getrxpacketerror(scs_error))
            print("error")
            print("self.packethandler.getrxpacketerror(scs_error)")

    def readTxRx(self, byte_length, address, servo_id=SCS_ID):
        if byte_length == 4:
            scs_present_position_speed, scs_comm_result, scs_error = self.packetHandler.read4ByteTxRx(self.portHandler, servo_id, address)
        else:   
            raise Exception("Invalid byte length")

        if scs_comm_result != COMM_SUCCESS:
            message = self.packetHandler.getTxRxResult(scs_comm_result)
            print("%s" % message)
            if 'There is no status packet' in message:
                print('should restart serial mode....')

        elif scs_error != 0:
            print(self.packetHandler.getRxPacketError(scs_error))

        return scs_present_position_speed, scs_comm_result, scs_error
    


    def set_acceleration(self, acceleration=0):
        self.writeTxRx(1, ADDR_SCS_GOAL_ACC, acceleration)

    def set_speed(self, moving_speed=0):
        self.writeTxRx(2, ADDR_SCS_GOAL_SPEED, moving_speed)

    def set_position(self, position, toggle_bytes=False):
        # Write SCServo goal position

        if toggle_bytes:
            position=int(position)
            hight_byte = position >> 8 & 0xff
            low_byte = position & 0xff
            position = low_byte << 8 | hight_byte
            print(position)

        self.writeTxRx(2, ADDR_SCS_GOAL_POSITION, position)

    def read_state(self, print_state=False):
        # Read SCServo present position
        scs_present_position_speed, scs_comm_result, scs_error = self.readTxRx(4, ADDR_SCS_PRESENT_POSITION)
    
        scs_present_position = SCS_LOWORD(scs_present_position_speed)
        scs_present_speed = SCS_HIWORD(scs_present_position_speed)
        speed_real = SCS_TOHOST(scs_present_speed, 15)

        if print_state:
            print(f"position {scs_present_position} speed {scs_present_speed} real speed {speed_real}")
        return scs_present_position_speed, speed_real
    
if __name__ == "__main__":
    with busServoWrapper() as servo:
        #servo.set_acceleration(SCS_MOVING_ACC)
        #servo.set_speed(SCS_MOVING_SPEED)
        while(True):
            servo.read_state()
            new_pos = input("new position?")
            if new_pos=='':
                servo.set_speed(4000)
                continue
            new_pos=int(new_pos) %4096
            servo.set_position(new_pos)
            continue
            i=0
            while i < 10:
                pos, speed = servo.read_state()
                if abs(pos-new_pos)<30:
                    break
                time.sleep(0.5)
                i=i+1



if __name__ == "__main__del":
    with busServoWrapper() as servo:
        #servo.set_acceleration(SCS_MOVING_ACC)
        #servo.set_speed(SCS_MOVING_SPEED)
        while(True):
            servo.read_state()
            new_pos = input("new position?")
            new_pos=int(new_pos) %4096
            servo.set_position(new_pos)
            i=0
            while i < 10:
                pos, speed = servo.read_state()
                if abs(pos-new_pos)<30:
                    break
                time.sleep(0.5)
                i=i+1


