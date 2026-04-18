import json
import html
import logging
import re
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, Optional

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

# =========================
# НАСТРОЙКИ
# =========================
BOT_TOKEN = "8608199519:AAHkuEycs5O5kfws6WFvV_bdLSJR-vo-Ngk"
ADMIN_CHAT_ID = 1096811893
BOT_USERNAME = "priemzhalobshymkentbot"  # без @
CHANNEL_URL = "https://t.me/gorodskieobrasheniashymkent"

TIMEZONE = timezone(timedelta(hours=5))  # Казахстан UTC+5
COOLDOWN_MINUTES = 15
DAILY_LIMIT = 3
MIN_TEXT_LENGTH = 30
MAX_TEXT_LENGTH = 1000
MIN_ADDRESS_LENGTH = 6
MAX_ADDRESS_LENGTH = 200
DUPLICATE_SIMILARITY = 0.88

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
USERS_FILE = DATA_DIR / "users.json"
REPORTS_FILE = DATA_DIR / "reports.json"

logging.basicConfig(
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# =========================
# СОСТОЯНИЯ
# =========================
(
    LANG,
    RULES_ACK,
    MENU,
    CATEGORY,
    TRANSPORT_BRANCH,
    TRANSPORT_ROUTE,
    TRANSPORT_DRIVER_TYPE,
    SHORT_TEXT,
    DISTRICT,
    ADDRESS,
    EVENT_TIME,
    CUSTOM_DATE,
    PHOTO,
    CONFIRM,
    EDIT_CHOICE,
    EDIT_TEXT,
    EDIT_ADDRESS,
    EDIT_DATE,
    EDIT_PHOTO,
) = range(19)

# =========================
# СПРАВОЧНИКИ
# =========================
CATEGORIES = {
    "ru": [
        "Мусор",
        "Освещение",
        "Дороги",
        "Вода",
        "Опасное место",
        "Нарушение",
        "Транспорт",
        "Другое",
    ],
    "kz": [
        "Қоқыс",
        "Жарықтандыру",
        "Жолдар",
        "Су",
        "Қауіпті орын",
        "Бұзушылық",
        "Көлік",
        "Басқа",
    ],
}

TRANSPORT_BRANCHES = {
    "ru": [
        "Общественный транспорт",
        "Водитель автомобиля",
    ],
    "kz": [
        "Қоғамдық көлік",
        "Жүргізуші",
    ],
}

TRANSPORT_DRIVER_TYPES = {
    "ru": [
        "Опасное вождение",
        "Парковка в неположенном месте",
        "Грубое поведение",
        "Другое",
    ],
    "kz": [
        "Қауіпті жүргізу",
        "Рұқсатсыз жерге тұрақ",
        "Дөрекі мінез-құлық",
        "Басқа",
    ],
}

DISTRICTS = {
    "ru": [
        "Абайский район",
        "Аль-Фарабийский район",
        "Енбекшинский район",
        "Каратауский район",
        "Туранский район",
    ],
    "kz": [
        "Абай ауданы",
        "Әл-Фараби ауданы",
        "Еңбекші ауданы",
        "Қаратау ауданы",
        "Тұран ауданы",
    ],
}

DATE_OPTIONS = {
    "ru": [
        "Сегодня",
        "Вчера",
        "За последние 3 дня",
        "На этой неделе",
        "В прошлом месяце",
        "Указать свою дату",
    ],
    "kz": [
        "Бүгін",
        "Кеше",
        "Соңғы 3 күнде",
        "Осы аптада",
        "Өткен айда",
        "Күнді өзім енгіземін",
    ],
}

TEXTS = {
    "ru": {
        "language_title": "🌐 Выберите язык интерфейса:",
        "rules": (
            "<b>Добро пожаловать в анонимный бот сообщений по городу Шымкент.</b>\n\n"
            "✅ Все сообщения отправляются анонимно.\n"
            "🛡 Жалобы проходят проверку на содержание.\n"
            "ℹ️ Администратор бота не является представителем государственных или правоохранительных органов.\n\n"
            f"⏱ Ограничение: не более {DAILY_LIMIT} жалоб в день и не чаще 1 раза в {COOLDOWN_MINUTES} минут.\n\n"
            "<b>⚠️ Запрещено:</b>\n"
            "Ложные сведения и необоснованные обвинения.\n"
            "Личные данные других людей.\n"
            "Угрозы, оскорбления и давление.\n"
            "Попытки организовать травлю или преследование.\n\n"
            "<b>За нарушение правил — бан без предупреждения.</b>"
        ),
        "agree": "Согласен, продолжить",
        "more_rules": "Показать правила ещё раз",
        "menu_text": "🏠 Главное меню\n\nВыберите действие:",
        "menu_send": "📨 Сообщить о ситуации",
        "menu_rules": "📜 Правила",
        "menu_about": "ℹ️ О проекте",
        "menu_change_language": "🌐 Сменить язык",
        "menu_last_report": "🧾 Моя последняя жалоба",
        "menu_how_to": "✍️ Как правильно написать",
        "menu_clear_form": "🗑 Очистить текущую форму",
        "menu_share_bot": "📣 Поделиться ботом",
        "menu_channel": "📢 Перейти в канал",
        "main_menu": "🏠 Главное меню",
        "back": "Назад",
        "skip": "Пропустить",
        "remove_photo": "Удалить фото",
        "unknown_route": "Не знаю",
        "warning_tail": "⚠️ Не указывайте телефоны, аккаунты и личные данные других людей.",
        "transport_warning_tail": "⚠️ Не используйте жалобу для травли или преследования человека. Опишите только саму ситуацию.",
        "about": (
            "ℹ️ О проекте\n\n"
            "Этот бот создан для того, чтобы жители Шымкента не молчали о городских проблемах, а могли спокойно и анонимно сообщать о них. 📢\n\n"
            "Проект помогает замечать важные ситуации, говорить о них открыто и привлекать внимание к тем вопросам, которые влияют на жизнь города. 🏙\n\n"
            "Бот не решает проблемы и не принимает никаких решений.\n"
            "Он только помогает безопасно передать сообщение для рассмотрения и анализа. 👁\n\n"
            "Все обращения рассматриваются внимательно.\n"
            "Сообщения с клеветой, ложными обвинениями, травлей и личными данными не поддерживаются.\n\n"
            "Клевета — враг справедливого обращения.\n\n"
            "Когда информация изложена ясно и без нарушений, она может помочь донести проблему до тех, кто действительно может повлиять на ситуацию на городском уровне. 🤝"
        ),
        "how_to": (
            "✍️ Как правильно написать жалобу\n\n"
            "Пишите коротко и по сути.\n\n"
            "Укажите, что произошло.\n"
            "Укажите, где это произошло.\n"
            "Укажите, когда это произошло.\n"
            "Если есть возможность — добавьте одно фото."
        ),
        "share_bot": (
            "📣 Поделиться ботом\n\n"
            "Если хотите помочь проекту, отправьте ссылку на бота знакомым или соседям.\n\n"
            "Ссылка:\n"
            "https://t.me/{bot_username}"
        ),
        "channel_text": "📢 Нажмите кнопку ниже, чтобы открыть канал.",
        "clear_form_done": "🗑 Текущая незавершённая форма очищена.\n\nВы снова в главном меню.",
        "clear_form_empty": "Сейчас нет незавершённой формы.\n\nВы уже в главном меню.",
        "last_report_empty": "У вас пока нет отправленных жалоб.",
        "last_report_title": "🧾 Ваша последняя жалоба:",
        "last_report_status": "отправлена на рассмотрение",
        "choose_category": (
            "📂 Выберите категорию\n\n"
            "Пожалуйста, выберите наиболее подходящий вариант."
        ),
        "choose_transport_branch": (
            "🚌 Уточните тип ситуации\n\n"
            "Выберите, о каком виде транспорта идёт речь."
        ),
        "choose_driver_type": (
            "🚗 Уточните тип ситуации с автомобилем\n\n"
            "Выберите наиболее подходящий вариант."
        ),
        "transport_route": (
            "🚌 Укажите номер маршрута\n\n"
            "Если знаете номер автобуса или маршрута, напишите его.\n"
            "Если не знаете — нажмите «Не знаю».\n\n"
            "Пример:\n"
            "45\n"
            "12А"
        ),
        "short_text": (
            "📝 Кратко опишите ситуацию\n\n"
            "Пожалуйста, напишите, что именно произошло, чтобы суть жалобы была понятна сразу.\n\n"
            "Пример:\n"
            "Во дворе уже несколько дней не вывозят мусор, контейнеры переполнены."
        ),
        "short_text_transport_public": (
            "📝 Кратко опишите ситуацию\n\n"
            "Пожалуйста, напишите, что произошло в транспорте или на маршруте.\n\n"
            "Пример:\n"
            "Водитель автобуса резко закрыл двери, не дождавшись пассажиров на остановке."
        ),
        "short_text_transport_driver": (
            "📝 Кратко опишите ситуацию\n\n"
            "Пожалуйста, напишите, что именно произошло на дороге или возле транспорта.\n\n"
            "Пример:\n"
            "Водитель припарковал машину прямо на пешеходной зоне возле входа."
        ),
        "district": (
            "📍 Выберите район\n\n"
            "Пожалуйста, выберите район, где произошла ситуация."
        ),
        "address": (
            "🏠 Укажите место, где это произошло\n\n"
            "Пожалуйста, напишите улицу или микрорайон, дом, либо понятный ориентир.\n\n"
            "Пример:\n"
            "мкр Нурсат, дом 12\n"
            "или\n"
            "ул. Тауке хана, возле остановки"
        ),
        "transport_place": (
            "📍 Укажите место, где это произошло\n\n"
            "Можно написать остановку, улицу, ориентир или другое понятное место.\n\n"
            "Пример:\n"
            "остановка возле рынка\n"
            "или\n"
            "ул. Республики, рядом с магазином"
        ),
        "event_time": (
            "📅 Укажите, когда это произошло\n\n"
            "Выберите один из вариантов ниже\n"
            "или введите дату самостоятельно."
        ),
        "custom_date": (
            "📅 Введите дату или время события\n\n"
            "Можно указать точную дату\n"
            "или написать понятным образом.\n\n"
            "Пример:\n"
            "16.04.2026\n"
            "или\n"
            "2 дня назад"
        ),
        "photo": (
            "📸 Добавьте фото, если оно есть\n\n"
            "Отправьте одно изображение.\n"
            "Если фото нет — нажмите «Пропустить»."
        ),
        "photo_expected": (
            "📸 Сейчас ожидается одно фото\n\n"
            "Если фото нет — нажмите «Пропустить»."
        ),
        "confirm_title": "✅ Проверьте жалобу перед отправкой:",
        "confirm_send": "Отправить",
        "confirm_edit": "Изменить",
        "confirm_cancel": "Отменить",
        "edit_title": "✏️ Что хотите изменить?",
        "edit_text": "Изменить текст",
        "edit_address": "Изменить адрес",
        "edit_date": "Изменить дату",
        "edit_photo": "Изменить фото",
        "sent": (
            "✅ Жалоба принята.\n\n"
            "Она отправлена на рассмотрение проверки содержания.\n\n"
            f"Следующую жалобу можно отправить через {COOLDOWN_MINUTES} минут."
        ),
        "cancelled": "❌ Отправка отменена.",
        "too_soon_full": "⌛ До следующей жалобы осталось: {time}",
        "too_soon_warn": "⌛ Ещё рано. Осталось: {time}\n\nПожалуйста, не нажимайте слишком часто — это создаёт лишнюю нагрузку.",
        "too_soon_short": "Ожидайте окончания ограничения.",
        "daily_limit": "📛 Сегодня вы уже отправили 3 жалобы.\n\nПопробуйте снова завтра.",
        "bad_short_min": f"Текст слишком короткий.\n\nНужно минимум {MIN_TEXT_LENGTH} символов.",
        "bad_short_max": f"Текст слишком длинный.\n\nСократите описание до {MAX_TEXT_LENGTH} символов и оставьте только главное.",
        "bad_address_min": "Место выглядит слишком коротким.\n\nУкажите улицу, остановку, дом или ориентир.",
        "bad_address_max": f"Описание места слишком длинное.\n\nСократите его до {MAX_ADDRESS_LENGTH} символов.",
        "bad_date": "Напишите дату или понятное время события.\n\nНапример: 16.04.2026 или вчера вечером.",
        "bad_photo": "Пожалуйста, отправьте одно фото или нажмите «Пропустить».",
        "blocked": "Ваш доступ ограничен.\n\nОбратитесь к администратору.",
        "status_photo": "Есть фото",
        "status_no_photo": "Без фото",
        "preview_category": "Категория",
        "preview_transport": "Тип транспорта",
        "preview_driver_type": "Тип ситуации",
        "preview_route": "Маршрут",
        "preview_text": "Описание",
        "preview_district": "Район",
        "preview_address": "Адрес / ориентир",
        "preview_date": "Когда произошло",
        "preview_status": "Фото",
        "preview_status_field": "Статус",
        "unknown_action": "Неизвестное действие.",
        "report_not_found": "Данные жалобы не найдены.\n\nНачните заново.",
        "error_prefix": "Произошла ошибка:",
        "admin_title": "Новая история №{number:04d}",
        "admin_ready": "Черновик для публикации",
        "admin_status": "Статус: готово к рассмотрению",
        "choose_language_again": "🌐 Выберите новый язык:",
        "duplicate_report": "Похоже, вы уже отправляли очень похожую жалобу.\n\nЕсли это новая ситуация, уточните текст сообщения.",
    },
    "kz": {
        "language_title": "🌐 Интерфейс тілін таңдаңыз:",
        "rules": (
            "<b>Шымкент қаласы бойынша анонимді хабарламалар ботына қош келдіңіз.</b>\n\n"
            "✅ Барлық хабарламалар анонимді түрде жіберіледі.\n"
            "🛡 Шағымдар мазмұны бойынша тексеріледі.\n"
            "ℹ️ Бот әкімшісі мемлекеттік немесе құқық қорғау органының өкілі емес.\n\n"
            f"⏱ Шектеу: күніне {DAILY_LIMIT} шағымнан артық емес және әр {COOLDOWN_MINUTES} минут сайын 1 реттен жиі емес.\n\n"
            "<b>⚠️ Тыйым салынады:</b>\n"
            "Жалған мәлімет пен дәлелсіз айыптау.\n"
            "Басқа адамдардың жеке деректері.\n"
            "Қорқыту, қорлау және қысым жасау.\n"
            "Қудалауға немесе топтасуға шақыру.\n\n"
            "<b>Ережені бұзғаны үшін — ескертусіз бұғаттау.</b>"
        ),
        "agree": "Келісемін, жалғастыру",
        "more_rules": "Ережелерді қайта көрсету",
        "menu_text": "🏠 Басты мәзір\n\nӘрекетті таңдаңыз:",
        "menu_send": "📨 Жағдай туралы хабарлау",
        "menu_rules": "📜 Ережелер",
        "menu_about": "ℹ️ Жоба туралы",
        "menu_change_language": "🌐 Тілді өзгерту",
        "menu_last_report": "🧾 Соңғы шағымым",
        "menu_how_to": "✍️ Қалай дұрыс жазу керек",
        "menu_clear_form": "🗑 Ағымдағы форманы тазалау",
        "menu_share_bot": "📣 Ботпен бөлісу",
        "menu_channel": "📢 Арнаға өту",
        "main_menu": "🏠 Басты мәзір",
        "back": "Артқа",
        "skip": "Өткізіп жіберу",
        "remove_photo": "Фотоны өшіру",
        "unknown_route": "Білмеймін",
        "warning_tail": "⚠️ Басқа адамдардың телефон нөмірін, аккаунтын және жеке деректерін көрсетпеңіз.",
        "transport_warning_tail": "⚠️ Шағымды адамды қудалау немесе топтасу үшін қолданбаңыз. Тек жағдайдың өзін сипаттаңыз.",
        "about": (
            "ℹ️ Жоба туралы\n\n"
            "Бұл бот Шымкент тұрғындары қалалық мәселелер туралы үндемей қалмай, оларды тыныш әрі анонимді түрде жеткізе алуы үшін жасалған. 📢\n\n"
            "Жоба маңызды жағдайларды байқап, олар туралы ашық айтуға және қала өміріне әсер ететін мәселелерге назар аудартуға көмектеседі. 🏙\n\n"
            "Бот мәселені өзі шешпейді және ешқандай шешім қабылдамайды.\n"
            "Ол тек хабарламаны қауіпсіз түрде қарау мен талдауға жеткізуге көмектеседі. 👁\n\n"
            "Барлық өтініштер мұқият қаралады.\n"
            "Жала, жалған айыптау, қудалау және жеке деректер бар хабарламалар қолдау таппайды.\n\n"
            "Жала — әділ өтініштің жауы.\n\n"
            "Егер ақпарат анық әрі ережесіз бұзылмай берілсе, ол мәселені қала деңгейінде ықпал ете алатын адамдарға жеткізуге көмектесуі мүмкін. 🤝"
        ),
        "how_to": (
            "✍️ Шағымды қалай дұрыс жазу керек\n\n"
            "Қысқа әрі нақты жазыңыз.\n\n"
            "Не болғанын көрсетіңіз.\n"
            "Қай жерде болғанын көрсетіңіз.\n"
            "Қашан болғанын көрсетіңіз.\n"
            "Мүмкіндік болса, бір фото қосыңыз."
        ),
        "share_bot": (
            "📣 Ботпен бөлісу\n\n"
            "Жобаға көмектескіңіз келсе, бот сілтемесін таныстарыңызға немесе көршілеріңізге жіберіңіз.\n\n"
            "Сілтеме:\n"
            "https://t.me/{bot_username}"
        ),
        "channel_text": "📢 Арнаны ашу үшін төмендегі батырманы басыңыз.",
        "clear_form_done": "🗑 Аяқталмаған форма тазартылды.\n\nСіз қайтадан басты мәзірдесіз.",
        "clear_form_empty": "Қазір аяқталмаған форма жоқ.\n\nСіз басты мәзірдесіз.",
        "last_report_empty": "Сізде әлі жіберілген шағым жоқ.",
        "last_report_title": "🧾 Сіздің соңғы шағымыңыз:",
        "last_report_status": "қарауға жіберілді",
        "choose_category": (
            "📂 Санатты таңдаңыз\n\n"
            "Өтінеміз, ең сәйкес келетін нұсқаны таңдаңыз."
        ),
        "choose_transport_branch": (
            "🚌 Жағдай түрін нақтылаңыз\n\n"
            "Қай көлік түрі туралы екенін таңдаңыз."
        ),
        "choose_driver_type": (
            "🚗 Көлікке қатысты жағдай түрін нақтылаңыз\n\n"
            "Ең сәйкес келетін нұсқаны таңдаңыз."
        ),
        "transport_route": (
            "🚌 Маршрут нөмірін көрсетіңіз\n\n"
            "Автобус немесе маршрут нөмірін білсеңіз, жазыңыз.\n"
            "Білмесеңіз — «Білмеймін» түймесін басыңыз.\n\n"
            "Мысал:\n"
            "45\n"
            "12А"
        ),
        "short_text": (
            "📝 Жағдайды қысқаша сипаттаңыз\n\n"
            "Өтінеміз, не болғанын бірден түсінікті болатындай жазыңыз.\n\n"
            "Мысал:\n"
            "Аулада бірнеше күннен бері қоқыс шығарылмай жатыр, контейнерлер толып кеткен."
        ),
        "short_text_transport_public": (
            "📝 Жағдайды қысқаша сипаттаңыз\n\n"
            "Өтінеміз, көлікте немесе маршрутта не болғанын жазыңыз.\n\n"
            "Мысал:\n"
            "Автобус жүргізушісі аялдамада жолаушыларды күтпей есікті тез жауып кетті."
        ),
        "short_text_transport_driver": (
            "📝 Жағдайды қысқаша сипаттаңыз\n\n"
            "Өтінеміз, жолда немесе көлікке қатысты не болғанын жазыңыз.\n\n"
            "Мысал:\n"
            "Жүргізуші көлікті жаяу жүргіншілер аймағына қойып кетті."
        ),
        "district": (
            "📍 Ауданды таңдаңыз\n\n"
            "Өтінеміз, жағдай болған ауданды таңдаңыз."
        ),
        "address": (
            "🏠 Оқиға болған орынды көрсетіңіз\n\n"
            "Көше немесе шағынаудан, үй нөмірі не түсінікті бағдар жазыңыз.\n\n"
            "Мысал:\n"
            "Нұрсәт ш/а, 12 үй\n"
            "немесе\n"
            "Тәуке хан көшесі, аялдама жанында"
        ),
        "transport_place": (
            "📍 Оқиға болған орынды көрсетіңіз\n\n"
            "Аялдама, көше, бағдар немесе түсінікті басқа орынды жазыңыз.\n\n"
            "Мысал:\n"
            "нарық жанындағы аялдама\n"
            "немесе\n"
            "Республика көшесі, дүкен қасында"
        ),
        "event_time": (
            "📅 Бұл қашан болды\n\n"
            "Төменнен бір нұсқаны таңдаңыз\n"
            "немесе күнді өзіңіз енгізіңіз."
        ),
        "custom_date": (
            "📅 Күнін немесе уақытын енгізіңіз\n\n"
            "Нақты күнді көрсетуге болады\n"
            "немесе түсінікті түрде жазыңыз.\n\n"
            "Мысал:\n"
            "16.04.2026\n"
            "немесе\n"
            "2 күн бұрын"
        ),
        "photo": (
            "📸 Егер фото болса, қосыңыз\n\n"
            "Бір сурет жіберіңіз.\n"
            "Фото жоқ болса — «Өткізіп жіберу» түймесін басыңыз."
        ),
        "photo_expected": (
            "📸 Қазір бір фото күтілуде\n\n"
            "Фото жоқ болса — «Өткізіп жіберу» түймесін басыңыз."
        ),
        "confirm_title": "✅ Жіберер алдында шағымды тексеріңіз:",
        "confirm_send": "Жіберу",
        "confirm_edit": "Өзгерту",
        "confirm_cancel": "Бас тарту",
        "edit_title": "✏️ Нені өзгерткіңіз келеді?",
        "edit_text": "Мәтінді өзгерту",
        "edit_address": "Мекенжайды өзгерту",
        "edit_date": "Күнін өзгерту",
        "edit_photo": "Фотоны өзгерту",
        "sent": (
            "✅ Шағым қабылданды.\n\n"
            "Ол мазмұнды қарауға жіберілді.\n\n"
            f"Келесі шағымды {COOLDOWN_MINUTES} минуттан кейін жібере аласыз."
        ),
        "cancelled": "❌ Жіберу тоқтатылды.",
        "too_soon_full": "⌛ Келесі шағымға дейін қалды: {time}",
        "too_soon_warn": "⌛ Әлі ерте. Қалды: {time}\n\nТым жиі баспаңыз — бұл ботқа артық жүктеме береді.",
        "too_soon_short": "Шектеу аяқталғанша күтіңіз.",
        "daily_limit": "📛 Бүгін сіз 3 шағым жіберіп қойдыңыз.\n\nҚайтадан ертең көріңіз.",
        "bad_short_min": f"Мәтін тым қысқа.\n\nКемінде {MIN_TEXT_LENGTH} таңба қажет.",
        "bad_short_max": f"Мәтін тым ұзын.\n\nСипаттаманы {MAX_TEXT_LENGTH} таңбаға дейін қысқартыңыз.",
        "bad_address_min": "Орын тым қысқа көрсетілген.\n\nКөше, аялдама, үй немесе бағдар жазыңыз.",
        "bad_address_max": f"Орын сипаттамасы тым ұзын.\n\nОны {MAX_ADDRESS_LENGTH} таңбаға дейін қысқартыңыз.",
        "bad_date": "Күнді немесе уақытты түсінікті түрде жазыңыз.\n\nМысалы: 16.04.2026 немесе кеше кешке.",
        "bad_photo": "Бір фото жіберіңіз немесе «Өткізіп жіберу» түймесін басыңыз.",
        "blocked": "Қолжетімділігіңіз шектелген.\n\nӘкімшіге жазыңыз.",
        "status_photo": "Фото бар",
        "status_no_photo": "Фото жоқ",
        "preview_category": "Санат",
        "preview_transport": "Көлік түрі",
        "preview_driver_type": "Жағдай түрі",
        "preview_route": "Маршрут",
        "preview_text": "Сипаттама",
        "preview_district": "Аудан",
        "preview_address": "Мекенжай / бағдар",
        "preview_date": "Қашан болды",
        "preview_status": "Фото",
        "preview_status_field": "Күйі",
        "unknown_action": "Белгісіз әрекет.",
        "report_not_found": "Шағым деректері табылмады.\n\nҚайта бастап көріңіз.",
        "error_prefix": "Қате орын алды:",
        "admin_title": "Жаңа оқиға №{number:04d}",
        "admin_ready": "Жариялауға арналған қара жоба",
        "admin_status": "Мәртебе: қарауға дайын",
        "choose_language_again": "🌐 Жаңа тілді таңдаңыз:",
        "duplicate_report": "Сіз бұған өте ұқсас шағым жіберген сияқтысыз.\n\nЕгер бұл жаңа жағдай болса, мәтінді нақтылап қайта жіберіңіз.",
    },
}

# =========================
# JSON ХРАНИЛИЩЕ
# =========================
def ensure_json_file(path: Path, default_data: Any) -> None:
    if not path.exists():
        path.write_text(json.dumps(default_data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_json(path: Path, default_data: Any) -> Any:
    ensure_json_file(path, default_data)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        path.write_text(json.dumps(default_data, ensure_ascii=False, indent=2), encoding="utf-8")
        return default_data


def save_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_users() -> Dict[str, Any]:
    return load_json(USERS_FILE, {})


def get_reports() -> Dict[str, Any]:
    return load_json(REPORTS_FILE, {"last_number": 0, "items": []})


def save_users(data: Dict[str, Any]) -> None:
    save_json(USERS_FILE, data)


def save_reports(data: Dict[str, Any]) -> None:
    save_json(REPORTS_FILE, data)


# =========================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =========================
def get_lang(context: ContextTypes.DEFAULT_TYPE) -> str:
    return context.user_data.get("lang", "ru")


def now_local() -> datetime:
    return datetime.now(TIMEZONE)


def now_iso() -> str:
    return now_local().isoformat()


def today_str() -> str:
    return now_local().strftime("%Y-%m-%d")


def format_remaining(seconds: int) -> str:
    if seconds <= 0:
        return "0 мин 0 сек"
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes} мин {secs} сек"


def format_created(dt_iso: str) -> str:
    dt = datetime.fromisoformat(dt_iso)
    return dt.strftime("%d.%m.%Y, %H:%M")


def get_or_create_user(user_id: int) -> Dict[str, Any]:
    users = get_users()
    key = str(user_id)
    if key not in users:
        users[key] = {
            "lang": "ru",
            "accepted_rules": False,
            "last_submit_at": None,
            "is_banned": False,
            "daily_date": today_str(),
            "daily_count": 0,
            "cooldown_taps": 0,
            "last_report_preview": None,
        }
        save_users(users)
    else:
        changed = False
        defaults = {
            "lang": "ru",
            "accepted_rules": False,
            "last_submit_at": None,
            "is_banned": False,
            "daily_date": today_str(),
            "daily_count": 0,
            "cooldown_taps": 0,
            "last_report_preview": None,
        }
        for k, v in defaults.items():
            if k not in users[key]:
                users[key][k] = v
                changed = True
        if changed:
            save_users(users)
    return users[key]


def update_user(user_id: int, **kwargs: Any) -> None:
    users = get_users()
    key = str(user_id)
    if key not in users:
        get_or_create_user(user_id)
        users = get_users()
    users[key].update(kwargs)
    save_users(users)


def reset_daily_if_needed(user_id: int) -> Dict[str, Any]:
    user = get_or_create_user(user_id)
    if user.get("daily_date") != today_str():
        user["daily_date"] = today_str()
        user["daily_count"] = 0
        user["cooldown_taps"] = 0
        update_user(user_id, daily_date=user["daily_date"], daily_count=0, cooldown_taps=0)
        user = get_or_create_user(user_id)
    return user


def check_daily_limit(user_id: int) -> bool:
    user = reset_daily_if_needed(user_id)
    return int(user.get("daily_count", 0)) >= DAILY_LIMIT


def check_cooldown(user_id: int) -> tuple[bool, int, int]:
    user = get_or_create_user(user_id)
    last_submit_at = user.get("last_submit_at")
    if not last_submit_at:
        update_user(user_id, cooldown_taps=0)
        return False, 0, 0

    last_dt = datetime.fromisoformat(last_submit_at)
    next_dt = last_dt + timedelta(minutes=COOLDOWN_MINUTES)
    remaining = int((next_dt - now_local()).total_seconds())
    if remaining > 0:
        taps = int(user.get("cooldown_taps", 0)) + 1
        update_user(user_id, cooldown_taps=taps)
        return True, remaining, taps

    update_user(user_id, cooldown_taps=0)
    return False, 0, 0


def increment_daily_submit(user_id: int) -> None:
    user = reset_daily_if_needed(user_id)
    count = int(user.get("daily_count", 0)) + 1
    update_user(user_id, daily_count=count, last_submit_at=now_iso(), cooldown_taps=0)


def sanitize_text(text: str) -> str:
    text = text.strip()
    text = re.sub(r"https?://\S+|www\.\S+", "[ссылка скрыта]", text, flags=re.IGNORECASE)
    text = re.sub(r"@\w+", "[@скрыто]", text)
    text = re.sub(r"\+?\d[\d\s\-()]{7,}\d", "[номер скрыт]", text)
    bad_words = ["дурак", "идиот", "тупой", "тварь", "мразь", "сволочь"]
    for word in bad_words:
        text = re.sub(rf"\b{re.escape(word)}\b", "***", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text)
    return text


def normalize_for_compare(text: Optional[str]) -> str:
    if text is None:
        return ""
    text = str(text).lower().strip()
    text = re.sub(r"[^\w\sа-яәіңғүұқөһ-]", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text)
    return text


def is_duplicate_report(user_id: int, report: Dict[str, Any]) -> bool:
    reports = get_reports().get("items", [])
    current_text = normalize_for_compare(report.get("short_text", ""))
    current_address = normalize_for_compare(report.get("address", ""))
    current_category = normalize_for_compare(report.get("category", ""))
    current_district = normalize_for_compare(report.get("district", ""))
    current_branch = normalize_for_compare(report.get("transport_branch", ""))
    current_route = normalize_for_compare(report.get("transport_route", ""))
    current_driver_type = normalize_for_compare(report.get("driver_type", ""))

    for item in reversed(reports[-20:]):
        if item.get("user_id") != user_id:
            continue

        old_text = normalize_for_compare(item.get("short_text", ""))
        old_address = normalize_for_compare(item.get("address", ""))
        old_category = normalize_for_compare(item.get("category", ""))
        old_district = normalize_for_compare(item.get("district", ""))
        old_branch = normalize_for_compare(item.get("transport_branch", ""))
        old_route = normalize_for_compare(item.get("transport_route", ""))
        old_driver_type = normalize_for_compare(item.get("driver_type", ""))

        text_ratio = SequenceMatcher(None, current_text, old_text).ratio()
        address_ratio = SequenceMatcher(None, current_address, old_address).ratio() if current_address and old_address else 0

        same_meta = (
            current_category == old_category
            and current_district == old_district
            and current_branch == old_branch
            and current_route == old_route
            and current_driver_type == old_driver_type
        )

        if same_meta and (text_ratio >= DUPLICATE_SIMILARITY or address_ratio >= DUPLICATE_SIMILARITY):
            return True

    return False


def ensure_report(context: ContextTypes.DEFAULT_TYPE) -> Dict[str, Any]:
    if "report" not in context.user_data:
        context.user_data["report"] = {}
    return context.user_data["report"]


def clear_current_form(context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop("report", None)


def build_main_menu(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [TEXTS[lang]["menu_send"]],
            [TEXTS[lang]["menu_last_report"], TEXTS[lang]["menu_how_to"]],
            [TEXTS[lang]["menu_rules"], TEXTS[lang]["menu_about"]],
            [TEXTS[lang]["menu_change_language"], TEXTS[lang]["menu_share_bot"]],
            [TEXTS[lang]["menu_channel"]],
            [TEXTS[lang]["menu_clear_form"]],
        ],
        resize_keyboard=True,
    )


def build_navigation_buttons(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[TEXTS[lang]["back"], TEXTS[lang]["main_menu"]], [TEXTS[lang]["menu_clear_form"]]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def build_categories(lang: str) -> ReplyKeyboardMarkup:
    cats = CATEGORIES[lang]
    rows = [
        [cats[0], cats[1]],
        [cats[2], cats[3]],
        [cats[4], cats[5]],
        [cats[6], cats[7]],
        [TEXTS[lang]["back"], TEXTS[lang]["main_menu"]],
        [TEXTS[lang]["menu_clear_form"]],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=True)


def build_transport_branches(lang: str) -> ReplyKeyboardMarkup:
    items = TRANSPORT_BRANCHES[lang]
    rows = [
        [items[0]],
        [items[1]],
        [TEXTS[lang]["back"], TEXTS[lang]["main_menu"]],
        [TEXTS[lang]["menu_clear_form"]],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=True)


def build_transport_driver_types(lang: str) -> ReplyKeyboardMarkup:
    items = TRANSPORT_DRIVER_TYPES[lang]
    rows = [
        [items[0]],
        [items[1]],
        [items[2]],
        [items[3]],
        [TEXTS[lang]["back"], TEXTS[lang]["main_menu"]],
        [TEXTS[lang]["menu_clear_form"]],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=True)


def build_transport_route_buttons(lang: str) -> ReplyKeyboardMarkup:
    rows = [
        [TEXTS[lang]["unknown_route"]],
        [TEXTS[lang]["back"], TEXTS[lang]["main_menu"]],
        [TEXTS[lang]["menu_clear_form"]],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=True)


def build_districts(lang: str) -> ReplyKeyboardMarkup:
    arr = DISTRICTS[lang]
    rows = [
        [arr[0], arr[1]],
        [arr[2], arr[3]],
        [arr[4]],
        [TEXTS[lang]["back"], TEXTS[lang]["main_menu"]],
        [TEXTS[lang]["menu_clear_form"]],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=True)


def build_date_options(lang: str) -> ReplyKeyboardMarkup:
    arr = DATE_OPTIONS[lang]
    rows = [
        [arr[0], arr[1]],
        [arr[2], arr[3]],
        [arr[4]],
        [arr[5]],
        [TEXTS[lang]["back"], TEXTS[lang]["main_menu"]],
        [TEXTS[lang]["menu_clear_form"]],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=True)


def build_photo_options(lang: str, editing: bool = False) -> ReplyKeyboardMarkup:
    first_row = [TEXTS[lang]["skip"]]
    if editing:
        first_row.append(TEXTS[lang]["remove_photo"])
    rows = [first_row, [TEXTS[lang]["back"], TEXTS[lang]["main_menu"]], [TEXTS[lang]["menu_clear_form"]]]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=True)


def build_rules_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(TEXTS[lang]["agree"], callback_data="agree_rules")],
            [InlineKeyboardButton(TEXTS[lang]["more_rules"], callback_data="show_rules")],
        ]
    )


