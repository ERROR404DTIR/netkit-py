#!/usr/bin/env python3
"""
netkit-py — جعبه‌ابزار شبکه در یک فایل (بدون نیاز به pip install)

دستورها:
    python netkit.py myip [--public]            # آی‌پی محلی (و اختیاری آی‌پی عمومی)
    python netkit.py dns example.com            # پیدا کردن آی‌پی‌ها و reverse DNS
    python netkit.py tcping example.com 443     # تاخیر اتصال TCP (مثل ping برای یک پورت)
    python netkit.py ports 192.168.1.1          # اسکن پورت‌های رایج
    python netkit.py ports host -p 1-1024       # اسکن بازه‌ی دلخواه
    python netkit.py http https://example.com   # وضعیت، زمان پاسخ، هدرها و انقضای SSL

فقط روی سیستم‌ها و شبکه‌هایی استفاده کنید که مالک آن‌ها هستید یا اجازه دارید.
"""

import argparse
import socket
import ssl
import statistics
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from urllib.parse import urlparse

COMMON_PORTS = [21, 22, 23, 25, 53, 80, 110, 123, 143, 443, 445, 465, 587, 993, 995,
                1433, 1723, 3000, 3306, 3389, 5000, 5432, 5900, 6379, 8000, 8080, 8443, 27017]


# ----------------------------------------------------------------- myip
def local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))  # بسته‌ای ارسال نمی‌شود
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def cmd_myip(args) -> None:
    print(f"نام دستگاه : {socket.gethostname()}")
    print(f"آی‌پی محلی  : {local_ip()}")
    if args.public:
        try:
            with urllib.request.urlopen("https://api.ipify.org", timeout=args.timeout) as r:
                print(f"آی‌پی عمومی : {r.read().decode().strip()}")
        except Exception as e:  # noqa: BLE001
            print(f"آی‌پی عمومی : دریافت نشد ({e})")


# ------------------------------------------------------------------ dns
def cmd_dns(args) -> None:
    try:
        infos = socket.getaddrinfo(args.host, None)
    except socket.gaierror as e:
        sys.exit(f"DNS ناموفق: {e}")
    seen = []
    for fam, _, _, _, sockaddr in infos:
        ip = sockaddr[0]
        if ip not in seen:
            seen.append(ip)
            kind = "IPv6" if fam == socket.AF_INET6 else "IPv4"
            try:
                rev = socket.gethostbyaddr(ip)[0]
            except OSError:
                rev = "-"
            print(f"{kind:5} {ip:40} reverse: {rev}")


# --------------------------------------------------------------- tcping
def cmd_tcping(args) -> None:
    times = []
    lost = 0
    print(f"TCP ping به {args.host}:{args.port}")
    for i in range(args.count):
        t0 = time.perf_counter()
        try:
            with socket.create_connection((args.host, args.port), timeout=args.timeout):
                ms = (time.perf_counter() - t0) * 1000
                times.append(ms)
                print(f"  #{i + 1}: متصل شد — {ms:.1f} ms")
        except OSError as e:
            lost += 1
            print(f"  #{i + 1}: ناموفق — {e}")
        if i < args.count - 1:
            time.sleep(0.5)
    if times:
        print(f"\nmin/avg/max = {min(times):.1f}/{statistics.mean(times):.1f}/{max(times):.1f} ms | از دست رفته: {lost}/{args.count}")
    else:
        print(f"\nهیچ اتصالی برقرار نشد ({lost}/{args.count} ناموفق)")


# ---------------------------------------------------------------- ports
def parse_ports(spec: str):
    ports = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            ports.update(range(int(a), int(b) + 1))
        else:
            ports.add(int(part))
    bad = [p for p in ports if not 1 <= p <= 65535]
    if bad:
        raise ValueError(f"پورت نامعتبر: {bad[0]}")
    return sorted(ports)


def probe(host: str, port: int, timeout: float):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return port
    except OSError:
        return None


def service_name(port: int) -> str:
    try:
        return socket.getservbyport(port, "tcp")
    except OSError:
        return "-"


