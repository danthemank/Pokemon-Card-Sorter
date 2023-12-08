import pigpio
import time 

pi = pigpio.pi()
pi.write(22, 1)
#pi.set_mode(12, pigpio.OUTPUT)	#Is this line needed? The line below should automatically take care of it, no?
#pi.hardware_PWM(13, 50, 1e6*0.25) # 800Hz 25% dutycycle
pi.hardware_PWM(13, 50, 25*10000) # 800Hz 25% dutycycle
time.sleep(3)
pi.hardware_PWM(13, 50, 2*10000) # 800Hz 25% dutycycle
time.sleep(3)
pi.hardware_PWM(13, 50, 5*10000) # 800Hz 25% dutycycle
time.sleep(3)