def build_confirm_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(TEXTS[lang]["confirm_send"], callback_data="send_report")],
            [InlineKeyboardButton(TEXTS[lang]["confirm_edit"], callback_data="edit_report")],
            [InlineKeyboardButton(TEXTS[lang]["confirm_cancel"], callback_data="cancel_report")],
        ]
    )


def build_edit_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(TEXTS[lang]["edit_text"], callback_data="edit_text")],
            [InlineKeyboardButton(TEXTS[lang]["edit_address"], callback_data="edit_address")],
            [InlineKeyboardButton(TEXTS[lang]["edit_date"], callback_data="edit_date")],
            [InlineKeyboardButton(TEXTS[lang]["edit_photo"], callback_data="edit_photo")],
            [InlineKeyboardButton(TEXTS[lang]["back"], callback_data="back_to_preview")],
        ]
    )


def preview_text(context: ContextTypes.DEFAULT_TYPE) -> str:
    lang = get_lang(context)
    report = context.user_data["report"]
    photo_status = TEXTS[lang]["status_photo"] if report.get("photo_file_id") else TEXTS[lang]["status_no_photo"]

    parts = [
        f"<b>{TEXTS[lang]['confirm_title']}</b>",
        "",
        f"<b>{TEXTS[lang]['preview_category']}:</b> {html.escape(report['category'])}",
    ]

    if report.get("transport_branch"):
        parts.append(f"<b>{TEXTS[lang]['preview_transport']}:</b> {html.escape(report['transport_branch'])}")

    if report.get("transport_route"):
        parts.append(f"<b>{TEXTS[lang]['preview_route']}:</b> {html.escape(report['transport_route'])}")

    if report.get("driver_type"):
        parts.append(f"<b>{TEXTS[lang]['preview_driver_type']}:</b> {html.escape(report['driver_type'])}")

    if report.get("district"):
        parts.append(f"<b>{TEXTS[lang]['preview_district']}:</b> {html.escape(report['district'])}")

    parts.extend([
        f"<b>{TEXTS[lang]['preview_address']}:</b> {html.escape(report['address'])}",
        f"<b>{TEXTS[lang]['preview_date']}:</b> {html.escape(report['event_time'])}",
        f"<b>{TEXTS[lang]['preview_text']}:</b> {html.escape(report['short_text'])}",
        f"<b>{TEXTS[lang]['preview_status']}:</b> {html.escape(photo_status)}",
    ])

    return "\n".join(parts)


