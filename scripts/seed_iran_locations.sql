-- Seeds `provinces` and `cities` with all 31 provinces of Iran and their
-- main cities. Safe to import directly: mysql -u root -p your_db < seed_iran_locations.sql
-- NOT idempotent (unlike scripts/seed_iran_locations.py) - running this twice
-- will create duplicate rows, since plain SQL INSERT has no easy 'skip if
-- exists by name' here. Only run once per database.

SET NAMES utf8mb4;

INSERT INTO `provinces` (`name`, `created_at`, `updated_at`) VALUES ('آذربایجان شرقی', NOW(), NOW());
SET @province_id = LAST_INSERT_ID();
INSERT INTO `cities` (`province_id`, `name`, `created_at`, `updated_at`) VALUES (@province_id, 'تبریز', NOW(), NOW()), (@province_id, 'مراغه', NOW(), NOW()), (@province_id, 'میانه', NOW(), NOW()), (@province_id, 'مرند', NOW(), NOW()), (@province_id, 'اهر', NOW(), NOW()), (@province_id, 'بناب', NOW(), NOW()), (@province_id, 'آذرشهر', NOW(), NOW()), (@province_id, 'شبستر', NOW(), NOW()), (@province_id, 'هریس', NOW(), NOW()), (@province_id, 'کلیبر', NOW(), NOW()), (@province_id, 'جلفا', NOW(), NOW()), (@province_id, 'بستان‌آباد', NOW(), NOW()), (@province_id, 'هشترود', NOW(), NOW()), (@province_id, 'سراب', NOW(), NOW()), (@province_id, 'اسکو', NOW(), NOW()), (@province_id, 'ملکان', NOW(), NOW()), (@province_id, 'عجب‌شیر', NOW(), NOW());

INSERT INTO `provinces` (`name`, `created_at`, `updated_at`) VALUES ('آذربایجان غربی', NOW(), NOW());
SET @province_id = LAST_INSERT_ID();
INSERT INTO `cities` (`province_id`, `name`, `created_at`, `updated_at`) VALUES (@province_id, 'ارومیه', NOW(), NOW()), (@province_id, 'خوی', NOW(), NOW()), (@province_id, 'میاندوآب', NOW(), NOW()), (@province_id, 'بوکان', NOW(), NOW()), (@province_id, 'مهاباد', NOW(), NOW()), (@province_id, 'سلماس', NOW(), NOW()), (@province_id, 'پیرانشهر', NOW(), NOW()), (@province_id, 'نقده', NOW(), NOW()), (@province_id, 'تکاب', NOW(), NOW()), (@province_id, 'شاهین‌دژ', NOW(), NOW()), (@province_id, 'سردشت', NOW(), NOW()), (@province_id, 'اشنویه', NOW(), NOW()), (@province_id, 'چالدران', NOW(), NOW()), (@province_id, 'ماکو', NOW(), NOW()), (@province_id, 'پلدشت', NOW(), NOW());

INSERT INTO `provinces` (`name`, `created_at`, `updated_at`) VALUES ('اردبیل', NOW(), NOW());
SET @province_id = LAST_INSERT_ID();
INSERT INTO `cities` (`province_id`, `name`, `created_at`, `updated_at`) VALUES (@province_id, 'اردبیل', NOW(), NOW()), (@province_id, 'مشگین‌شهر', NOW(), NOW()), (@province_id, 'پارس‌آباد', NOW(), NOW()), (@province_id, 'خلخال', NOW(), NOW()), (@province_id, 'گرمی', NOW(), NOW()), (@province_id, 'بیله‌سوار', NOW(), NOW()), (@province_id, 'نمین', NOW(), NOW()), (@province_id, 'نیر', NOW(), NOW()), (@province_id, 'کوثر', NOW(), NOW());

