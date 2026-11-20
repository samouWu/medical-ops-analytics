from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=300)
    start: str | None = None
    end: str | None = None
    dept_code: str | None = None


class ReportRequest(BaseModel):
    period: str = "month"
    date: str | None = None
    dept_code: str | None = None


class ReportQuery(BaseModel):
    metrics: list[str] = Field(min_length=1, max_length=8)
    dimensions: list[str] = Field(default_factory=lambda: ["date", "dept_code"])
    filters: dict = Field(default_factory=dict)
    grain: str = "month"
    comparisons: list[str] = Field(default_factory=list)


class AdsRefreshRequest(BaseModel):
    start: str | None = None
    end: str | None = None
    grains: list[str] = Field(default_factory=lambda: ["day", "week", "month"])
    dept_code: str | None = None


class DataSourceRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    kind: str = Field(pattern="^(csv|excel|mysql|oracle|sqlserver|api)$")
    path: str | None = Field(default=None, max_length=500)
    enabled: bool = True


class UserRequest(BaseModel):
    username: str = Field(pattern="^[A-Za-z0-9_]{3,32}$")
    display_name: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(pattern="^(admin|analyst|department|engineer)$")
    dept_codes: list[str] = Field(default_factory=list)


class UserUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=64)
    password: str | None = Field(default=None, min_length=8, max_length=128)
    role: str | None = Field(default=None, pattern="^(admin|analyst|department|engineer)$")
    dept_codes: list[str] | None = None
    enabled: bool | None = None


class DataSourceUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    kind: str | None = Field(default=None, pattern="^(csv|excel|mysql|oracle|sqlserver|api)$")
    path: str | None = Field(default=None, max_length=500)
    enabled: bool | None = None


class EtlJobRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    source_table: str = Field(pattern="^(his_outpatient|his_inpatient|his_charge|emr_record|lis_report|finance_excel)$")
    schedule: str = Field(min_length=1, max_length=64)
    enabled: bool = True
    retry_limit: int = Field(default=3, ge=0, le=10)


class EtlJobUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    schedule: str | None = Field(default=None, min_length=1, max_length=64)
    enabled: bool | None = None
    retry_limit: int | None = Field(default=None, ge=0, le=10)