def make_admin_text(number: int, report: Dict[str, Any], user: Any) -> str:
    created = format_created(report["created_at"])

    parts = [
        f"<b>{TEXTS['ru']['admin_title'].format(number=number)}</b>",
        f"<b>{TEXTS['ru']['admin_status']}</b>",
        "",
        f"<b>Дата создания:</b> {created}",
        f"<b>User ID:</b> <code>{user.id}</code>",
        f"<b>Username:</b> {html.escape(user.username or '-')}",
        f"<b>Язык:</b> {html.escape(report['lang'])}",
        "",
        f"<b>Категория:</b> {html.escape(report['category'])}",
    ]

    if report.get("transport_branch"):
        parts.append(f"<b>Тип транспорта:</b> {html.escape(report['transport_branch'])}")
    if report.get("transport_route"):
        parts.append(f"<b>Маршрут:</b> {html.escape(report['transport_route'])}")
    if report.get("driver_type"):
        parts.append(f"<b>Тип ситуации:</b> {html.escape(report['driver_type'])}")
    if report.get("district"):
        parts.append(f"<b>Район:</b> {html.escape(report['district'])}")

    parts.extend([
        f"<b>Адрес / ориентир:</b> {html.escape(report['address'])}",
        f"<b>Когда произошло:</b> {html.escape(report['event_time'])}",
        f"<b>Описание:</b> {html.escape(report['short_text'])}",
        "",
        f"<b>{TEXTS['ru']['admin_ready']}:</b>",
        "В городе Шымкент поступило сообщение о следующей ситуации.",
        "",
        f"<b>Категория:</b> {html.escape(report['category'])}",
    ])

    if report.get("transport_branch"):
        parts.append(f"<b>Тип транспорта:</b> {html.escape(report['transport_branch'])}")
    if report.get("transport_route"):
        parts.append(f"<b>Маршрут:</b> {html.escape(report['transport_route'])}")
    if report.get("driver_type"):
        parts.append(f"<b>Тип ситуации:</b> {html.escape(report['driver_type'])}")
    if report.get("district"):
        parts.append(f"<b>Район:</b> {html.escape(report['district'])}")

    parts.extend([
        f"<b>Адрес:</b> {html.escape(report['address'])}",
        f"<b>Когда произошло:</b> {html.escape(report['event_time'])}",
        f"<b>Описание:</b> {html.escape(report['short_text'])}",
    ])

    return "\n".join(parts)


