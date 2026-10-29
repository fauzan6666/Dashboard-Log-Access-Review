# Dashboard Log & Access Review — REY (hosting internal)

Dashboard statis (HTML + JSON) yang disajikan nginx di Docker.
Akses dibatasi ke jaringan privat kantor **dan** wajib login.

## Isi folder

| Path | Fungsi |
|---|---|
| `site/index.html` | Halaman dashboard |
| `site/assets/` | d3 v7.9.0 (lokal, tanpa internet), runtime dashboard, tema |
| `site/data/*.json` | Data log (**berisi data pribadi**) |
| `docker-compose.yml` | Definisi container nginx |
| `nginx.conf` | Batas akses IP privat, login, header keamanan |
| `buat-password.sh` / `.ps1` | Membuat user login (`.htpasswd`) |
| `tools/build_data.py` | Membuat ulang `site/data` dari export mentah |

## Deploy pertama kali

1. Copy folder ini ke server Docker **tepat di** `/opt/gws-dashboard` (path ini dipakai di `docker-compose.yml`).
2. Buat user login (di server, dari dalam folder):
   ```sh
   cd /opt/gws-dashboard
   ./buat-password.sh namaanda
   ```
3. Jalankan:
   - **Lewat Dockhand:** buat stack baru, isi path/compose dari `docker-compose.yml` di folder ini, lalu Deploy.
   - **Lewat terminal:** `docker compose up -d`
4. Buka `http://IP-SERVER:8088` dari jaringan kantor, lalu login.

## Update data periode berikutnya

```sh
pip install pandas openpyxl
python tools/build_data.py --hr HR.csv --akun Akun.csv --user User.csv \
  --admin Admin.csv --drive Drive.csv --temuan Review.xlsx \
  --cutoff 2026-12-31 --out site/data
```
Tidak perlu restart container: cukup refresh browser.

## Catatan keamanan

- Jangan port-forward 8088 ke internet di MikroTik.
- Simpan folder di server dengan izin terbatas (`chmod 750`), karena `site/data` berisi data pribadi.
- Hapus data periode lama sesuai kebijakan retensi.
- Jangan commit `site/data/*.json` dan `.htpasswd` ke Git (sudah di `.gitignore`).
# Dashboard-Log-Access-Review