INSERT INTO `provinces` (`name`, `created_at`, `updated_at`) VALUES ('اصفهان', NOW(), NOW());
SET @province_id = LAST_INSERT_ID();
INSERT INTO `cities` (`province_id`, `name`, `created_at`, `updated_at`) VALUES (@province_id, 'اصفهان', NOW(), NOW()), (@province_id, 'کاشان', NOW(), NOW()), (@province_id, 'نجف‌آباد', NOW(), NOW()), (@province_id, 'خمینی‌شهر', NOW(), NOW()), (@province_id, 'شاهین‌شهر', NOW(), NOW()), (@province_id, 'نائین', NOW(), NOW()), (@province_id, 'اردستان', NOW(), NOW()), (@province_id, 'گلپایگان', NOW(), NOW()), (@province_id, 'فریدن', NOW(), NOW()), (@province_id, 'شهرضا', NOW(), NOW()), (@province_id, 'مبارکه', NOW(), NOW()), (@province_id, 'زرین‌شهر', NOW(), NOW()), (@province_id, 'فلاورجان', NOW(), NOW()), (@province_id, 'تیران', NOW(), NOW()), (@province_id, 'دهاقان', NOW(), NOW()), (@province_id, 'سمیرم', NOW(), NOW()), (@province_id, 'نطنز', NOW(), NOW()), (@province_id, 'آران و بیدگل', NOW(), NOW()), (@province_id, 'خوانسار', NOW(), NOW()), (@province_id, 'چادگان', NOW(), NOW());

INSERT INTO `provinces` (`name`, `created_at`, `updated_at`) VALUES ('البرز', NOW(), NOW());
SET @province_id = LAST_INSERT_ID();
INSERT INTO `cities` (`province_id`, `name`, `created_at`, `updated_at`) VALUES (@province_id, 'کرج', NOW(), NOW()), (@province_id, 'نظرآباد', NOW(), NOW()), (@province_id, 'هشتگرد', NOW(), NOW()), (@province_id, 'فردیس', NOW(), NOW()), (@province_id, 'اشتهارد', NOW(), NOW()), (@province_id, 'طالقان', NOW(), NOW()), (@province_id, 'کمالشهر', NOW(), NOW()), (@province_id, 'ماهدشت', NOW(), NOW());

INSERT INTO `provinces` (`name`, `created_at`, `updated_at`) VALUES ('ایلام', NOW(), NOW());
SET @province_id = LAST_INSERT_ID();
INSERT INTO `cities` (`province_id`, `name`, `created_at`, `updated_at`) VALUES (@province_id, 'ایلام', NOW(), NOW()), (@province_id, 'دهلران', NOW(), NOW()), (@province_id, 'آبدانان', NOW(), NOW()), (@province_id, 'دره‌شهر', NOW(), NOW()), (@province_id, 'ایوان', NOW(), NOW()), (@province_id, 'مهران', NOW(), NOW()), (@province_id, 'چرداول', NOW(), NOW()), (@province_id, 'ملکشاهی', NOW(), NOW()), (@province_id, 'بدره', NOW(), NOW());

INSERT INTO `provinces` (`name`, `created_at`, `updated_at`) VALUES ('بوشهر', NOW(), NOW());
SET @province_id = LAST_INSERT_ID();
INSERT INTO `cities` (`province_id`, `name`, `created_at`, `updated_at`) VALUES (@province_id, 'بوشهر', NOW(), NOW()), (@province_id, 'گناوه', NOW(), NOW()), (@province_id, 'دیلم', NOW(), NOW()), (@province_id, 'برازجان', NOW(), NOW()), (@province_id, 'خورموج', NOW(), NOW()), (@province_id, 'تنگستان', NOW(), NOW()), (@province_id, 'دیر', NOW(), NOW()), (@province_id, 'جم', NOW(), NOW()), (@province_id, 'کنگان', NOW(), NOW());

INSERT INTO `provinces` (`name`, `created_at`, `updated_at`) VALUES ('تهران', NOW(), NOW());
SET @province_id = LAST_INSERT_ID();
INSERT INTO `cities` (`province_id`, `name`, `created_at`, `updated_at`) VALUES (@province_id, 'تهران', NOW(), NOW()), (@province_id, 'ری', NOW(), NOW()), (@province_id, 'شهریار', NOW(), NOW()), (@province_id, 'اسلامشهر', NOW(), NOW()), (@province_id, 'رباط‌کریم', NOW(), NOW()), (@province_id, 'ورامین', NOW(), NOW()), (@province_id, 'پاکدشت', NOW(), NOW()), (@province_id, 'پردیس', NOW(), NOW()), (@province_id, 'پیشوا', NOW(), NOW()), (@province_id, 'دماوند', NOW(), NOW()), (@province_id, 'فیروزکوه', NOW(), NOW()), (@province_id, 'ملارد', NOW(), NOW()), (@province_id, 'قدس', NOW(), NOW()), (@province_id, 'باقرشهر', NOW(), NOW()), (@province_id, 'قرچک', NOW(), NOW()), (@province_id, 'پرند', NOW(), NOW());

