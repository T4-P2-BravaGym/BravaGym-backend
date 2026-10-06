import os
from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models import (
    Booking,
    ClassSession,
    ClassType,
    DiscountCode,
    Exercise,
    MembershipPlan,
    Payment,
    Product,
    ProductCategory,
    Role,
    Routine,
    RoutineExercise,
    Subscription,
    TrainerProfile,
    User,
)
from app.models.enums import PaymentStatus, RoleName
from app.models.types import utc_now

DEMO_PASSWORD = os.environ.get("SEED_PASSWORD", "BravaDemo2026!")


def next_monday(today: date) -> date:
    return today + timedelta(days=7 - today.weekday())


def seed(db: Session) -> None:
    today = date.today()
    monday = next_monday(today)

    roles = {name: Role(name=name) for name in RoleName}
    db.add_all(roles.values())

    password_hash = hash_password(DEMO_PASSWORD)

    def new_user(email: str, first_name: str, last_name: str, role: RoleName) -> User:
        return User(
            email=email,
            password_hash=password_hash,
            first_name=first_name,
            last_name=last_name,
            role=roles[role],
        )

    superadmin = new_user("superadmin@example.com", "Sara", "Vidal", RoleName.SUPERADMIN)
    admin = new_user("admin@example.com", "Elena", "Ruiz", RoleName.ADMIN)
    ana = new_user("ana@example.com", "Ana", "Torres", RoleName.TRAINER)
    ana.trainer_profile = TrainerProfile(
        bio="Entrenadora de fuerza con 8 años de experiencia. Powerlifting y técnica.",
        specialty="Powerlifting",
    )
    marta = new_user("marta@example.com", "Marta", "Soler", RoleName.TRAINER)
    marta.trainer_profile = TrainerProfile(
        bio="Halterofilia y movilidad. Le encanta enseñar a levantar desde cero.",
        specialty="Halterofilia y movilidad",
    )
    lucia = new_user("lucia@example.com", "Lucía", "Gil", RoleName.MEMBER)
    carmen = new_user("carmen@example.com", "Carmen", "Ortega", RoleName.MEMBER)
    db.add_all([superadmin, admin, ana, marta, lucia, carmen])

    basic = MembershipPlan(
        name="Básico", description="Hasta 2 clases a la semana.", monthly_price_cents=3900
    )
    unlimited = MembershipPlan(
        name="Ilimitado", description="Todas las clases que quieras.", monthly_price_cents=5900
    )
    premium = MembershipPlan(
        name="Premium",
        description="Clases ilimitadas y entrenamiento personal.",
        monthly_price_cents=8900,
        includes_personal_training=True,
    )
    db.add_all([basic, unlimited, premium])

    lucia_subscription = Subscription(user=lucia, plan=premium, start_date=today)
    carmen_subscription = Subscription(user=carmen, plan=basic, start_date=today)
    db.add_all([lucia_subscription, carmen_subscription])

    db.add(
        Payment(
            user=lucia,
            subscription=lucia_subscription,
            base_amount_cents=premium.monthly_price_cents,
            final_amount_cents=premium.monthly_price_cents,
            status=PaymentStatus.PAID,
            paid_at=utc_now(),
        )
    )

    strength = ClassType(name="Fuerza total", description="Sentadilla, peso muerto y press.")
    mobility = ClassType(name="Movilidad y core", description="Movilidad, estabilidad y core.")
    olympic = ClassType(
        name="Taller de halterofilia",
        description="Técnica de arrancada y dos tiempos en grupo reducido.",
        extra_price_cents=1200,
    )
    personal = ClassType(
        name="Entrenamiento personal",
        description="Sesión individual de 60 minutos.",
        is_personal_training=True,
    )
    db.add_all([strength, mobility, olympic, personal])

    def starts_at(day_offset: int, hour: int, minute: int = 0) -> datetime:
        return datetime.combine(monday + timedelta(days=day_offset), time(hour, minute))

    sessions: list[ClassSession] = []
    for day in range(5):
        sessions.append(
            ClassSession(
                class_type=strength, trainer=ana, starts_at=starts_at(day, 7), capacity=12
            )
        )
        sessions.append(
            ClassSession(
                class_type=mobility,
                trainer=marta,
                starts_at=starts_at(day, 16),
                duration_minutes=45,
                capacity=15,
            )
        )
        evening_type = olympic if day in (1, 3) else strength
        sessions.append(
            ClassSession(
                class_type=evening_type,
                trainer=ana,
                starts_at=starts_at(day, 17, 30),
                capacity=8 if evening_type is olympic else 12,
            )
        )

    saturday, sunday = 5, 6
    sessions.append(
        ClassSession(class_type=strength, trainer=marta, starts_at=starts_at(saturday, 8), capacity=12)
    )
    sessions.append(
        ClassSession(
            class_type=mobility,
            trainer=ana,
            starts_at=starts_at(saturday, 9, 30),
            duration_minutes=45,
            capacity=15,
        )
    )
    sessions.append(
        ClassSession(
            class_type=mobility,
            trainer=marta,
            starts_at=starts_at(sunday, 9),
            duration_minutes=45,
            capacity=15,
        )
    )

    sessions.append(
        ClassSession(class_type=personal, trainer=marta, starts_at=starts_at(2, 10), capacity=1)
    )
    db.add_all(sessions)

    db.add(Booking(user=lucia, class_session=sessions[0]))

    exercises = {
        name: Exercise(name=name, muscle_group=group)
        for name, group in [
            ("Sentadilla trasera", "Piernas"),
            ("Peso muerto rumano", "Isquiotibiales"),
            ("Hip thrust", "Glúteos"),
            ("Press de banca", "Pecho"),
            ("Remo con barra", "Espalda"),
            ("Press militar", "Hombros"),
        ]
    }
    db.add_all(exercises.values())

    def slot(name: str, day: int, position: int, sets: int, reps: int, rest: int):
        return RoutineExercise(
            exercise=exercises[name],
            day_number=day,
            position=position,
            sets=sets,
            reps=reps,
            rest_seconds=rest,
        )

    db.add(
        Routine(
            member=lucia,
            trainer=ana,
            name="Fuerza base · 4 semanas",
            start_date=monday,
            notes="Subir peso cuando completes todas las series con buena técnica.",
            items=[
                slot("Sentadilla trasera", 1, 1, 4, 6, 150),
                slot("Hip thrust", 1, 2, 3, 10, 90),
                slot("Remo con barra", 1, 3, 3, 10, 90),
                slot("Peso muerto rumano", 2, 1, 4, 8, 120),
                slot("Press de banca", 2, 2, 4, 6, 120),
                slot("Press militar", 2, 3, 3, 8, 90),
            ],
        )
    )

    supplements = ProductCategory(name="Suplementos")
    clothing = ProductCategory(name="Ropa")
    accessories = ProductCategory(name="Accesorios")
    db.add_all(
        [
            Product(category=supplements, name="Proteína whey 1 kg", price_cents=3490, stock=20),
            Product(category=supplements, name="Creatina 300 g", price_cents=2290, stock=15),
            Product(category=clothing, name="Camiseta Brava", price_cents=2200, stock=30),
            Product(category=clothing, name="Leggings Brava", price_cents=3900, stock=25),
            Product(
                category=accessories, name="Cinturón de levantamiento", price_cents=4500, stock=10
            ),
            Product(category=accessories, name="Magnesio en bloque", price_cents=690, stock=40),
        ]
    )

    db.add(
        DiscountCode(
            code="BIENVENIDA10",
            percent_off=10,
            valid_from=today,
            valid_until=today + timedelta(days=90),
            max_uses=100,
            creator=admin,
        )
    )


def main() -> None:
    if get_settings().environment != "local":
        raise SystemExit("seed.py only runs with ENVIRONMENT=local. Never run it on real data.")

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        if db.scalar(select(Role.id).limit(1)) is not None:
            raise SystemExit("The database already has data. Delete brava.db and run it again.")
        seed(db)
        db.commit()

    print("Sample data created. Every user has the password:", DEMO_PASSWORD)
    print("Users: superadmin@, admin@, ana@ and marta@ (trainers), lucia@ and carmen@ (members)")
    print("       all of them @example.com")


if __name__ == "__main__":
    main()