# Süni İntellekt Əsaslı, Rol-Yönümlü Fişinq Simulyasiya Platforması
## Layihə Təfərrüatları + 4 Həftəlik İcra Planı (R.2 — Sosial Mühəndislik Layihəsi)

---

## 1. Layihə Haqqında

Müasir kibertəhlükəsizlik sistemlərində texniki müdafiə mexanizmlərinin (firewall, IDS/IPS, EDR) təkmilləşməsinə baxmayaraq, təşkilata yönəlmiş uğurlu kibertəcavüzlərin əksəriyyəti hələ də **insan amilinin** istismarına əsaslanır. MITRE ATT&CK çərçivəsində *Phishing* (T1566) və *Spearphishing* (T1566.001–.003) texnikaları ilkin giriş (Initial Access) taktikasının ən çox rast gəlinən vektorları arasındadır.

Mövcud fişinq-simulyasiya alətləri (GoPhish və analoji həllər) əsasən statik, generic ssenarilərə əsaslanır və hədəflənmiş (spear-phishing) hücumların davranış modelini adekvat əks etdirmir. Bu layihə həmin metodoloji boşluğu aradan qaldırmaq məqsədilə, işçi profilinə və təşkilat daxilindəki operativ kontekstə uyğun, süni intellekt (LLM) vasitəsilə dinamik generasiya olunan fişinq ssenarilərinin işlənib hazırlanmasını təklif edir.

**Tədqiqat/layihə sualı:** İşçi məlumatı və operativ təşkilati kontekst LLM əsaslı avtomatlaşdırılmış generasiya prosesi ilə birləşdirildikdə, fişinq simulyasiyasının realistlik və diaqnostik dəyəri nə dərəcədə artırıla bilər?

---

## 2. Mövcud Metodoloji Məhdudiyyətlər

| Məhdudiyyət | Təsviri |
|---|---|
| Generik ssenari modeli | Bütün istifadəçilərə eyni şablonun tətbiqi real hədəflənmiş hücum davranışını simulyasiya etmir |
| Statik məzmun istehsalı | Yeni kampaniya üçün məzmunun əl ilə hazırlanması resurstələb və miqyaslanmayan prosesdir |
| Rol-diferensasiyasının olmaması | Fərqli funksional rolların (maliyyə, İT, İHR) fərqli hücum səthinə malik olması nəzərə alınmır |
| Kəmiyyət ölçmə çətinliyi | Təşkilat daxilində insan-riskinin departament/rol üzrə obyektiv qiymətləndirilməsi mövcud alətlərlə mümkün deyil |
| Nəticə-təlim əlaqəsinin zəifliyi | Kampaniya nəticələri adətən fərdiləşdirilmiş korrektiv tədbirlərə transformasiya olunmur |

---

## 3. Məqsəd və Vəzifələr

**Məqsəd:** Rol-əsaslı, kontekstual cəhətdən adaptiv fişinq simulyasiya platformasının konseptual dizaynını və prototipini hazırlamaq.

**Vəzifələr:**
1. İşçi atributlarına (vəzifə, şöbə, dil) əsaslanan risk-profilləşdirmə modelinin qurulması
2. LLM inteqrasiyası vasitəsilə rola uyğun məzmun generasiya mexanizminin işlənməsi
3. Təhlükəsiz, izolə edilmiş credential-harvesting mühitinin qurulması
4. Kampaniya nəticələrinin kəmiyyət analizini təmin edən analitik modulun hazırlanması
5. Etik və metodoloji çərçivənin (icazə, məlumat minimallaşdırılması, anonimləşdirmə) tərtibi

---

## 4. Sistem Arxitekturası — Funksional Modullar

**4.1. Persona və Risk-Profilləşdirmə Modulu**
İşçi atributları (rol, şöbə, dil) əsasında hər hədəf üçün struktur halında risk profili formalaşdırır; real mühitdə HR sistemi ilə, akademik prototipdə isə sintetik data seti ilə qidalanır.

**4.2. AI-Əsaslı Məzmun Generasiya Modulu**
LLM API vasitəsilə rola uyğun e-poçt mətni və pretext ssenarisi generasiya edir; çoxdilli çıxış dəstəklənir.

