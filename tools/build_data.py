"""
Bangun ulang file data dashboard dari export mentah.

Pakai:
  pip install pandas openpyxl
  python tools/build_data.py --hr Daftar_Karyawan.csv --akun Daftar_Akun_Google.csv \
      --user GWSUserActivity.csv --admin GWSAdminActivity.csv --drive GWSDriveActivity.csv \
      --temuan GWS_Access_Review.xlsx --cutoff 2026-10-23 --out site/data

Hasil: 5 file JSON di folder --out. Refresh browser untuk melihat data baru.
"""
import argparse, re, os
import pandas as pd

SHARED = {'admin','admin.partnership','partnership','peopleops','reimbursement','inpatient','legal','corporate.ops','care',
          'product','hello','billing','support','finance','business.operations','business','hr','masterdata'}
DOMAIN = 'rey.id'
ADMIN_KAT = {'Add Privilege':'Privilege','Assign Role':'Privilege','Enforce 2-Step Verification':'Kebijakan keamanan','Allow 2-Step Verification':'Kebijakan keamanan',
 'Change 2-Step Verification Frequency':'Kebijakan keamanan','Change Allowed 2-Step Verification Methods':'Kebijakan keamanan','Change 2-Step Verification Enrollment Period Duration':'Kebijakan keamanan',
 'Change 2-Step Verification Start Date':'Kebijakan keamanan','Change 2-Step Verification Grace Period Duration':'Kebijakan keamanan','User Strong Auth Unenroll':'Bypass keamanan akun',
 'Unblock User Session':'Bypass keamanan akun','Toggle Service Enabled':'Setting aplikasi','Change Application Setting':'Setting aplikasi','Org Unit Creation':'Struktur OU',
 'Org Unit Deletion':'Struktur OU','User Org Unit Change':'Struktur OU','User List Download':'Ekspor data','Audit and Investigation Query':'Ekspor data',
 'Audit and Investigation Query Export':'Ekspor data','Alert Center Viewed':'Alert Center (otomatis)'}
USER_EV = {'logged in':'Login sukses','failed to login':'Login gagal','logged out':'Logout','was presented with login verification':'Verifikasi login',
 'was presented with a login challenge':'Login challenge','changed Account password':'Ganti password','changed Account recovery phone':'Ganti recovery phone',
 'changed Account recovery email':'Ganti recovery email','enrolled for 2-step verification':'Enroll 2SV','unenrolled from 2-step verification':'Unenroll 2SV',
 'turned off 2-step verification':'Matikan 2SV'}
DRIVE_REL = ['Download','Change user access','Change document visibility','Change access scope','User Sharing Permissions Change','Owner changed']

norm = lambda s: s.astype(str).str.strip().str.lower()
iso = lambda s: s.dt.strftime('%Y-%m-%dT%H:%M:%S')

def klas(email, ou, hrset):
    loc, dom = email.split('@') if '@' in email else (email, '')
    if ou == '/ServiceAccount' or 'monitoring' in loc: return 'Service account'
    if dom != DOMAIN: return 'Domain lain'
    if loc in SHARED: return 'Akun shared'
    return 'Karyawan' if email in hrset else 'Personal tanpa data HR'

