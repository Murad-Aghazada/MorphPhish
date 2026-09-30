"""Synthetic operational-context module (adapter pattern).

Composes three synthetic internal sources per persona — a mock ticket/task
system, a mock calendar, and team-communication metadata — into localized
(AZ/EN/RU) context items. Selection is deterministic per employee (seeded by
id) so results are stable yet varied across personas.

Each item carries structured metadata (ticket id, priority, due dates, event
timing, channel, participant counts) and an `anchor` weight indicating how
suitable it is as a scenario pretext. No real systems are contacted and
communication CONTENT is never included — only metadata.
"""
import hashlib
from abc import ABC, abstractmethod
from app.llm.prompts import normalize_language

LANGS = ("en", "az", "ru")
DEPT_PREFIX = {"Finance": "FIN", "IT": "ITS", "Security": "SEC", "HR": "HRP", "Management": "EXE",
               "Legal": "LGL", "Sales": "SAL", "Marketing": "MKT", "Operations": "OPS", "Engineering": "ENG"}

# Ticket/task templates (anchor: pretext suitability). {d}=department, {r}=role.
TICKETS = [
    {"key": "access_review", "anchor": 9, "priority": "high",
     "title": {"en": "{d} access review", "az": "{d} giriş yoxlaması", "ru": "Проверка доступа: {d}"},
     "summary": {"en": "Quarterly access review for {r} is awaiting confirmation.",
                 "az": "{r} üçün rüblük giriş yoxlaması təsdiqinizi gözləyir.",
                 "ru": "Ежеквартальная проверка доступа для роли «{r}» ожидает подтверждения."}},
    {"key": "doc_approval", "anchor": 8, "priority": "high",
     "title": {"en": "Document approval pending", "az": "Sənəd təsdiqi gözləyir", "ru": "Ожидает утверждения документа"},
     "summary": {"en": "A {d} document is awaiting your sign-off.",
                 "az": "{d} sənədi təsdiqinizi gözləyir.",
                 "ru": "Документ отдела «{d}» ожидает вашего утверждения."}},
    {"key": "device_reenroll", "anchor": 7, "priority": "medium",
     "title": {"en": "Device re-enrollment required", "az": "Cihazın yenidən qeydiyyatı tələb olunur", "ru": "Требуется повторная регистрация устройства"},
     "summary": {"en": "Your workstation enrollment expires soon.",
                 "az": "İş stansiyanızın qeydiyyatı tezliklə bitir.",
                 "ru": "Регистрация вашей рабочей станции скоро истекает."}},
]
# Calendar templates.
CALENDAR = [
    {"key": "quarterly_review", "anchor": 5,
     "title": {"en": "Quarterly {d} review", "az": "Rüblük {d} baxışı", "ru": "Ежеквартальный обзор: {d}"},
     "summary": {"en": "Scheduled team review; you are listed as a participant.",
                 "az": "Planlaşdırılmış komanda baxışı; iştirakçı kimi qeyd olunmusunuz.",
                 "ru": "Запланированный обзор команды; вы указаны как участник."}},
    {"key": "awareness_brief", "anchor": 4,
     "title": {"en": "Security awareness briefing", "az": "Təhlükəsizlik brifinqi", "ru": "Брифинг по безопасности"},
     "summary": {"en": "An awareness session is on the calendar this week.",
                 "az": "Bu həftə təqvimdə maarifləndirmə sessiyası var.",
                 "ru": "На этой неделе в календаре запланирована сессия по осведомлённости."}},
]
# Team-communication metadata (content intentionally excluded).
COMMS = {
    "title": {"en": "Active {d} team thread", "az": "Aktiv {d} komanda mövzusu", "ru": "Активная ветка команды «{d}»"},
    "summary": {"en": "Metadata only: an internal thread is active (message content excluded).",
                "az": "Yalnız metadata: daxili mövzu aktivdir (mesaj məzmunu istisna edilir).",
                "ru": "Только метаданные: активна внутренняя ветка (содержимое сообщений исключено)."},
}


def _h(employee_id, salt):
    return int(hashlib.sha256(f"{employee_id}:{salt}".encode()).hexdigest()[:8], 16)


def _i18n(mapping, d, r):
    return {L: mapping[L].format(d=d, r=r) for L in LANGS}


class ContextAdapter(ABC):
    @abstractmethod
    def generate(self, employee): ...


class MockContextAdapter(ContextAdapter):
    def generate(self, employee):
        lang = normalize_language(employee.preferred_language)
        d, r, eid = employee.department, employee.role, employee.id
        prefix = DEPT_PREFIX.get(d, "GEN")
        items = []

        # Two distinct tickets, deterministically selected.
        i1 = _h(eid, "ticket") % len(TICKETS)
        i2 = (i1 + 1 + _h(eid, "ticket2") % (len(TICKETS) - 1)) % len(TICKETS)
        for t in (TICKETS[i1], TICKETS[i2]):
            title_i18n, summary_i18n = _i18n(t["title"], d, r), _i18n(t["summary"], d, r)
            meta = {"source": "mock-ticketing", "ticket_id": f"{prefix}-{1000 + _h(eid, t['key']) % 9000}",
                    "priority": t["priority"], "due_in_days": 1 + _h(eid, "due" + t["key"]) % 6,
                    "anchor": t["anchor"], "title_i18n": title_i18n, "summary_i18n": summary_i18n}
            items.append(("ticket", title_i18n[lang], summary_i18n[lang], meta))

        # One calendar event.
        cal = CALENDAR[_h(eid, "cal") % len(CALENDAR)]
        title_i18n, summary_i18n = _i18n(cal["title"], d, r), _i18n(cal["summary"], d, r)
        items.append(("calendar", title_i18n[lang], summary_i18n[lang],
                      {"source": "mock-calendar", "in_days": 1 + _h(eid, "calday") % 5,
                       "anchor": cal["anchor"], "title_i18n": title_i18n, "summary_i18n": summary_i18n}))

        # One team-communication metadata item (no content).
        title_i18n, summary_i18n = _i18n(COMMS["title"], d, r), _i18n(COMMS["summary"], d, r)
        items.append(("communication", title_i18n[lang], summary_i18n[lang],
                      {"source": "mock-comms", "channel": f"#{d.lower()}-team",
                       "thread_count": 3 + _h(eid, "thr") % 12, "participants": 4 + _h(eid, "ppl") % 20,
                       "content_excluded": True, "anchor": 2, "title_i18n": title_i18n, "summary_i18n": summary_i18n}))
        return items
