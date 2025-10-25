from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.utils import timezone
from random import randint, choice, random
from datetime import timedelta, date

from schools.models import School
from users.models import Profile
from academics.models import ClassRoom, Section, Subject, StudentProfile, TeacherAssignment
from attendance.models import AttendanceRecord
from fees.models import FeeStructure, Payment

User = get_user_model()


class Command(BaseCommand):
    help = "Seed demo data for a given school: classrooms, sections, subjects, teachers, students, attendance, fees, payments, assignments"

    def add_arguments(self, parser):
        parser.add_argument('--school-id', type=int, help='Existing School ID to seed data for')
        parser.add_argument('--create-school', action='store_true', help='Create a new demo school if school-id not provided')
        parser.add_argument('--school-name', type=str, default='Demo School', help='Name for the demo school (if creating)')
        parser.add_argument('--students', type=int, default=20, help='Number of students to create')
        parser.add_argument('--teachers', type=int, default=5, help='Number of teachers to create')
        parser.add_argument('--classes', type=int, default=3, help='Number of classrooms to create')
        parser.add_argument('--sections-per-class', type=int, default=2, help='Number of sections per classroom')
        parser.add_argument('--subjects', type=int, default=4, help='Number of subjects to create')
        parser.add_argument('--attendance-days', type=int, default=7, help='Number of past days to create attendance for')
        parser.add_argument('--payments-days', type=int, default=30, help='Number of past days to create fee payments for')

    def handle(self, *args, **options):
        school_id = options.get('school_id')
        create_school = options.get('create_school')
        school_name = options.get('school_name')
        num_students = options.get('students')
        num_teachers = options.get('teachers')
        num_classes = options.get('classes')
        sections_per_class = options.get('sections_per_class')
        num_subjects = options.get('subjects')
        attendance_days = options.get('attendance_days')
        payments_days = options.get('payments_days')

        # Resolve or create school
        school = None
        if school_id:
            try:
                school = School.objects.get(id=school_id)
            except School.DoesNotExist:
                if create_school:
                    school = School.objects.create(id=school_id, name=school_name)
                    self.stdout.write(self.style.WARNING(f"Created new School with id={school.id} name={school.name}"))
                else:
                    raise CommandError(f"School with id={school_id} does not exist. Use --create-school to create it.")
        else:
            if create_school:
                school = School.objects.create(name=school_name)
                self.stdout.write(self.style.WARNING(f"Created new School with id={school.id} name={school.name}"))
            else:
                raise CommandError("Provide --school-id or use --create-school to create a demo school.")

        # Create classrooms
        classrooms = []
        for i in range(1, num_classes + 1):
            cls, _ = ClassRoom.objects.get_or_create(school=school, name=f"Class {i}")
            classrooms.append(cls)
        self.stdout.write(self.style.SUCCESS(f"Classrooms: {len(classrooms)}"))

        # Create sections per classroom (A, B, C ...)
        section_names = [chr(ord('A') + i) for i in range(sections_per_class)]
        sections = []
        for cls in classrooms:
            for sname in section_names:
                sec, _ = Section.objects.get_or_create(classroom=cls, name=sname)
                sections.append(sec)
        self.stdout.write(self.style.SUCCESS(f"Sections: {len(sections)}"))

        # Create subjects
        subjects = []
        for i in range(1, num_subjects + 1):
            sub, _ = Subject.objects.get_or_create(school=school, name=f"Subject {i}")
            subjects.append(sub)
        self.stdout.write(self.style.SUCCESS(f"Subjects: {len(subjects)}"))

        # Create teachers
        teachers = []
        for i in range(1, num_teachers + 1):
            username = f"teacher{i}_school{school.id}"
            user, _ = User.objects.get_or_create(username=username, defaults={"first_name": f"Teacher{i}", "last_name": "Demo"})
            Profile.objects.get_or_create(user=user, defaults={"school": school, "role": "teacher"})
            teachers.append(user)
        self.stdout.write(self.style.SUCCESS(f"Teachers: {len(teachers)}"))

        # Create students and student profiles
        students = []
        for i in range(1, num_students + 1):
            username = f"student{i}_school{school.id}"
            user, _ = User.objects.get_or_create(username=username, defaults={"first_name": f"Student{i}", "last_name": "Demo"})
            Profile.objects.get_or_create(user=user, defaults={"school": school, "role": "student"})
            cls = choice(classrooms) if classrooms else None
            sec = None
            if cls:
                sec_list = list(cls.sections.all())
                sec = choice(sec_list) if sec_list else None
            sp, _ = StudentProfile.objects.get_or_create(user=user, defaults={
                "school": school,
                "classroom": cls,
                "section": sec,
                "roll_number": str(1000 + i)
            })
            students.append(sp)
        self.stdout.write(self.style.SUCCESS(f"Students: {len(students)}"))

        # Create teacher assignments (random mapping)
        assignments = []
        for t in teachers:
            for cls in classrooms:
                assigned_subject = choice(subjects) if subjects else None
                if assigned_subject:
                    sec_list = list(cls.sections.all())
                    sec = choice(sec_list) if sec_list else None
                    ta, _ = TeacherAssignment.objects.get_or_create(
                        teacher=t,
                        subject=assigned_subject,
                        classroom=cls,
                        section=sec,
                    )
                    assignments.append(ta)
        self.stdout.write(self.style.SUCCESS(f"Assignments: {len(assignments)}"))

        # Fee structures
        monthly_fee, _ = FeeStructure.objects.get_or_create(school=school, name="Monthly Fee", defaults={"amount": 1000})
        exam_fee, _ = FeeStructure.objects.get_or_create(school=school, name="Exam Fee", defaults={"amount": 500})

        # Payments in the last N days
        payments_created = 0
        today = date.today()
        for sp in students:
            # Each student may have 1-3 payments randomly over the period
            for _ in range(randint(1, 3)):
                days_ago = randint(0, max(0, payments_days - 1))
                pay_date = today - timedelta(days=days_ago)
                fee = choice([monthly_fee, exam_fee])
                amount = fee.amount
                # Create payments directly to allow multiple payments per day/fee
                Payment.objects.create(
                    student=sp,
                    fee=fee,
                    date=pay_date,
                    amount=amount,
                    reference=f"PAY-{sp.id}-{fee.id}-{pay_date.isoformat()}-{randint(1000,9999)}"
                )
                payments_created += 1
        self.stdout.write(self.style.SUCCESS(f"Payments created: {payments_created}"))

        # Attendance for last attendance_days
        attendance_created = 0
        for d in range(attendance_days):
            day = today - timedelta(days=d)
            for sp in students:
                present = random() > 0.1  # 90% present
                AttendanceRecord.objects.get_or_create(
                    school=school,
                    student=sp,
                    date=day,
                    defaults={"present": present}
                )
                attendance_created += 1
        self.stdout.write(self.style.SUCCESS(f"Attendance records created: {attendance_created}"))

        self.stdout.write(self.style.SUCCESS("Demo data seeding complete."))
