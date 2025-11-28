from datetime import date
from typing import List, Optional
from datetime import datetime, timedelta


from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Boolean,
    Float,
    Date,
    ForeignKey,
    DateTime,
)
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, Session

# ============================================
# Database setup
# ============================================

DATABASE_URL = "sqlite:///./employees.db"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)  # needed for SQLite + FastAPI

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency to get DB session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================
# SQLAlchemy Models
# ============================================


class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(String(255), nullable=True)

    employees = relationship("Employee", back_populates="department")


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(150), nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    phone = Column(String(20), nullable=True)
    role = Column(String(100), nullable=True)
    salary = Column(Float, nullable=True)
    is_active = Column(Boolean, default=True)
    date_joined = Column(Date, default=date.today)

    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    department = relationship("Department", back_populates="employees")

    # ✅ IMPORTANT: this must exist and the name must match back_populates in Attendance
    attendance_records = relationship(
        "Attendance",
        back_populates="employee",
        cascade="all, delete-orphan",
    )


class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    date = Column(Date, nullable=False)
    check_in = Column(DateTime, nullable=False)
    check_out = Column(DateTime, nullable=True)
    total_hours = Column(Float, nullable=True)

    # ✅ back_populates MUST match Employee.attendance_records
    employee = relationship("Employee", back_populates="attendance_records")


# Create tables
Base.metadata.create_all(bind=engine)



# ============================================
# Pydantic Schemas (Request/Response models)
# ============================================

# ----- Department Schemas -----


class DepartmentBase(BaseModel):
    name: str = Field(..., example="Engineering")
    description: Optional[str] = Field(
        None, example="Handles all product development and tech."
    )


class DepartmentCreate(DepartmentBase):
    pass


class DepartmentRead(DepartmentBase):
    id: int

    class Config:
        orm_mode = True


# ----- Employee Schemas -----


class EmployeeBase(BaseModel):
    full_name: str = Field(..., example="John Doe")
    email: EmailStr = Field(..., example="john.doe@example.com")
    phone: Optional[str] = Field(None, example="+91-9876543210")
    role: Optional[str] = Field(None, example="Software Engineer")
    salary: Optional[float] = Field(None, example=75000.0)
    is_active: Optional[bool] = True
    date_joined: Optional[date] = None
    department_id: Optional[int] = Field(None, example=1)


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    salary: Optional[float] = None
    is_active: Optional[bool] = None
    department_id: Optional[int] = None


class EmployeeRead(EmployeeBase):
    id: int
    department: Optional[DepartmentRead] = None

    class Config:
        orm_mode = True

        # ----- Attendance Schemas -----


class AttendanceCreate(BaseModel):
    employee_id: int = Field(..., example=1)
    check_in: datetime = Field(..., example="2025-11-28T09:00:00")


class AttendanceRead(BaseModel):
    id: int
    employee_id: int
    date: date
    check_in: datetime
    check_out: Optional[datetime] = None
    total_hours: Optional[float] = None

    class Config:
        orm_mode = True



# ============================================
# FastAPI App
# ============================================

app = FastAPI(
    title="Employee Management Mini ERP API",
    description="Simple ERP-style API to manage departments and employees.",
    version="1.0.0",
)


# ============================================
# Department Endpoints
# ============================================


@app.post(
    "/departments",
    response_model=DepartmentRead,
    status_code=status.HTTP_201_CREATED,
    tags=["Departments"],
)
def create_department(
    department: DepartmentCreate, db: Session = Depends(get_db)
):
    existing = (
        db.query(Department).filter(Department.name == department.name).first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Department with this name already exists.",
        )

    db_dept = Department(
        name=department.name, description=department.description
    )
    db.add(db_dept)
    db.commit()
    db.refresh(db_dept)
    return db_dept


@app.get(
    "/departments",
    response_model=List[DepartmentRead],
    tags=["Departments"],
)
def list_departments(db: Session = Depends(get_db)):
    return db.query(Department).all()


@app.get(
    "/departments/{department_id}",
    response_model=DepartmentRead,
    tags=["Departments"],
)
def get_department(department_id: int, db: Session = Depends(get_db)):
    dept = db.query(Department).filter(Department.id == department_id).first()
    if not dept:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found.",
        )
    return dept


@app.delete(
    "/departments/{department_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Departments"],
)
def delete_department(department_id: int, db: Session = Depends(get_db)):
    dept = db.query(Department).filter(Department.id == department_id).first()
    if not dept:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found.",
        )
    # Note: In real ERP, we may prevent delete if employees exist
    db.delete(dept)
    db.commit()
    return None


# ============================================
# Employee Endpoints
# ============================================