def save_last_report(user_id: int, item: Dict[str, Any], lang: str) -> None:
    users = get_users()
    key = str(user_id)
    if key not in users:
        get_or_create_user(user_id)
        users = get_users()

    users[key]["last_report_preview"] = {
        "number": item["number"],
        "category": item["category"],
        "transport_branch": item.get("transport_branch"),
        "transport_route": item.get("transport_route"),
        "driver_type": item.get("driver_type"),
        "district": item.get("district"),
        "address": item["address"],
        "event_time": item["event_time"],
        "short_text": item["short_text"],
        "created_at": item["created_at"],
        "lang": lang,
        "status": "pending",
    }
    save_users(users)


def get_last_report_preview(user_id: int) -> Optional[Dict[str, Any]]:
    user = get_or_create_user(user_id)
    return user.get("last_report_preview")


async def show_preview_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_lang(context)
    target = update.message if update.message else update.callback_query.message
    await target.reply_text(
        preview_text(context),
        parse_mode=ParseMode.HTML,
        reply_markup=build_confirm_keyboard(lang),
    )
    return CONFIRM


async def send_to_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, notice_key: Optional[str] = None) -> int:
    lang = get_lang(context)
    clear_current_form(context)
    text = TEXTS[lang][notice_key] if notice_key else TEXTS[lang]["menu_text"]
    if update.message:
        await update.message.reply_text(text, reply_markup=build_main_menu(lang))
    else:
        await update.callback_query.message.reply_text(text, reply_markup=build_main_menu(lang))
    return MENU


