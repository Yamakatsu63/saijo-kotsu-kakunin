import re

a = "09:00"
b = "test"

m = re.match(r'^([01][0-9]|2[0-3]):[0-5][0-9]$', a)

try:
    print(m.group(0))
except:
    print('not time')