INSERT INTO `provinces` (`name`, `created_at`, `updated_at`) VALUES ('چهارمحال و بختیاری', NOW(), NOW());
SET @province_id = LAST_INSERT_ID();
INSERT INTO `cities` (`province_id`, `name`, `created_at`, `updated_at`) VALUES (@province_id, 'شهرکرد', NOW(), NOW()), (@province_id, 'بروجن', NOW(), NOW()), (@province_id, 'فارسان', NOW(), NOW()), (@province_id, 'لردگان', NOW(), NOW()), (@province_id, 'کیار', NOW(), NOW()), (@province_id, 'اردل', NOW(), NOW()), (@province_id, 'کوهرنگ', NOW(), NOW()), (@province_id, 'سامان', NOW(), NOW()), (@province_id, 'بن', NOW(), NOW());

INSERT INTO `provinces` (`name`, `created_at`, `updated_at`) VALUES ('خراسان جنوبی', NOW(), NOW());
SET @province_id = LAST_INSERT_ID();
INSERT INTO `cities` (`province_id`, `name`, `created_at`, `updated_at`) VALUES (@province_id, 'بیرجند', NOW(), NOW()), (@province_id, 'قائنات', NOW(), NOW()), (@province_id, 'فردوس', NOW(), NOW()), (@province_id, 'نهبندان', NOW(), NOW()), (@province_id, 'سربیشه', NOW(), NOW()), (@province_id, 'درمیان', NOW(), NOW()), (@province_id, 'بشرویه', NOW(), NOW()), (@province_id, 'طبس', NOW(), NOW());

INSERT INTO `provinces` (`name`, `created_at`, `updated_at`) VALUES ('خراسان رضوی', NOW(), NOW());
SET @province_id = LAST_INSERT_ID();
INSERT INTO `cities` (`province_id`, `name`, `created_at`, `updated_at`) VALUES (@province_id, 'مشهد', NOW(), NOW()), (@province_id, 'نیشابور', NOW(), NOW()), (@province_id, 'سبزوار', NOW(), NOW()), (@province_id, 'تربت حیدریه', NOW(), NOW()), (@province_id, 'قوچان', NOW(), NOW()), (@province_id, 'کاشمر', NOW(), NOW()), (@province_id, 'تربت جام', NOW(), NOW()), (@province_id, 'چناران', NOW(), NOW()), (@province_id, 'طرقبه', NOW(), NOW()), (@province_id, 'گناباد', NOW(), NOW()), (@province_id, 'فریمان', NOW(), NOW()), (@province_id, 'درگز', NOW(), NOW()), (@province_id, 'سرخس', NOW(), NOW()), (@province_id, 'تایباد', NOW(), NOW()), (@province_id, 'خواف', NOW(), NOW()), (@province_id, 'بجستان', NOW(), NOW()), (@province_id, 'فیض‌آباد', NOW(), NOW());

INSERT INTO `provinces` (`name`, `created_at`, `updated_at`) VALUES ('خراسان شمالی', NOW(), NOW());
SET @province_id = LAST_INSERT_ID();
INSERT INTO `cities` (`province_id`, `name`, `created_at`, `updated_at`) VALUES (@province_id, 'بجنورد', NOW(), NOW()), (@province_id, 'شیروان', NOW(), NOW()), (@province_id, 'اسفراین', NOW(), NOW()), (@province_id, 'جاجرم', NOW(), NOW()), (@province_id, 'فاروج', NOW(), NOW()), (@province_id, 'مانه و سملقان', NOW(), NOW()), (@province_id, 'رازوجرگلان', NOW(), NOW());

