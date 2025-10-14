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

def extract_puissance (out,aff) :
    if platform.system() == 'Windows':
        if (aff):
            m = re.findall('SSID\s*:\s*([A-z0-9 _-]+).*?Signal.*?:.*?([0-9]+%)',out,re.DOTALL)
        else:
            m = re.findall('SSID\s*:\s*([A-Za-z0-9 _-]+).*?Rssi\s*:\s*(-?\d+)',out,re.DOTALL)
    else:
        raise Exception('reached else of if statement')
    return m


bool=False
while(bool==False):
    aff=int(input("entrez le parametre que vous vouler afficher \n(0)la puissance du signal\n(1) le pourcetage:\n"))
    if aff!=0 and aff!=1:
        print("donner un entier valide (0 ou 1)")
    else:
        bool=True
        print(read_data_from_cmd())
        while(True):
            print(extract_puissance(read_data_from_cmd(),aff))
            time.sleep(1)
