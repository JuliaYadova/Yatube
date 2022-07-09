from datetime import datetime

now = datetime.now()
year_now = int(now.strftime("%Y"))


def year(request):
    return {"year": year_now}