INSERT INTO `provinces` (`name`, `created_at`, `updated_at`) VALUES ('خوزستان', NOW(), NOW());
SET @province_id = LAST_INSERT_ID();
INSERT INTO `cities` (`province_id`, `name`, `created_at`, `updated_at`) VALUES (@province_id, 'اهواز', NOW(), NOW()), (@province_id, 'آبادان', NOW(), NOW()), (@province_id, 'خرمشهر', NOW(), NOW()), (@province_id, 'دزفول', NOW(), NOW()), (@province_id, 'اندیمشک', NOW(), NOW()), (@province_id, 'بهبهان', NOW(), NOW()), (@province_id, 'ماهشهر', NOW(), NOW()), (@province_id, 'شوشتر', NOW(), NOW()), (@province_id, 'ایذه', NOW(), NOW()), (@province_id, 'رامهرمز', NOW(), NOW()), (@province_id, 'شوش', NOW(), NOW()), (@province_id, 'باغ‌ملک', NOW(), NOW()), (@province_id, 'هویزه', NOW(), NOW()), (@province_id, 'مسجدسلیمان', NOW(), NOW()), (@province_id, 'هندیجان', NOW(), NOW()), (@province_id, 'امیدیه', NOW(), NOW()), (@province_id, 'حمیدیه', NOW(), NOW()), (@province_id, 'لالی', NOW(), NOW()), (@province_id, 'گتوند', NOW(), NOW());

INSERT INTO `provinces` (`name`, `created_at`, `updated_at`) VALUES ('زنجان', NOW(), NOW());
SET @province_id = LAST_INSERT_ID();
INSERT INTO `cities` (`province_id`, `name`, `created_at`, `updated_at`) VALUES (@province_id, 'زنجان', NOW(), NOW()), (@province_id, 'ابهر', NOW(), NOW()), (@province_id, 'قیدار', NOW(), NOW()), (@province_id, 'خرمدره', NOW(), NOW()), (@province_id, 'ماهنشان', NOW(), NOW()), (@province_id, 'طارم', NOW(), NOW()), (@province_id, 'ایجرود', NOW(), NOW());

INSERT INTO `provinces` (`name`, `created_at`, `updated_at`) VALUES ('سمنان', NOW(), NOW());
SET @province_id = LAST_INSERT_ID();
INSERT INTO `cities` (`province_id`, `name`, `created_at`, `updated_at`) VALUES (@province_id, 'سمنان', NOW(), NOW()), (@province_id, 'شاهرود', NOW(), NOW()), (@province_id, 'دامغان', NOW(), NOW()), (@province_id, 'گرمسار', NOW(), NOW()), (@province_id, 'مهدی‌شهر', NOW(), NOW()), (@province_id, 'آرادان', NOW(), NOW()), (@province_id, 'میامی', NOW(), NOW());

INSERT INTO `provinces` (`name`, `created_at`, `updated_at`) VALUES ('سیستان و بلوچستان', NOW(), NOW());
SET @province_id = LAST_INSERT_ID();
INSERT INTO `cities` (`province_id`, `name`, `created_at`, `updated_at`) VALUES (@province_id, 'زاهدان', NOW(), NOW()), (@province_id, 'زابل', NOW(), NOW()), (@province_id, 'ایرانشهر', NOW(), NOW()), (@province_id, 'چابهار', NOW(), NOW()), (@province_id, 'سراوان', NOW(), NOW()), (@province_id, 'خاش', NOW(), NOW()), (@province_id, 'کنارک', NOW(), NOW()), (@province_id, 'نیک‌شهر', NOW(), NOW()), (@province_id, 'میرجاوه', NOW(), NOW()), (@province_id, 'سرباز', NOW(), NOW()), (@province_id, 'زهک', NOW(), NOW()), (@province_id, 'هیرمند', NOW(), NOW());

INSERT INTO `provinces` (`name`, `created_at`, `updated_at`) VALUES ('فارس', NOW(), NOW());
SET @province_id = LAST_INSERT_ID();
INSERT INTO `cities` (`province_id`, `name`, `created_at`, `updated_at`) VALUES (@province_id, 'شیراز', NOW(), NOW()), (@province_id, 'مرودشت', NOW(), NOW()), (@province_id, 'جهرم', NOW(), NOW()), (@province_id, 'کازرون', NOW(), NOW()), (@province_id, 'فسا', NOW(), NOW()), (@province_id, 'لار', NOW(), NOW()), (@province_id, 'داراب', NOW(), NOW()), (@province_id, 'آباده', NOW(), NOW()), (@province_id, 'لامرد', NOW(), NOW()), (@province_id, 'استهبان', NOW(), NOW()), (@province_id, 'اقلید', NOW(), NOW()), (@province_id, 'نی‌ریز', NOW(), NOW()), (@province_id, 'فیروزآباد', NOW(), NOW()), (@province_id, 'ممسنی', NOW(), NOW()), (@province_id, 'زرقان', NOW(), NOW()), (@province_id, 'سپیدان', NOW(), NOW()), (@province_id, 'ارسنجان', NOW(), NOW()), (@province_id, 'خرامه', NOW(), NOW()), (@province_id, 'کوار', NOW(), NOW());

