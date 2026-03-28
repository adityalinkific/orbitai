from fastapi import HTTPException, status, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
from datetime import date, datetime, timezone
import os

from app.modules.project.project_model import Project
from app.modules.department.department_model import Department
from app.modules.auth.auth_model import User
from app.modules.task.task_model import Task, TaskAssignment, TaskStatusEnum, Report, ReportAttachment, ReportReview
from app.modules.task.task_schema import TaskRequestSchema, TaskStatusUpdateSchema, TaskUpdateSchema, TaskAssignRequestSchema, TaskAssignUpdateSchema, TaskSubmitSchema, VALID_TRANSITIONS
from app.modules.task.task_repository import TaskRepository, TaskDetails, RecordExists, TaskAssignmentRepository


BASE_PATH = "storage/task/assigned_task_documents"
ALLOWED_EXTENSIONS = {"pdf", "doc", "docx", "png", "jpg", "jpeg", "zip"}


class TaskService:

    @staticmethod
    async def create_task(db: AsyncSession, data: TaskRequestSchema, current_user: User):
        if await RecordExists.check(db, Task.title == data.title):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Task with this title already exists"
            )
        
        TaskService._validate_due_date(data.due_date)
        
        if not await RecordExists.check(db, Project.id == data.project_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid project selected"
            )
        if not await RecordExists.check(db, Department.id == data.department_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid department selected"
            )
        task_data = Task(
            task_id=f"T-{uuid.uuid4().hex[:6].upper()}",
            title=data.title,
            description=data.description,
            project_id=data.project_id,
            department_id=data.department_id,
            task_type=data.task_type,
            priority=data.priority,
            due_date=data.due_date,
            created_by=current_user.id,
        )
        try:
            task = await TaskRepository.create(db, task_data)
            await db.commit()
            await db.refresh(task)
            return task
        except Exception as e:
            db.rollback()
            raise
            

    @staticmethod
    async def update_task(db: AsyncSession, task_id: str, data: TaskUpdateSchema):
        if not data.model_dump(exclude_unset=True):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one field is required for updating the task."
            )
                
        task = await TaskDetails.get_by_id(db, task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
            
        if not await RecordExists.check(db, Project.id == data.project_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid project selected"
            )
        if not await RecordExists.check(db, Department.id == data.department_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid department selected"
            )
        
        TaskService._validate_due_date(data.due_date)
        
        update_data = data.model_dump(exclude_unset=True)
        try:
            task = await TaskRepository.update(update_data, task)
            await db.commit()
            await db.refresh(task)
            return task
        except Exception:
            db.rollback()
            raise

    @staticmethod
    async def delete_task(db: AsyncSession, task_id: int):
        task = await TaskDetails.get_by_id(db, task_id)

        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        try:
            await TaskRepository.delete(db, task)
            await db.commit()
            return
        except Exception:
            db.rollback()
            raise

    @staticmethod
    async def get_all_tasks(db: AsyncSession):
        return await TaskDetails.get_all(db, Task)

    @staticmethod
    async def get_task_detail(db: AsyncSession, task_id: int):
        task = await TaskDetails.get_by_id(db, task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        return task



    @staticmethod
    def _validate_due_date(due_date: date):
        today_utc = datetime.now(timezone.utc).date()
        if due_date < today_utc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Due date cannot be in the past."
        )


# Task Assignment Services
class TaskAssignService(TaskService):
    @staticmethod
    async def _assign_task(db: AsyncSession, data: TaskAssignRequestSchema, current_user):
        if not await RecordExists.check(db, Task.id == data.task_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found."
            )
            
        if not await RecordExists.check(db, User.id == data.user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found."
            )
        
        task_assigned = await RecordExists.check(db, TaskAssignment.task_id == data.task_id, TaskAssignment.user_id == data.user_id)
        if task_assigned:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Task is already assigned to the user."
            )
            
        TaskService._validate_due_date(data.due_date)
        assignment = TaskAssignment(
            task_id=data.task_id,
            user_id=data.user_id,
            assigned_at=datetime.now(timezone.utc),
            assigned_by=current_user.id,
            due_date=data.due_date,
            status="assigned"
        )
        try:
            assignment = await TaskAssignmentRepository.create(db, assignment)
            await db.commit()
            await db.refresh(assignment)
            return assignment
        except Exception:
            db.rollback()
            raise

    @staticmethod
    async def _update_task_assign(db: AsyncSession, assign_task_id: int, data: TaskAssignUpdateSchema, current_user):
        if not data.model_dump(exclude_unset=True):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one field is required for updating the task assignment."
            )
        
        assigned_task = await TaskDetails.get_one(db, TaskAssignment, TaskAssignment.id == assign_task_id)
        if not assigned_task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assigned task not found."
            )
        
        if not await RecordExists.check(db, Task.id == data.task_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found."
            )
            
        if not await RecordExists.check(db, User.id == data.user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found."
            )
            
        TaskService._validate_due_date(data.due_date)
        update_data = data.model_dump(exclude_unset=True)
        try:
            updated_assignment = await TaskRepository.update(update_data, assigned_task)
            await db.commit()
            return updated_assignment
        except Exception:
            db.rollback()
            raise

    
    
    @staticmethod
    async def _delete_task_assign(db: AsyncSession, assign_task_id):
        assigned_task = await TaskDetails.get_one(db, TaskAssignment, TaskAssignment.id == assign_task_id)
        if not assigned_task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assigned task not found."
            )
        try:
            await TaskRepository.delete(db, assigned_task)
            await db.commit()
            return
        except Exception:
            db.rollback()
            raise
    
    
    @staticmethod
    async def _update_task_status(db: AsyncSession, assign_task_id: int, data: TaskStatusUpdateSchema):
        assigned_task = await TaskDetails.get_one(db, TaskAssignment, TaskAssignment.id == assign_task_id)
        if not assigned_task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assigned task not found."
            )
        
        if assigned_task.status == data.status:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The assigned task already has this status."
            )
            
        try:
            assigned_task_status = await TaskRepository.update({"status": data.status}, assigned_task)
            await db.commit()
            return assigned_task_status
        except Exception:
            db.rollback()
            raise
        
    @staticmethod
    async def _get_task_assign_detail(db: AsyncSession, assign_task_id: int, current_user):
        assigned_task = await TaskDetails.get_one(db, TaskAssignment, TaskAssignment.id == assign_task_id)
        if not assigned_task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assigned task not found."
            )
            
        if current_user.role.role not in ["super_admin", "admin"]:
            if assigned_task.user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="This task is not assigned to you."
                )
            if assigned_task.status == TaskStatusEnum.assigned:
                assigned_task = await TaskRepository.update({"status": TaskStatusEnum.in_progress}, assigned_task)
                await db.commit()
                await db.refresh(assigned_task)
            
        return assigned_task
    
    @staticmethod
    async def _get_all_task_assign_detail(db: AsyncSession, current_user):
        print('current user is ', current_user)
        if current_user.role.role in ["super_admin", "admin"]:
            assigned_tasks = await TaskDetails.get_all(db, TaskAssignment)
        else:
            assigned_tasks = await TaskDetails.get_all(db, TaskAssignment, TaskAssignment.user_id == current_user.id)
        return assigned_tasks
    
    

