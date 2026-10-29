#!/bin/sh
# Pakai: ./buat-password.sh namauser
# Membuat/menambah user di file .htpasswd (password diminta, tidak tampil di layar)
set -e
[ -z "$1" ] && { echo "Pakai: ./buat-password.sh namauser"; exit 1; }
printf "Password untuk %s: " "$1"; stty -echo; read PASS; stty echo; echo
LINE=$(docker run --rm httpd:2.4.62-alpine htpasswd -nbm "$1" "$PASS")
touch .htpasswd
grep -v "^$1:" .htpasswd > .htpasswd.tmp || true
echo "$LINE" >> .htpasswd.tmp && mv .htpasswd.tmp .htpasswd
chmod 644 .htpasswd
echo "User $1 tersimpan di .htpasswd"
