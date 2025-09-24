from fastapi import APIRouter

router = APIRouter()


@router.get('/')
async def get_all():
    return {'message': 'all course'}


@router.get('/info/{course_id}')
async def info_by_id(course_id: str):
    return {'message info': course_id}


@router.get('/download/{course_id}')
async def download_by_id(course_id: str):
    return {'message download': course_id}


@router.get('/progress/{course_id}')
async def progress_by_id(course_id: str):
    return {'message progress': course_id}


@router.post('progress/{course_id}')
async def progress_by_id_post(course_id: str):
    return {'new message progress': course_id}
