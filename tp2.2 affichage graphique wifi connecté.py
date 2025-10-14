import subprocess
import re
import platform
from datetime import datetime
from matplotlib.animation import FuncAnimation
from matplotlib import pyplot

def read_data_from_cmd ( ) :

    p = subprocess.Popen("netsh wlan show interfaces", stdout=subprocess.PIPE,
    stderr=subprocess.PIPE)
    out = p.stdout.read().decode('unicode_escape').strip()
    #print(out)
    if platform.system() == 'Windows':
        m = re.findall('Name.*?:.*?([A-z0-9 ]*).*?Signal.*?:.*?([0-9]*)%',out,re.DOTALL)
    else:
        raise Exception('reached else of if statement')

    p.communicate()
    return m

x_data , y_data = [], []
figure = pyplot.figure()
start = datetime.now()
line, =pyplot.plot(x_data, y_data, '-', color='black', linewidth=2)
pyplot.xlabel('Temps (s)')
pyplot.ylabel('Puissance du signal')
pyplot.title('Puissance du signal au cours du Temps')
pyplot.axhspan(ymin=0, ymax=23, color='red',alpha=0.3)
pyplot.axhspan(ymin=23, ymax=38, color='orange',alpha=0.3)
pyplot.axhspan(ymin=38, ymax=53, color='yellow',alpha=0.3)
pyplot.axhspan(ymin=53, ymax=84, color='green',alpha=0.3)
text_label = pyplot.text(0, 0.95,'')

def update(frame):
    difference = (datetime.now() - start).total_seconds()
    x_data.append(difference)
    y_data.append(int(read_data_from_cmd()[0][1]))
    line.set_data(x_data,y_data)
    figure.gca().relim()
    figure.gca().autoscale_view()
    text_label.set_text(f"Puissance actuelle : {y_data[-1]}")
    return line, text_label

animation = FuncAnimation(figure, update, interval=1000)
pyplot.show()