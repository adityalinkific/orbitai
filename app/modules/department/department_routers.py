from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependency import get_db, require_roles
from app.core.schema import ApiResponse
from app.modules.department.department_schema import CreateDepartmentRequest, DepartmentCreateResponse, DepartmentResponse, UpdateDepartmentRequest
from app.modules.department.department_controller import DepartmentController

router = APIRouter(prefix="/departments", tags=["Departments"])

@router.post("/", response_model= ApiResponse[DepartmentCreateResponse], summary= "Create Department")
async def create_department(data: CreateDepartmentRequest, db: AsyncSession = Depends(get_db), _= Depends(require_roles("super_admin"))):
    return await DepartmentController._create_department(data, db)


@router.get("/", summary= "Get All Departments")
async def get_departments(db: AsyncSession = Depends(get_db)):
    return await DepartmentController._get_departments(db)



@router.get('/department-detail/{department_id}', response_model=ApiResponse[DepartmentResponse], summary= "Get Particular Department Detail")
async def get_one_department(department_id: int, db: AsyncSession = Depends(get_db)):
    return await DepartmentController._get_perticular_department(department_id, db)


@router.put('/update-department/{department_id}', response_model= ApiResponse[None], summary= "Update Department")
async def update_department(department_id: int, data: UpdateDepartmentRequest, db: AsyncSession = Depends(get_db), _= Depends(require_roles('super_admin', 'admin'))):
    return await DepartmentController._update_department(department_id, data, db)


@router.delete('/delete-department/{department_id}', response_model= ApiResponse[None], summary= 'Delete Department')
async def delet_department(department_id: int, db: AsyncSession = Depends(get_db), _= Depends(require_roles('super_admin', 'admin'))):
    return await DepartmentController._delete_department(department_id, db)