from core.models import Reason

REASONS = {
    "PUBLIC_API_REGION_RESTRICTED": ("INFRA", "Источник явно блокирует public API по стране IP сервера"),
    Reason.SLIPPAGE: ("DEPTH", "Недостаточно объёма в пределах заданного проскальзывания"),
    "PUBLIC_API_HTML_UNAVAILABLE": (
        "INFRA",
        "Вместо биржевого JSON получена HTML-заглушка; источник недоступен",
    ),
    "NON_JSON_RESPONSE": ("INFRA", "Источник вернул ответ вне формата биржевого API"),
    Reason.EMPTY: ("DEPTH", "Пустая сторона стакана; исполнение не подтверждено"),
    Reason.CROSSED: ("DEPTH", "Пересечённый стакан: лучший bid выше ask"),
    Reason.INVALID_BOOK: ("DEPTH", "Некорректные цены, объёмы или порядок уровней стакана"),
    Reason.BOOK_SKEW: ("MARKET_DATA", "Стаканы и котировки не синхронизированы по времени"),
    Reason.INVALID_TIME: ("MARKET_DATA", "Некорректная временная метка источника"),
    Reason.OUTAGE: ("INFRA", "Поток данных разорван; сигнал отозван до восстановления"),
    Reason.IDENTITY: ("IDENTITY", "Не подтверждено, что контракты относятся к одному активу"),
    Reason.CONTRACT: ("IDENTITY", "Не подтверждена совместимость спецификаций контрактов"),
    Reason.STALE: ("MARKET_DATA", "Котировка или стакан устарели либо время источника некорректно"),
    Reason.SKEW: ("MARKET_DATA", "Слишком большая разница времени котировок двух бирж"),
    Reason.DEPTH: ("DEPTH", "Недостаточно объёма для обеих ног на заданную сумму"),
    Reason.BOOK: ("DEPTH", "Нет свежего глубокого стакана"),
    Reason.GAP: ("DEPTH", "Разрыв последовательности стакана; требуется новый снимок"),
    Reason.MINIMUM: ("DEPTH", "Не выполнен минимум количества или стоимости ордера"),
    Reason.SIZE: ("RISK", "Стоимость с учётом глубины превышает заданный номинал"),
    Reason.FEES: ("NET", "Неизвестна комиссия"),
    Reason.FUNDING: ("NET", "Неизвестны или устарели ставка, время либо интервал funding"),
    Reason.NET: ("NET", "Сценарный NET после расходов ниже заданного порога"),
    Reason.COUNTERPART: ("DISCOVERY", "На второй бирже не найден контракт для сравнения"),
}


def explain(code):
    return REASONS.get(code, ("INFRA", str(code)))[1]
