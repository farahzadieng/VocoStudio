# اصلاح اختیاری کد اصلی ClearVoice

وب‌اپ حتی بدون اعمال این patch نیز دانلود خودکار را در زمان اجرا مسدود می‌کند و پیش از ساخت مدل، checkpoint محلی را بررسی می‌کند. بنابراین برای اجرای وب‌اپ، تغییر فایل‌های اصلی اجباری نیست.

اگر می‌خواهید دانلود خودکار در تمام اسکریپت‌های ClearVoice نیز برای همیشه حذف شود، از ریشه ریپو اجرا کنید:

```bash
git apply patches/clearvoice-local-checkpoints.patch
```

در Windows می‌توانید همین دستور را از Git Bash اجرا کنید. این patch فقط فایل زیر را تغییر می‌دهد:

```text
clearvoice/clearvoice/networks.py
```

تغییر انجام‌شده:

- حذف فراخوانی `snapshot_download`
- توقف صریح با `FileNotFoundError` در صورت نبودن `last_best_checkpoint`
- جلوگیری از ادامه inference با وزن‌های تصادفی یا ناقص

