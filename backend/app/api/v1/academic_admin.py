"""College scoped CRUD for catalogue, fees, and approved gallery assets."""
import hashlib
import uuid
from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import select

from app.api.v1.college_admin import CollegeTenantContext, get_college_context
from app.models.academic import AcademicChangeHistory, AcademicCourse, AcademicFee, CollegeGalleryImage
from app.schemas.common import APIResponse

router = APIRouter(prefix="/college-admin/academic", tags=["College Academic Catalogue"])


class CourseInput(BaseModel):
    course_name: str = Field(min_length=1, max_length=255)
    course_code: Optional[str] = None
    course_abbreviation: Optional[str] = None
    course_category: str = "OTHER"
    branch_name: Optional[str] = None
    program_level: Optional[str] = None
    duration: Optional[str] = None
    total_semesters: Optional[int] = Field(default=None, ge=1, le=16)
    eligibility: Optional[str] = None
    admission_information: Optional[str] = None
    syllabus_information: Optional[str] = None
    active_status: bool = False
    verification_status: str = "PENDING"


class FeeInput(BaseModel):
    course_id: uuid.UUID
    semester_number: Optional[int] = Field(default=None, ge=1, le=16)
    fee_amount: Decimal = Field(ge=0)
    currency: str = "INR"
    fee_type: str = "SEMESTER"
    academic_year: Optional[str] = None
    effective_from: Optional[date] = None
    effective_until: Optional[date] = None
    verification_status: str = "PENDING"
    source_page: Optional[int] = Field(default=None, ge=1)


class ImageInput(BaseModel):
    image_url: HttpUrl
    image_title: str = Field(min_length=1, max_length=255)
    image_description: Optional[str] = None
    image_category: str = "OTHER"
    facility_name: Optional[str] = None
    event_name: Optional[str] = None
    event_date: Optional[date] = None
    source_url: Optional[HttpUrl] = None
    verification_status: str = "PENDING"
    is_active: bool = False


def _history(context, entity_type, entity_id, action, data):
    context.session.add(AcademicChangeHistory(
        college_id=context.college.id, entity_type=entity_type, entity_id=entity_id,
        changed_by_user_id=context.user.id, change_action=action, change_data=data,
    ))


@router.get("/courses", response_model=APIResponse[list])
async def list_courses(context: CollegeTenantContext = Depends(get_college_context)):
    rows = (await context.session.execute(select(AcademicCourse).where(
        AcademicCourse.college_id == context.college.id).order_by(AcademicCourse.course_name))).scalars().all()
    return APIResponse(success=True, message="Courses loaded", data=[{c.name: getattr(row, c.name) for c in row.__table__.columns} for row in rows])


@router.post("/courses", response_model=APIResponse[dict])
async def create_course(payload: CourseInput, context: CollegeTenantContext = Depends(get_college_context)):
    row = AcademicCourse(college_id=context.college.id, **payload.model_dump())
    context.session.add(row)
    await context.session.flush()
    _history(context, "COURSE", row.id, "CREATE", payload.model_dump(mode="json"))
    await context.session.commit()
    await context.session.refresh(row)
    return APIResponse(success=True, message="Course saved", data={c.name: getattr(row, c.name) for c in row.__table__.columns})


@router.patch("/courses/{course_id}", response_model=APIResponse[dict])
async def update_course(course_id: uuid.UUID, payload: CourseInput, context: CollegeTenantContext = Depends(get_college_context)):
    row = await context.session.scalar(select(AcademicCourse).where(AcademicCourse.id == course_id, AcademicCourse.college_id == context.college.id))
    if not row:
        raise HTTPException(status_code=404, detail="Course not found")
    for key, value in payload.model_dump().items():
        setattr(row, key, value)
    _history(context, "COURSE", row.id, "UPDATE", payload.model_dump(mode="json"))
    await context.session.commit()
    await context.session.refresh(row)
    return APIResponse(success=True, message="Course updated", data={c.name: getattr(row, c.name) for c in row.__table__.columns})


@router.post("/fees", response_model=APIResponse[dict])
async def create_fee(payload: FeeInput, context: CollegeTenantContext = Depends(get_college_context)):
    course = await context.session.scalar(select(AcademicCourse).where(AcademicCourse.id == payload.course_id, AcademicCourse.college_id == context.college.id))
    if not course:
        raise HTTPException(status_code=404, detail="Course not found in this college")
    if payload.fee_type.upper() == "SEMESTER" and payload.semester_number is None:
        raise HTTPException(status_code=422, detail="Semester fees require a semester number")
    row = AcademicFee(college_id=context.college.id, **payload.model_dump())
    context.session.add(row)
    await context.session.flush()
    _history(context, "FEE", row.id, "CREATE", payload.model_dump(mode="json"))
    await context.session.commit()
    await context.session.refresh(row)
    return APIResponse(success=True, message="Fee schedule saved", data={c.name: getattr(row, c.name) for c in row.__table__.columns})


@router.get("/images", response_model=APIResponse[list])
async def list_images(context: CollegeTenantContext = Depends(get_college_context)):
    rows = (await context.session.execute(select(CollegeGalleryImage).where(
        CollegeGalleryImage.college_id == context.college.id).order_by(CollegeGalleryImage.created_at.desc()))).scalars().all()
    return APIResponse(success=True, message="Gallery loaded", data=[{c.name: getattr(row, c.name) for c in row.__table__.columns} for row in rows])


@router.post("/images", response_model=APIResponse[dict])
async def create_image(payload: ImageInput, context: CollegeTenantContext = Depends(get_college_context)):
    url = str(payload.image_url)
    digest = hashlib.sha256(url.encode()).hexdigest()
    row = CollegeGalleryImage(college_id=context.college.id, image_url=url,
        source_url=str(payload.source_url) if payload.source_url else None,
        content_hash=digest, **payload.model_dump(exclude={"image_url", "source_url"}))
    context.session.add(row)
    await context.session.flush()
    _history(context, "IMAGE", row.id, "CREATE", payload.model_dump(mode="json"))
    await context.session.commit()
    await context.session.refresh(row)
    return APIResponse(success=True, message="Gallery image saved", data={c.name: getattr(row, c.name) for c in row.__table__.columns})