class AssignTaskReportServices:
    
    @staticmethod
    async def _get_pending_report(db: AsyncSession, current_user):
        if current_user.role.role in ["super_admin"]:
            pending_report = await TaskDetails.get_all(db, TaskAssignment, TaskAssignment.status == TaskStatusEnum.submitted)
        else:
            pending_report = await TaskDetails.get_all(db, TaskAssignment, TaskAssignment.user_id == current_user.id, TaskAssignment.status == TaskStatusEnum.submitted)
        return pending_report
    
    @staticmethod
    async def _get_pending_report_by_id(db: AsyncSession, assign_task_id: int, current_user):
        if current_user.role.role in ["super_admin"]:
            pending_report = await TaskDetails.get_one(db, TaskAssignment, TaskAssignment.id == assign_task_id, TaskAssignment.status == TaskStatusEnum.submitted)
        else:
            pending_report = await TaskDetails.get_one(db, TaskAssignment, TaskAssignment.assigned_by == current_user.id, TaskAssignment.id == assign_task_id, TaskAssignment.status == TaskStatusEnum.submitted)
        if not pending_report:
            raise HTTPException(status_code=404, detail="Report not found")
        return pending_report
            
    @staticmethod
    async def _submit_report(data: TaskSubmitSchema, db: AsyncSession, current_user):
        submit_report = await TaskDetails.get_one(db, TaskAssignment, TaskAssignment.id == data.assign_task_id, TaskAssignment.user_id == current_user.id)
        if not submit_report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assigned task not found."
            )
        if submit_report.status in [TaskStatusEnum.submitted, TaskStatusEnum.reviewed]:
            raise HTTPException(
                status_code= status.HTTP_400_BAD_REQUEST,
                detail= "Task is already submitted"
            )
        
        # allowed = VALID_TRANSITIONS.get(submit_report.status, [])
        # if TaskStatusEnum.in_progress not in allowed:
        #     raise HTTPException(
        #         status_code=400, 
        #         detail="Task must be in progress before submission."
        #     )
        
        report = Report(
            assign_task_id = data.assign_task_id,
            user_id = current_user.id,
            submission_text = data.submission_text if data.submission_text else None,
        )
        print('devashish rajbhar')    
            
        try:
            report = await TaskAssignmentRepository.create(db, report)
            assignment = await TaskRepository.update({"status": TaskStatusEnum.submitted}, submit_report)
            print(report)
            print('assign created : ', assignment)
            await db.commit()
            await db.refresh(report)
            return report
        except Exception:
            await db.rollback()
            raise
        
    async def _upload_document(assign_task_id: int, link: str | None, file: UploadFile, db: AsyncSession, current_user):
        if not link and not file:
            raise HTTPException(
                status_code=400,
                detail="Either link or file must be provided"
            )
        
        assigned_task = await RecordExists.check(db, TaskAssignment.id == assign_task_id, TaskAssignment.user_id == current_user.id)
        
        if not assigned_task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="This task not assigned to you or invalid task id."
            )
        
        if file:
            ext = file.filename.split(".")[-1].lower()
            if ext not in ALLOWED_EXTENSIONS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported file type: {file.filename}"
                )

            filename = f"{uuid.uuid4()}.{ext}"
            dir_path = f"{BASE_PATH}/{current_user.id}/{assign_task_id}"
            os.makedirs(dir_path, exist_ok=True)

            file_path = f"{dir_path}/{filename}"

            with open(file_path, "wb") as f:
                f.write(await file.read())     
        
            
        attachment_data = ReportAttachment(
            assign_task_id = assign_task_id,
            document_url = link if link else None,
            file_path = file_path if file else None,
            uploaded_by = current_user.id
        )
            
        try:
            document = await TaskAssignmentRepository.create(db, attachment_data)
            print(document)
            await db.commit()
            await db.refresh(document)
            return document
        except Exception:
            await db.rollback()
            raise
        
        
        
# class ReportService:

#     @staticmethod
#     async def get_submitted_tasks(db, current_user):
#         if current_user.role.role in ["admin", "super_admin"]:
#             return await ReportRepository.get_submitted_tasks(db)
#         return await ReportRepository.get_submitted_tasks(db, current_user.id)

#     @staticmethod
#     async def get_pending_reviews(db, current_user):
#         if current_user.role.role not in ["admin", "super_admin"]:
#             raise HTTPException(403, "Not allowed")

#         return await ReportRepository.get_pending_reviews(db)
    
    
# class AttachmentService:

#     @staticmethod
#     async def upload(db, current_user, report, payload):
#         if (
#             report.task_assignment.user_id != current_user.id
#             and current_user.role.role not in ["admin", "super_admin"]
#         ):
#             raise HTTPException(403, "Unauthorized")

#         attachment = ReportAttachment(
#             report_id=report.id,
#             document_url=payload.document_url,
#             uploaded_by=current_user.id
#         )

#         db.add(attachment)
#         await db.commit()
#         return attachment