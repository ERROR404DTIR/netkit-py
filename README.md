<div align="center">

<img src="assets/banner.svg" alt="Netkit" width="100%"/>

# 🌐 netkit-py

**جعبه‌ابزار شبکه در یک فایل پایتون — بدون `pip install`**

![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![Dependencies](https://img.shields.io/badge/dependencies-none-brightgreen)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

</div>

---

## ✨ قابلیت‌ها

| دستور | کاربرد |
|---|---|
| `myip` | آی‌پی محلی و (اختیاری) آی‌پی عمومی |
| `dns` | پیدا کردن آی‌پی‌های یک دامنه + reverse DNS |
| `tcping` | سنجش تاخیر اتصال به یک پورت خاص (min/avg/max) |
| `ports` | اسکن سریع و چندنخی پورت‌های TCP |
| `http` | وضعیت HTTP، زمان پاسخ، هدرهای مهم و **تاریخ انقضای SSL** |

فقط کتابخانه‌های استاندارد پایتون استفاده شده؛ هیچ چیزی نصب نمی‌شود.

## 🚀 اجرا

```bash
git clone https://github.com/ERROR404DTIR/netkit-py.git
cd netkit-py

python netkit.py myip
python netkit.py myip --public
python netkit.py dns example.com
python netkit.py tcping example.com 443 -c 5
python netkit.py ports 192.168.1.1
python netkit.py ports 192.168.1.1 -p 1-1024
python netkit.py ports 192.168.1.1 -p 22,80,443,8080
python netkit.py http https://example.com
```

راهنمای هر دستور: `python netkit.py <command> -h`

## 📌 نمونه خروجی

```text
$ python netkit.py tcping 127.0.0.1 8765 -c 3
TCP ping به 127.0.0.1:8765
  #1: متصل شد — 1.0 ms
  #2: متصل شد — 0.2 ms
  #3: متصل شد — 0.2 ms

min/avg/max = 0.2/0.5/1.0 ms | از دست رفته: 0/3
```

```text
$ python netkit.py http https://example.com
آدرس نهایی  : https://example.com/
وضعیت       : 200
زمان پاسخ   : 120 ms
گواهی SSL    : اعتبار تا 2027-01-10 (59 روز مانده)
```

## ⚙️ گزینه‌های مفید

- `--timeout` — زمان انتظار هر اتصال (ثانیه)
- `ports --threads 500` — افزایش سرعت اسکن
- `ports -p 1-65535` — اسکن همه‌ی پورت‌ها

## ⚠️ مسئولیت استفاده

اسکن پورت را فقط روی سرورها و شبکه‌هایی انجام دهید که مالک آن‌ها هستید یا اجازه‌ی کتبی دارید.

## 📄 لایسنس

MIT
