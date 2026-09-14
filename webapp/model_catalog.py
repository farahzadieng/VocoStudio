"""Single source of truth for UI tools and ClearVoice models."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ModelSpec:
    name: str
    label_fa: str
    guidance_fa: str
    task: str
    sample_rate: int
    checkpoint_dir: str


@dataclass(frozen=True, slots=True)
class ToolSpec:
    slug: str
    title_fa: str
    short_fa: str
    description_fa: str
    task: str
    model_names: tuple[str, ...]
    accepted_extensions: tuple[str, ...]
    direct_extensions: tuple[str, ...]
    output_kind: str
    accent: str
    icon: str


MODEL_CATALOG = {
    "FRCRN_SE_16K": ModelSpec(
        "FRCRN_SE_16K", "مدل سریع و سبک",
        "برای فایل‌های گفتاری معمولی و پردازش سریع‌تر مناسب است.",
        "speech_enhancement", 16000, "FRCRN_SE_16K",
    ),
    "MossFormerGAN_SE_16K": ModelSpec(
        "MossFormerGAN_SE_16K", "مدل شفاف‌سازی گفتار",
        "برای کاهش نویز قوی و واضح‌تر شدن گفتار انتخاب مناسبی است.",
        "speech_enhancement", 16000, "MossFormerGAN_SE_16K",
    ),
    "MossFormer2_SE_48K": ModelSpec(
        "MossFormer2_SE_48K", "مدل تمام‌باند با کیفیت بالا",
        "برای ورودی باکیفیت و حفظ جزئیات فرکانسی بیشتر مناسب است.",
        "speech_enhancement", 48000, "MossFormer2_SE_48K",
    ),
    "MossFormer2_SS_16K": ModelSpec(
        "MossFormer2_SS_16K", "مدل جداسازی دو گوینده",
        "صدای ترکیبی دو نفر را به دو فایل مجزا تبدیل می‌کند.",
        "speech_separation", 16000, "MossFormer2_SS_16K",
    ),
    "MossFormer2_SR_48K": ModelSpec(
        "MossFormer2_SR_48K", "مدل افزایش وضوح و پهنای باند",
        "جزئیات فرکانسی گفتار کم‌کیفیت را بازسازی می‌کند.",
        "speech_super_resolution", 48000, "MossFormer2_SR_48K",
    ),
    "AV_MossFormer2_TSE_16K": ModelSpec(
        "AV_MossFormer2_TSE_16K", "مدل استخراج گوینده هدف",
        "با کمک تصویر لب‌های گوینده، صدای همان فرد را جدا می‌کند.",
        "target_speaker_extraction", 16000, "AV_MossFormer2_TSE_16K",
    ),
}


TOOL_CATALOG = {
    "enhancement": ToolSpec(
        "enhancement", "بهبود کیفیت صدا", "حذف نویز و شفاف‌سازی گفتار",
        "یک فایل صوتی نویزی را وارد کنید و مدل مناسب سرعت یا کیفیت را انتخاب کنید.",
        "speech_enhancement",
        ("FRCRN_SE_16K", "MossFormerGAN_SE_16K", "MossFormer2_SE_48K"),
        (".wav", ".flac", ".mp3", ".ogg", ".aac", ".aiff", ".m4a"),
        (".wav", ".flac"), "single_audio", "blue", "spark",
    ),
    "separation": ToolSpec(
        "separation", "جداسازی دو گوینده", "تبدیل مکالمه به دو صدای جدا",
        "فایل مکالمه دو نفره را وارد کنید تا برای هر گوینده یک خروجی ساخته شود.",
        "speech_separation", ("MossFormer2_SS_16K",),
        (".wav", ".flac", ".mp3", ".ogg", ".aac", ".aiff", ".m4a"),
        (".wav", ".flac"), "multi_audio", "violet", "split",
    ),
    "super-resolution": ToolSpec(
        "super-resolution", "افزایش وضوح صدا", "بازسازی جزئیات فرکانسی گفتار",
        "فایل گفتار کم‌کیفیت را وارد کنید تا خروجی ۴۸ کیلوهرتز آماده شود.",
        "speech_super_resolution", ("MossFormer2_SR_48K",),
        (".wav", ".flac", ".mp3", ".ogg", ".aac", ".aiff", ".m4a"),
        (".wav", ".flac"), "single_audio", "teal", "wave",
    ),
    "target-speaker": ToolSpec(
        "target-speaker", "استخراج گوینده هدف", "جداسازی صدا با کمک تصویر لب‌ها",
        "ویدئویی انتخاب کنید که صورت و حرکت لب‌های گوینده هدف در آن مشخص باشد.",
        "target_speaker_extraction", ("AV_MossFormer2_TSE_16K",),
        (".avi", ".mp4", ".mov", ".webm"),
        (".avi", ".mp4", ".mov", ".webm"), "video_outputs", "coral", "focus",
    ),
}


def get_model_spec(name: str) -> ModelSpec:
    return MODEL_CATALOG[name]


def get_tool_spec(slug: str) -> ToolSpec:
    return TOOL_CATALOG[slug]

