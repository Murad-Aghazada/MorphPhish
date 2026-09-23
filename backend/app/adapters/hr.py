"""HR data layer (adapter pattern).

The platform reads employee/persona data through an HRAdapter so the synthetic
source used in the prototype can later be swapped for a real, read-only HR
integration without touching the rest of the backend. Each adapter returns
normalized records; `sync_from_hr` (services) upserts them into the database.
"""
from abc import ABC, abstractmethod
import httpx
from app.core.config import settings

# Normalized record keys every adapter must return.
FIELDS = ("external_id", "full_name", "email", "department", "role",
          "preferred_language", "privilege_level", "access_sensitivity", "social_exposure")


class HRAdapter(ABC):
    @abstractmethod
    def list_employees(self) -> list[dict]:
        """Return a list of normalized employee records (see FIELDS)."""


# Synthetic HR directory — clearly non-real personas on demo.example.com.
# external_id mimics an HR system's stable employee id (what a real
# integration would map on). Columns after email: department, role, language,
# privilege / access-sensitivity / social-exposure (each 1-5).
_DIRECTORY = [
    ("HR-1001", "Aylin Məmmədova", "aylin.mammadova@demo.example.com", "Finance", "Senior Accountant", "az", 3, 4, 4),
    ("HR-1002", "Rəşad Quliyev", "rashad.guliyev@demo.example.com", "Finance", "Chief Financial Officer", "az", 5, 5, 4),
    ("HR-1003", "Murad Əliyev", "murad.aliyev@demo.example.com", "IT", "Systems Administrator", "az", 5, 5, 3),
    ("HR-1004", "Kənan Hüseynov", "kenan.huseynov@demo.example.com", "IT", "Help Desk Technician", "az", 2, 2, 5),
    ("HR-1005", "Elvin Quliyev", "elvin.guliyev@demo.example.com", "Security", "Security Engineer", "en", 5, 5, 2),
    ("HR-1006", "Nərmin Abbasova", "narmin.abbasova@demo.example.com", "Security", "SOC Analyst", "az", 3, 4, 2),
    ("HR-1007", "Nigar Həsənova", "nigar.hasanova@demo.example.com", "HR", "HR Specialist", "az", 2, 4, 5),
    ("HR-1008", "Səbinə Kərimli", "sabina.karimli@demo.example.com", "HR", "HR Manager", "az", 3, 5, 4),
    ("HR-1009", "Leyla Kərimova", "leyla.karimova@demo.example.com", "Management", "Chief Executive Officer", "en", 5, 5, 5),
    ("HR-1010", "Orxan Nəbiyev", "orxan.nabiyev@demo.example.com", "Management", "Operations Director", "az", 5, 5, 4),
    ("HR-1011", "Kamran Rzayev", "kamran.rzayev@demo.example.com", "Operations", "Operations Analyst", "az", 2, 3, 4),
    ("HR-1012", "Tural İsmayılov", "tural.ismayilov@demo.example.com", "Legal", "Corporate Counsel", "az", 3, 5, 3),
    ("HR-1013", "Aysel Vəliyeva", "aysel.valiyeva@demo.example.com", "Sales", "Account Executive", "az", 2, 3, 5),
    ("HR-1014", "Ramil Cəfərov", "ramil.jafarov@demo.example.com", "Sales", "Sales Manager", "az", 3, 4, 5),
    ("HR-1015", "Günel Məmmədli", "gunel.mammadli@demo.example.com", "Marketing", "Marketing Specialist", "az", 2, 2, 5),
    ("HR-1016", "Daniel Roberts", "daniel.roberts@demo.example.com", "Engineering", "DevOps Engineer", "en", 5, 5, 2),
    ("HR-1017", "Fərid Bağırov", "farid.baghirov@demo.example.com", "Engineering", "Software Engineer", "az", 3, 3, 2),
    ("HR-1018", "Viktor Sokolov", "viktor.sokolov@demo.example.com", "IT", "Network Engineer", "ru", 4, 4, 3),
    ("HR-1019", "Anna Ivanova", "anna.ivanova@demo.example.com", "Finance", "Accounts Payable Specialist", "ru", 2, 4, 4),
]


class MockHRAdapter(HRAdapter):
    def list_employees(self):
        return [dict(zip(FIELDS, row)) for row in _DIRECTORY]


class RestHRAdapter(HRAdapter):
    """Read-only adapter for a future real HR REST API.

    Expects an endpoint returning records that map to FIELDS. Kept behind the
    same interface so enabling it (HR_PROVIDER=rest) needs no other code change.
    Per the RoE, a real integration must be read-only, OAuth-scoped and audited.
    """
    def list_employees(self):
        if not settings.hr_api_url:
            raise RuntimeError("HR_API_URL is not configured")
        headers = {"Authorization": f"Bearer {settings.hr_api_key}"} if settings.hr_api_key else {}
        with httpx.Client(timeout=15) as c:
            r = c.get(settings.hr_api_url.rstrip("/") + "/employees", headers=headers)
            r.raise_for_status()
            data = r.json()
        rows = data.get("employees", data) if isinstance(data, dict) else data
        return [{k: rec.get(k) for k in FIELDS} for rec in rows]


def get_hr_adapter() -> HRAdapter:
    return MockHRAdapter() if settings.hr_provider.lower() == "mock" else RestHRAdapter()