def cmd_ports(args) -> None:
    try:
        ports = parse_ports(args.ports) if args.ports else COMMON_PORTS
        ip = socket.gethostbyname(args.host)
    except (ValueError, socket.gaierror) as e:
        sys.exit(f"خطا: {e}")

    print(f"اسکن {args.host} ({ip}) — {len(ports)} پورت، timeout={args.timeout}s")
    t0 = time.perf_counter()
    open_ports = []
    with ThreadPoolExecutor(max_workers=args.threads) as ex:
        futures = [ex.submit(probe, ip, p, args.timeout) for p in ports]
        for f in as_completed(futures):
            res = f.result()
            if res:
                open_ports.append(res)
    open_ports.sort()
    if open_ports:
        print("\nپورت‌های باز:")
        for p in open_ports:
            print(f"  {p:<6} {service_name(p)}")
    else:
        print("\nپورت بازی پیدا نشد.")
    print(f"\nتمام شد در {time.perf_counter() - t0:.2f} ثانیه")


# ----------------------------------------------------------------- http
def ssl_days_left(host: str, port: int, timeout: float):
    ctx = ssl.create_default_context()
    with socket.create_connection((host, port), timeout=timeout) as sock:
        with ctx.wrap_socket(sock, server_hostname=host) as ss:
            cert = ss.getpeercert()
    exp = datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
    return (exp - datetime.now(timezone.utc)).days, exp


def cmd_http(args) -> None:
    url = args.url if "://" in args.url else "https://" + args.url
    req = urllib.request.Request(url, headers={"User-Agent": "netkit-py/1.0"})
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=args.timeout) as r:
            elapsed = (time.perf_counter() - t0) * 1000
            status, final_url, headers = r.status, r.geturl(), r.headers
    except urllib.error.HTTPError as e:
        elapsed = (time.perf_counter() - t0) * 1000
        status, final_url, headers = e.code, e.geturl(), e.headers
    except Exception as e:  # noqa: BLE001
        sys.exit(f"اتصال ناموفق: {e}")

    print(f"آدرس نهایی  : {final_url}")
    print(f"وضعیت       : {status}")
    print(f"زمان پاسخ   : {elapsed:.0f} ms")
    for key in ("Server", "Content-Type", "Content-Length", "Cache-Control", "Strict-Transport-Security"):
        if headers.get(key):
            print(f"{key:<12}: {headers.get(key)}")

    parsed = urlparse(final_url)
    if parsed.scheme == "https":
        try:
            days, exp = ssl_days_left(parsed.hostname, parsed.port or 443, args.timeout)
            warn = "  ⚠️ نزدیک انقضا!" if days < 14 else ""
            print(f"گواهی SSL    : اعتبار تا {exp:%Y-%m-%d} ({days} روز مانده){warn}")
        except Exception as e:  # noqa: BLE001
            print(f"گواهی SSL    : خطا ({e})")


# ----------------------------------------------------------------- main
def main() -> None:
    ap = argparse.ArgumentParser(description="جعبه‌ابزار شبکه", formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("myip", help="آی‌پی محلی/عمومی")
    p.add_argument("--public", action="store_true", help="آی‌پی عمومی هم نمایش داده شود (نیاز به اینترنت)")
    p.add_argument("--timeout", type=float, default=5)
    p.set_defaults(fn=cmd_myip)

    p = sub.add_parser("dns", help="جستجوی DNS")
    p.add_argument("host")
    p.set_defaults(fn=cmd_dns)

    p = sub.add_parser("tcping", help="تاخیر اتصال TCP")
    p.add_argument("host")
    p.add_argument("port", type=int)
    p.add_argument("-c", "--count", type=int, default=4)
    p.add_argument("--timeout", type=float, default=3)
    p.set_defaults(fn=cmd_tcping)

    p = sub.add_parser("ports", help="اسکن پورت TCP")
    p.add_argument("host")
    p.add_argument("-p", "--ports", help="مثلا 22,80,443 یا 1-1024 (پیش‌فرض: پورت‌های رایج)")
    p.add_argument("--timeout", type=float, default=0.8)
    p.add_argument("--threads", type=int, default=200)
    p.set_defaults(fn=cmd_ports)

    p = sub.add_parser("http", help="چک وضعیت HTTP و گواهی SSL")
    p.add_argument("url")
    p.add_argument("--timeout", type=float, default=8)
    p.set_defaults(fn=cmd_http)

    args = ap.parse_args()
    try:
        args.fn(args)
    except KeyboardInterrupt:
        print("\nلغو شد.")


if __name__ == "__main__":
    main()