INSERT INTO `provinces` (`name`, `created_at`, `updated_at`) VALUES ('قزوین', NOW(), NOW());
SET @province_id = LAST_INSERT_ID();
INSERT INTO `cities` (`province_id`, `name`, `created_at`, `updated_at`) VALUES (@province_id, 'قزوین', NOW(), NOW()), (@province_id, 'تاکستان', NOW(), NOW()), (@province_id, 'محمدیه', NOW(), NOW()), (@province_id, 'بوئین‌زهرا', NOW(), NOW()), (@province_id, 'آبیک', NOW(), NOW()), (@province_id, 'آوج', NOW(), NOW());

INSERT INTO `provinces` (`name`, `created_at`, `updated_at`) VALUES ('قم', NOW(), NOW());
SET @province_id = LAST_INSERT_ID();
INSERT INTO `cities` (`province_id`, `name`, `created_at`, `updated_at`) VALUES (@province_id, 'قم', NOW(), NOW());

INSERT INTO `provinces` (`name`, `created_at`, `updated_at`) VALUES ('کردستان', NOW(), NOW());
SET @province_id = LAST_INSERT_ID();
INSERT INTO `cities` (`province_id`, `name`, `created_at`, `updated_at`) VALUES (@province_id, 'سنندج', NOW(), NOW()), (@province_id, 'سقز', NOW(), NOW()), (@province_id, 'مریوان', NOW(), NOW()), (@province_id, 'بانه', NOW(), NOW()), (@province_id, 'بیجار', NOW(), NOW()), (@province_id, 'قروه', NOW(), NOW()), (@province_id, 'دیواندره', NOW(), NOW()), (@province_id, 'کامیاران', NOW(), NOW()), (@province_id, 'دهگلان', NOW(), NOW());

INSERT INTO `provinces` (`name`, `created_at`, `updated_at`) VALUES ('کرمان', NOW(), NOW());
SET @province_id = LAST_INSERT_ID();
INSERT INTO `cities` (`province_id`, `name`, `created_at`, `updated_at`) VALUES (@province_id, 'کرمان', NOW(), NOW()), (@province_id, 'رفسنجان', NOW(), NOW()), (@province_id, 'سیرجان', NOW(), NOW()), (@province_id, 'بم', NOW(), NOW()), (@province_id, 'جیرفت', NOW(), NOW()), (@province_id, 'زرند', NOW(), NOW()), (@province_id, 'بردسیر', NOW(), NOW()), (@province_id, 'شهربابک', NOW(), NOW()), (@province_id, 'کهنوج', NOW(), NOW()), (@province_id, 'بافت', NOW(), NOW()), (@province_id, 'راور', NOW(), NOW()), (@province_id, 'رودبار جنوب', NOW(), NOW()), (@province_id, 'عنبرآباد', NOW(), NOW()), (@province_id, 'ماهان', NOW(), NOW()), (@province_id, 'انار', NOW(), NOW());

INSERT INTO `provinces` (`name`, `created_at`, `updated_at`) VALUES ('کرمانشاه', NOW(), NOW());
SET @province_id = LAST_INSERT_ID();
INSERT INTO `cities` (`province_id`, `name`, `created_at`, `updated_at`) VALUES (@province_id, 'کرمانشاه', NOW(), NOW()), (@province_id, 'اسلام‌آباد غرب', NOW(), NOW()), (@province_id, 'سنقر', NOW(), NOW()), (@province_id, 'صحنه', NOW(), NOW()), (@province_id, 'کنگاور', NOW(), NOW()), (@province_id, 'هرسین', NOW(), NOW()), (@province_id, 'پاوه', NOW(), NOW()), (@province_id, 'جوانرود', NOW(), NOW()), (@province_id, 'سرپل ذهاب', NOW(), NOW()), (@province_id, 'قصر شیرین', NOW(), NOW()), (@province_id, 'گیلانغرب', NOW(), NOW()), (@province_id, 'ثلاث باباجانی', NOW(), NOW());

