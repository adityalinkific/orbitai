from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependency import get_db, get_current_user, require_roles
from app.core.schema import ApiResponse
from app.modules.task.task_controller import TaskController, TaskAssignController, AssignTaskReportController
from app.modules.task.task_schema import (
    TaskRequestSchema, 
    TaskStatusUpdateSchema, 
    TaskUpdateSchema, 
    TaskResponseSchema, 
    TaskAssignRequestSchema, 
    TaskAssignUpdateSchema, 
    TaskAssignResponseSchema, 
    AssignTaskResponseSchema,
    TaskSubmitSchema
)

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post("/", response_model= ApiResponse[None], summary= "Create Task")
async def create_task(data: TaskRequestSchema,  db: AsyncSession = Depends(get_db),  current_user=Depends(require_roles("super_admin", "admin"))):
    return await TaskController._create_task(db, data, current_user)


@router.put("/update-task/{task_id}", response_model= ApiResponse[None], summary= "Update Task")
async def update_task(task_id: int,  data: TaskUpdateSchema,  db: AsyncSession = Depends(get_db),  _=Depends(require_roles("super_admin", "admin"))):
    return await TaskController._update_task(db, task_id, data)


@router.delete("/delete-task/{task_id}", response_model= ApiResponse[None], summary= "Delete Task")
async def delete_task(task_id: int, db: AsyncSession = Depends(get_db), _=Depends(require_roles("super_admin", "admin"))):
    return await TaskController._delete_task(db, task_id)

@router.get("/task-detail", summary= "Get All Task Details")
async def get_task_detail(db: AsyncSession = Depends(get_db), _=Depends(require_roles("super_admin", "admin"))):
    return await TaskController._get_all_task_detail(db)


@router.get("/task-detail/{task_id}", response_model= ApiResponse[TaskResponseSchema], summary= "Get Particular Task Details")
async def get_task_detail(task_id: int, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    return await TaskController._get_task_detail(db, task_id, current_user)


# Task Assignment Routes

@router.post("/task-assign", response_model= ApiResponse[AssignTaskResponseSchema], summary= "Assign Task To Intern")
async def assign_task(data: TaskAssignRequestSchema,  db: AsyncSession = Depends(get_db),  current_user=Depends(require_roles("super_admin", "admin", "employee"))):
    return await TaskAssignController._assign_task(db, data, current_user)

@router.put("/task-assign/update-task-assign/{assign_task_id}", response_model= ApiResponse[None], summary= "Update Assigned Task")
async def update_task_assign(assign_task_id: int, data: TaskAssignUpdateSchema, db: AsyncSession = Depends(get_db), current_user=Depends(require_roles("super_admin", "admin"))):
    return await TaskAssignController._update_task_assign(db, assign_task_id, data, current_user)

@router.delete("/task-assign/delete-task-assign/{assign_task_id}", response_model= ApiResponse[None], summary= "Delete Assigned Task")
async def delete_task_assign(assign_task_id: int, db: AsyncSession = Depends(get_db), _=Depends(require_roles("super_admin", "admin"))):
    return await TaskAssignController._delete_task_assign(db, assign_task_id)


@router.patch("/task-assign/update-status/{assign_task_id}", response_model= ApiResponse[None], summary= "Update Task Status")
async def update_status(assign_task_id: int, data: TaskStatusUpdateSchema, db: AsyncSession = Depends(get_db), _=Depends(require_roles("super_admin"))):
    return await TaskAssignController._update_task_status(db, assign_task_id, data)

@router.post("/task-assign/task-assign-detail/{assign_task_id}", response_model= ApiResponse[TaskAssignResponseSchema], summary= "Get Assigned Task Details")
async def get_task_assign_detail(assign_task_id: int, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    return await TaskAssignController._get_task_assign_detail(db, assign_task_id, current_user)

@router.get("/task-assign/all-task-assign-detail", response_model= ApiResponse[list[TaskAssignResponseSchema]], summary= "Get All Assigned Task Details")
async def get_all_task_assign_detail(db: AsyncSession = Depends(get_db), current_user= Depends(get_current_user)):
    return await TaskAssignController._get_all_task_assign_detail(db, current_user)



# Report Assigned Task Router

report_router = APIRouter(prefix= '/task/report', tags=['Assigned Task Report'])

@report_router.get('/pending-submitted-task', response_model= ApiResponse[list[TaskAssignResponseSchema]], summary= "Get Pending Submitted Task")
async def get_pending_reports(db: AsyncSession = Depends(get_db), current_user= Depends(require_roles('super_admin', 'admin'))):
    return await AssignTaskReportController._get_pending_reports(db, current_user)


@report_router.get("/pending-submitted-task/{assign_task_id}", response_model= ApiResponse[TaskAssignResponseSchema], summary= "Get Particular Pending Submitted Task")
async def get_pending_report_by_id(assign_task_id: int, db: AsyncSession = Depends(get_db), current_user= Depends(require_roles('super_admin', 'admin'))):
    return await AssignTaskReportController._get_pending_report_by_id(assign_task_id, db, current_user)

@report_router.post("/submit-task", response_model=ApiResponse[None], summary= "Submit The Assigned Task")
async def submit_report(data: TaskSubmitSchema, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    return await AssignTaskReportController._submit_report(data, db, current_user)

@report_router.post('/upload-document', response_model=ApiResponse[None], summary= "Upload Document Related to Assigned Task")
async def upload_document(assign_task_id: int = Form(...), link: str | None = Form(None), file: UploadFile | None = File(None), db: AsyncSession = Depends(get_db), current_user= Depends(get_current_user)):
    return await AssignTaskReportController._upload_document(assign_task_id, link, file, db, current_user)