def append_warning(lang: str, text: str, transport: bool = False) -> str:
    tail = TEXTS[lang]["transport_warning_tail"] if transport else TEXTS[lang]["warning_tail"]
    return f"{text}\n\n{tail}"


def is_transport_report(report: Dict[str, Any]) -> bool:
    return bool(report.get("transport_branch"))


def get_short_text_prompt(lang: str, report: Dict[str, Any]) -> str:
    if report.get("transport_branch") == TRANSPORT_BRANCHES[lang][0]:
        return append_warning(lang, TEXTS[lang]["short_text_transport_public"], transport=True)
    if report.get("transport_branch") == TRANSPORT_BRANCHES[lang][1]:
        return append_warning(lang, TEXTS[lang]["short_text_transport_driver"], transport=True)
    return append_warning(lang, TEXTS[lang]["short_text"])


def get_address_prompt(lang: str, report: Dict[str, Any]) -> str:
    if is_transport_report(report):
        return append_warning(lang, TEXTS[lang]["transport_place"], transport=True)
    return append_warning(lang, TEXTS[lang]["address"])


def get_event_time_prompt(lang: str, report: Dict[str, Any]) -> str:
    return append_warning(lang, TEXTS[lang]["event_time"], transport=is_transport_report(report))


def get_custom_date_prompt(lang: str, report: Dict[str, Any]) -> str:
    return append_warning(lang, TEXTS[lang]["custom_date"], transport=is_transport_report(report))


def get_photo_prompt(lang: str, report: Dict[str, Any]) -> str:
    return append_warning(lang, TEXTS[lang]["photo"], transport=is_transport_report(report))


# =========================
# ОБРАБОТЧИКИ
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    stored = get_or_create_user(user.id)
    context.user_data.clear()
    context.user_data["lang"] = stored.get("lang", "ru")

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Русский", callback_data="lang_ru")],
            [InlineKeyboardButton("Қазақша", callback_data="lang_kz")],
        ]
    )
    await update.message.reply_text(TEXTS["ru"]["language_title"], reply_markup=keyboard)
    return LANG


async def choose_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    lang = "ru" if query.data == "lang_ru" else "kz"
    context.user_data["lang"] = lang
    update_user(update.effective_user.id, lang=lang)

    await query.message.reply_text(
        TEXTS[lang]["rules"],
        parse_mode=ParseMode.HTML,
        reply_markup=build_rules_keyboard(lang),
    )
    return RULES_ACK


async def rules_actions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    lang = get_lang(context)

    if query.data == "show_rules":
        await query.message.reply_text(TEXTS[lang]["rules"], parse_mode=ParseMode.HTML)
        return RULES_ACK

    if query.data == "agree_rules":
        update_user(update.effective_user.id, accepted_rules=True)
        await query.message.reply_text(TEXTS[lang]["menu_text"], reply_markup=build_main_menu(lang))
        return MENU

    return RULES_ACK