INSERT INTO `provinces` (`name`, `created_at`, `updated_at`) VALUES ('کهگیلویه و بویراحمد', NOW(), NOW());
SET @province_id = LAST_INSERT_ID();
INSERT INTO `cities` (`province_id`, `name`, `created_at`, `updated_at`) VALUES (@province_id, 'یاسوج', NOW(), NOW()), (@province_id, 'گچساران', NOW(), NOW()), (@province_id, 'دهدشت', NOW(), NOW()), (@province_id, 'لیکک', NOW(), NOW()), (@province_id, 'باشت', NOW(), NOW()), (@province_id, 'چرام', NOW(), NOW());

INSERT INTO `provinces` (`name`, `created_at`, `updated_at`) VALUES ('گلستان', NOW(), NOW());
SET @province_id = LAST_INSERT_ID();
INSERT INTO `cities` (`province_id`, `name`, `created_at`, `updated_at`) VALUES (@province_id, 'گرگان', NOW(), NOW()), (@province_id, 'گنبدکاووس', NOW(), NOW()), (@province_id, 'علی‌آباد کتول', NOW(), NOW()), (@province_id, 'آق‌قلا', NOW(), NOW()), (@province_id, 'بندرترکمن', NOW(), NOW()), (@province_id, 'کردکوی', NOW(), NOW()), (@province_id, 'مینودشت', NOW(), NOW()), (@province_id, 'رامیان', NOW(), NOW()), (@province_id, 'آزادشهر', NOW(), NOW()), (@province_id, 'کلاله', NOW(), NOW()), (@province_id, 'گمیشان', NOW(), NOW());

INSERT INTO `provinces` (`name`, `created_at`, `updated_at`) VALUES ('گیلان', NOW(), NOW());
SET @province_id = LAST_INSERT_ID();
INSERT INTO `cities` (`province_id`, `name`, `created_at`, `updated_at`) VALUES (@province_id, 'رشت', NOW(), NOW()), (@province_id, 'بندرانزلی', NOW(), NOW()), (@province_id, 'لاهیجان', NOW(), NOW()), (@province_id, 'لنگرود', NOW(), NOW()), (@province_id, 'آستارا', NOW(), NOW()), (@province_id, 'تالش', NOW(), NOW()), (@province_id, 'رودسر', NOW(), NOW()), (@province_id, 'صومعه‌سرا', NOW(), NOW()), (@province_id, 'فومن', NOW(), NOW()), (@province_id, 'رودبار', NOW(), NOW()), (@province_id, 'آستانه‌اشرفیه', NOW(), NOW()), (@province_id, 'ماسال', NOW(), NOW()), (@province_id, 'شفت', NOW(), NOW()), (@province_id, 'رضوانشهر', NOW(), NOW()), (@province_id, 'سیاهکل', NOW(), NOW()), (@province_id, 'املش', NOW(), NOW());

INSERT INTO `provinces` (`name`, `created_at`, `updated_at`) VALUES ('لرستان', NOW(), NOW());
SET @province_id = LAST_INSERT_ID();
INSERT INTO `cities` (`province_id`, `name`, `created_at`, `updated_at`) VALUES (@province_id, 'خرم‌آباد', NOW(), NOW()), (@province_id, 'بروجرد', NOW(), NOW()), (@province_id, 'دورود', NOW(), NOW()), (@province_id, 'الیگودرز', NOW(), NOW()), (@province_id, 'کوهدشت', NOW(), NOW()), (@province_id, 'ازنا', NOW(), NOW()), (@province_id, 'پلدختر', NOW(), NOW()), (@province_id, 'نورآباد', NOW(), NOW()), (@province_id, 'الشتر', NOW(), NOW()), (@province_id, 'رومشکان', NOW(), NOW());

