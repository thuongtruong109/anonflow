# text_randomizer.py
# All-in-one: random word/phrase/sentence/comment (meaningful), EN/VN,
# with templates, emojis, length control, context-aware, and de-duplication.
#
# Install (optional but recommended):
#   pip install faker
#
# Usage:
#   from text_randomizer import TextRandomizer
#   tr = TextRandomizer(lang="en")
#   print(tr.comment(context="follow", tone="friendly", length="short"))
#   print(tr.sentence(length="medium"))
#   print(tr.words(n=3))
#
# Notes:
# - If Faker isn't installed, it still works using built-in banks/templates.
# - Dedup uses an in-memory recent set; call tr.reset_history() if needed.

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

try:
    from faker import Faker  # type: ignore
except Exception:
    Faker = None


def _clamp(n: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, n))


def _normalize_spaces(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


@dataclass
class TextRandomizer:
    lang: str = "en"  # "en" or "vi"
    seed: Optional[int] = None

    # Keep last N generated outputs to avoid repeats
    history_size: int = 200
    _history: List[str] = field(default_factory=list)
    _history_set: set = field(default_factory=set)

    # Emoji config
    emoji_prob: float = 0.45
    emoji_max: int = 2

    # Faker config
    faker_enabled: bool = True

    def __post_init__(self):
        if self.seed is not None:
            random.seed(self.seed)

        self.lang = (self.lang or "en").lower()
        if self.lang not in ("en", "vi"):
            self.lang = "en"

        self._fake = None
        if self.faker_enabled and Faker is not None:
            try:
                self._fake = Faker("vi_VN" if self.lang == "vi" else "en_US")
            except Exception:
                self._fake = Faker()

        self._banks = self._build_banks(self.lang)

    # -----------------------------
    # Public API
    # -----------------------------

    def reset_history(self):
        self._history.clear()
        self._history_set.clear()

    def word(self) -> str:
        # Prefer meaningful adjectives/nouns over lorem
        w = self._pick(self._banks["words"])
        return w

    def words(self, n: int = 3) -> str:
        n = _clamp(n, 1, 12)
        items = random.sample(self._banks["words"], k=min(n, len(self._banks["words"])))
        return " ".join(items)

    def phrase(self, tone: str = "neutral") -> str:
        tone = self._tone(tone)
        key = f"phrases_{tone}"
        s = self._pick(self._banks.get(key) or self._banks["phrases_neutral"])
        return self._maybe_emoji(s)

    def sentence(self, length: str = "medium", tone: str = "neutral") -> str:
        length = self._length(length)
        tone = self._tone(tone)

        # Try faker for natural-looking sentence
        if self._fake is not None and random.random() < 0.45:
            s = self._fake.sentence(nb_words={"short": 6, "medium": 10, "long": 16}[length])
            return self._postprocess(s, tone=tone, add_emoji=True)

        # Template-based sentence
        tmpl = self._pick(self._banks[f"sentence_templates_{tone}"])
        s = self._render_template(tmpl, lang=self.lang)
        s = self._fit_length(s, length=length)
        return self._postprocess(s, tone=tone, add_emoji=True)

    def paragraph(self, sentences: int = 3, tone: str = "neutral") -> str:
        sentences = _clamp(sentences, 1, 8)
        tone = self._tone(tone)

        if self._fake is not None and random.random() < 0.5:
            p = self._fake.paragraph(nb_sentences=sentences)
            return self._postprocess(p, tone=tone, add_emoji=False)

        parts = [self.sentence(length="medium", tone=tone) for _ in range(sentences)]
        # Avoid emoji spam in paragraphs
        parts = [self._strip_trailing_emojis(x) for x in parts]
        return _normalize_spaces(" ".join(parts))

    def comment(
        self,
        context: str = "generic",
        tone: str = "friendly",
        length: str = "short",
        unique: bool = True,
        max_tries: int = 12,
    ) -> str:
        """
        context:
          - generic, follow, like, reply, review, support, shipping, quality
        tone:
          - friendly, neutral, enthusiastic, polite
        length:
          - short, medium, long
        unique:
          - avoid repeating recently generated outputs
        """
        context = (context or "generic").lower().strip()
        tone = self._tone(tone)
        length = self._length(length)

        # Pick a template bank by context; fallback to generic
        bank_key = f"comment_{context}_{tone}"
        templates = self._banks.get(bank_key) or self._banks.get(f"comment_generic_{tone}") or []

        if not templates:
            templates = self._banks["comment_generic_friendly"]

        for _ in range(max_tries if unique else 1):
            # Sometimes return a short phrase directly
            if length == "short" and random.random() < 0.25:
                s = self.phrase(tone=tone)
            else:
                tmpl = self._pick(templates)
                s = self._render_template(tmpl, lang=self.lang)
                s = self._fit_length(s, length=length)
                s = self._postprocess(s, tone=tone, add_emoji=True)

            s = self._dedupe(s) if unique else s
            if s:
                return s

        # Last resort
        return self._postprocess(self.phrase(tone=tone), tone=tone, add_emoji=True)

    # -----------------------------
    # Internals
    # -----------------------------

    def _dedupe(self, s: str) -> str:
        """Return s if not in history; otherwise return ''."""
        key = s.lower().strip()
        if key in self._history_set:
            return ""
        self._history.append(key)
        self._history_set.add(key)
        if len(self._history) > self.history_size:
            old = self._history.pop(0)
            self._history_set.discard(old)
        return s

    def _pick(self, seq: Sequence[str]) -> str:
        return random.choice(list(seq))

    def _tone(self, tone: str) -> str:
        tone = (tone or "neutral").lower().strip()
        if tone not in ("friendly", "neutral", "enthusiastic", "polite"):
            tone = "neutral"
        return tone

    def _length(self, length: str) -> str:
        length = (length or "medium").lower().strip()
        if length not in ("short", "medium", "long"):
            length = "medium"
        return length

    def _maybe_emoji(self, s: str) -> str:
        if random.random() > self.emoji_prob:
            return s
        ems = self._banks["emojis"]
        k = 1 if random.random() < 0.75 else min(self.emoji_max, 2)
        chosen = random.sample(ems, k=k)
        # 70% add end emoji, 30% add start emoji
        if random.random() < 0.7:
            return _normalize_spaces(f"{s} {' '.join(chosen)}")
        return _normalize_spaces(f"{' '.join(chosen)} {s}")

    def _strip_trailing_emojis(self, s: str) -> str:
        # crude: remove common emoji chars at end
        return re.sub(r"(\s*[^\w\s,.'\"!?-]{1,4}\s*)+$", "", s).strip()

    def _postprocess(self, s: str, tone: str, add_emoji: bool) -> str:
        s = _normalize_spaces(s)
        # Ensure terminal punctuation for EN; VN is flexible but we keep it tidy
        if self.lang == "en":
            if s and s[-1] not in ".!?":
                s += "."
        else:
            # VN: add punctuation less aggressively
            if s and s[-1] not in ".!?":
                if random.random() < 0.5:
                    s += "."

        if add_emoji:
            s = self._maybe_emoji(s)

        # Minor casing fixes
        s = s[:1].upper() + s[1:] if s else s
        return s

    def _fit_length(self, s: str, length: str) -> str:
        # Length = approx character range
        ranges = {
            "short": (8, 45),
            "medium": (35, 95),
            "long": (80, 180),
        }
        lo, hi = ranges[length]
        s = _normalize_spaces(s)

        # If too short, add a small clause
        if len(s) < lo:
            extra = self._pick(self._banks["add_ons"])
            s = _normalize_spaces(f"{s} {extra}")

        # If too long, trim safely
        if len(s) > hi:
            s = s[:hi].rsplit(" ", 1)[0].rstrip(",;:")  # cut at word boundary
            if s and s[-1] not in ".!?":
                s += "."
        return s

    def _render_template(self, tmpl: str, lang: str) -> str:
        # Simple slots: {adj} {noun} {verb} {benefit} {thanks} {time} {place}
        slots = self._banks["slots"]
        def rep(m: re.Match) -> str:
            key = m.group(1)
            vals = slots.get(key)
            if not vals:
                return m.group(0)
            return random.choice(vals)

        s = re.sub(r"\{(\w+)\}", rep, tmpl)
        return _normalize_spaces(s)

    # -----------------------------
    # Banks
    # -----------------------------

    def _build_banks(self, lang: str) -> Dict[str, List[str]]:
        if lang == "vi":
            return self._banks_vi()
        return self._banks_en()

    def _banks_en(self) -> Dict[str, List[str]]:
        words = [
            "clean", "cozy", "solid", "smart", "useful", "simple", "beautiful", "smooth",
            "reliable", "handy", "great", "amazing", "impressive", "quality", "design",
            "value", "detail", "finish", "comfort", "upgrade", "perfect", "nice",
            "sturdy", "compact", "lightweight", "durable", "practical", "awesome",
        ]

        emojis = ["👍", "✨", "🔥", "💯", "😊", "🙌", "👏", "✅", "💡", "😍", "🙂"]

        slots = {
            "adj": ["great", "clean", "smart", "solid", "cozy", "impressive", "beautiful", "useful"],
            "noun": ["idea", "setup", "product", "design", "choice", "upgrade", "detail", "solution"],
            "verb": ["helps", "works", "fits", "looks", "feels", "performs", "delivers"],
            "benefit": [
                "exactly what I needed",
                "a big difference",
                "super easy to use",
                "so convenient",
                "worth it",
                "better than expected",
            ],
            "thanks": ["Thanks for sharing", "Appreciate it", "Thanks a lot", "Much appreciated"],
            "time": ["today", "this week", "recently", "so far"],
            "place": ["at home", "on the go", "at work", "while traveling"],
        }

        add_ons = [
            "Really happy with it",
            "Looks super clean",
            "So easy to use",
            "This is a nice upgrade",
            "Love the details",
        ]

        phrases_neutral = [
            "Looks good", "Nice one", "Well done", "Good stuff", "Solid choice",
            "Very helpful", "Pretty clean", "Nice details",
        ]
        phrases_friendly = [
            "Love this!", "So nice!", "This is awesome", "Great work!", "Looks amazing",
            "So helpful", "Really cool", "Nice upgrade",
        ]
        phrases_enthusiastic = [
            "Absolutely love this!", "This is next level", "So impressed!", "Incredible!",
            "So good!!", "Wow, amazing",
        ]
        phrases_polite = [
            "Looks great, thank you", "Well done, thanks for sharing", "Appreciate the post",
            "Thanks—very helpful", "Looks nice, thank you",
        ]

        sentence_templates = {
            "sentence_templates_neutral": [
                "This is a {adj} {noun} and it {verb} really well.",
                "Honestly, the {noun} looks {adj} and feels {adj}.",
                "Simple, {adj}, and {benefit}.",
                "The overall {noun} is {adj}—{benefit}.",
            ],
            "sentence_templates_friendly": [
                "Love the {adj} {noun}—it {verb} so well {place}.",
                "This looks {adj}! {thanks}.",
                "Such a {adj} {noun}, {benefit}.",
                "Really nice—{benefit} {time}.",
            ],
            "sentence_templates_enthusiastic": [
                "Wow, this is {adj}! The {noun} {verb} and it's {benefit}!",
                "So {adj}—I’m genuinely impressed. {benefit}!",
                "This is {noun} goals: {adj}, {adj}, and {benefit}!",
            ],
            "sentence_templates_polite": [
                "Thank you for sharing—this is a {adj} {noun}.",
                "This looks {adj} and {benefit}. {thanks}.",
                "I appreciate this—such a {adj} {noun}.",
            ],
        }

        # Context-aware comment templates
        def c(*xs): return list(xs)

        banks: Dict[str, List[str]] = {
            "words": words,
            "emojis": emojis,
            "slots": slots,
            "add_ons": add_ons,
            "phrases_neutral": phrases_neutral,
            "phrases_friendly": phrases_friendly,
            "phrases_enthusiastic": phrases_enthusiastic,
            "phrases_polite": phrases_polite,
            **sentence_templates,
            # Generic
            "comment_generic_friendly": c(
                "Love this! {benefit}",
                "Looks {adj}—{benefit}",
                "Nice {noun}! {thanks}",
                "This is so {adj}.",
                "Great pick—{benefit}",
            ),
            "comment_generic_neutral": c(
                "Looks good.",
                "Solid {noun}.",
                "Nice details.",
                "{benefit}.",
                "Clean and {adj}.",
            ),
            "comment_generic_enthusiastic": c(
                "Wow!! This is {adj}—{benefit}!",
                "So impressed—{benefit}!",
                "This is amazing. {thanks}!",
                "Absolutely love it—{benefit}!",
            ),
            "comment_generic_polite": c(
                "Looks great, thank you.",
                "Thank you for sharing—{benefit}.",
                "Appreciate it. Looks {adj}.",
                "Well done, thanks for the info.",
            ),
            # Follow
            "comment_follow_friendly": c(
                "Followed—love your vibe!",
                "Followed! Looking forward to more.",
                "Just followed—your content is {adj}.",
                "Followed. {thanks}!",
            ),
            "comment_follow_neutral": c(
                "Followed.",
                "Following.",
                "Followed—nice posts.",
            ),
            "comment_follow_enthusiastic": c(
                "Followed!! Can’t wait to see more {adj} stuff!",
                "Instant follow—so {adj}!",
            ),
            "comment_follow_polite": c(
                "I’ve followed your page—thank you for sharing.",
                "Followed. Appreciate your work.",
            ),
            # Like
            "comment_like_friendly": c(
                "Liked! This is {adj}.",
                "Big like—{benefit}.",
                "Liked—love the {noun}.",
            ),
            "comment_like_neutral": c(
                "Liked.",
                "Nice.",
                "Good one.",
            ),
            "comment_like_enthusiastic": c(
                "Loved this!! {benefit}!",
                "This deserves a like—so {adj}!",
            ),
            "comment_like_polite": c(
                "Liked—thank you for sharing.",
                "Liked. Much appreciated.",
            ),
            # Reply
            "comment_reply_friendly": c(
                "Totally agree—{benefit}.",
                "Same here! {benefit}.",
                "Good point—thanks for explaining.",
            ),
            "comment_reply_neutral": c(
                "Agreed.",
                "That makes sense.",
                "Good point.",
            ),
            "comment_reply_enthusiastic": c(
                "Exactly!! {benefit}!",
                "Yes!! That’s spot on!",
            ),
            "comment_reply_polite": c(
                "I agree—thank you for clarifying.",
                "That’s helpful, thank you.",
            ),
            # Review
            "comment_review_friendly": c(
                "Honestly, {benefit}. Great {noun}!",
                "Super {adj} and {benefit}.",
                "Really happy with this—{benefit}.",
            ),
            "comment_review_neutral": c(
                "{benefit}.",
                "Works as expected.",
                "Good quality overall.",
            ),
            "comment_review_enthusiastic": c(
                "Exceeded my expectations—{benefit}!",
                "So {adj}! {benefit}!",
            ),
            "comment_review_polite": c(
                "I’m satisfied—{benefit}. Thank you.",
                "Good quality and {benefit}.",
            ),
            # Shipping / Support / Quality
            "comment_shipping_friendly": c(
                "Arrived fast—thanks!",
                "Shipping was smooth. {thanks}.",
                "Came in great condition—love it!",
            ),
            "comment_support_polite": c(
                "Support was helpful—thank you.",
                "Appreciate the quick assistance.",
                "Thank you for resolving this.",
            ),
            "comment_quality_friendly": c(
                "Quality feels {adj}—love the finish.",
                "Really {adj} build, {benefit}.",
                "Nice materials and clean details.",
            ),
        }
        return banks

    def _banks_vi(self) -> Dict[str, List[str]]:
        words = [
            "đẹp", "gọn", "xịn", "ổn", "mượt", "tiện", "nhanh", "chắc",
            "bền", "dễ dùng", "tinh tế", "hữu ích", "đáng tiền", "chuẩn",
            "nhẹ", "thực dụng", "gọn gàng", "sang", "tối giản",
        ]

        emojis = ["👍", "✨", "🔥", "😍", "😊", "👏", "✅", "💯", "🙌", "🙂"]

        slots = {
            "adj": ["đẹp", "xịn", "gọn", "tinh tế", "tiện", "ổn áp", "đáng tiền"],
            "noun": ["ý tưởng", "thiết kế", "sản phẩm", "set-up", "lựa chọn", "chi tiết"],
            "verb": ["dùng", "hợp", "trông", "hoạt động", "ổn", "chạy"],
            "benefit": [
                "đúng cái mình cần",
                "tiện cực",
                "dễ dùng lắm",
                "đáng đồng tiền",
                "vượt mong đợi",
                "xài thích thật",
            ],
            "thanks": ["Cảm ơn bạn chia sẻ", "Thanks nha", "Cảm ơn nhiều", "Appreciate quá"],
            "time": ["hôm nay", "dạo này", "mới đây", "từ lúc dùng tới giờ"],
            "place": ["ở nhà", "đi chơi", "đi làm", "khi đi du lịch"],
        }

        add_ons = [
            "Nhìn gọn gàng thật",
            "Dùng chắc thích lắm",
            "Chi tiết nhìn rất ổn",
            "Thấy đáng mua đó",
        ]

        phrases_neutral = ["Ổn đó", "Đẹp", "Gọn", "Hay", "Ổn áp", "Chuẩn", "Ngon"]
        phrases_friendly = ["Đỉnh nha!", "Đẹp quá!", "Hay ghê", "Xịn!", "Thích thật", "Ngon đó!"]
        phrases_enthusiastic = ["Quá đỉnh!!", "Xịn xò quá!", "Đỉnh của chóp!", "Mê luôn!!"]
        phrases_polite = ["Đẹp quá, cảm ơn bạn", "Cảm ơn bạn chia sẻ", "Rất hữu ích, cảm ơn"]

        sentence_templates = {
            "sentence_templates_neutral": [
                "{noun} {adj}, {benefit}.",
                "Nhìn {adj} và {benefit}.",
                "Tổng thể {adj}—{benefit}.",
            ],
            "sentence_templates_friendly": [
                "Đẹp quá! {thanks}.",
                "Nhìn {adj} thật—{benefit}.",
                "Thích cái {noun} này, {benefit}.",
            ],
            "sentence_templates_enthusiastic": [
                "Trời ơi {adj} quá!! {benefit}!",
                "Quá {adj}—mình mê luôn. {benefit}!",
            ],
            "sentence_templates_polite": [
                "{thanks}—{noun} {adj} và {benefit}.",
                "Rất {adj}. {thanks}.",
            ],
        }

        def c(*xs): return list(xs)

        banks: Dict[str, List[str]] = {
            "words": words,
            "emojis": emojis,
            "slots": slots,
            "add_ons": add_ons,
            "phrases_neutral": phrases_neutral,
            "phrases_friendly": phrases_friendly,
            "phrases_enthusiastic": phrases_enthusiastic,
            "phrases_polite": phrases_polite,
            **sentence_templates,
            "comment_generic_friendly": c(
                "Đẹp quá! {benefit}",
                "Nhìn {adj}—{benefit}",
                "Hay ghê. {thanks}",
                "Xịn đó, {benefit}",
            ),
            "comment_generic_neutral": c(
                "Ổn đó.",
                "Đẹp.",
                "Gọn gàng.",
                "{benefit}.",
            ),
            "comment_generic_enthusiastic": c(
                "Đỉnh nha!! {benefit}!",
                "Xịn xò quá—{benefit}!",
                "Mê luôn!! {thanks}!",
            ),
            "comment_generic_polite": c(
                "{thanks}.",
                "Rất hữu ích, cảm ơn bạn.",
                "Cảm ơn bạn chia sẻ—{benefit}.",
            ),
            "comment_follow_friendly": c(
                "Mình follow rồi nha!",
                "Follow liền—thích vibe này!",
                "Follow nhé, mong bạn đăng thêm.",
            ),
            "comment_like_friendly": c(
                "Thả tim nha ❤️",
                "Like cái! {adj} quá.",
                "Like liền—{benefit}.",
            ),
            "comment_reply_friendly": c(
                "Chuẩn luôn—{benefit}.",
                "Đúng ý mình nè!",
                "Hay đó, cảm ơn bạn giải thích.",
            ),
            "comment_review_friendly": c(
                "Dùng thấy {adj}, {benefit}.",
                "Khá {adj} và {benefit}.",
                "Mình thấy đáng tiền—{benefit}.",
            ),
            "comment_shipping_friendly": c(
                "Giao nhanh ghê, cảm ơn nha!",
                "Nhận hàng ổn áp—đóng gói kỹ.",
            ),
            "comment_support_polite": c(
                "Hỗ trợ nhanh, cảm ơn bạn.",
                "Cảm ơn đã giải quyết giúp mình.",
            ),
            "comment_quality_friendly": c(
                "Chất lượng nhìn {adj} thật.",
                "Hoàn thiện {adj}, {benefit}.",
            ),
        }
        return banks


# -----------------------------
# Quick demo (run directly)
# -----------------------------
if __name__ == "__main__":
    tr = TextRandomizer(lang="en", seed=42)
    print("WORD:", tr.word())
    print("WORDS:", tr.words(4))
    print("PHRASE:", tr.phrase(tone="friendly"))
    print("SENT:", tr.sentence(length="short", tone="neutral"))
    print("PARA:", tr.paragraph(sentences=3, tone="polite"))
    print("COMMENT:", tr.comment(context="follow", tone="friendly", length="short"))
    print("COMMENT:", tr.comment(context="review", tone="enthusiastic", length="medium"))

    tr_vi = TextRandomizer(lang="vi", seed=7)
    print("VI COMMENT:", tr_vi.comment(context="like", tone="friendly", length="short"))