**4.3. Operativ Kontekst Modulu (fərqləndirici komponent)**
Simulyasiyanın diaqnostik dəyərini artıran əsas innovasiya budur: sistem generasiya prosesinə təşkilat daxilindəki cari fəaliyyət kontekstini (mock tapşırıq/bilet sistemi, kalendar hadisələri, komanda kommunikasiyası metadatası) daxil edir, nəticədə ssenarilər ümumi deyil, konkret və zaman-kontekstual olur (məs. davam edən bir pentest tapşırığına və ya təqdimat hazırlığına istinad edən pretext). Akademik versiyada modul tam sintetik data üzərində işləyir; istehsalat mühitində isə yalnız read-only, OAuth-scoped, audit-nəzarətli inteqrasiya ilə fəaliyyət göstərməsi tələb olunur, çünki bu səviyyəli daxili kontekstə giriş özü əlavə hücum səthi yaradır.

**4.4. İzolə Edilmiş Sınaq Mühiti (Sandbox)**
Credential-harvesting simulyasiyası tam təcrid olunmuş mühitdə aparılır; real etimadnamə heç bir formada saxlanmır, yalnız binar interaksiya event-i (klik/məlumat-daxiletmə) qeydə alınır.

**4.5. Analitik və Hesabat Modulu**
Klik nisbəti, reaksiya vaxtı və düzgün hesabat vermə göstəricilərini rol/departament kəsimi üzrə aqreqasiya edərək vizual risk xəritəsi formalaşdırır və nəticələr əsasında fərdiləşdirilmiş maarifləndirmə tövsiyələri çıxarır.

---

## 5. Texnoloji İnfrastruktur

| Qat | Texnologiya | Əsaslandırma |
|---|---|---|
| Simulyasiya mühərriki | GoPhish (Go) | Sınanmış, açıq mənbəli kampaniya idarəetməsi |
| Backend / API orkestrasiyası | Python, FastAPI | Yüksək performanslı asinxron API qatı |
| Məzmun generasiyası | LLM API (Claude/GPT) | Kontekstual təbii dil generasiyası |
| Verilənlər bazası | PostgreSQL | Struktur data və kampaniya tarixçəsi üçün etibarlı saxlama |
| Kontekst/HR data qatı | Mock REST API (adapter pattern) | Sintetik testdən real inteqrasiyaya keçidi asanlaşdıran arxitektura |
| E-poçt çatdırılması | SendGrid / Amazon SES, test üçün Mailtrap | Sənaye standartına uyğun çatdırılma və təhlükəsiz sınaq mühiti |
| Vizualizasiya | React, Recharts | Real-vaxt analitik dashboard |
| İnfrastruktur | Docker | Mühitlərin izolyasiyası və reproduksiya oluna bilənlik |

---

## 6. Etik və Metodoloji Çərçivə

Layihə *responsible security testing* prinsiplərinə əsaslanır:

- **İcazə əsası (Authorization):** Hər kampaniya yalnız formal razılaşma (Rules of Engagement) əsasında icra olunur
- **Məlumatın minimallaşdırılması:** Yalnız simulyasiya üçün zəruri atributlar işlənir; PII mümkün olduqda pseudonimləşdirilir
- **Zərərsizlik prinsipi:** Real zərərli yük (payload) heç vaxt istifadə olunmur; bütün interaksiyalar izolə edilmiş sandbox daxilində qalır
- **Şəffaflıq:** Kampaniyadan sonra iştirakçılara debrief və məqsəd izahı təqdim olunur
- **Qeyri-cəzalandırıcı yanaşma:** Nəticələr fərdi qınama deyil, sistemli maarifləndirmə məqsədilə istifadə olunur

**İstinad edilən çərçivələr:** MITRE ATT&CK (T1566 — Phishing), OWASP Top 10, ümumi "Rules of Engagement" (RoE) təhlükəsizlik testi metodologiyası.

---

## 7. Gələcək İnkişaf İstiqamətləri (bu 4 həftədən sonra)

- Reaksiya tarixçəsinə əsaslanan adaptiv çətinlik səviyyəsi modelinin inteqrasiyası
- Çoxkanallı (SMS, korporativ messencer) simulyasiyaya genişlənmə
- SIEM/SOC sistemləri ilə korrelyativ inteqrasiya
- Davranış-əsaslı davamlı risk qiymətləndirmə modelinə keçid
- Çoxtəşkilatlı (multi-tenant) tətbiq arxitekturasına transformasiya

---

## 8. 4 Həftəlik İcra Planı

### Ümumi Baxış

| Həftə | Fokus |
|---|---|
| 1 | Planlaşdırma, mühit qurulumu, verilənlər modeli |
| 2 | Risk-profilləşdirmə modulu + AI məzmun generasiyasının başlanğıcı |
| 3 | Operativ kontekst modulu + Sandbox mühiti |
| 4 | Analitik dashboard, inteqrasiya, sınaq və təqdimat |