def main():
    ap = argparse.ArgumentParser()
    for a in ['hr','akun','user','admin','drive']: ap.add_argument('--'+a, required=True)
    ap.add_argument('--temuan'); ap.add_argument('--cutoff', required=True); ap.add_argument('--out', default='site/data')
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True); cut = pd.Timestamp(a.cutoff)

    hr = pd.read_csv(a.hr); hr.columns = ['email','status','tgl_efektif','tgl_hapus','dept'][:len(hr.columns)]
    hr['email'] = norm(hr.email); hr['tgl_hapus'] = pd.to_datetime(hr.tgl_hapus, dayfirst=True, errors='coerce')
    hr = hr.drop_duplicates('email'); hrset = set(hr.email)

    ac = pd.read_csv(a.akun)
    ac = ac[['Email Address [Required]','Org Unit Path [Required]','Status [READ ONLY]','Last Sign In [READ ONLY]','2sv Enrolled [READ ONLY]']]
    ac.columns = ['email','ou','status','last_signin','2sv']; ac['email'] = norm(ac.email)
    never = ac.last_signin.eq('Never logged in')
    last = pd.to_datetime(ac.last_signin.where(~never), errors='coerce'); days = (cut - last).dt.days
    ac = ac.merge(hr[['email','status','tgl_hapus','dept']].rename(columns={'status':'status_hr'}), on='email', how='left')
    flags = []
    for i, r in ac.iterrows():
        f = []
        k = klas(r.email, r.ou, hrset)
        if r.status_hr == 'Deactivated': f.append('Deactivated di HR tapi aktif')
        if pd.isna(r.status_hr) and k == 'Personal tanpa data HR': f.append('Orphan')
        if never[i] or (days[i] > 90): f.append('Dormant')
        if str(r['2sv']).lower() != 'true': f.append('Tanpa 2SV')
        if r.ou == '/Disable-2FA': f.append('OU Disable-2FA')
        flags.append(', '.join(f))
    pd.DataFrame({'email':ac.email,'klasifikasi':[klas(e,o,hrset) for e,o in zip(ac.email,ac.ou)],'status_google':ac.status,'org_unit':ac.ou,
        'login_terakhir':ac.last_signin,'2sv':ac['2sv'].astype(str).str.lower().map({'true':'Ya'}).fillna('Tidak'),'status_hr':ac.status_hr.fillna('Tidak ada di HR'),
        'departemen_hr':ac.dept.fillna(''),'tgl_hapus_hr':ac.tgl_hapus.dt.strftime('%Y-%m-%d').fillna(''),'masalah':flags}
    ).to_json(f'{a.out}/accounts.json', orient='records', force_ascii=False)

    us = pd.read_csv(a.user, usecols=['Date','Description','Login type','IP address','Sensitive action name','User','Network info'])
    us['Date'] = pd.to_datetime(us.Date); us['User'] = norm(us.User)
    reg = us['Network info'].fillna('').map(lambda s: (re.search(r'"Region code": "(\w+)"', s) or [None, 'N/A'])[1])
    act = us.Description.str.extract('(' + '|'.join(map(re.escape, USER_EV)) + ')', expand=False).map(USER_EV)
    act = act.where(act.notna() | us['Sensitive action name'].isna(), 'Sensitive action: ' + us['Sensitive action name'].fillna('')).fillna('Lainnya')
    pd.DataFrame({'id':['U'+str(i) for i in range(len(us))],'waktu':iso(us.Date),'email':us.User,'event':act,'negara':reg,
        'ip':us['IP address'].fillna(''),'login_type':us['Login type'].fillna(''),'detail':us.Description.fillna('').str.slice(0,200)}
    ).to_json(f'{a.out}/user_events.json', orient='records', force_ascii=False)

    ad = pd.read_csv(a.admin, usecols=['Date','Event','Description','Actor','IP address'])
    ad['Date'] = pd.to_datetime(ad.Date)
    tgt = ad.Description.str.extract(r'([\w.+-]+@[\w.-]+\.\w+)')[0].str.lower().fillna('')
    pd.DataFrame({'id':['A'+str(i) for i in range(len(ad))],'waktu':iso(ad.Date),'admin':norm(ad.Actor),'target':tgt,
        'kategori':ad.Event.map(ADMIN_KAT).fillna('Lifecycle akun'),'event':ad.Event,'ip':ad['IP address'].fillna(''),'detail':ad.Description.fillna('').str.slice(0,300)}
    ).to_json(f'{a.out}/admin_events.json', orient='records', force_ascii=False)

    dr = pd.read_csv(a.drive, usecols=['Date','Title','Document type','Visibility','Event','Actor','Owner','Description','IP address'])
    dr['Date'] = pd.to_datetime(dr.Date); dr['Actor'] = norm(dr.Actor); dr['Owner'] = norm(dr.Owner).replace('nan', '')
    ext = ~dr.Actor.str.endswith('@' + DOMAIN) & ~dr.Actor.str.contains('gserviceaccount|google system|^nan$', regex=True)
    d = dr[dr.Event.isin(DRIVE_REL) | ext].copy(); e = ext[d.index]
    d['kategori'] = 'Lainnya'
    d.loc[d.Event == 'Download', 'kategori'] = 'Download'
    d.loc[d.Event.isin(DRIVE_REL[1:]), 'kategori'] = 'Perubahan sharing'
    d.loc[d.Description.fillna('').str.contains('to Anyone with the link for all'), 'kategori'] = 'Dibuka ke publik'
    d.loc[e, 'kategori'] = 'Akses akun eksternal'
    pd.DataFrame({'id':['D'+str(i) for i in range(len(d))],'waktu':iso(d.Date),'email':d.Actor,'kategori':d.kategori,'event':d.Event,
        'judul':d.Title.fillna('').str.slice(0,120),'tipe':d['Document type'].fillna(''),'visibilitas':d.Visibility.fillna(''),'owner':d.Owner,'ip':d['IP address'].fillna('')}
    ).to_json(f'{a.out}/drive_events.json', orient='records', force_ascii=False)

    if a.temuan:
        t = pd.read_excel(a.temuan, sheet_name='temuan')
        t = t[['ID','Tiket','Risiko','Sub-kategori','Akun','Deskripsi temuan','Rekomendasi','Status']]
        t.columns = ['id','tiket','risiko','judul','akun','deskripsi','rekomendasi','status']
        t.fillna('').to_json(f'{a.out}/findings.json', orient='records', force_ascii=False)
    print('Selesai. File di', a.out)

if __name__ == '__main__':
    main()
