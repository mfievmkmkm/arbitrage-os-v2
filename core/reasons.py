from core.models import Reason

REASONS = {
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
