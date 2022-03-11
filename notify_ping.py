# Скрипт опрашивает компьютер в сети с заданной периодичностью на наличие связи с ним, в случае отсутствия/восстановления связи отправляется уведомление по почте.
# Параметры:
#  -a (--address)  - пингуемый адрес в формате ХХ.ХХ.ХХ.ХХ или www.address.some (обязателен).
#  -s (--smtpaddr) - адрес smtp, например для почтовых ящиков Mail.ru он будет smtp.mail.ru, для GMail - smtp.gmail.com (обязателен).
#  -e (--email)    - адрес почтового ящика в формате mail@domain.ru с которого будет отправляться уведомление (обязателен).
#  -p (--pswd)     - пароль почтового ящика с которого будет отправляться уведомление (обязателен).
#  -t (--to)       - адрес почтового ящика в формате mail@domain.ru на который будет приходить уведомление (обязателен).
#  -i (--interval) - интервал времени в минутах с которым осуществляется опрос (по умолчанию 5).

# Например:
# Linux:
#   python3 notify_ping.py --address google.com --smtpaddr smtp.mail.ru --email from@mail.ru --pswd email_password --to to@mail.ru --interval 5
# Windows:
#   python notify_ping.py --address google.com --smtpaddr smtp.mail.ru --email from@mail.ru --pswd email_password --to to@mail.ru --interval 5
#
#   Будет опрашивать google.com каждые 5 минут, в случае обрыва/восстановления соединения (не отправляются пакеты с помощью ping) с почтового ящика from@mail.ru
#   на to@mail.ru будет прислано письмо с сообщением.
#
# ВНИМАНИЕ! Уведомление на почту не будет отправлено в случае проблем с сетью у компьютера с которого запускается скрипт. Будет выведено соответствующее сообщение в консоль.

import platform
import sys
import argparse
import subprocess as sp
import smtplib
import time
import datetime
import chardet

# TODO Функция возвращает True если пинг есть, иначе False.
def ping(host):
    ret = False
    param = '-n' if platform.system().lower()=='windows' else '-c'
    args = "ping " + param + " 4 " + str(host)
    # В ОС Windows в случае возврата ответа "Заданный узел недоступен", метод getstatusoutput не сработает ожидаемым образом, в этом случае ищем строку в полученном ответе.
    if platform.system().lower()=='windows':
        # Получение вывода команды ping.
        output = sp.getoutput(args)
        # Определение кодировки.
        encoding = chardet.detect(output.encode('cp1251'))['encoding']
        decoding_text = output.encode("cp1251").decode(encoding)
        index = decoding_text.find("Заданный узел недоступен")
        # Если текст "Заданный узел недоступен" не найден в тексте вывода, получаем ответ обычным способом.
        if (index == -1):
            status,result = sp.getstatusoutput(args)
            ret = (status == 0)
        # Иначе если текст найден, значит пинга нет.
        else:
            ret = False
    # В отличных от OC Windows.
    else:
        status,result = sp.getstatusoutput(args)
        ret = (status == 0)

    return ret

# Функция отправляет письмо с уведомлением об обрыве связи на почту.
def send_message(address, smtp, email, pswd, to, up):
    smtpObj = smtplib.SMTP(smtp, 587)
    smtpObj.starttls()
    smtpObj.login(email, pswd)
    smtpObj.sendmail(email, to, "Connection to " + address + " is " + ("restored!" if up else "lost!"))
    smtpObj.quit()

# Функция проверяет наличие сети путем выполнения ping www.google.ru. Возвращает True если адрес пингуется, иначе False.
def internet_connected():
    try:
        param = '-n' if platform.system().lower()=='windows' else '-c'
        sp.check_call(["ping", param, "4", "www.google.ru"], stdout=sp.DEVNULL)
        result = True
        print(str(datetime.datetime.now()) + ": Internet connection available")
    except sp.CalledProcessError:
        result = False
        print(str(datetime.datetime.now()) + ": Internet connection disabled :(")

    return result

# Функция делает попытку отправки уведомления. Если result==True отправляется сообщение о восстановлении связи, иначе уведомление о сбое.
def try_send_message(address, smtpaddr, email, pswd, to, result):
    if internet_connected():
        send_message(address, smtpaddr, email, pswd, to, result)
        print(str(datetime.datetime.now()) + ": Notification sent to " + to)
    else:
        print(str(datetime.datetime.now()) + ": Unable to send email notification.")

# Разбор командной строки.
parser = argparse.ArgumentParser()
parser.add_argument ('-a', '--address')
parser.add_argument ('-s', '--smtpaddr')
parser.add_argument ('-e', '--email')
parser.add_argument ('-t', '--to')
parser.add_argument ('-p', '--pswd')
parser.add_argument ('-i', '--interval', default = 5)
namespace = parser.parse_args(sys.argv[1:])
address = namespace.address
smtpaddr = namespace.smtpaddr
email = namespace.email
to = namespace.to
pswd = namespace.pswd
interval = int(namespace.interval)

# Проверка ввода параметров.
if (not address) or (not smtpaddr) or (not email) or (not to) or (not pswd):
    sys.exit("Error. Some required parameters are missing.")

print("working...")

# Определение начального состояния связи. В случае отсутствия ping также отправляется уведомление на почту.
was_connected = False
if ping(address):
    print(str(datetime.datetime.now()) + ": Connection to " + address + " is " + "available!")
    was_connected = True
else:
    print(str(datetime.datetime.now()) + ": No connect to " + address)
    # Попытка отправки уведомления.
    try_send_message(address, smtpaddr, email, pswd, to, False)
    was_connected = False

# Засыпаем до следующего ping.
time.sleep(interval * 60)

# Бесконечный цикл. Окончание работы скрипта завершится только по закрытию окна выполнения пользователем.
while True:
    # Уведомление в случае обрыва связи.
    if not ping(address):
        # Уведомляем об обрыве только при смене состояния.
        if was_connected:
            print(str(datetime.datetime.now()) + ": Connection to " + address + " is " + "lost!")
            # Попытка отправки уведомления.
            try_send_message(address, smtpaddr, email, pswd, to, False)
            was_connected = False
    # Уведомление в случае восстановления связи.
    else:
        # Уведомление о восстановлении только при смене состояния.
        if not was_connected:
            print(str(datetime.datetime.now()) + ": Connection to " + address + " is " + "restored!")
            # Попытка отправки уведомления.
            try_send_message(address, smtpaddr, email, pswd, to, True)
            was_connected = True

    # Засыпаем до следующего ping.
    time.sleep(interval * 60)