async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_lang(context)
    text = (update.message.text or "").strip()
    user_id = update.effective_user.id
    user_info = reset_daily_if_needed(user_id)

    if user_info.get("is_banned"):
        await update.message.reply_text(TEXTS[lang]["blocked"])
        return MENU

    if text == TEXTS[lang]["menu_rules"]:
        await update.message.reply_text(TEXTS[lang]["rules"], parse_mode=ParseMode.HTML, reply_markup=build_main_menu(lang))
        return MENU

    if text == TEXTS[lang]["menu_about"]:
        await update.message.reply_text(TEXTS[lang]["about"], reply_markup=build_main_menu(lang))
        return MENU

    if text == TEXTS[lang]["menu_how_to"]:
        await update.message.reply_text(TEXTS[lang]["how_to"], reply_markup=build_main_menu(lang))
        return MENU

    if text == TEXTS[lang]["menu_share_bot"]:
        await update.message.reply_text(
            TEXTS[lang]["share_bot"].format(bot_username=BOT_USERNAME),
            reply_markup=build_main_menu(lang),
        )
        return MENU

    if text == TEXTS[lang]["menu_channel"]:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(TEXTS[lang]["menu_channel"], url=CHANNEL_URL)]
        ])
        await update.message.reply_text(
            TEXTS[lang]["channel_text"],
            reply_markup=keyboard,
        )
        return MENU

    if text == TEXTS[lang]["menu_clear_form"]:
        if context.user_data.get("report"):
            clear_current_form(context)
            await update.message.reply_text(TEXTS[lang]["clear_form_done"], reply_markup=build_main_menu(lang))
        else:
            await update.message.reply_text(TEXTS[lang]["clear_form_empty"], reply_markup=build_main_menu(lang))
        return MENU

    if text == TEXTS[lang]["menu_last_report"]:
        preview = get_last_report_preview(user_id)
        if not preview:
            await update.message.reply_text(TEXTS[lang]["last_report_empty"], reply_markup=build_main_menu(lang))
            return MENU

        parts = [
            f"<b>{TEXTS[lang]['last_report_title']}</b>",
            "",
            f"<b>№:</b> {preview['number']:04d}",
            f"<b>{TEXTS[lang]['preview_category']}:</b> {html.escape(preview['category'])}",
        ]

        if preview.get("transport_branch"):
            parts.append(f"<b>{TEXTS[lang]['preview_transport']}:</b> {html.escape(preview['transport_branch'])}")
        if preview.get("transport_route"):
            parts.append(f"<b>{TEXTS[lang]['preview_route']}:</b> {html.escape(preview['transport_route'])}")
        if preview.get("driver_type"):
            parts.append(f"<b>{TEXTS[lang]['preview_driver_type']}:</b> {html.escape(preview['driver_type'])}")
        if preview.get("district"):
            parts.append(f"<b>{TEXTS[lang]['preview_district']}:</b> {html.escape(preview['district'])}")

        parts.extend([
            f"<b>{TEXTS[lang]['preview_address']}:</b> {html.escape(preview['address'])}",
            f"<b>{TEXTS[lang]['preview_date']}:</b> {html.escape(preview['event_time'])}",
            f"<b>{TEXTS[lang]['preview_text']}:</b> {html.escape(preview['short_text'])}",
            f"<b>{TEXTS[lang]['preview_status_field']}:</b> {TEXTS[lang]['last_report_status']}",
            f"<b>Дата:</b> {format_created(preview['created_at'])}",
        ])

        await update.message.reply_text(
            "\n".join(parts),
            parse_mode=ParseMode.HTML,
            reply_markup=build_main_menu(lang),
        )
        return MENU

    if text == TEXTS[lang]["menu_change_language"]:
        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("Русский", callback_data="lang_ru_menu")],
                [InlineKeyboardButton("Қазақша", callback_data="lang_kz_menu")],
            ]
        )
        await update.message.reply_text(TEXTS[lang]["choose_language_again"], reply_markup=keyboard)
        return MENU

    if text == TEXTS[lang]["menu_send"]:
        if check_daily_limit(user_id):
            await update.message.reply_text(TEXTS[lang]["daily_limit"], reply_markup=build_main_menu(lang))
            return MENU

        cooldown, remaining, taps = check_cooldown(user_id)
        if cooldown:
            if taps == 1:
                msg = TEXTS[lang]["too_soon_full"].format(time=format_remaining(remaining))
            elif taps == 2:
                msg = TEXTS[lang]["too_soon_warn"].format(time=format_remaining(remaining))
            else:
                msg = TEXTS[lang]["too_soon_short"]
            await update.message.reply_text(msg, reply_markup=build_main_menu(lang))
            return MENU

        context.user_data["report"] = {
            "started_at": now_iso(),
            "transport_branch": None,
            "transport_route": None,
            "driver_type": None,
            "district": None,
        }
        await update.message.reply_text(TEXTS[lang]["choose_category"], reply_markup=build_categories(lang))
        return CATEGORY

    await update.message.reply_text(TEXTS[lang]["menu_text"], reply_markup=build_main_menu(lang))
    return MENU


async def change_language_from_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    lang = "ru" if query.data.endswith("ru_menu") else "kz"
    context.user_data["lang"] = lang
    update_user(update.effective_user.id, lang=lang)
    await query.message.reply_text(TEXTS[lang]["menu_text"], reply_markup=build_main_menu(lang))


async def category_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_lang(context)
    text = (update.message.text or "").strip()

    if text == TEXTS[lang]["main_menu"]:
        return await send_to_main_menu(update, context)
    if text == TEXTS[lang]["menu_clear_form"]:
        return await send_to_main_menu(update, context, "clear_form_done")
    if text == TEXTS[lang]["back"]:
        return await send_to_main_menu(update, context)

    if text not in CATEGORIES[lang]:
        await update.message.reply_text(TEXTS[lang]["choose_category"], reply_markup=build_categories(lang))
        return CATEGORY

    report = ensure_report(context)
    report["category"] = text
    report["transport_branch"] = None
    report["transport_route"] = None
    report["driver_type"] = None
    report["district"] = None

    if text == CATEGORIES[lang][6]:
        await update.message.reply_text(TEXTS[lang]["choose_transport_branch"], reply_markup=build_transport_branches(lang))
        return TRANSPORT_BRANCH

    await update.message.reply_text(get_short_text_prompt(lang, report), reply_markup=build_navigation_buttons(lang))
    return SHORT_TEXT


async def transport_branch_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_lang(context)
    text = (update.message.text or "").strip()
    report = ensure_report(context)

    if text == TEXTS[lang]["main_menu"]:
        return await send_to_main_menu(update, context)
    if text == TEXTS[lang]["menu_clear_form"]:
        return await send_to_main_menu(update, context, "clear_form_done")
    if text == TEXTS[lang]["back"]:
        await update.message.reply_text(TEXTS[lang]["choose_category"], reply_markup=build_categories(lang))
        return CATEGORY

    if text not in TRANSPORT_BRANCHES[lang]:
        await update.message.reply_text(TEXTS[lang]["choose_transport_branch"], reply_markup=build_transport_branches(lang))
        return TRANSPORT_BRANCH

    report["transport_branch"] = text
    report["district"] = None

    if text == TRANSPORT_BRANCHES[lang][0]:
        await update.message.reply_text(
            append_warning(lang, TEXTS[lang]["transport_route"], transport=True),
            reply_markup=build_transport_route_buttons(lang),
        )
        return TRANSPORT_ROUTE

    await update.message.reply_text(
        append_warning(lang, TEXTS[lang]["choose_driver_type"], transport=True),
        reply_markup=build_transport_driver_types(lang),
    )
    return TRANSPORT_DRIVER_TYPE


async def transport_route_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_lang(context)
    text = (update.message.text or "").strip()
    report = ensure_report(context)

    if text == TEXTS[lang]["main_menu"]:
        return await send_to_main_menu(update, context)
    if text == TEXTS[lang]["menu_clear_form"]:
        return await send_to_main_menu(update, context, "clear_form_done")
    if text == TEXTS[lang]["back"]:
        await update.message.reply_text(TEXTS[lang]["choose_transport_branch"], reply_markup=build_transport_branches(lang))
        return TRANSPORT_BRANCH

    cleaned = sanitize_text(text)
    if not cleaned:
        await update.message.reply_text(
            append_warning(lang, TEXTS[lang]["transport_route"], transport=True),
            reply_markup=build_transport_route_buttons(lang),
        )
        return TRANSPORT_ROUTE

    report["transport_route"] = cleaned
    await update.message.reply_text(get_address_prompt(lang, report), reply_markup=build_navigation_buttons(lang))
    return ADDRESS


async def transport_driver_type_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_lang(context)
    text = (update.message.text or "").strip()
    report = ensure_report(context)

    if text == TEXTS[lang]["main_menu"]:
        return await send_to_main_menu(update, context)
    if text == TEXTS[lang]["menu_clear_form"]:
        return await send_to_main_menu(update, context, "clear_form_done")
    if text == TEXTS[lang]["back"]:
        await update.message.reply_text(TEXTS[lang]["choose_transport_branch"], reply_markup=build_transport_branches(lang))
        return TRANSPORT_BRANCH

    if text not in TRANSPORT_DRIVER_TYPES[lang]:
        await update.message.reply_text(
            append_warning(lang, TEXTS[lang]["choose_driver_type"], transport=True),
            reply_markup=build_transport_driver_types(lang),
        )
        return TRANSPORT_DRIVER_TYPE

    report["driver_type"] = text
    await update.message.reply_text(get_address_prompt(lang, report), reply_markup=build_navigation_buttons(lang))
    return ADDRESS