INSERT INTO `provinces` (`name`, `created_at`, `updated_at`) VALUES ('مازندران', NOW(), NOW());
SET @province_id = LAST_INSERT_ID();
INSERT INTO `cities` (`province_id`, `name`, `created_at`, `updated_at`) VALUES (@province_id, 'ساری', NOW(), NOW()), (@province_id, 'بابل', NOW(), NOW()), (@province_id, 'آمل', NOW(), NOW()), (@province_id, 'قائم‌شهر', NOW(), NOW()), (@province_id, 'بهشهر', NOW(), NOW()), (@province_id, 'نوشهر', NOW(), NOW()), (@province_id, 'چالوس', NOW(), NOW()), (@province_id, 'تنکابن', NOW(), NOW()), (@province_id, 'بابلسر', NOW(), NOW()), (@province_id, 'فریدونکنار', NOW(), NOW()), (@province_id, 'نور', NOW(), NOW()), (@province_id, 'رامسر', NOW(), NOW()), (@province_id, 'جویبار', NOW(), NOW()), (@province_id, 'نکا', NOW(), NOW()), (@province_id, 'سوادکوه', NOW(), NOW()), (@province_id, 'گلوگاه', NOW(), NOW()), (@province_id, 'محمودآباد', NOW(), NOW()), (@province_id, 'عباس‌آباد', NOW(), NOW()), (@province_id, 'کلاردشت', NOW(), NOW());

INSERT INTO `provinces` (`name`, `created_at`, `updated_at`) VALUES ('مرکزی', NOW(), NOW());
SET @province_id = LAST_INSERT_ID();
INSERT INTO `cities` (`province_id`, `name`, `created_at`, `updated_at`) VALUES (@province_id, 'اراک', NOW(), NOW()), (@province_id, 'ساوه', NOW(), NOW()), (@province_id, 'خمین', NOW(), NOW()), (@province_id, 'محلات', NOW(), NOW()), (@province_id, 'دلیجان', NOW(), NOW()), (@province_id, 'تفرش', NOW(), NOW()), (@province_id, 'آشتیان', NOW(), NOW()), (@province_id, 'شازند', NOW(), NOW()), (@province_id, 'زرندیه', NOW(), NOW()), (@province_id, 'کمیجان', NOW(), NOW());

INSERT INTO `provinces` (`name`, `created_at`, `updated_at`) VALUES ('هرمزگان', NOW(), NOW());
SET @province_id = LAST_INSERT_ID();
INSERT INTO `cities` (`province_id`, `name`, `created_at`, `updated_at`) VALUES (@province_id, 'بندرعباس', NOW(), NOW()), (@province_id, 'میناب', NOW(), NOW()), (@province_id, 'بندرلنگه', NOW(), NOW()), (@province_id, 'قشم', NOW(), NOW()), (@province_id, 'کیش', NOW(), NOW()), (@province_id, 'رودان', NOW(), NOW()), (@province_id, 'حاجی‌آباد', NOW(), NOW()), (@province_id, 'بستک', NOW(), NOW()), (@province_id, 'پارسیان', NOW(), NOW()), (@province_id, 'جاسک', NOW(), NOW()), (@province_id, 'ابوموسی', NOW(), NOW());

INSERT INTO `provinces` (`name`, `created_at`, `updated_at`) VALUES ('همدان', NOW(), NOW());
SET @province_id = LAST_INSERT_ID();
INSERT INTO `cities` (`province_id`, `name`, `created_at`, `updated_at`) VALUES (@province_id, 'همدان', NOW(), NOW()), (@province_id, 'ملایر', NOW(), NOW()), (@province_id, 'نهاوند', NOW(), NOW()), (@province_id, 'تویسرکان', NOW(), NOW()), (@province_id, 'اسدآباد', NOW(), NOW()), (@province_id, 'بهار', NOW(), NOW()), (@province_id, 'رزن', NOW(), NOW()), (@province_id, 'کبودراهنگ', NOW(), NOW()), (@province_id, 'فامنین', NOW(), NOW());

INSERT INTO `provinces` (`name`, `created_at`, `updated_at`) VALUES ('یزد', NOW(), NOW());
SET @province_id = LAST_INSERT_ID();
INSERT INTO `cities` (`province_id`, `name`, `created_at`, `updated_at`) VALUES (@province_id, 'یزد', NOW(), NOW()), (@province_id, 'میبد', NOW(), NOW()), (@province_id, 'اردکان', NOW(), NOW()), (@province_id, 'بافق', NOW(), NOW()), (@province_id, 'ابرکوه', NOW(), NOW()), (@province_id, 'تفت', NOW(), NOW()), (@province_id, 'مهریز', NOW(), NOW()), (@province_id, 'خاتم', NOW(), NOW()), (@province_id, 'بهاباد', NOW(), NOW()), (@province_id, 'اشکذر', NOW(), NOW());
