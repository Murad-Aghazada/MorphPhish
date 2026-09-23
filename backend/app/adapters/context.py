"""Synthetic operational-context adapter.

Produces localized (AZ / EN / RU) context items per persona. Each item stores
its display text in the persona's language plus a `*_i18n` map in metadata, so
scenario generation can resolve the title/summary to whatever output language
is requested (see services._localize_context).
"""
from abc import ABC, abstractmethod
from app.llm.prompts import normalize_language


class ContextAdapter(ABC):
    @abstractmethod
    def generate(self, employee): ...


def _items(department, role):
    """Return (kind, title_i18n, summary_i18n, source) tuples."""
    return [
        ("ticket",
         {"en": f"{department} access review", "az": f"{department} giriş yoxlaması", "ru": f"Проверка доступа: {department}"},
         {"en": f"Quarterly synthetic access review for {role}.",
          "az": f"{role} üçün rüblük sintetik giriş yoxlaması.",
          "ru": f"Ежеквартальная синтетическая проверка доступа для роли {role}."},
         "mock-ticketing"),
        ("calendar",
         {"en": "Security awareness briefing", "az": "Təhlükəsizlik brifinqi", "ru": "Брифинг по информационной безопасности"},
         {"en": "Synthetic calendar event scheduled this week.",
          "az": "Bu həftə üçün planlaşdırılmış sintetik təqvim hadisəsi.",
          "ru": "Синтетическое событие календаря, запланированное на эту неделю."},
         "mock-calendar"),
        ("communication",
         {"en": "Team project update", "az": "Komanda layihə yeniləməsi", "ru": "Обновление командного проекта"},
         {"en": "Synthetic metadata: internal team update thread is active.",
          "az": "Sintetik metadata: daxili komanda yeniləmə mövzusu aktivdir.",
          "ru": "Синтетические метаданные: активна внутренняя ветка обновлений команды."},
         "mock-comms"),
        ("task",
         {"en": "Pending document review", "az": "Gözləyən sənəd yoxlaması", "ru": "Ожидающая проверка документа"},
         {"en": f"Synthetic task relevant to {department} workflow.",
          "az": f"{department} iş axını ilə əlaqəli sintetik tapşırıq.",
          "ru": f"Синтетическая задача, связанная с рабочим процессом {department}."},
         "mock-task"),
    ]


class MockContextAdapter(ContextAdapter):
    def generate(self, employee):
        lang = normalize_language(employee.preferred_language)
        out = []
        for kind, title_i18n, summary_i18n, source in _items(employee.department, employee.role):
            meta = {"source": source, "title_i18n": title_i18n, "summary_i18n": summary_i18n}
            if kind == "communication":
                meta["content_excluded"] = True
            out.append((kind, title_i18n[lang], summary_i18n[lang], meta))
        return out