async def short_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_lang(context)
    text = (update.message.text or "").strip()
    report = ensure_report(context)

    if text == TEXTS[lang]["main_menu"]:
        return await send_to_main_menu(update, context)
    if text == TEXTS[lang]["menu_clear_form"]:
        return await send_to_main_menu(update, context, "clear_form_done")
    if text == TEXTS[lang]["back"]:
        if is_transport_report(report):
            if report.get("transport_branch") == TRANSPORT_BRANCHES[lang][0]:
                await update.message.reply_text(
                    append_warning(lang, TEXTS[lang]["transport_route"], transport=True),
                    reply_markup=build_transport_route_buttons(lang),
                )
                return TRANSPORT_ROUTE
            await update.message.reply_text(
                append_warning(lang, TEXTS[lang]["choose_driver_type"], transport=True),
                reply_markup=build_transport_driver_types(lang),
            )
            return TRANSPORT_DRIVER_TYPE
        await update.message.reply_text(TEXTS[lang]["choose_category"], reply_markup=build_categories(lang))
        return CATEGORY

    cleaned = sanitize_text(text)
    if len(cleaned) < MIN_TEXT_LENGTH:
        await update.message.reply_text(TEXTS[lang]["bad_short_min"], reply_markup=build_navigation_buttons(lang))
        return SHORT_TEXT
    if len(cleaned) > MAX_TEXT_LENGTH:
        await update.message.reply_text(TEXTS[lang]["bad_short_max"], reply_markup=build_navigation_buttons(lang))
        return SHORT_TEXT

    report["short_text"] = cleaned

    if is_transport_report(report):
        await update.message.reply_text(get_photo_prompt(lang, report), reply_markup=build_photo_options(lang))
        return PHOTO

    await update.message.reply_text(append_warning(lang, TEXTS[lang]["district"]), reply_markup=build_districts(lang))
    return DISTRICT


async def district_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_lang(context)
    text = (update.message.text or "").strip()
    report = ensure_report(context)

    if text == TEXTS[lang]["main_menu"]:
        return await send_to_main_menu(update, context)
    if text == TEXTS[lang]["menu_clear_form"]:
        return await send_to_main_menu(update, context, "clear_form_done")
    if text == TEXTS[lang]["back"]:
        await update.message.reply_text(get_short_text_prompt(lang, report), reply_markup=build_navigation_buttons(lang))
        return SHORT_TEXT

    if text not in DISTRICTS[lang]:
        await update.message.reply_text(TEXTS[lang]["district"], reply_markup=build_districts(lang))
        return DISTRICT

    report["district"] = text
    await update.message.reply_text(get_address_prompt(lang, report), reply_markup=build_navigation_buttons(lang))
    return ADDRESS


async def address_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_lang(context)
    text = (update.message.text or "").strip()
    report = ensure_report(context)

    if text == TEXTS[lang]["main_menu"]:
        return await send_to_main_menu(update, context)
    if text == TEXTS[lang]["menu_clear_form"]:
        return await send_to_main_menu(update, context, "clear_form_done")
    if text == TEXTS[lang]["back"]:
        if is_transport_report(report):
            if report.get("transport_branch") == TRANSPORT_BRANCHES[lang][0]:
                await update.message.reply_text(
                    append_warning(lang, TEXTS[lang]["transport_route"], transport=True),
                    reply_markup=build_transport_route_buttons(lang),
                )
                return TRANSPORT_ROUTE
            await update.message.reply_text(
                append_warning(lang, TEXTS[lang]["choose_driver_type"], transport=True),
                reply_markup=build_transport_driver_types(lang),
            )
            return TRANSPORT_DRIVER_TYPE
        await update.message.reply_text(append_warning(lang, TEXTS[lang]["district"]), reply_markup=build_districts(lang))
        return DISTRICT

    cleaned = sanitize_text(text)
    if len(cleaned) < MIN_ADDRESS_LENGTH:
        await update.message.reply_text(TEXTS[lang]["bad_address_min"], reply_markup=build_navigation_buttons(lang))
        return ADDRESS
    if len(cleaned) > MAX_ADDRESS_LENGTH:
        await update.message.reply_text(TEXTS[lang]["bad_address_max"], reply_markup=build_navigation_buttons(lang))
        return ADDRESS

    report["address"] = cleaned
    await update.message.reply_text(get_event_time_prompt(lang, report), reply_markup=build_date_options(lang))
    return EVENT_TIME


async def event_time_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_lang(context)
    text = (update.message.text or "").strip()
    report = ensure_report(context)

    if text == TEXTS[lang]["main_menu"]:
        return await send_to_main_menu(update, context)
    if text == TEXTS[lang]["menu_clear_form"]:
        return await send_to_main_menu(update, context, "clear_form_done")
    if text == TEXTS[lang]["back"]:
        await update.message.reply_text(get_address_prompt(lang, report), reply_markup=build_navigation_buttons(lang))
        return ADDRESS

    if text not in DATE_OPTIONS[lang]:
        await update.message.reply_text(TEXTS[lang]["event_time"], reply_markup=build_date_options(lang))
        return EVENT_TIME

    if text == DATE_OPTIONS[lang][5]:
        await update.message.reply_text(get_custom_date_prompt(lang, report), reply_markup=build_navigation_buttons(lang))
        return CUSTOM_DATE

    report["event_time"] = text

    if is_transport_report(report):
        await update.message.reply_text(get_short_text_prompt(lang, report), reply_markup=build_navigation_buttons(lang))
        return SHORT_TEXT

    await update.message.reply_text(get_photo_prompt(lang, report), reply_markup=build_photo_options(lang))
    return PHOTO


async def custom_date_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_lang(context)
    text = (update.message.text or "").strip()
    report = ensure_report(context)

    if text == TEXTS[lang]["main_menu"]:
        return await send_to_main_menu(update, context)
    if text == TEXTS[lang]["menu_clear_form"]:
        return await send_to_main_menu(update, context, "clear_form_done")
    if text == TEXTS[lang]["back"]:
        await update.message.reply_text(get_event_time_prompt(lang, report), reply_markup=build_date_options(lang))
        return EVENT_TIME

    cleaned = sanitize_text(text)
    if len(cleaned) < 4:
        await update.message.reply_text(TEXTS[lang]["bad_date"], reply_markup=build_navigation_buttons(lang))
        return CUSTOM_DATE

    report["event_time"] = cleaned

    if is_transport_report(report):
        await update.message.reply_text(get_short_text_prompt(lang, report), reply_markup=build_navigation_buttons(lang))
        return SHORT_TEXT

    await update.message.reply_text(get_photo_prompt(lang, report), reply_markup=build_photo_options(lang))
    return PHOTO


async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_lang(context)
    report = ensure_report(context)
    text = (update.message.text or "").strip() if update.message.text else None

    if text == TEXTS[lang]["main_menu"]:
        return await send_to_main_menu(update, context)
    if text == TEXTS[lang]["menu_clear_form"]:
        return await send_to_main_menu(update, context, "clear_form_done")

    if text == TEXTS[lang]["back"]:
        if is_transport_report(report):
            await update.message.reply_text(get_short_text_prompt(lang, report), reply_markup=build_navigation_buttons(lang))
            return SHORT_TEXT
        await update.message.reply_text(get_event_time_prompt(lang, report), reply_markup=build_date_options(lang))
        return EVENT_TIME

    if text == TEXTS[lang]["skip"]:
        report["photo_file_id"] = None
        return await show_preview_message(update, context)

    if not update.message.photo:
        await update.message.reply_text(append_warning(lang, TEXTS[lang]["photo_expected"], transport=is_transport_report(report)), reply_markup=build_photo_options(lang))
        return PHOTO

    report["photo_file_id"] = update.message.photo[-1].file_id
    return await show_preview_message(update, context)