### HƏFTƏ 1 — Planlaşdırma və Təməl Qurulum

**Subtasklar:**
- [ ] Rules of Engagement (RoE) sənədinin ilkin layihəsinin yazılması
- [ ] Komanda rollarının bölüşdürülməsi (kim hansı modula məsuldur)
- [ ] Docker əsaslı dev mühitinin qurulması (Python, FastAPI, PostgreSQL)
- [ ] GoPhish-in quraşdırılması və test kampaniyası ilə tanışlıq
- [ ] Git repo strukturu və workflow-un təsbiti
- [ ] PostgreSQL sxeminin dizaynı (işçi, rol, şöbə, kampaniya cədvəlləri)
- [ ] Sintetik işçi data setinin (mock HR data) hazırlanması

**Həftə sonu çıxışı:** İşləyən dev mühiti + verilənlər bazası sxemi + mock data.

### HƏFTƏ 2 — Risk-Profilləşdirmə və AI Generasiyaya Başlanğıc

**Subtasklar:**
- [ ] Adapter pattern ilə mock REST API-nin qurulması (gələcək real HR inteqrasiyası üçün)
- [ ] Rol/şöbə/dil atributlarına əsaslanan risk-profil sxeminin işlənməsi
- [ ] Profil generasiya alqoritminin backend-də implementasiyası
- [ ] FastAPI endpoint-lərinin yazılması (profil CRUD)
- [ ] LLM API-nin (Claude/GPT) backend-ə qoşulması
- [ ] Prompt mühəndisliyi: rol atributlarına görə e-poçt/pretext generasiyası üçün ilkin şablonlar
- [ ] Çoxdilli çıxış üçün ilkin test (Azərbaycan/İngilis)

**Həftə sonu çıxışı:** İşləyən risk-profilləşdirmə modulu + LLM ilə ilk generasiya testləri.

### HƏFTƏ 3 — Operativ Kontekst Modulu və Sandbox

**Subtasklar:**
- [ ] Mock tapşırıq/bilet sistemi datasının yaradılması
- [ ] Mock kalendar hadisələri və komanda kommunikasiya metadatasının generasiyası
- [ ] Bu kontekstin LLM prompt-una inteqrasiyası (persona + risk-profil + kontekst → ssenari)
- [ ] Generasiya olunan ssenarilərin keyfiyyət qiymətləndirilməsi (manual review)
- [ ] İzolə edilmiş sandbox mühitinin qurulması (credential-harvesting simulyasiyası üçün)
- [ ] Yalnız binar interaksiya event-lərinin (klik/data-daxiletmə) qeydə alınması məntiqi
- [ ] Real etimadnamənin heç bir formada saxlanmamasının texniki təmini

**Həftə sonu çıxışı:** Kontekstual ssenari generasiya pipeline-ı + tam izolə edilmiş sandbox.

### HƏFTƏ 4 — Analitika, İnteqrasiya, Sınaq və Təqdimat

**Subtasklar:**
- [ ] E-poçt çatdırılması üçün Mailtrap (test) inteqrasiyası
- [ ] Klik nisbəti, reaksiya vaxtı, düzgün hesabat vermə göstəricilərinin toplanması
- [ ] Rol/departament üzrə aqreqasiya sorğularının yazılması
- [ ] React/Recharts ilə real-vaxt risk xəritəsi dashboard-unun hazırlanması
- [ ] Bütün modulların (profil → generasiya → sandbox → analitika) uçdan-uca inteqrasiyası
- [ ] End-to-end test ssenariləri və bug fixing
- [ ] Etik çərçivənin (icazə, anonimləşdirmə, debrief prosesi) sənədləşdirilməsi
- [ ] Təqdimat materiallarının (slaydlar, demo) hazırlanması

**Həftə sonu çıxışı:** Demo-hazır prototip + tam kampaniya axını (generasiya → göndərmə → nəticə → dashboard) + təqdimat materialları.

---

## Qeyd

Bu sənəd layihənin tam kontekstini (problem, arxitektura, texnologiya, etik çərçivə) və ilk 4 həftəlik icra planını özündə birləşdirir — başqa bir Claude söhbətinə yalnız bu faylı ötürməklə tam kontekst ötürülmüş olur. 7-ci bölmədəki gələcək istiqamətlər bu 4 həftəlik çərçivədən kənarda, layihənin sonrakı mərhələsi üçün nəzərdə tutulub.
