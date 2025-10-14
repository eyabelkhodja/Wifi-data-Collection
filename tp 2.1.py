import subprocess
import re
import platform
import time

def read_data_from_cmd ( ) :

    p = subprocess.Popen("netsh wlan show interfaces", stdout=subprocess.PIPE,
    stderr=subprocess.PIPE)
    out = p.stdout.read().decode('unicode_escape').strip()
    p.communicate()
    #print(out)
    return out

def extract_puissance (out) :
    if platform.system() == 'Windows':
        m = re.findall('SSID\s*:\s*([A-z0-9 _-]+).*?Signal.*?:.*?([0-9]+%)',out,re.DOTALL)
    else:
        raise Exception('reached else of if statement')
    return m


print(read_data_from_cmd())
while(True):
    print(extract_puissance(read_data_from_cmd()))
    time.sleep(1)
