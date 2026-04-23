from app.modules.task.task_services import TaskService, TaskAssignService, AssignTaskReportServices
from app.core.schema import Response


class TaskController:

    async def _create_task(db, data, current_user):
        await TaskService.create_task(db, data, current_user)
        return await Response._success_response("Task created successfully")


    async def _update_task(db, task_id, data):
        await TaskService.update_task(db, task_id, data)
        return await Response._success_response("Task updated successfully")


    async def _delete_task(db, task_id):
        await TaskService.delete_task(db, task_id)
        return await Response._success_response("Task deleted successfully")


    async def _get_all_task_detail(db):
        result = await TaskService.get_all_tasks(db)
        tasks = result.get("data", []) if isinstance(result, dict) else result
        data = [
            {
                'id': task.get('id') if isinstance(task, dict) else task.id,
                'task_id': task.get('task_id') if isinstance(task, dict) else task.task_id,
                'title': task.get('title') if isinstance(task, dict) else task.title,
                'description': task.get('description') if isinstance(task, dict) else task.description,
                'project_id': task.get('project_id') if isinstance(task, dict) else task.project_id,
                'department_id': task.get('department_id') if isinstance(task, dict) else task.department_id,
                'task_type': task.get('task_type') if isinstance(task, dict) else task.task_type,
                'priority': task.get('priority') if isinstance(task, dict) else task.priority,
                'due_date': task.get('due_date') if isinstance(task, dict) else task.due_date,
                'created_by': task.get('created_by') if isinstance(task, dict) else task.created_by,
                'created_at': task.get('created_at') if isinstance(task, dict) else task.created_at,
                'updated_at': task.get('updated_at') if isinstance(task, dict) else task.updated_at
            } for task in tasks
        ]
        return await Response._success_response("Task details fetched successfully", data)


    async def _get_task_detail(db, task_id, current_user):
        task = await TaskService.get_task_detail(db, task_id)
        data = {
            'id': task.id,
            'task_id': task.task_id,
            'title': task.title,
            'description': task.description,
            'project_id': task.project_id,
            'department_id': task.department_id,
            'task_type': task.task_type,
            'priority': task.priority,
            'due_date': task.due_date,
            'created_by': task.created_by,
            'created_at': task.created_at,
            'updated_at': task.updated_at
        }        
        return await Response._success_response("Task details fetched successfully", data)


class TaskAssignController:
    @staticmethod
    async def _assign_task(db, data, current_user):
        result = await TaskAssignService._assign_task(db, data, current_user)
        data = {
            'id' : result.id,
            'task_id': result.task_id,
            'user_id': result.user_id
        }
        return await Response._success_response("Task assigned successfully", data)
    
    
    @staticmethod
    async def _update_task_assign(db, assign_task_id, data, current_user):
        await TaskAssignService._update_task_assign(db, assign_task_id, data, current_user)
        return await Response._success_response("Task assignment updated successfully")
    
    
    @staticmethod
    async def _delete_task_assign(db, assign_task_id):
        await TaskAssignService._delete_task_assign(db, assign_task_id)
        return await Response._success_response("Task assignment deleted successfully")
    
    @staticmethod
    async def _update_task_status(db, assign_task_id, data):
        await TaskAssignService._update_task_status(db, assign_task_id, data)
        return await Response._success_response("Assigned task status updated successfully")

    @staticmethod
    async def _get_task_assign_detail(db, assign_task_id, current_user):
        assigned_task = await TaskAssignService._get_task_assign_detail(db, assign_task_id, current_user)
        data = {
            'id': assigned_task.id,
            'task_id': assigned_task.task_id,
            'user_id': assigned_task.user_id,
            'assigned_at': assigned_task.assigned_at,
            'assigned_by': assigned_task.assigned_by,
            'due_date': assigned_task.due_date,
            'status': assigned_task.status,
            'created_at': assigned_task.created_at,
            'updated_at': assigned_task.updated_at
        }
        return await Response._success_response("Assigned task details fetched successfully", data)
   
   
    @staticmethod
    async def _get_all_task_assign_detail(db, current_user):
        assigned_tasks = await TaskAssignService._get_all_task_assign_detail(db, current_user)
        data = [
            {
                'id': assigned_task.id,
                'task_id': assigned_task.task_id,
                'user_id': assigned_task.user_id,
                'assigned_at': assigned_task.assigned_at,
                'assigned_by': assigned_task.assigned_by,
                'due_date': assigned_task.due_date,
                'status': assigned_task.status,
                'created_at': assigned_task.created_at,
                'updated_at': assigned_task.updated_at
            } for assigned_task in assigned_tasks
        ]
        return await Response._success_response("All assigned task details fetched successfully", data)
 
 
 
class AssignTaskReportController:
    
    @staticmethod
    async def _get_pending_reports(db, current_user):
        pending_reports = await AssignTaskReportServices._get_pending_report(db, current_user)
        data = [
            {
                'id': pending_report.id,
                'task_id': pending_report.task_id,
                'user_id': pending_report.user_id,
                'assigned_at': pending_report.assigned_at,
                'assigned_by': pending_report.assigned_by,
                'due_date': pending_report.due_date,
                'status': pending_report.status,
                'created_at': pending_report.created_at,
                'updated_at': pending_report.updated_at
            } for pending_report in pending_reports
        ]
        return await Response._success_response("Pending reports fetched successfully!", data)
      
        
    async def _get_pending_report_by_id(assign_task_id: int, db, current_user):
        pending_report = await AssignTaskReportServices._get_pending_report_by_id(db, assign_task_id, current_user)
        data = {
            'id': pending_report.id,
            'task_id': pending_report.task_id,
            'user_id': pending_report.user_id,
            'assigned_at': pending_report.assigned_at,
            'assigned_by': pending_report.assigned_by,
            'due_date': pending_report.due_date,
            'status': pending_report.status,
            'created_at': pending_report.created_at,
            'updated_at': pending_report.updated_at
        }
        return await Response._success_response("Pending reports fetched successfully!", data)
        
        
    async def _submit_report(data, db, current_user):
        await AssignTaskReportServices._submit_report(data, db, current_user)
        return await Response._success_response('Task is submitted')
        
    async def _upload_document(assign_task_id, link, file, db, current_user):
        await AssignTaskReportServices._upload_document(assign_task_id, link, file, db, current_user)
        return await Response._success_response('Document uploaded successfully.')