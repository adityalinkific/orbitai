import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import select
from app.modules.task.task_model import Task
from app.modules.auth.auth_model import User
from app.core.config import settings

async def main():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async with AsyncSession(engine) as session:
        task = await session.get(Task, 49)
        print('task49:', task)
        if task:
            print('task title', task.title, 'task_id', task.task_id, 'id', task.id)
        res = await session.execute(select(User).where(User.name.ilike('%rahul%')))
        user = res.scalars().first()
        print('user:', user)
        if user:
            print('user id', user.id, 'name', user.name, 'email', user.email)

if __name__ == '__main__':
    asyncio.run(main())