async def confirm_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    lang = get_lang(context)

    try:
        if query.data == "cancel_report":
            clear_current_form(context)
            await query.message.reply_text(TEXTS[lang]["cancelled"], reply_markup=build_main_menu(lang))
            return MENU

        if query.data == "edit_report":
            await query.message.reply_text(TEXTS[lang]["edit_title"], reply_markup=build_edit_keyboard(lang))
            return EDIT_CHOICE

        if query.data != "send_report":
            await query.message.reply_text(TEXTS[lang]["unknown_action"])
            return CONFIRM

        report = context.user_data.get("report")
        if not report:
            await query.message.reply_text(TEXTS[lang]["report_not_found"], reply_markup=build_main_menu(lang))
            return MENU

        user_id = update.effective_user.id

        if check_daily_limit(user_id):
            clear_current_form(context)
            await query.message.reply_text(TEXTS[lang]["daily_limit"], reply_markup=build_main_menu(lang))
            return MENU

        cooldown, remaining, taps = check_cooldown(user_id)
        if cooldown:
            if taps == 1:
                msg = TEXTS[lang]["too_soon_full"].format(time=format_remaining(remaining))
            elif taps == 2:
                msg = TEXTS[lang]["too_soon_warn"].format(time=format_remaining(remaining))
            else:
                msg = TEXTS[lang]["too_soon_short"]
            await query.message.reply_text(msg, reply_markup=build_main_menu(lang))
            return MENU

        if is_duplicate_report(user_id, report):
            await query.message.reply_text(TEXTS[lang]["duplicate_report"], reply_markup=build_confirm_keyboard(lang))
            return CONFIRM

        reports = get_reports()
        reports["last_number"] += 1
        number = reports["last_number"]

        item = {
            "number": number,
            "user_id": user_id,
            "lang": lang,
            "created_at": now_iso(),
            "category": report["category"],
            "transport_branch": report.get("transport_branch"),
            "transport_route": report.get("transport_route"),
            "driver_type": report.get("driver_type"),
            "district": report.get("district"),
            "address": report["address"],
            "event_time": report["event_time"],
            "short_text": report["short_text"],
            "photo_file_id": report.get("photo_file_id"),
        }

        reports["items"].append(item)
        save_reports(reports)
        save_last_report(user_id, item, lang)
        increment_daily_submit(user_id)

        admin_text = make_admin_text(number, item, update.effective_user)
        if item.get("photo_file_id"):
            await context.bot.send_photo(
                chat_id=ADMIN_CHAT_ID,
                photo=item["photo_file_id"],
                caption=admin_text[:1024],
                parse_mode=ParseMode.HTML,
            )
            if len(admin_text) > 1024:
                await context.bot.send_message(
                    chat_id=ADMIN_CHAT_ID,
                    text=admin_text,
                    parse_mode=ParseMode.HTML,
                )
        else:
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=admin_text,
                parse_mode=ParseMode.HTML,
            )

        clear_current_form(context)
        await query.message.reply_text(TEXTS[lang]["sent"], reply_markup=build_main_menu(lang))
        return MENU

    except Exception as e:
        print("ОШИБКА В confirm_handler:", e)
        await query.message.reply_text(f"{TEXTS[lang]['error_prefix']} {e}", reply_markup=build_main_menu(lang))
        return MENU


async def edit_choice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    lang = get_lang(context)
    report = ensure_report(context)

    if query.data == "back_to_preview":
        return await show_preview_message(update, context)
    if query.data == "edit_text":
        await query.message.reply_text(get_short_text_prompt(lang, report), reply_markup=build_navigation_buttons(lang))
        return EDIT_TEXT
    if query.data == "edit_address":
        await query.message.reply_text(get_address_prompt(lang, report), reply_markup=build_navigation_buttons(lang))
        return EDIT_ADDRESS
    if query.data == "edit_date":
        await query.message.reply_text(get_custom_date_prompt(lang, report), reply_markup=build_navigation_buttons(lang))
        return EDIT_DATE
    if query.data == "edit_photo":
        await query.message.reply_text(get_photo_prompt(lang, report), reply_markup=build_photo_options(lang, editing=True))
        return EDIT_PHOTO

    await query.message.reply_text(TEXTS[lang]["unknown_action"])
    return EDIT_CHOICE


async def edit_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_lang(context)
    text = (update.message.text or "").strip()

    if text == TEXTS[lang]["main_menu"]:
        return await send_to_main_menu(update, context)
    if text == TEXTS[lang]["menu_clear_form"]:
        return await send_to_main_menu(update, context, "clear_form_done")
    if text == TEXTS[lang]["back"]:
        return await show_preview_message(update, context)

    cleaned = sanitize_text(text)
    if len(cleaned) < MIN_TEXT_LENGTH:
        await update.message.reply_text(TEXTS[lang]["bad_short_min"], reply_markup=build_navigation_buttons(lang))
        return EDIT_TEXT
    if len(cleaned) > MAX_TEXT_LENGTH:
        await update.message.reply_text(TEXTS[lang]["bad_short_max"], reply_markup=build_navigation_buttons(lang))
        return EDIT_TEXT

    ensure_report(context)["short_text"] = cleaned
    return await show_preview_message(update, context)


async def edit_address_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_lang(context)
    text = (update.message.text or "").strip()

    if text == TEXTS[lang]["main_menu"]:
        return await send_to_main_menu(update, context)
    if text == TEXTS[lang]["menu_clear_form"]:
        return await send_to_main_menu(update, context, "clear_form_done")
    if text == TEXTS[lang]["back"]:
        return await show_preview_message(update, context)

    cleaned = sanitize_text(text)
    if len(cleaned) < MIN_ADDRESS_LENGTH:
        await update.message.reply_text(TEXTS[lang]["bad_address_min"], reply_markup=build_navigation_buttons(lang))
        return EDIT_ADDRESS
    if len(cleaned) > MAX_ADDRESS_LENGTH:
        await update.message.reply_text(TEXTS[lang]["bad_address_max"], reply_markup=build_navigation_buttons(lang))
        return EDIT_ADDRESS

    ensure_report(context)["address"] = cleaned
    return await show_preview_message(update, context)


async def edit_date_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_lang(context)
    text = (update.message.text or "").strip()

    if text == TEXTS[lang]["main_menu"]:
        return await send_to_main_menu(update, context)
    if text == TEXTS[lang]["menu_clear_form"]:
        return await send_to_main_menu(update, context, "clear_form_done")
    if text == TEXTS[lang]["back"]:
        return await show_preview_message(update, context)

    cleaned = sanitize_text(text)
    if len(cleaned) < 4:
        await update.message.reply_text(TEXTS[lang]["bad_date"], reply_markup=build_navigation_buttons(lang))
        return EDIT_DATE

    ensure_report(context)["event_time"] = cleaned
    return await show_preview_message(update, context)


async def edit_photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_lang(context)
    report = ensure_report(context)
    text = (update.message.text or "").strip() if update.message.text else None

    if text == TEXTS[lang]["main_menu"]:
        return await send_to_main_menu(update, context)
    if text == TEXTS[lang]["menu_clear_form"]:
        return await send_to_main_menu(update, context, "clear_form_done")
    if text == TEXTS[lang]["back"]:
        return await show_preview_message(update, context)
    if text == TEXTS[lang]["skip"] or text == TEXTS[lang]["remove_photo"]:
        report["photo_file_id"] = None
        return await show_preview_message(update, context)

    if not update.message.photo:
        await update.message.reply_text(
            append_warning(lang, TEXTS[lang]["photo_expected"], transport=is_transport_report(report)),
            reply_markup=build_photo_options(lang, editing=True),
        )
        return EDIT_PHOTO

    report["photo_file_id"] = update.message.photo[-1].file_id
    return await show_preview_message(update, context)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_lang(context)
    clear_current_form(context)
    if update.message:
        await update.message.reply_text(TEXTS[lang]["cancelled"], reply_markup=build_main_menu(lang))
    return MENU


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    print("ГЛОБАЛЬНАЯ ОШИБКА:", context.error)


def build_application() -> Application:
    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            LANG: [CallbackQueryHandler(choose_language, pattern=r"^lang_(ru|kz)$")],
            RULES_ACK: [CallbackQueryHandler(rules_actions, pattern=r"^(agree_rules|show_rules)$")],
            MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler),
                CallbackQueryHandler(change_language_from_menu, pattern=r"^lang_(ru|kz)_menu$")
            ],
            CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, category_handler)],
            TRANSPORT_BRANCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, transport_branch_handler)],
            TRANSPORT_ROUTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, transport_route_handler)],
            TRANSPORT_DRIVER_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, transport_driver_type_handler)],
            SHORT_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, short_text_handler)],
            DISTRICT: [MessageHandler(filters.TEXT & ~filters.COMMAND, district_handler)],
            ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, address_handler)],
            EVENT_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, event_time_handler)],
            CUSTOM_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, custom_date_handler)],
            PHOTO: [
                MessageHandler(filters.PHOTO, photo_handler),
                MessageHandler(filters.TEXT & ~filters.COMMAND, photo_handler),
            ],
            CONFIRM: [CallbackQueryHandler(confirm_handler, pattern=r"^(send_report|edit_report|cancel_report)$")],
            EDIT_CHOICE: [CallbackQueryHandler(edit_choice_handler, pattern=r"^(edit_text|edit_address|edit_date|edit_photo|back_to_preview)$")],
            EDIT_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_text_handler)],
            EDIT_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_address_handler)],
            EDIT_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_date_handler)],
            EDIT_PHOTO: [
                MessageHandler(filters.PHOTO, edit_photo_handler),
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_photo_handler),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )

    app.add_handler(conv)
    app.add_error_handler(error_handler)
    return app


def main() -> None:
    ensure_json_file(USERS_FILE, {})
    ensure_json_file(REPORTS_FILE, {"last_number": 0, "items": []})

    if BOT_TOKEN == "PASTE_YOUR_BOT_TOKEN_HERE":
        raise ValueError("Укажи BOT_TOKEN в начале файла.")
    if ADMIN_CHAT_ID == 123456789:
        raise ValueError("Укажи ADMIN_CHAT_ID в начале файла.")
    if BOT_USERNAME == "your_bot_username":
        raise ValueError("Укажи BOT_USERNAME в начале файла.")
    if CHANNEL_URL == "https://t.me/your_channel_here":
        raise ValueError("Укажи CHANNEL_URL в начале файла.")

    app = build_application()
    logger.info("Bot is running...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()