import json
import random
import re
from pathlib import Path
import yaml

# ── Load config ──────────────────────────────────────────────────────
with open("config.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

OUTPUT_FILE = Path(config["prompts"]["output_file"])
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

# ── Egyptian Arabic Prompt Bank ───────────────────────────────────────
PROMPT_BANK = {
    "daily_conversation": [
        "إزيك؟ عامل إيه النهارده؟",
        "الجو حر أوي النهارده، مش كده؟",
        "عايز احجز اوضه ليلتين لو سمحت",
        "امتى الأوتوبيس الجاي؟",
        "ممكن تساعدني ثانيه؟",
        "أنا مش فاهم قصدك، ممكن تعيد؟",
        "اهلا ، عندك وقت دلوقتي؟",
        "بكرا هروح السوق مع أمي",
        "الأكل بتاعكم حلو جداً",
        "محتاج أكلم حد مسؤول",
        "فين الحمام من فضلك؟",
        "ممكن كوباية مية؟",
        "أنا تعبان شوية النهارده",
        "إمتى هترجع من الشغل؟",
        "اتصل بيا لما توصل",
    ],
    "numbers_and_dates": [
        "الحساب بكام؟ تلاتة وعشرين جنيه؟",
        "اتقابلنا يوم الخميس الساعة تلاتة",
        "عندي موعد الساعة عشرة الصبح",
        "الشقة بتاعتي في الدور السابع",
        "اشتريت عشر كيلو بطاطس بخمسين جنيه",
        "رقم تليفوني صفر واحد صفر",
        "الامتحان يوم ١٥ مارس",
        "عندي ٢٠٠ جنيه بس معايا",
        "السنة دي عندي ٢٥ سنة",
        "الرحلة هتاخد ساعتين ونص",
        "اشتريت ٣ تيشرتات بـ ١٥٠ جنيه",
        "المباراة الساعة ٨ بالليل",
        "عندي ٤ إخوات",
        "اشتغلت ١٢ ساعة امبارح",
        "الفيلم بيبدأ الساعة ٩ ونص",
    ],
    "places_and_directions": [
        "روح على طول لحد ما توصل الإشارة",
        "فين محطة مترو المرج؟",
        "عايز أروح وسط البلد، أركب إيه؟",
        "الدكتور عيادته في شارع التحرير",
        "قريب من برج القاهرة شوية",
        "أنا ساكن في المعادي ناحية كورنيش النيل",
        "لف يمين عند الجامع الكبير",
        "المسافة من هنا لهناك كام دقيقة؟",
        "في زحمة على الطريق الدائري دلوقتي",
        "فين أقرب فرع بنك هنا؟",
        "عايز تاكسي من مطار القاهرة",
        "المستشفى على اليسار بعد الإشارة",
        "السوق الكبير قريب من هنا",
        "عايز أروح الأهرامات إيه أحسن طريق؟",
        "إزاي أوصل لمدينة نصر؟",
    ],
    "food_and_orders": [
        "عايز طبق كشري كبير بدون خل",
        "جيبلي اتنين فلافل وعصير قصب",
        "الأكل الصيني عندكم ولا بس مصري؟",
        "عايز بيتزا مارغريتا سايز وسط",
        "ممكن تزود التحريرة شوية؟",
        "البيت المحشي بكام النهارده؟",
        "عايز شاورما فراخ مع كل حاجة",
        "ممكن تبعت أوردر على العنوان ده؟",
        "عندكم أكل نباتي؟",
        "جيبلي قهوة سادة وكباية ميه",
        "الوجبة دي بتاخد أد إيه؟",
        "عايز تورتة شيكولاتة لأربع أشخاص",
        "في إيه أكل خفيف دلوقتي؟",
        "ممكن تبدل الأرز بسلطة؟",
        "الأكل هنا طازة ولا لأ؟",
    ],
    "questions_and_requests": [
        "ممكن تعملي معروف وتجيبلي الكتاب ده؟",
        "عندك فكرة إمتى المحل ده بيفتح؟",
        "مش قادر أفتح الباب، في مشكلة؟",
        "ممكن تتكلم أهدى شوية من فضلك؟",
        "إيه رأيك في الموضوع ده؟",
        "ممكن تساعدني في حاجة بسيطة؟",
        "عارف حد يصلح موبايلات كويس هنا؟",
        "ليه التليفون مش بيرد؟",
        "فين الأوضة رقم ١٢ من فضلك؟",
        "محتاج إيه عشان أعمل الخطوات دي؟",
        "تقدر تبعتلي الملف على الإيميل؟",
        "متأخر على الموعد، تقدر تستنى؟",
        "إيه أحسن دكتور أسنان في المنطقة دي؟",
        "مش عارف أختار بين الاتنين، تنصحني بإيه؟",
        "ممكن توقع هنا من فضلك؟",
    ],
    "code_switching": [
        "الـ meeting اتأجل لبكرا الصبح",
        "عندي deadline النهارده وأنا stress",
        "الـ internet عندنا slow أوي",
        "بعت الـ email بس مفيش reply لسه",
        "الـ laptop بتاعي crash وأنا بشتغل",
        "محتاج أعمل update للـ software",
        "الـ file مش بيفتح عندي",
        "هعمل download للبرنامج ده دلوقتي",
        "الـ password بتاعي اتنسيت",
        "في error في الـ system مش عارف أصلحه",
        "بعت الـ report على الـ WhatsApp",
        "الـ battery خلصت وأنا بره",
        "محتاج أعمل backup للصور دول",
        "الـ connection عندي weak أوي",
        "هنعمل online meeting بكرا الساعة ٢",
    ],
    "edge_cases": [
        "مممم، أيوه، يعني... مش عارف",
        "لأ لأ لأ، مش كده خالص",
        "أيوه! تمام! عظيم! يلا!",
        "إيه ده؟! مش معقول!",
        "سبحان الله، الدنيا غريبة",
        "يا ريت، بس مش هينفع",
        "ها؟ بجد؟ إمتى ده حصل؟",
        "طب وبعدين؟ قوللي اللي حصل",
        "آه، فهمت قصدك دلوقتي",
        "والله العظيم مش عارف أقولك",
        "يعني إيه بالظبط؟",
        "اصبر اصبر، خليني أفكر",
        "مش أنا اللي قلت كده!",
        "تمام تمام، خلاص فهمت",
        "إيه اللي بتعمله ده يابني؟",
    ],
}

# ── Edge case text normalizer ─────────────────────────────────────────
def normalize_egyptian(text: str) -> str:
    """Handle common Egyptian Arabic writing inconsistencies."""
    # Normalize common variant spellings
    replacements = {
        "إزيك": "إزيك",
        "ازيك": "إزيك",
        "عزيك": "إزيك",
        "دلوقتى": "دلوقتي",
        "امبارح": "امبارح",
        "إمبارح": "امبارح",
        "هيجي": "هييجي",
        "جاى": "جاي",
    }
    for variant, canonical in replacements.items():
        text = text.replace(variant, canonical)
    return text

def has_edge_case(text: str) -> list:
    """Flag potential TTS edge cases in a prompt."""
    flags = []
    if re.search(r'[a-zA-Z]', text):
        flags.append("code_switching")
    if re.search(r'[٠-٩0-9]', text):
        flags.append("contains_numbers")
    if re.search(r'[!؟?]{2,}', text):
        flags.append("repeated_punctuation")
    if len(text.split()) <= 2:
        flags.append("very_short")
    if len(text.split()) >= 15:
        flags.append("very_long")
    return flags

# ── Main generator ────────────────────────────────────────────────────
def generate_prompts(total: int = 100) -> list:
    prompts = []
    prompt_id = 1

    categories = list(PROMPT_BANK.keys())
    per_category = total // len(categories)
    remainder = total % len(categories)

    for i, category in enumerate(categories):
        count = per_category + (1 if i < remainder else 0)
        pool = PROMPT_BANK[category].copy()

        # If pool smaller than count, allow repeats with shuffle
        while len(pool) < count:
            pool += PROMPT_BANK[category].copy()
        random.shuffle(pool)
        selected = pool[:count]

        for text in selected:
            normalized = normalize_egyptian(text)
            flags = has_edge_case(normalized)
            prompts.append({
                "id": f"prompt_{prompt_id:04d}",
                "text": normalized,
                "category": category,
                "char_count": len(normalized),
                "word_count": len(normalized.split()),
                "edge_case_flags": flags,
                "has_edge_case": len(flags) > 0,
            })
            prompt_id += 1

    random.shuffle(prompts)
    return prompts

# ── Run ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    total = config["prompts"]["total"]
    print(f"Generating {total} Egyptian Arabic prompts...")

    prompts = generate_prompts(total)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(prompts, f, ensure_ascii=False, indent=2)

    # Stats
    categories = {}
    edge_cases = 0
    for p in prompts:
        categories[p["category"]] = categories.get(p["category"], 0) + 1
        if p["has_edge_case"]:
            edge_cases += 1

    print(f"\n✅ Generated {len(prompts)} prompts → {OUTPUT_FILE}")
    print(f"📊 Categories:")
    for cat, count in categories.items():
        print(f"   {cat}: {count}")
    print(f"⚠️  Edge cases flagged: {edge_cases}")