@app.post(
    "/employees",
    response_model=EmployeeRead,
    status_code=status.HTTP_201_CREATED,
    tags=["Employees"],
)
def create_employee(
    employee: EmployeeCreate, db: Session = Depends(get_db)
):
    existing = (
        db.query(Employee).filter(Employee.email == employee.email).first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Employee with this email already exists.",
        )

    db_emp = Employee(
        full_name=employee.full_name,
        email=employee.email,
        phone=employee.phone,
        role=employee.role,
        salary=employee.salary,
        is_active=employee.is_active,
        date_joined=employee.date_joined or date.today(),
        department_id=employee.department_id,
    )
    db.add(db_emp)
    db.commit()
    db.refresh(db_emp)
    return db_emp


@app.get(
    "/employees",
    response_model=List[EmployeeRead],
    tags=["Employees"],
)
def list_employees(
    is_active: Optional[bool] = None,
    department_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """List employees with optional filters."""
    query = db.query(Employee)

    if is_active is not None:
        query = query.filter(Employee.is_active == is_active)

    if department_id is not None:
        query = query.filter(Employee.department_id == department_id)

    return query.all()


@app.get(
    "/employees/{employee_id}",
    response_model=EmployeeRead,
    tags=["Employees"],
)
def get_employee(employee_id: int, db: Session = Depends(get_db)):
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found.",
        )
    return emp


@app.put(
    "/employees/{employee_id}",
    response_model=EmployeeRead,
    tags=["Employees"],
)
def update_employee(
    employee_id: int,
    update_data: EmployeeUpdate,
    db: Session = Depends(get_db),
):
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found.",
        )

    for field, value in update_data.dict(exclude_unset=True).items():
        setattr(emp, field, value)

    db.commit()
    db.refresh(emp)
    return emp


@app.delete(
    "/employees/{employee_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Employees"],
)
def delete_employee(employee_id: int, db: Session = Depends(get_db)):
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found.",
        )
    db.delete(emp)
    db.commit()
    return None

# ============================================
# Attendance Endpoints
# ============================================


@app.post(
    "/attendance/check-in",
    response_model=AttendanceRead,
    status_code=status.HTTP_201_CREATED,
    tags=["Attendance"],
)
def check_in_attendance(
    attendance: AttendanceCreate, db: Session = Depends(get_db)
):
    # Ensure employee exists
    employee = db.query(Employee).filter(Employee.id == attendance.employee_id).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found.",
        )

    # Derive date from check_in timestamp
    attendance_date = attendance.check_in.date()

    # Optional: prevent multiple check-ins on same day
    existing = (
        db.query(Attendance)
        .filter(
            Attendance.employee_id == attendance.employee_id,
            Attendance.date == attendance_date,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Attendance already exists for this employee on this date.",
        )

    db_att = Attendance(
        employee_id=attendance.employee_id,
        date=attendance_date,
        check_in=attendance.check_in,
    )
    db.add(db_att)
    db.commit()
    db.refresh(db_att)
    return db_att


class AttendanceCheckout(BaseModel):
    check_out: datetime = Field(..., example="2025-11-28T18:00:00")


@app.put(
    "/attendance/{attendance_id}/check-out",
    response_model=AttendanceRead,
    tags=["Attendance"],
)
def check_out_attendance(
    attendance_id: int,
    checkout_data: AttendanceCheckout,
    db: Session = Depends(get_db),
):
    att = db.query(Attendance).filter(Attendance.id == attendance_id).first()
    if not att:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attendance record not found.",
        )

    if att.check_out is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Check-out already recorded for this attendance.",
        )

    if checkout_data.check_out < att.check_in:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Check-out time cannot be earlier than check-in time.",
        )

    att.check_out = checkout_data.check_out
    delta = att.check_out - att.check_in
    att.total_hours = round(delta.total_seconds() / 3600, 2)

    db.commit()
    db.refresh(att)
    return att


@app.get(
    "/attendance",
    response_model=List[AttendanceRead],
    tags=["Attendance"],
)
def list_attendance(
    employee_id: Optional[int] = None,
    date_filter: Optional[date] = None,
    db: Session = Depends(get_db),
):
    """List attendance with optional filters."""
    query = db.query(Attendance)

    if employee_id is not None:
        query = query.filter(Attendance.employee_id == employee_id)

    if date_filter is not None:
        query = query.filter(Attendance.date == date_filter)

    return query.order_by(Attendance.date.desc()).all()



# ============================================
# Root health check
# ============================================


@app.get("/")
def root():
    return {
        "message": "Employee Management Mini ERP API is running",
        "author": "Created by Jaffar Shariff",
        "github": "https://github.com/jaffar-shariff/employee-mini-erp-api/tree/main",
        "docs": "/docs"
    }

