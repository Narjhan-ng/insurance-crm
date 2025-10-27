"""
Seed script to create initial users for testing
Run: python -m scripts.seed_users
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.database import SessionLocal
from app.models.user import User, UserRole
from app.services.auth_service import AuthService


def create_initial_users():
    """
    Create initial users for testing the authentication system.

    Creates:
    - 1 Admin
    - 1 Head of Sales
    - 1 Manager
    - 2 Brokers
    - 1 Affiliate

    All with password: "password123" (CHANGE IN PRODUCTION!)
    """
    db = SessionLocal()

    try:
        # Check if users already exist
        existing_users = db.query(User).count()
        if existing_users > 0:
            print(f"⚠️  Database already has {existing_users} users.")
            response = input("Do you want to continue and add more users? (y/n): ")
            if response.lower() != 'y':
                print("Aborted.")
                return

        users_to_create = [
            {
                "username": "admin",
                "email": "admin@insurancecrm.com",
                "password": "password123",
                "role": UserRole.ADMIN,
                "supervisor_id": None
            },
            {
                "username": "head_sales",
                "email": "headsales@insurancecrm.com",
                "password": "password123",
                "role": UserRole.HEAD_OF_SALES,
                "supervisor_id": None  # Reports to admin (will set later)
            },
            {
                "username": "manager1",
                "email": "manager1@insurancecrm.com",
                "password": "password123",
                "role": UserRole.MANAGER,
                "supervisor_id": None  # Reports to head_sales (will set later)
            },
            {
                "username": "broker1",
                "email": "broker1@insurancecrm.com",
                "password": "password123",
                "role": UserRole.BROKER,
                "supervisor_id": None  # Reports to manager1 (will set later)
            },
            {
                "username": "broker2",
                "email": "broker2@insurancecrm.com",
                "password": "password123",
                "role": UserRole.BROKER,
                "supervisor_id": None  # Reports to manager1 (will set later)
            },
            {
                "username": "affiliate1",
                "email": "affiliate1@insurancecrm.com",
                "password": "password123",
                "role": UserRole.AFFILIATE,
                "supervisor_id": None  # Reports to broker1 (will set later)
            }
        ]

        created_users = {}

        # Create users
        for user_data in users_to_create:
            # Check if user already exists
            existing = db.query(User).filter(User.username == user_data["username"]).first()
            if existing:
                print(f"⚠️  User '{user_data['username']}' already exists, skipping...")
                created_users[user_data["username"]] = existing
                continue

            # Hash password
            password_hash = AuthService.get_password_hash(user_data["password"])

            # Create user
            user = User(
                username=user_data["username"],
                email=user_data["email"],
                password_hash=password_hash,
                role=user_data["role"],
                is_active=True
            )

            db.add(user)
            db.flush()  # Get ID without committing

            created_users[user_data["username"]] = user

            print(f"✅ Created user: {user.username} ({user.role.value}) - ID: {user.id}")

        # Set supervisor relationships
        if "admin" in created_users and "head_sales" in created_users:
            created_users["head_sales"].supervisor_id = created_users["admin"].id

        if "head_sales" in created_users and "manager1" in created_users:
            created_users["manager1"].supervisor_id = created_users["head_sales"].id

        if "manager1" in created_users:
            if "broker1" in created_users:
                created_users["broker1"].supervisor_id = created_users["manager1"].id
            if "broker2" in created_users:
                created_users["broker2"].supervisor_id = created_users["manager1"].id

        if "broker1" in created_users and "affiliate1" in created_users:
            created_users["affiliate1"].supervisor_id = created_users["broker1"].id

        # Commit all changes
        db.commit()

        print("\n" + "="*60)
        print("✅ Initial users created successfully!")
        print("="*60)
        print("\n📝 Login Credentials (ALL USERS USE SAME PASSWORD):")
        print("-" * 60)
        print(f"{'Username':<20} {'Role':<20} {'Password':<20}")
        print("-" * 60)

        for username, user in created_users.items():
            print(f"{username:<20} {user.role.value:<20} password123")

        print("-" * 60)
        print("\n⚠️  WARNING: Change passwords in production!")
        print("\n🔗 Test login at: http://localhost:8000/docs")
        print("   Use 'Try it out' on POST /api/v1/auth/login")
        print("\n🔑 Example login request:")
        print('   username: "admin"')
        print('   password: "password123"')
        print("\n")

    except Exception as e:
        print(f"\n❌ Error creating users: {e}")
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    print("🌱 Seeding initial users...")
    print("-" * 60)
    create_initial_users()
